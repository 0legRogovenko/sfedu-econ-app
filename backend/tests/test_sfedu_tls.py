"""TLS verification for sfedu.ru's incomplete server certificate chain."""

from __future__ import annotations

import hashlib
import ssl

from src.sfedu_tls import SFEDU_INTERMEDIATE_CERT, make_sfedu_ssl_context

EXPECTED_INTERMEDIATE_SHA256 = (
    "a883559231f8388daf35ce41c8101040ae8fd9b656434247b9475af592cc08ca"
)


def _certificate_fingerprint(pem: str) -> str:
    der = ssl.PEM_cert_to_DER_cert(pem)
    return hashlib.sha256(der).hexdigest()


def test_vendored_certificate_is_the_expected_globalsign_intermediate():
    pem = SFEDU_INTERMEDIATE_CERT.read_text(encoding="ascii")

    assert _certificate_fingerprint(pem) == EXPECTED_INTERMEDIATE_SHA256


def test_context_keeps_hostname_verification_and_loads_the_intermediate():
    context = make_sfedu_ssl_context()
    trusted_fingerprints = {
        hashlib.sha256(cert).hexdigest()
        for cert in context.get_ca_certs(binary_form=True)
    }

    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert EXPECTED_INTERMEDIATE_SHA256 in trusted_fingerprints
