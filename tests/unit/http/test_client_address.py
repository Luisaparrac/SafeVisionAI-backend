import pytest
from starlette.requests import Request

from safevision.adapters.inbound.http.security import client_address


def request(headers: dict[str, str], client=("192.0.2.1", 5000)) -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": client,
        }
    )


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({}, "192.0.2.1"),
        ({"X-Forwarded-For": "203.0.113.9"}, "203.0.113.9"),
        # The nearest proxy appends the last entry; the client can only forge the first.
        ({"X-Forwarded-For": "198.51.100.1, 203.0.113.9"}, "203.0.113.9"),
        ({"CF-Connecting-IP": "203.0.113.5", "X-Forwarded-For": "198.51.100.1"}, "203.0.113.5"),
        ({"CF-Connecting-IP": "2001:db8::1"}, "2001:db8::1"),
        ({"CF-Connecting-IP": "no-es-ip"}, "192.0.2.1"),
        ({"CF-Connecting-IP": "no-es-ip", "X-Forwarded-For": "203.0.113.9"}, "203.0.113.9"),
        ({"X-Forwarded-For": "203.0.113.9, basura"}, "192.0.2.1"),
    ],
)
def test_client_address(headers, expected):
    assert client_address(request(headers)) == expected


def test_without_a_connection_address():
    assert client_address(request({}, client=None)) == "unknown"
