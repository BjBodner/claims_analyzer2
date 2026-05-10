import difflib
from typing import List, Tuple, Dict, Any, Optional

def compute_diff(text_a: str, text_b: str) -> List[Dict[str, Any]]:
    """
    Computes a line-by-line diff between two texts.
    Returns a list of blocks, each containing the type of change and the lines involved.
    """
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()
    
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    result = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append({
                "type": "equal", 
                "a_lines": lines_a[i1:i2], 
                "b_lines": lines_b[j1:j2]
            })
        elif tag == "replace":
            # Treat replace as a removal followed by an addition
            result.append({
                "type": "remove", 
                "a_lines": lines_a[i1:i2], 
                "b_lines": []
            })
            result.append({
                "type": "add", 
                "a_lines": [], 
                "b_lines": lines_b[j1:j2]
            })
        elif tag == "delete":
            result.append({
                "type": "remove", 
                "a_lines": lines_a[i1:i2], 
                "b_lines": []
            })
        elif tag == "insert":
            result.append({
                "type": "add", 
                "a_lines": [], 
                "b_lines": lines_b[j1:j2]
            })
            
    return result

def render_diff_html(diff: List[Dict[str, Any]], mode: str = "split") -> Any:
    """
    Renders the diff as HTML.
    Modes: 
    - 'split': returns (left_html, right_html)
    - 'unified': returns single html string
    """
    # Premium colors for dark mode glassmorphism
    colors = {
        "add_bg": "rgba(40, 167, 69, 0.15)",
        "add_text": "#2fb344",
        "add_border": "#28a745",
        "remove_bg": "rgba(220, 53, 69, 0.15)",
        "remove_text": "#d63939",
        "remove_border": "#dc3545",
        "equal_bg": "transparent",
        "equal_text": "#E0E0E0",
        "equal_border": "transparent"
    }

    style = """
    <style>
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.5;
        }
        .diff-row td {
            padding: 2px 8px;
            white-space: pre-wrap;
            word-break: break-all;
            vertical-align: top;
        }
        .diff-line-num {
            width: 40px;
            color: #666;
            text-align: right;
            user-select: none;
            border-right: 1px solid rgba(255,255,255,0.1);
            padding-right: 10px !important;
        }
    </style>
    """

    if mode == "unified":
        rows = []
        line_a = 1
        line_b = 1
        for block in diff:
            t = block["type"]
            a_lines = block["a_lines"]
            b_lines = block["b_lines"]
            
            if t == "equal":
                for line in a_lines:
                    rows.append(f'<tr class="diff-row" style="background:{colors["equal_bg"]}; color:{colors["equal_text"]}"><td class="diff-line-num">{line_a}</td><td class="diff-line-num">{line_b}</td><td>  {line.rstrip()}</td></tr>')
                    line_a += 1
                    line_b += 1
            elif t == "remove":
                for line in a_lines:
                    rows.append(f'<tr class="diff-row" style="background:{colors["remove_bg"]}; color:{colors["remove_text"]}; border-left: 3px solid {colors["remove_border"]}"><td class="diff-line-num">{line_a}</td><td class="diff-line-num"></td><td>- {line.rstrip()}</td></tr>')
                    line_a += 1
            elif t == "add":
                for line in b_lines:
                    rows.append(f'<tr class="diff-row" style="background:{colors["add_bg"]}; color:{colors["add_text"]}; border-left: 3px solid {colors["add_border"]}"><td class="diff-line-num"></td><td class="diff-line-num">{line_b}</td><td>+ {line.rstrip()}</td></tr>')
                    line_b += 1
        
        return f'{style}<table class="diff-table">{"".join(rows)}</table>'

    else:
        # Split view
        left_rows = []
        right_rows = []
        line_a = 1
        line_b = 1
        
        for block in diff:
            t = block["type"]
            a_lines = block["a_lines"]
            b_lines = block["b_lines"]
            
            max_len = max(len(a_lines), len(b_lines))
            
            for i in range(max_len):
                la = a_lines[i].rstrip() if i < len(a_lines) else None
                lb = b_lines[i].rstrip() if i < len(b_lines) else None
                
                # Left side (A)
                if la is not None:
                    bg = colors["remove_bg"] if t == "remove" else colors["equal_bg"]
                    txt = colors["remove_text"] if t == "remove" else colors["equal_text"]
                    brd = colors["remove_border"] if t == "remove" else colors["equal_border"]
                    border_style = f"border-left: 3px solid {brd}" if t == "remove" else ""
                    left_rows.append(f'<tr class="diff-row" style="background:{bg}; color:{txt}; {border_style}"><td class="diff-line-num">{line_a}</td><td>{la}</td></tr>')
                    line_a += 1
                else:
                    left_rows.append(f'<tr class="diff-row"><td class="diff-line-num"></td><td>&nbsp;</td></tr>')
                
                # Right side (B)
                if lb is not None:
                    bg = colors["add_bg"] if t == "add" else colors["equal_bg"]
                    txt = colors["add_text"] if t == "add" else colors["equal_text"]
                    brd = colors["add_border"] if t == "add" else colors["equal_border"]
                    border_style = f"border-left: 3px solid {brd}" if t == "add" else ""
                    right_rows.append(f'<tr class="diff-row" style="background:{bg}; color:{txt}; {border_style}"><td class="diff-line-num">{line_b}</td><td>{lb}</td></tr>')
                    line_b += 1
                else:
                    right_rows.append(f'<tr class="diff-row"><td class="diff-line-num"></td><td>&nbsp;</td></tr>')
                    
        left_html = f'{style}<table class="diff-table">{"".join(left_rows)}</table>'
        right_html = f'{style}<table class="diff-table">{"".join(right_rows)}</table>'
        return left_html, right_html
