"""Verified TLS context for sfedu.ru.

The server currently omits the intermediate certificate that signed its leaf
certificate. Browsers can recover it through AIA, while OpenSSL clients used by
the Linux sync runner cannot. Keep normal system roots and add only the missing
public GlobalSign intermediate; hostname and certificate verification remain
enabled.
"""

from __future__ import annotations

import ssl
from pathlib import Path

import requests

SFEDU_INTERMEDIATE_CERT = (
    Path(__file__).with_name("certs") / "globalsign-gcc-r6-alphassl-ca-2025.pem"
)


def make_sfedu_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=SFEDU_INTERMEDIATE_CERT)
    return context


class SfeduTLSAdapter(requests.adapters.HTTPAdapter):
    """Requests adapter using the augmented verified context."""

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = make_sfedu_ssl_context()
        return super().init_poolmanager(*args, **kwargs)
