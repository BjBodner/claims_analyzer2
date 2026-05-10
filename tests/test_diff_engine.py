import pytest
from diff_engine import compute_diff, render_diff_html

def test_compute_diff_basic():
    text_a = "Line 1\nLine 2\nLine 3"
    text_b = "Line 1\nLine 2 changed\nLine 3"
    diff = compute_diff(text_a, text_b)
    
    # Expect: equal, remove, add, equal
    types = [d["type"] for d in diff]
    assert "remove" in types
    assert "add" in types
    assert "equal" in types

def test_compute_diff_addition():
    text_a = "Line 1"
    text_b = "Line 1\nLine 2"
    diff = compute_diff(text_a, text_b)
    assert diff[-1]["type"] == "add"

def test_compute_diff_removal():
    text_a = "Line 1\nLine 2"
    text_b = "Line 1"
    diff = compute_diff(text_a, text_b)
    assert diff[-1]["type"] == "remove"

def test_render_unified_html():
    text_a = "Old"
    text_b = "New"
    diff = compute_diff(text_a, text_b)
    html = render_diff_html(diff, mode="unified")
    assert "<table" in html
    assert "Old" in html
    assert "New" in html

def test_render_split_html():
    text_a = "Old"
    text_b = "New"
    diff = compute_diff(text_a, text_b)
    left, right = render_diff_html(diff, mode="split")
    assert "Old" in left
    assert "New" in right
