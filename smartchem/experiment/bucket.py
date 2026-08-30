"""The four epistemic buckets, made executable -- M-5's whole discipline in one enum.

The refined W3 boundary (``known-physics, never new-physics``) is not a comment in this package; it is
a TYPE.  Every quantity the Experiment Compiler emits is a :class:`Quantity` that carries the
:class:`Bucket` it belongs to, so a caller can never mistake an idealised conservation ceiling for a
predicted yield, or an ``UNKNOWN`` gap for a cleared "fine".  The four buckets are deliberately
non-interchangeable, exactly as :class:`~smartchem.contracts.EvidenceStatus` is:

* ``CONSERVATION`` -- a formal, free consequence of mass/charge bookkeeping (the 100%-efficiency
  ceiling).  An idealised bound, never a claim about what actually happens.
* ``COMPOSABILITY`` -- a constraint-satisfaction verdict over declared/sourced envelopes ("these two
  stated conditions contradict").  A logical refusal, not a prediction about chemistry.
* ``KNOWN_SOURCED`` -- a value reproduced from a SOURCE or COMPUTED by an ESTABLISHED, VALIDATED model on
  sourced inputs, under the oracle's calibrate/state-envelope/refuse discipline.  This covers both a
  looked-up datum and one DERIVED (interpolated) or PREDICTED (extrapolated, flagged) from established
  theory -- reproducing known chemistry, never inventing it.
* ``UNKNOWN`` -- no source and no established model reaches it.  The honest gap.  Manufacturing a number
  here -- a NOVEL (not-established) feasibility/kinetics/yield model, or a value contradicting a sourced
  fact -- is the forbidden move, so this bucket exists to be emitted *loudly* instead.

These four are the epistemic label on a single :class:`Quantity`.  They are the finer, per-value shadow of
the whole-combination verdict the compiler grades a reaction with (KNOWN / DERIVED / PREDICTED /
HYPOTHESIZED / REFUTED / UNKNOWN -- see the roadmap's governing frame): a DERIVED or PREDICTED verdict is
carried by ``KNOWN_SOURCED`` quantities, a REFUTED verdict cites ``CONSERVATION`` / ``COMPOSABILITY`` /
``KNOWN_SOURCED`` facts, and an UNKNOWN verdict is all ``UNKNOWN``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..contracts import Digestible

__all__ = ["Bucket", "Quantity", "unknown"]


class Bucket(str, Enum):
    """Which kind of knowledge a quantity rests on.  Non-interchangeable by construction."""

    CONSERVATION = "CONSERVATION"
    COMPOSABILITY = "COMPOSABILITY"
    KNOWN_SOURCED = "KNOWN_SOURCED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_known(self) -> bool:
        """True for a quantity that rests on real evidence (conservation, a source, a verdict)."""
        return self is not Bucket.UNKNOWN


@dataclass(frozen=True)
class Quantity(Digestible):
    """One labelled quantity: a value, its bucket, its unit, and (for a claim) its provenance.

    The provenance rule is the teeth: a ``KNOWN_SOURCED`` quantity MUST carry a non-empty provenance
    (a value reproduced from nowhere is not sourced), and an ``UNKNOWN`` quantity MUST carry ``None``
    for its value (an unknown with a number is a smuggled guess).  Both are enforced here so the label
    cannot drift from the thing it labels.
    """

    label: str
    value: Any
    unit: str
    bucket: Bucket
    provenance: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("label must be a non-empty string")
        if not isinstance(self.unit, str):
            raise TypeError("unit must be a string")
        if not isinstance(self.bucket, Bucket):
            raise TypeError("bucket must be a Bucket")
        if not isinstance(self.provenance, str):
            raise TypeError("provenance must be a string")
        if self.bucket is Bucket.UNKNOWN and self.value is not None:
            raise ValueError(
                "an UNKNOWN quantity must carry value=None; a number under UNKNOWN is a smuggled "
                "guess. State a source and change the bucket, or leave the value None"
            )
        if self.bucket is Bucket.KNOWN_SOURCED and not self.provenance.strip():
            raise ValueError(
                "a KNOWN_SOURCED quantity must carry a non-empty provenance; a value reproduced "
                "from no source is not sourced"
            )
        if self.bucket is not Bucket.UNKNOWN and self.value is None:
            raise ValueError(
                f"a {self.bucket.value} quantity must carry a value; only UNKNOWN may be value-less"
            )

    @property
    def is_known(self) -> bool:
        return self.bucket.is_known

    def render(self) -> str:
        """A one-line human rendering: ``label = value unit  [BUCKET: provenance]``."""
        if self.bucket is Bucket.UNKNOWN:
            body = f"{self.label} = UNKNOWN"
        else:
            unit = f" {self.unit}" if self.unit else ""
            body = f"{self.label} = {self.value}{unit}"
        tag = self.bucket.value
        if self.provenance:
            tag = f"{tag}: {self.provenance}"
        return f"{body}  [{tag}]"


def unknown(label: str, unit: str = "", provenance: str = "") -> Quantity:
    """The honest gap: a value-less ``UNKNOWN`` quantity.

    A provenance may be given to say *why* it is unknown (e.g. "no sourced decomposition threshold"),
    which is documentation of the gap, never a value.
    """
    return Quantity(label=label, value=None, unit=unit, bucket=Bucket.UNKNOWN, provenance=provenance)
