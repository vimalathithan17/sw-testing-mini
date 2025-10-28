from app.utils import sanitize_input


def test_sanitize_removes_script_tags():
    s = "<script>alert(1)</script>Bob"
    out = sanitize_input(s)
    assert "script" not in out.lower()
    assert "bob" in out.lower()


def test_sanitize_strips_sql_meta():
    s = "Alice; DROP TABLE users; --"
    out = sanitize_input(s)
    # separators removed, core words may remain but punctuation should be gone
    assert ";" not in out
    assert "--" not in out
    assert "drop" in out.lower()