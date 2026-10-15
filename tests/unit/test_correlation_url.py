"""Unit tests for canonical URL normalization (B12.3).

Follows master.md R8, R11 and 10_CORRELATION.md §B12.3:
- Lowercase scheme/host
- Strips www. prefix
- Strips default ports (:80, :443)
- Strips fragments (#...)
- Trailing slash on path stripped
- Drops advertising/tracking params (utm_*, fbclid, gclid, etc.)
- Path remains significant: same host + different path => NO link
"""

import pytest
from forensic.correlation.artifacts import normalize_url


def test_url_normalization_cross_platform_pair():
    """Verify identical URL with differing tracking parameters normalizes to the same value."""
    wa_url = "https://www.example.test/case-files/archive-2026?utm_source=whatsapp&utm_medium=chat"
    tg_url = "https://example.test/case-files/archive-2026?utm_source=telegram&utm_campaign=audit"

    norm_wa = normalize_url(wa_url)
    norm_tg = normalize_url(tg_url)

    assert norm_wa is not None
    assert norm_tg is not None
    assert norm_wa == norm_tg
    assert norm_wa == "https://example.test/case-files/archive-2026"


def test_url_normalization_path_significance():
    """Verify path is significant: same domain host with different paths must NOT match."""
    url1 = "https://example.test/case-files/folder-alpha"
    url2 = "https://example.test/case-files/folder-beta"

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)

    assert norm1 != norm2
    assert norm1 == "https://example.test/case-files/folder-alpha"
    assert norm2 == "https://example.test/case-files/folder-beta"


@pytest.mark.parametrize("raw_url, expected", [
    ("HTTP://WWW.EXAMPLE.COM:80/path/to/page/", "http://example.com/path/to/page"),
    ("https://example.com:443/doc#heading1", "https://example.com/doc"),
    ("https://example.com/search?q=test&utm_source=twitter&fbclid=123", "https://example.com/search?q=test"),
    ("https://www.google.com/?gclid=abc&ref=share", "https://google.com/"),
    ("ftp://example.com/file", None),  # Non-http/https ignored
    ("", None),
])
def test_url_normalization_table(raw_url: str, expected: str):
    res = normalize_url(raw_url)
    assert res == expected
