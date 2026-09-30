"""Transport integrity: the pure wire-digest fold, the transport-mode constants and the producer HMAC.

Extracted verbatim from :mod:`smartchem.service` (0.9.5 consolidation incision I1, barrier
``docs/research/V0_9_5_ARCHITECTURE_FREEZE.md`` §9).  Nothing here knows what a response IS: these are functions of a
payload dict, a digest string and a key.  The module imports nothing from :mod:`smartchem.service` -- the service (and
:mod:`smartchem.verification`) import IT, so the fold rule has exactly one home and the loader, the producer and
re-execution all read the same one.  One resident is not pure and says so: :func:`resolve_producer_key` reads the
environment and the keyfile (and writes it under ``create=True``) -- it lives here because the key and the HMAC it
feeds belong in the same room.

Surgical note: the service still binds every name it calls from here as its own module global, so a harness that
patches ``smartchem.service._payload_body_digest`` (M189) still reaches the three callers that stay behind.  The
patient was moved, not re-wired.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from .contracts import canonical_digest

__all__ = [
    "TRANSPORT_CANONICAL_VERIFIED",
    "TRANSPORT_THIN_ADVISORY",
    "resolve_producer_key",
]


# v0.8 Round II (D5, canonical transport): the two declared transport modes.  CANONICAL_VERIFIED means the producer
# emitted the thick ``replay_payload`` so every above-FORMAL readiness claim is RE-DERIVABLE -- and is re-derived,
# fail-closed, on load; THIN_ADVISORY is the explicit lean opt-out whose above-FORMAL claims stay advisory, and on which
# PROCESS_SPECIFIED is not admissible at all (Lane F forward ruling).  The mode is FOLDED into the wire result_digest
# so a downgrade-strip (relabel CANONICAL->THIN to dodge the mandatory re-derivation) is caught like a readiness tamper.
TRANSPORT_CANONICAL_VERIFIED = "CANONICAL_VERIFIED"
TRANSPORT_THIN_ADVISORY = "THIN_ADVISORY"
_TRANSPORT_MODES = frozenset({TRANSPORT_CANONICAL_VERIFIED, TRANSPORT_THIN_ADVISORY})


#: X-high D27.2: the ONLY payload keys the wire body digest excludes -- the digest itself and the signature over it.
_BODY_DIGEST_EXCLUDED_KEYS = frozenset({"result_digest", "producer_signature"})


def _payload_body_digest(payload: dict) -> str:
    """X-high D27.2 (Wave C4 C4T-2/C4T-8): SHA-256 over the ENTIRE response payload except ``result_digest`` and
    ``producer_signature``, in the canonical wire encoding (sorted keys, compact separators, UTF-8) -- the exact bytes
    :func:`smartchem.service.serialize_response` writes, so a payload that went through ``json.loads`` re-encodes identically.  Every field
    a response carries -- the affordability frontier, diagnostics, the parse receipt, provider snapshots, DAG serial
    holds, IR candidate text, replay payloads on the thick wire -- is inside it; nothing a payload SAYS can move without
    moving the wire digest the producer HMAC signs and ``require_reexecution`` compares."""
    body = {key: value for key, value in payload.items() if key not in _BODY_DIGEST_EXCLUDED_KEYS}
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _transport_bound_result_digest(base_digest: str, transport_mode: str, body_digest: "str | None" = None) -> str:
    """Bind the declared ``transport_mode`` -- and, on a CURRENT payload, the WHOLE payload body -- into the wire
    ``result_digest``.

    ``base_digest`` is the in-memory :attr:`CompilationResponse.result_digest`: the RESULT identity, deliberately
    alias-invariant (SVC-REQ-01 -- ``paracetamol`` and ``smiles:CC(=O)Nc1ccc(O)cc1`` share it, so it excludes the
    parse receipt and other provenance).  The WIRE digest is a different object: the integrity pin of THIS payload.

    * ``body_digest`` given (every CURRENT payload, X-high D27.2): ``canonical_digest(("compilation-transport-v1alpha2",
      base, mode, body))`` -- the body digest (:func:`_payload_body_digest`) folds in every field the payload carries,
      so the producer HMAC now authenticates the frontier, diagnostics, receipts, provider snapshots and serial holds
      too (Round IV-V signed only the base digest, and Wave C4 C4T-2 showed a forged frontier surviving the HMAC), and a
      downgrade relabel moves it as before.  A keyless attacker can still recompute a public digest -- that is the
      unsigned-wire boundary every load-time re-derivation exists for; the key closes it.
    * ``body_digest`` ``None`` (the FROZEN pre-D27 rule, used ONLY for legacy v0.8 payloads): THIN_ADVISORY is the
      identity (the bare base digest); CANONICAL_VERIFIED folds the mode in ("compilation-transport-v1alpha1").  Real
      v0.8 fixtures verify under exactly this rule, byte for byte."""
    if transport_mode not in _TRANSPORT_MODES:
        raise ValueError(f"unknown transport_mode {transport_mode!r}")
    if body_digest is not None:
        return canonical_digest(("compilation-transport-v1alpha2", base_digest, transport_mode, body_digest))
    if transport_mode == TRANSPORT_THIN_ADVISORY:
        return base_digest
    return canonical_digest(("compilation-transport-v1alpha1", base_digest, transport_mode))


# -- COMBINED-VERDICT-AUTH: an optional producer signature over the response identity ----------------------------
#
# ``response_from_payload`` already RE-DERIVES process admission on load (PROCESS-ADMIT-01), but that binds only the
# PROCESS axis, and every other self-declared field is trusted from a payload anyone can mint.  A producer signature
# closes the OUT-OF-BAND tamper: the producer signs the WIRE ``result_digest`` with a secret key; a consumer holding the
# same key verifies it and REFUSES a payload whose bytes were altered without the key.  Since X-high D27.2 the wire
# digest of a current payload is the canonical digest of the WHOLE payload body (every key except ``result_digest`` and
# ``producer_signature`` -- ``_payload_body_digest``), so the HMAC authenticates EVERYTHING the response carries: the
# ranked dossiers, the affordability frontier, diagnostics, receipts, the thick replay, the parse receipt, provider
# snapshots and DAG serial holds (before D27.2 it signed only the alias-invariant result identity, and the frontier /
# replay / provenance rode outside it -- Wave C4 C4T-2/C4T-8).
#
# HONEST SCOPE -- what a signature can and cannot do:
#   * CLOSES: an attacker WITHOUT the key who edits a serialized response (relabel a route's ``fit_status`` to FITS, swap
#     the admissible list, even coherently recompute ``result_digest``) -- the HMAC no longer matches, so verification
#     with ``require_signature`` raises.  This is the transport/storage-tamper threat.
#   * DOES NOT CLOSE: a controlling forger who runs code INSIDE the producing process (or holds the key) can always
#     construct-then-sign a lie -- a signature proves "these bytes came from a key-holder, unmodified", NEVER "this
#     verdict was honestly derived".  That residual (test_admission_residual_needs_a_signature_to_close) is not closable
#     by ANY signature; it would need an independent re-derivation service the thin projection deliberately omits.
#   * It is a SYMMETRIC, same-owner tag: it does not defend against an attacker who can read the key.
#
# Signing is strictly OPT-IN: with no key the payload is byte-identical to the unsigned form (``producer_signature`` is
# ``null``), so every existing caller and golden fixture is unchanged.

_PRODUCER_KEY_ENV = "SMARTCHEM_PRODUCER_KEY"
_PRODUCER_KEY_PATH = Path.home() / ".smartchem" / "producer.key"
_PRODUCER_KEY_MIN_BYTES = 16


def resolve_producer_key(*, create: bool = False) -> bytes | None:
    """The local producer key for signing/verifying responses, or ``None`` when unavailable.

    Resolution order: the ``SMARTCHEM_PRODUCER_KEY`` env var (hex-encoded), then a ``~/.smartchem/producer.key``
    keyfile (raw bytes).  With ``create=True`` a fresh 32-byte key is written to the keyfile (mode ``0600``) if none
    exists -- the zero-config path for a same-machine producer/consumer.  Returns ``None`` for a missing key (never
    raises), so an unsigned default stays the graceful, explicit fallback rather than a crash; it raises only for a
    malformed env value, which is an operator error worth surfacing loudly.
    """
    env = os.environ.get(_PRODUCER_KEY_ENV)
    if env:
        try:
            key = bytes.fromhex(env.strip())
        except ValueError as exc:
            raise ValueError(f"{_PRODUCER_KEY_ENV} must be hex-encoded") from exc
        if len(key) < _PRODUCER_KEY_MIN_BYTES:
            raise ValueError(f"{_PRODUCER_KEY_ENV} must decode to at least {_PRODUCER_KEY_MIN_BYTES} bytes")
        return key
    if _PRODUCER_KEY_PATH.exists():
        return _PRODUCER_KEY_PATH.read_bytes()
    if create:
        _PRODUCER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        _PRODUCER_KEY_PATH.write_bytes(key)
        _PRODUCER_KEY_PATH.chmod(0o600)
        return key
    return None


def _sign_result_digest(result_digest: str, key: bytes) -> str:
    """The producer signature: an HMAC-SHA256 over the response's WIRE ``result_digest`` (hex).

    For a current payload that digest folds the whole-body digest (X-high D27.2), so signing it authenticates every
    field the payload carries -- on the thin wire every field it carries, without the heavy ExperimentRoute graph.
    """
    return hmac.new(key, result_digest.encode("utf-8"), hashlib.sha256).hexdigest()
