"""COST-VEC-01 (Lane C): the Methanex methanol price seed -- the FIRST sourced ORGANIC commodity price.

Why this exists
---------------
The USGS seed (``experiments/usgs_commodity_seed.py``) recorded, as a deliberate honesty boundary, that "USGS prices
NO organic acid" and that the only organic per-ton figures found were a "commercial aggregator (IndexBox) with no
traceable primary authority", so NO organic price was committed (section 10.4 forbids fabrication).  ROUND-13's
item-4a hunt re-hit the same wall (Lab Alley behind client-side JS; USGS inorganic-only).  This round a PRIMARY
authority WAS found and verified, so the organic-price block is LIFTED -- for METHANOL only.

Source (single, dated, PRIMARY)
-------------------------------
Methanex Methanol Price Sheet, Aug 28, 2026 -- Methanex Corporation (the producer itself).  Verified in-sandbox: the
price-sheet PDF was fetched and READ DIRECTLY (not trusted from a search summary), and the North America "Methanex
Non-Discounted Reference Price" row -- USD 1,414/MT -- was read off the sheet.  The same sheet's U.S. Gulf Coast
figure USD 4.25/Gal cross-checks against it at the sheet's OWN stated conversion (332.6 Gal/MT): 4.25 * 332.6 =
1,414.55 ~= 1,414, so the two published figures on the sheet agree.
  price sheet: https://www.methanex.com/wp-content/uploads/Mx-Price-Sheet-Aug-2026.pdf
  pricing page: https://www.methanex.com/our-products/about-methanol/pricing/

Honesty boundaries (recorded, not hidden)
-----------------------------------------
* This is a PRODUCER'S POSTED bulk REFERENCE price (the "Non-Discounted Reference Price"), North America -- NOT a
  spot, contract, retail, or transaction price.  It is a list/reference number a real buyer negotiates off, the
  direct analogue of the USGS "average unit value" basis: a bulk wholesale reference, never retail.
* Methanol is a bulk COMMODITY sold at varying purity/grade; ``price_usd_per_t`` is the reference for the commodity,
  and a COST consumer treats it as an UNKNOWN-assay commodity lead (the STOCK-01 bridge), never a pure-reagent price.
* Effective Sep 1-30, 2026 (the sheet's stated validity); ``posted_date`` is the sheet's Aug 28, 2026 posting, which
  is the observation date carried into section-10.4 provenance.
* This lifts the organic-price block for METHANOL ONLY.  Acetic acid, formic acid and the rest still have no verified
  primary per-ton authority here and stay UNPRICED (section 10.4 no-fabrication) until one is sourced and READ.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

__all__ = [
    "MethanolPrice", "METHANEX_METHANOL_PRICES", "SOURCE", "ACCESS_DATE",
    "validate", "content_hash", "FROZEN_HASH", "report",
]

SOURCE = "Methanex Methanol Price Sheet (Aug 28, 2026) -- Methanex Corporation"
ACCESS_DATE = "2026-09-05"          # the in-sandbox date the price-sheet PDF was fetched and read directly
_PRICE_SHEET = "https://www.methanex.com/wp-content/uploads/Mx-Price-Sheet-Aug-2026.pdf"


@dataclass(frozen=True)
class MethanolPrice:
    """One Methanex regional posted methanol price, dollars per metric ton, with its sourced basis and the sheet URL."""

    commodity: str          # "methanol"
    region: str             # "North America"
    price_usd_per_t: float  # the posted reference price, dollars per metric ton
    basis: str              # e.g. "Methanex Non-Discounted Reference Price (posted bulk reference, not retail)"
    effective: str          # the sheet's stated validity window
    posted_date: str        # the sheet's posting date -- the section-10.4 observation date
    sheet_url: str

    def key(self) -> tuple[str, str]:
        return (self.commodity, self.region)


# The FROZEN Methanex value, transcribed from the Aug 28, 2026 sheet's North America row and cross-checked against the
# same sheet's $/Gal figure at its stated 332.6 Gal/MT. Do NOT edit the number without re-fetching and re-READING the
# dated source PDF (the anti-fabrication discipline: a price is only ever transcribed from a source actually read).
METHANEX_METHANOL_PRICES: tuple[MethanolPrice, ...] = (
    MethanolPrice(
        "methanol", "North America", 1414.0,
        "Methanex Non-Discounted Reference Price (producer's posted bulk reference, not retail/spot/contract)",
        "2026-09-01 to 2026-09-30", "2026-08-28", _PRICE_SHEET,
    ),
)

#: Organic commodities still UNPRICED here (no verified primary per-ton authority READ at the source): a test pins
#: their absence so a later edit cannot fabricate one, exactly as the USGS seed pins its own no-primary-source set.
UNPRICED_NO_PRIMARY_SOURCE: tuple[str, ...] = ("acetic acid", "formic acid", "ethanol", "acetone", "propan-2-ol")


def validate(rows: "tuple[MethanolPrice, ...]" = METHANEX_METHANOL_PRICES) -> None:
    """The NON-VACUOUS price discipline (mirrors the USGS seed): a committed price is a SOURCED dollars-per-ton value
    (> 0) with a named basis and a Methanex source URL -- a hollow/zero/negative price, or a row missing its basis or
    source, is REFUSED, and the guard fires on such a record, not merely on an empty set.  Refuses duplicate keys,
    non-finite numbers, and any UNPRICED_NO_PRIMARY_SOURCE organic fabricated into the priced set."""
    if not rows:
        raise ValueError("the Methanex methanol-price seed must not be empty (a non-vacuous guard needs a subject)")
    seen: set = set()
    for r in rows:
        if r.key() in seen:
            raise ValueError(f"duplicate price key {r.key()}; the seed must be single-valued per (commodity, region)")
        seen.add(r.key())
        val = r.price_usd_per_t
        if not isinstance(val, (int, float)) or val != val or val in (float("inf"), float("-inf")):
            raise ValueError(f"{r.commodity}: price_usd_per_t must be a finite number")
        if val <= 0:
            raise ValueError(
                f"{r.commodity}: price_usd_per_t must be a real sourced price (> 0 $/t); a hollow/zero price is "
                "refused (COST-VEC-01 non-vacuity, section 10.4)"
            )
        if not (r.commodity and r.region and r.basis and r.effective and r.posted_date):
            raise ValueError(f"{r.commodity}: commodity, region, basis, effective and posted_date are all required")
        if not r.sheet_url.startswith("https://www.methanex.com/"):
            raise ValueError(f"{r.commodity}: a price MUST name its Methanex source URL (section 10.4: dated AND sourced)")
        if r.commodity.casefold() in {c.casefold() for c in UNPRICED_NO_PRIMARY_SOURCE}:
            raise ValueError(
                f"{r.commodity}: is in UNPRICED_NO_PRIMARY_SOURCE and must not be fabricated into the priced seed"
            )


def content_hash(rows: "tuple[MethanolPrice, ...]" = METHANEX_METHANOL_PRICES) -> str:
    """A tamper-evident content hash of the frozen set."""
    canonical = sorted(
        [[r.commodity, r.region, r.price_usd_per_t, r.basis, r.effective, r.posted_date, r.sheet_url] for r in rows]
    )
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


#: The frozen hash of the committed Methanex seed (regenerate DELIBERATELY, only after re-reading the dated source
#: PDF, by running this module as __main__).
FROZEN_HASH = "0c7509f6e2e31609c7b959a66c056664afeaf33a0b7d5435c39a6a743d58d91e"


def report() -> dict:
    validate()
    return {
        "source": SOURCE,
        "access_date": ACCESS_DATE,
        "priced": len(METHANEX_METHANOL_PRICES),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("content_hash:", content_hash())
    print("(paste into FROZEN_HASH)")
