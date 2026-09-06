"""COST-VEC-01 / TERM-MAT-01 (Lane C): the USGS commodity-price seed -- a FROZEN, dated, cited reference dataset of
average unit values for the bulk commodities a poor-man's route bottoms out at (table salt, soda ash, lime, sulfur).

Why this exists
---------------
COST-VEC-01 was BLOCKED with the exact reason "needs sourced, dated prices -- section 10.4 forbids inventing them",
and a prior (2026-09-04) hunt found the USGS Mineral Commodity Summaries but "the sandbox could not verify the
figures". This round the figures WERE verified: the public-domain USGS PDFs were fetched (curl) and parsed
(pdftotext -layout), and every number below was read directly off the Salient Statistics price row of its chapter
and cross-checked against the column-year header. So the "no verifiable dated price data" block is LIFTED for this
closed set: the values are transcribed from the dated source per standard section 10.4, never fabricated.

Source (single, dated edition)
------------------------------
USGS Mineral Commodity Summaries 2026 -- U.S. Geological Survey, February 2026 (public domain). Per-chapter PDFs at
https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-<chapter>.pdf. Each `price_usd_per_t` is the "Price, average unit
value ... dollars per metric ton" row of that chapter's "Salient Statistics -- United States" table; the committed
value is the most recent FINAL (non-estimated) year, 2024, and `estimate_2025_usd_per_t` is the following year's
USGS ESTIMATE (the "2025e" column). Verified in-sandbox on the access date below.

Honesty boundaries (recorded, not hidden)
-----------------------------------------
* These are U.S. DOMESTIC average unit values, f.o.b. mine/plant -- NOT global spot, contract, or retail prices.
  (The sulfur chapter also carries a Tampa contract spot series in dollars per LONG ton; it is a different basis and
  is deliberately NOT transcribed here.)
* `price_usd_per_t` is the 2024 FINAL value; `estimate_2025_usd_per_t` is the USGS 2025 ESTIMATE ('e' column) and is
  flagged as such -- an estimate is carried, never silently promoted to a firm price.
* A commodity is a MIXTURE, not a pure reagent: rock salt is not pure NaCl, quicklime not pure CaO. `formula` is the
  idealized principal composition ONLY, so a COST consumer MUST treat each row as an UNKNOWN-assay commodity lead
  (the STOCK-01 `CommodityReagent` -> UNKNOWN-fraction bridge), never as a pure-reagent price. This is exactly
  TERM-MAT-01's "a commodity lead stays UNKNOWN-assay, never terminates a route as a pure reagent".
* ABSENT ON PURPOSE: acetic acid / vinegar and sodium bicarbonate (baking soda) have NO primary-source per-ton
  price -- USGS names sodium bicarbonate only as an UNPRICED coproduct of soda ash, and prices no organic acid. The
  only free per-ton figures found were a commercial aggregator (IndexBox) with no traceable primary authority, so
  they are NOT committed here (section 10.4 no-fabrication). Soda ash (Na2CO3) is the priced parent commodity and is
  a labelled PROXY/floor for sodium bicarbonate, never a bicarbonate price.
* This is the sourced DATA the block was waiting on, NOT the affordability engine. Building the section-10.4 vector
  affordability (cost/access/evidence/equipment/hazard/time as separate Pareto axes) and wiring each price into a
  dated, sourced STOCK-01 `CostObservation` on the `CommodityReagent` registry is the named next COST-VEC-01 brick.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

__all__ = [
    "CommodityPrice", "USGS_COMMODITY_PRICES", "SOURCE", "ACCESS_DATE", "FINAL_YEAR", "ESTIMATE_YEAR",
    "FROZEN_HASH", "content_hash", "validate", "report",
]

SOURCE = "USGS Mineral Commodity Summaries 2026 (U.S. Geological Survey, February 2026)"
ACCESS_DATE = "2026-09-04"
FINAL_YEAR = 2024      # the most recent NON-estimated year in the MCS 2026 edition
ESTIMATE_YEAR = 2025   # the 'e' (estimated) column in the MCS 2026 edition


@dataclass(frozen=True)
class CommodityPrice:
    """One USGS average unit value for a bulk commodity form: the 2024 FINAL price and the 2025 USGS estimate,
    both dollars per metric ton, with the sourced basis and chapter URL."""

    commodity: str                      # the USGS chapter, e.g. "salt"
    material: str                       # the priced form, e.g. "rock salt"
    formula: str                        # idealized PRINCIPAL composition only -- a mixture, treat as UNKNOWN assay
    price_usd_per_t: float              # 2024 FINAL average unit value, dollars per metric ton
    estimate_2025_usd_per_t: float      # the USGS 2025 ESTIMATE ('e' column), dollars per metric ton
    basis: str                          # e.g. "f.o.b. mine and plant, average unit value of bulk/pellets/packaged"
    chapter_url: str

    def key(self) -> tuple[str, str]:
        return (self.commodity, self.material)


# The FROZEN USGS values, transcribed from the MCS 2026 chapter price rows and each verified against its column-year
# header (2021 2022 2023 2024 2025e). Do NOT edit a number without re-fetching and re-reading the dated source PDF.
_SALT = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-salt.pdf"
_SODA = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-soda-ash.pdf"
_LIME = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-lime.pdf"
_SULF = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-sulfur.pdf"
_BROM = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-bromine.pdf"
_SALT_BASIS = "average unit value of bulk, pellets and packaged salt, f.o.b. mine and plant"
# Bromine is quoted PER KILOGRAM of bromine content in the MCS chapter (2.70 $/kg 2024 final; 3.00 $/kg 2025e); the
# seed stores $/metric ton, so these are the exact per-kg figures scaled x1000 -- a definitional unit conversion, NOT
# a fabricated number.  The basis discloses the per-kg origin so the scale is auditable, AND (evil-morty fold) that
# the figure is a COMPOUND-DOMINATED import blend (~90% bromide compounds per the MCS chapter) normalized to contained
# bromine -- a contained-bromine cost anchor, NOT an elemental-Br2 spot price (a caveat the DOW synthesis-ranking
# phase must respect before leaning on it as "the Br2 price").
_BROM_BASIS = ("average unit value of imports (c.i.f.), per kilogram of bromine content -- a compound-dominated import "
               "blend (~90% bromide compounds) normalized to contained bromine, not an elemental-Br2 spot price "
               "(2.70 $/kg in 2024; x1000 to $/t)")

USGS_COMMODITY_PRICES: tuple[CommodityPrice, ...] = (
    CommodityPrice("salt", "rock salt", "NaCl", 52.95, 54.0, _SALT_BASIS, _SALT),
    CommodityPrice("salt", "solar salt", "NaCl", 152.87, 150.0, _SALT_BASIS, _SALT),
    CommodityPrice("salt", "vacuum and open pan salt", "NaCl", 259.69, 260.0, _SALT_BASIS, _SALT),
    CommodityPrice("salt", "salt in brine", "NaCl", 10.56, 11.0, _SALT_BASIS, _SALT),
    CommodityPrice("soda ash", "soda ash (natural)", "Na2CO3", 169.35, 150.0,
                   "average unit value of sales (natural source), f.o.b. mine or plant", _SODA),
    CommodityPrice("lime", "quicklime", "CaO", 261.4, 260.0, "average value at plant", _LIME),
    CommodityPrice("lime", "hydrated lime", "Ca(OH)2", 274.2, 280.0, "average value at plant", _LIME),
    CommodityPrice("sulfur", "elemental sulfur", "S", 46.42, 180.0,
                   "average unit value, f.o.b. mine and (or) plant, per metric ton of elemental sulfur", _SULF),
    CommodityPrice("bromine", "bromine (import unit value)", "Br2", 2700.0, 3000.0, _BROM_BASIS, _BROM),
)

#: Commodities deliberately NOT priced here: no primary-source per-ton price exists (see the docstring). A test pins
#: their absence so a later edit cannot silently fabricate one from a commercial aggregator.
UNPRICED_NO_PRIMARY_SOURCE: tuple[str, ...] = ("acetic acid", "vinegar", "sodium bicarbonate", "baking soda")


def validate(rows: "tuple[CommodityPrice, ...]" = USGS_COMMODITY_PRICES) -> None:
    """The NON-VACUOUS price discipline: a committed price is a SOURCED dollars-per-ton value (> 0) with its 2025
    estimate (> 0), a named basis and a chapter URL -- a hollow/zero/negative price, or a row missing its basis or
    source, is REFUSED, and the guard fires on such a record (not merely on an empty set). Also refuses duplicate
    keys, non-finite numbers, and a fabricated no-primary-source commodity (acetic acid / vinegar / bicarbonate)."""
    seen: set = set()
    if not rows:
        raise ValueError("the USGS commodity-price seed must not be empty (a non-vacuous guard needs a subject)")
    for r in rows:
        if r.key() in seen:
            raise ValueError(f"duplicate commodity key {r.key()}; the seed must be single-valued per (commodity, form)")
        seen.add(r.key())
        for field, val in (("price_usd_per_t", r.price_usd_per_t), ("estimate_2025_usd_per_t", r.estimate_2025_usd_per_t)):
            if not isinstance(val, (int, float)) or val != val or val in (float("inf"), float("-inf")):
                raise ValueError(f"{r.material}: {field} must be a finite number")
            # a price is a SOURCED positive dollars-per-ton value; a zero/negative "price" is a hollow claim, refused.
            if val <= 0:
                raise ValueError(
                    f"{r.material}: {field} must be a real sourced price (> 0 $/t); a hollow/zero price is refused "
                    f"(COST-VEC-01 non-vacuity, section 10.4)"
                )
        if not (r.commodity and r.material and r.formula and r.basis):
            raise ValueError(f"{r.material or r.key()}: commodity, material, formula and basis are all required")
        if not r.chapter_url.startswith("https://pubs.usgs.gov/"):
            raise ValueError(f"{r.material}: a price MUST name its USGS source URL (section 10.4: dated AND sourced)")
        if r.material.casefold() in {c.casefold() for c in UNPRICED_NO_PRIMARY_SOURCE}:
            raise ValueError(
                f"{r.material}: has no primary-source per-ton price (see UNPRICED_NO_PRIMARY_SOURCE); it must not be "
                f"fabricated into the priced seed from a commercial aggregator"
            )


def content_hash(rows: "tuple[CommodityPrice, ...]" = USGS_COMMODITY_PRICES) -> str:
    """A tamper-evident content hash of the frozen set -- the sorted (commodity, material, formula, price, estimate,
    basis, url) rows."""
    canonical = sorted(
        [[r.commodity, r.material, r.formula, r.price_usd_per_t, r.estimate_2025_usd_per_t, r.basis, r.chapter_url]
         for r in rows]
    )
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


#: The frozen hash of the committed USGS seed (regenerate DELIBERATELY, only after re-reading the dated source PDFs,
#: by running this module as __main__).
FROZEN_HASH = "dc2bcced49b7cbfeee0b609816362793291e28c0e4f1e960d59ff3d7b708d19d"


def report() -> dict:
    validate()
    return {
        "source": SOURCE,
        "access_date": ACCESS_DATE,
        "final_year": FINAL_YEAR,
        "estimate_year": ESTIMATE_YEAR,
        "priced_forms": len(USGS_COMMODITY_PRICES),
        "commodities": sorted({r.commodity for r in USGS_COMMODITY_PRICES}),
        "unpriced_no_primary_source": list(UNPRICED_NO_PRIMARY_SOURCE),
        "content_hash": content_hash(),
        "frozen_hash": FROZEN_HASH,
        "hash_matches": content_hash() == FROZEN_HASH,
    }


if __name__ == "__main__":
    validate()
    print("content_hash =", content_hash())
    print("(set FROZEN_HASH to this value to freeze)")
    for r in USGS_COMMODITY_PRICES:
        print(f"  {r.commodity:9s} {r.material:26s} {r.formula:8s}: {FINAL_YEAR} ${r.price_usd_per_t:8.2f}/t (final); "
              f"{ESTIMATE_YEAR}e ${r.estimate_2025_usd_per_t:7.2f}/t  [{r.basis}]")
