"""Typed, reviewable source locators for chemistry-facing evidence.

A locator is not evidence merely because it is a non-empty string.  This module separates
syntactically reviewable DOI/HTTP locators from the explicit review decision that allows a
curated record to raise an evidence tier.  Callers may carry unreviewed citations for later
inspection; only ``ACCEPTED`` citations earn sourced behavior.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from .contracts import Digestible

__all__ = ["SourceReview", "SourceCitation"]

_DOI = re.compile(r"^(?:doi:|https://doi\.org/)10\.\d{4,9}/\S+$", re.IGNORECASE)


class SourceReview(str, Enum):
    """Whether a data-loader/reviewer has accepted a citation for the exact record context."""

    UNREVIEWED = "UNREVIEWED"
    ACCEPTED = "ACCEPTED"


@dataclass(frozen=True)
class SourceCitation(Digestible):
    """A syntactically reviewable source locator plus an explicit acceptance state."""

    locator: str
    review: SourceReview = SourceReview.UNREVIEWED

    def __post_init__(self) -> None:
        if not isinstance(self.locator, str) or not self.locator.strip():
            raise ValueError("source locator must be a non-empty DOI or HTTP(S) URL")
        locator = self.locator.strip()
        object.__setattr__(self, "locator", locator)
        if not isinstance(self.review, SourceReview):
            raise TypeError("review must be a SourceReview")
        if not _DOI.match(locator):
            parsed = urlparse(locator)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "." not in parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError(
                    "source locator must be DOI:10.<registrant>/<suffix>, a doi.org URL, or a complete "
                    "HTTP(S) URL with a hostname"
                )

    @property
    def accepted(self) -> bool:
        """Whether review has accepted this locator for use as sourced evidence."""
        return self.review is SourceReview.ACCEPTED
