"""The frozen legacy v0.8 kernel: the verify-only digest rule, the 0.9-only wire-key scan and the decode migrations.

Extracted verbatim from :mod:`smartchem.service` (0.9.5 consolidation incision I2, barrier
``docs/research/V0_9_5_ARCHITECTURE_FREEZE.md`` §9).  Every function here is a pure function of its argument (plus
the frozen tables below) and the module imports nothing from :mod:`smartchem.service`.  What did NOT come along, on
purpose: the legacy BEHAVIOURAL forks woven through the request/response records and the load checks (Lane A counted
144 legacy touch points across 38 service functions: ``is_legacy_v08`` branches, ``_legacy_hint()`` suffixes, the
generation dispatch, the smuggling REFUSAL that names the service's schema id).  Those are load-bearing tissue, not a
tumour -- they stay in the service until 1.0 retires the v0.8 read leg and deletes the whole boundary in one pass.

Two anatomical warnings for whoever operates here next:

* ``_V08_OMITTED_FIELDS`` keys on QUALIFIED class names (``smartchem.service.CompilationRequest`` ...).  Those strings
  name where the classes LIVE, which is still the service -- they did not move with this table, and must not.
* A harness that patches ``_V08_OMITTED_FIELDS`` must patch it HERE (M108/M116 were retargeted accordingly): the one
  reader, :func:`_v08_canonical_payload`, looks the table up in this module's globals.  The service deliberately does
  not re-bind the table, so a stale ``svc._V08_OMITTED_FIELDS`` patch fails loudly instead of patching nothing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace as dataclasses_replace

from .contracts import canonical_payload


# -- the FROZEN v0.8 digest rule (D11, verify-only) ----------------------------------------------------------------
# Every digest in this package is ``canonical_digest`` over ALL compare=True dataclass fields, so ADDING a field to a
# digest-covered record moves every digest above it even when the new field sits at its default.  0.9 added exactly
# these fields to records a v0.8 (main@df1b38d) response digests over -- measured by diffing the dataclass field lists
# of the two trees (``git archive df1b38d`` vs this tree), not guessed:
#   CompilationRequest.capability_profile / .capability_profile_origin, RankedRouteSummary.capability_assessment,
#   ProcedureOperation.material_uses, and (X-high D14) PhysicalBounds.min_temperature_k.
# (MaterialComponent.basis/StockMaterial.states also grew, but no v0.8 payload can reach a StockMaterial -- a v0.8
# request carries stock as strings and no capability profile -- so they are deliberately NOT in the table.)
# A legacy payload is verified by re-encoding its reconstructed objects with those fields OMITTED -- but ONLY when
# they hold their default (the value a v0.8 producer could not have set).  A non-default value is refused outright:
# it is 0.9 content wearing a 0.8 identity.  This is a NARROW verify-only encoder; the global canonical hashing rule
# (``contracts.canonical_payload``) is untouched, and nothing current is ever digested with it.
_V08_OMITTED_FIELDS: "dict[str, dict[str, object]]" = {
    "smartchem.service.CompilationRequest": {"capability_profile": None, "capability_profile_origin": ""},
    "smartchem.service.RankedRouteSummary": {"capability_assessment": None},
    "smartchem.procedure_evidence.ProcedureOperation": {"material_uses": ()},
    # X-high D14: the temperature FLOOR a v0.8 (physical-bounds-v1alpha1) box could not express.  The legacy decode
    # also keeps the stored v1alpha1 id on the object, so the re-encoded bytes are exactly main@df1b38d's.
    "smartchem.constraints.PhysicalBounds": {"min_temperature_k": None},
}


def _v08_canonical_payload(value: object) -> object:
    """``contracts.canonical_payload`` with the frozen v0.8 field omissions applied at every dataclass level.

    Containers and dataclasses are walked here (so the omission reaches nested records); every scalar/enum/type leaf
    is delegated to ``canonical_payload`` itself, so the leaf encoding cannot drift from the real rule."""
    from dataclasses import fields as _fields, is_dataclass
    if is_dataclass(value) and not isinstance(value, type):
        qualified = f"{type(value).__module__}.{type(value).__qualname__}"
        omitted = _V08_OMITTED_FIELDS.get(qualified, {})
        encoded = []
        for f in _fields(value):
            if f.name.startswith("_") or not f.compare:
                continue
            v = getattr(value, f.name)
            if f.name in omitted:
                if v != omitted[f.name]:
                    raise ValueError(
                        f"legacy v0.8 payload carries 0.9-only content ({qualified}.{f.name} is not its default); "
                        f"refused -- a 0.9 field cannot wear a 0.8 schema id"
                    )
                continue
            encoded.append([f.name, _v08_canonical_payload(v)])
        return {"type": "dataclass", "class": qualified, "fields": encoded}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_v08_canonical_payload(i) for i in value]}
    if isinstance(value, list):
        return {"type": "list", "items": [_v08_canonical_payload(i) for i in value]}
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("semantic mapping keys must be strings")
        return {"type": "mapping", "items": [[k, _v08_canonical_payload(value[k])] for k in sorted(value)]}
    if isinstance(value, (set, frozenset)):
        items = [_v08_canonical_payload(i) for i in value]
        items.sort(key=lambda i: json.dumps(i, separators=(",", ":"), sort_keys=True))
        return {"type": "frozenset" if isinstance(value, frozenset) else "set", "items": items}
    return canonical_payload(value)


def _v08_digest(value: object) -> str:
    """SHA-256 over :func:`_v08_canonical_payload` -- byte-for-byte the v0.8 ``canonical_digest`` of a legacy record
    (pinned against the real main@df1b38d fixtures in tests/test_v0_9_round_v_schema_migration.py)."""
    encoded = json.dumps(_v08_canonical_payload(value), ensure_ascii=False, separators=(",", ":"),
                         sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _route_identity(route: object, *, legacy: bool) -> str:
    """The identity a reconstructed route/DAG must bind to: the current ``.digest``, or -- for a LEGACY v0.8 response --
    the frozen v0.8 digest of the same object (never a looser check: exact equality either way)."""
    return _v08_digest(route) if legacy else route.digest


#: D11: the keys that exist ONLY in the 0.9 wire.  None of them occurs anywhere in a genuine main@df1b38d payload
#: (verified against the real v0.8 fixtures), so their presence ANYWHERE in a v1alpha15 payload is 0.9 content wearing
#: a 0.8 id -- tamper T4b, or a 0.9.0a1-branch payload that reused the id -- and is refused, never reinterpreted.
_V09_ONLY_WIRE_KEYS = frozenset({
    "capability_question_digest", "capability_profile", "capability_profile_origin", "capability_assessment",
    "material_uses", "specification",
    # X-high D14: the temperature floor exists only on the 0.9 wire (a v1alpha1 constraints box cannot carry it).
    "min_temperature_k",
})


def _v09_only_keys(payload: object) -> "list[str]":
    """Every 0.9-only wire key present at ANY depth of ``payload`` (sorted, distinct)."""
    found: "set[str]" = set()
    stack: list = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            found |= _V09_ONLY_WIRE_KEYS & set(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return sorted(found)


def _migrate_legacy_v08_dossier(dossier: dict) -> dict:
    """Decode-side migration of ONE legacy route/DAG dossier (D11): every replayed procedure operation gains the
    0.9 ``material_uses`` slot at its ONLY v0.8-expressible value, ``[]`` (a v0.8 procedure could not type an
    auxiliary).  Returns a copy; the caller's payload is not mutated.  Digests are still verified under the frozen
    v0.8 rule, which omits exactly that default -- so this adds no identity, it only lets the current codec decode."""
    import copy
    migrated = copy.deepcopy(dossier)
    for step in migrated.get("replay_payload") or ():
        envelope = step.get("envelope") if isinstance(step, dict) else None
        procedure = envelope.get("procedure") if isinstance(envelope, dict) else None
        if isinstance(procedure, dict):
            for op in procedure.get("operations") or ():
                if isinstance(op, dict):
                    op["material_uses"] = []
    return migrated


def _without_material_uses(envelope: "object") -> "object":
    """X-high D27.1 (legacy leg): ``envelope`` with every procedure operation's ``material_uses`` emptied -- the ONE
    0.9-only slot a v0.8 envelope could not carry (the frozen v0.8 rule omits exactly that default), so a v0.8 envelope
    is compared with today's corpus lookup modulo it."""
    procedure = getattr(envelope, "procedure", None)
    if procedure is None:
        return envelope
    operations = tuple(dataclasses_replace(op, material_uses=()) for op in procedure.operations)
    return dataclasses_replace(envelope, procedure=dataclasses_replace(procedure, operations=operations))
