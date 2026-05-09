# Working with the EPO OPS v3.2 API — Lessons Learned

This document captures every issue we hit while building the Patent Family Claims Explorer against EPO Open Patent Services (OPS) v3.2, plus concrete recommendations for the next time someone integrates this API.

---

## 1. Overview

EPO OPS v3.2 is the European Patent Office's REST API for patent bibliographic data, family relationships, full text, claims, descriptions, and images. We used two endpoints:

- `GET /rest-services/family/publication/docdb/{country}.{number}.{kind}/biblio` — INPADOC family across jurisdictions.
- `GET /rest-services/published-data/publication/docdb/{country}.{number}.{kind}/claims` — claims text per family member.

All calls go through a Supabase Edge Function (`epo-ops`) so the consumer key/secret never reach the browser.

---

## 2. Authentication

- OAuth2 **client_credentials** grant. POST to `https://ops.epo.org/3.2/auth/accesstoken` with HTTP Basic auth (`btoa("key:secret")`) and body `grant_type=client_credentials`.
- Tokens last ~20 minutes (`expires_in` ≈ 1200s). Cache in-memory per isolate, refresh ~60s before expiry, and clear on any 401.
- Credentials **must** live as backend secrets (`EPO_OPS_CONSUMER_KEY`, `EPO_OPS_CONSUMER_SECRET`). Never ship them to the browser.
- The proxy edge function needs `verify_jwt = false` in `supabase/config.toml` so the public app can call it without auth.

**Gotcha:** edge function isolates die and respawn, so token caching is best-effort. With heavy traffic, consider a shared cache (KV / Postgres) to avoid hammering the auth endpoint.

---

## 3. Publication number normalization

Users paste publication numbers in many shapes:

- `WO2020227475A1`
- `WO 2020/227475 A1`
- `wo-2020-227475-a1`
- `EP1000000A1`, `US9876543B2`, …

OPS DOCDB format requires three parts joined by dots: `country.number.kind` (e.g. `WO.2020227475.A1`). Our normalizer:

```ts
input.replace(/[\s/_,.\-]/g, "").toUpperCase()
     .match(/^([A-Z]{2})(\d+)([A-Z]\d?)?$/)
```

**Gotcha — kind code:** if the user omits the kind, OPS often returns 404. We default to `A`, but that's wrong for many publications (`B1`, `B2`, `T3`, `U1`, …).

**Recommendation:** build a kind-code resolver that lists all kinds available for a number (via the biblio endpoint) and lets the user pick, instead of guessing.

---

## 4. Family endpoint quirks

- Response is deeply nested: `ops:world-patent-data → ops:patent-family → ops:family-member`.
- Each member carries multiple `document-id` entries (`docdb`, `epodoc`, `original`). **Only `docdb` has the clean country/number/kind tuple** suitable for re-querying OPS.
- All scalar values are wrapped as `{ "$": "..." }` objects, so every leaf access needs a `textOf` helper.
- Shapes vary slightly per response — we ended up writing a recursive `collectByKey` walker rather than relying on fixed paths.
- The same publication can appear more than once across `exchange-document` blocks; dedupe by composed publication string.
- **"Has claims" is not a first-class field.** We currently sniff for the substring `"claims"` in the member's JSON blob, which is unreliable.

**Recommendation:** lazily probe `/published-data/.../claims` (HEAD or a tiny GET) per member, or use the OPS `links`/`constituents` data, instead of substring sniffing.

---

## 5. Claims endpoint quirks (the biggest source of bugs)

This is where we lost the most time.

- The response can be JSON or XML. Even when you ask for JSON, **claim text often arrives as one giant string in a single `claim-text` node**, with all numbered claims concatenated and only `\n` separators — not as one element per claim.
- Some jurisdictions prefix the body with a header line that must be stripped: `CLAIMS`, `REVENDICATIONS`, `ANSPRÜCHE`, `PATENTANSPRÜCHE`, `WHAT IS CLAIMED IS:`.
- The `@num` attribute on `<claim>` is unreliable (sometimes missing, sometimes wrong, sometimes only present on the first element). We re-split the blob with regex `/(^|\n)\s*(\d{1,4})\.\s+/g`.
- Sub-claims and paragraphs are nested inside `<claim-text>` recursively. A flat `.text` extraction loses content — you need a `deepText` walker that recurses through arrays, `$` leaves, and child objects.
- Whitespace must be normalized: collapse runs of spaces/tabs to one, collapse 3+ newlines to two.
- **404 on claims is common** (claims not yet published for that family member). Treat it as `{ notFound: true }`, not as a hard error.
- Languages differ across family members. OPS exposes `@lang` on the `claims` node, but does not translate. A FR ↔ EN diff is not meaningful without translation.

**Recommendation:** treat the claims splitter/normalizer as a **separate, well-tested module** with golden fixtures from EP, WO, US, JP, CN, KR. It is by far the biggest correctness risk.

---

## 6. Error handling and quotas

- Rate limits return HTTP 403 or 429 with an `X-RejectionReason` header (e.g. `IndividualQuotaPerHour`, `IndividualQuotaPerWeek`). We currently only map by status code; we should parse this header and surface a clear "quota exceeded, retry in N minutes" toast.
- 401 means the access token expired or was revoked. Clear cache and retry once.
- 404 from family vs claims means very different things (bad publication vs no claims published for that member). Keep them distinct in the API surface — don't collapse to a generic "not found".
- OPS error bodies are XML even when you asked for JSON. Don't `JSON.parse` blindly — keep the raw text for the error message.

**Recommendation:** also track `X-Throttling-Control` to back off proactively before you get rejected.

---

## 7. CORS and edge function plumbing

- Standard `Access-Control-Allow-Origin: *` plus `Access-Control-Allow-Headers: authorization, x-client-info, apikey, content-type`.
- **All responses must include CORS headers — including error responses** — otherwise the browser swallows the body and you see only a generic "Failed to fetch".
- Handle `OPTIONS` preflight by returning 204/200 with the CORS headers and no body.

---

## 8. Testing

- Live OPS tests must be **gated on credentials being present** (`Deno.env.get("EPO_OPS_CONSUMER_KEY")`); otherwise CI fails for contributors without keys.
- Pin one stable patent for live tests. We chose **`WO2020227475A1`** because it has a rich multi-jurisdiction family (CA, US, EP, CN, JP, …) and published claims.
- Frontend tests should mock the **edge function** boundary (not OPS itself) — keeps them fast, offline, and free of quota concerns.
- Add at least one negative test (`NOTAPATENT` → 400) and one token-cache test (two consecutive calls, one auth request).

---

## 9. Recommendations for next time

1. **Use a typed OPS client where possible.** The Python `python-epo-ops-client` library models the auth, caching, and parsing concerns. If you're in Node/Deno, port its parsing layer rather than re-deriving it from blank fetch calls.
2. **Prefer XML + a real XML parser** over the JSON projection. The JSON shape is lossy and inconsistent across endpoints — `claim-text` is the worst offender. XML is what OPS actually emits internally.
3. **Build an `OpsDocument` normalizer** that returns `{ country, number, kind, date, lang }` regardless of which endpoint produced it. Every other module should consume this, not raw OPS JSON.
4. **Add a persistent cache** (Supabase table or KV) keyed by `country.number.kind + endpoint`. OPS quotas are tight, and family/claims data changes rarely. Cache for hours or days.
5. **Resolve kind codes explicitly.** Don't guess `A` — query the biblio endpoint and let the user choose when ambiguous.
6. **Surface throttling state** (`X-RejectionReason`, `X-Throttling-Control`) in the UI, and back off automatically before hitting hard rejections.
7. **Make language/translation a first-class concern.** Either pair with EPO Patent Translate or an LLM, or clearly mark cross-language diffs as "languages differ — diff is not semantically meaningful".
8. **Treat the claims splitter as its own module with golden fixtures** from EP, WO, US, JP, CN, KR. Jurisdiction shape drift is the #1 source of regressions.
9. **Write contract tests** against ~6 canonical publications spanning the major offices, run nightly, so you notice OPS-side shape changes before users do.
10. **Always proxy through a backend.** The consumer key/secret cannot live in the browser, and the proxy is also the natural place for caching, throttling, retry, and normalization.

---

## Appendix: endpoints we used

| Purpose | Method + Path |
|---|---|
| Auth token | `POST /3.2/auth/accesstoken` (Basic auth, `grant_type=client_credentials`) |
| Family | `GET /3.2/rest-services/family/publication/docdb/{C}.{N}.{K}/biblio` |
| Claims | `GET /3.2/rest-services/published-data/publication/docdb/{C}.{N}.{K}/claims` |

Useful but unused here: `/biblio`, `/abstract`, `/description`, `/full-cycle`, `/images`, `/equivalents`, and the `/published-data/search` endpoint for free-text/CQL queries.
