import pytest

from safevision.application.evidence_url import public_evidence_url


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/evidencias/0001.jpg",
        "http://example.com/evidencias/0001.jpg",
        "HTTPS://example.com/video.mp4",
        "https://example.com:8443/x.jpg?firma=abc#t=3",
        "https://192.0.2.10/x.jpg",
        "https://[2001:db8::1]/x.jpg",
    ],
)
def test_absolute_http_urls_with_a_host_are_published_unchanged(url):
    assert public_evidence_url(url) == url


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "data:image/png;base64,iVBORw0KGgo=",
        "C:\\evidencias\\x.jpg",
        "/evidencias/x.jpg",
        "evidencias/x.jpg",
        "file:///evidencias/x.jpg",
        "ftp://example.com/x.jpg",
        "//example.com/x.jpg",
        "https://",
        "https:///x.jpg",
        "http:example.com/x.jpg",
        "https://:443/x.jpg",
        "https://example.com/a b.jpg",
        " https://example.com/x.jpg",
        "https://example.com/x.jpg\n",
        "https://example.com/\x00.jpg",
        "https://example.com:99999/x.jpg",
        "https://example.com:0/x.jpg",
        "https://example.com:abc/x.jpg",
        "https://[2001:db8::1/x.jpg",
    ],
)
def test_anything_else_is_withheld(value):
    assert public_evidence_url(value) is None
