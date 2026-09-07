# Sourcing reconnaissance: Br₂ kinetics and Cl₂ pricing

Accessed **2026-09-07 UTC** (2026-09-06 America/New_York). Baseline:
`043a3cd87acdc33d1df9a3b8ad4b2215d93e8890`; report written in the isolated
`SmartChem-codex-20260907` worktree. This is source reconnaissance, not a production seed change.
Machine-readable receipts: [`experiments/sourcing_recon_2026_09_07.json`](../../experiments/sourcing_recon_2026_09_07.json).

**Both broad source-access walls are corrected.** A directly readable Br₂ dissociation primary exists,
but its rate law does not fit the first-order survival primitive. A dated absolute Cl₂ municipal
procurement offer exists with an explicit pound denominator and recorded council approval. Neither
finding establishes the DOW cost ranking or a Br₂ survival verdict.

## Br₂: primary recovered; model admission remains blocked

Marvin Warshay, *Shock-Tube Investigation of Bromine Dissociation Rates in Presence of Argon, Neon,
and Krypton*, NASA TN D-3502, July 1966. [Primary PDF](https://ntrs.nasa.gov/api/citations/19660020577/downloads/19660020577.pdf).
The summary specifies gas mixtures containing 1% Br₂ and 99% noble gas, incident shocks, 1200–1900 K.
Printed p. 10 (PDF p. 12), equations (1)–(2), defines initial Br₂ consumption:

```text
Br2 + M <=> 2 Br + M
-d[Br2]/dt = kD [Br2][M]
```

Printed p. 12 (PDF p. 14), equations (8)–(10):

| Collider M | Coefficient A | Ea (kcal/mol) | Source rate expression |
|---|---:|---:|---|
| Ar | 2.18 × 10⁸ | 31.5 | kD = A T^(1/2) exp(-Ea/RT) |
| Ne | 1.82 × 10⁸ | 31.3 | same form |
| Kr | 4.32 × 10⁸ | 33.6 | same form |

`kD` has units **L mol⁻¹ s⁻¹**, T is kelvin, and R must match the energy units.
The dimensionally inferred units of A are L mol⁻¹ s⁻¹ K⁻¹/². Reverse reaction and Br₂-as-collider
contributions were omitted for initial-rate, dilute measurements. Printed p. 13, Table I provides
one representative point: initial pressure 26.1 mmHg, shocked T = 1825 K,
[Ar] = 4.727 × 10⁻³ mol/L, observed kD = 1.48 × 10⁶ L mol⁻¹ s⁻¹.
That pressure is **one initial-pressure example, not a measured validity range**.

The table, equations, exponents, and units were checked on rendered pages because text extraction
lost the exponents. A transcription sanity calculation gives kD(1825 K) ≈ 1.57374 × 10⁶ L mol⁻¹ s⁻¹,
6.33% above the representative observation. This reuses the fitted dataset: it is a transcription
check, not an independent validation or a new fitted record.

Application inference from the source and the current code:

- `KineticRef` represents a constant-A Arrhenius law; this fit has a T^(1/2) factor.
- `surviving_fraction` requires `s^-1` and applies irreversible exponential loss. The source supplies
  a bimolecular coefficient. Multiplication by a declared, constant collider concentration could
  define a **conditional derived** pseudo-first-order initial loss coefficient; that is additional
  modeling, not a sourced universal first-order constant.
- An extended hold needs a justified reverse-reaction treatment and condition scope. Initial shock
  measurements cannot by themselves certify an ambient, aqueous, liquid, air, pure-Br₂, or arbitrary
  long-hold survival claim. The experiment's initial pressure is not the hot-state pressure.
- Consequently **do not add these values to the existing first-order seed or rename their units**.
  Item 3's Br₂ blocker should now say: accessible collider-dependent primary; modified-rate-law,
  collider-state, and reversible-hold admission work remains. A source independently satisfying
  the existing primitive's narrower scope has not been found in this round.

Independent literature leads, not replacement data: [Palmer and Hornig (1957)](https://doi.org/10.1063/1.1743272)
reports pure/argon shock measurements; its publisher abstract is readable but full text requires access.
[Ip and Burns (1967)](https://pubs.rsc.org/en/content/articlelanding/1967/df/df9674400241)
reports a recombination/shock disagreement and vibrational-relaxation explanation.
[Boyd et al. (1975)](https://doi.org/10.1016/S0082-0784(75)80342-0) reports three shock observables.
These are useful probes of historical instrument disagreement; they were not adjudicated here.
The exact next research task is compare the NASA fit with later primary corrections before treating it
as a recommended modern kinetic reference. The NASA result alone suffices to refute blanket inaccessibility.

## Cl₂: approved municipal offer, with scope and unit basis

The strongest fully scoped find is the City of Los Fresnos, Texas, **2025/2026 chemical procurement**.
The [city RFP](https://cityoflosfresnos.com/community/page/request-proposals-chemicals-0) identifies the
August 25, 2025 bid deadline and September 9 council meeting. The
[meeting attachment](https://mccmeetingspublic.blob.core.usgovcloudapi.net/losfrsnstx-meet-6084709cb2ef4da7a741e1246b1ab28c/ITEM-Attachment-001-9f5f937ee53b49ba9d06982257e264aa.pdf),
PDF pp. 7–8, names PVS DX, Inc. and records:

| Material/packaging | Absolute material offer | Separate rental | Proposed term |
|---|---:|---:|---|
| Chlorine gas, one-ton cylinder | **$2,480/cylinder; $1.24/lb** | $50/month | 2025-10-01 through 2026-09-30 |

The numerical denominator cross-check is `2480 / 1.24 = 2000 lb`; this is a US short-ton cylinder,
not 1000 kg. Definitional conversion using 0.45359237 kg/lb gives **$2.733732051/kg** of offered
material, or $2733.732051/metric tonne. It does not include the separate monthly rental.
The table's CURRENT column includes a tax entry that must not be silently copied into the new bid.

The [September 9 meeting minutes](https://mccmeetings.blob.core.usgovcloudapi.net/losfrsnstx-pubu/MEET-Minutes-6084709cb2ef4da7a741e1246b1ab28c.pdf),
PDF p. 4, item F.3, records approval of the bids including Chemicals, with five affirmative votes.
The attachment identifies the vendor and price; the minutes approve the category and do not repeat
line-level prices. That joined evidence supports **`approved_offer`**, with the join made explicit.
The attachment's agreement has blank signature lines. No executed agreement, invoice, delivery,
assay certificate, or payment was recovered. Those must remain unverified.

Application inference: a municipality's packaged delivery procurement is a valid dated absolute
observation **of that offered procurement**, not an industrial plant-gate/spot/retail benchmark.
Do not collapse it with the USGS bromine-content import blend or present it as a current generally
available purchase price. A future price record must retain region, observation/validity dates,
package mass, approval status, fee exclusions, unknown assay, and source linkage. Use a separate
municipal source path, following the existing separation of Methanex from the USGS-only seed.
The DOW ranking still needs a coherent NaBr/feedstock basis and whole-path cost coverage.

### A further conditional cost obstruction

The roadmap's proposed NaBr price derived solely from the same bromine-content price cannot
demonstrate an undercut of that bromine benchmark. Let `q > 0` be its price per unit mass of
contained Br, and derive `p(NaBr) = q M(Br)/M(NaBr)` by mass fraction. Stoichiometrically, one unit
mass of Br₂ requires `M(NaBr)/M(Br)` units of NaBr. Their product is exactly `q`: the feedstock alone
already costs the whole bromine benchmark, before any positive chlorine, rental, losses, or process
cost. Thus this proposed proxy ranks synthesis above the benchmark even at perfect yield and zero
other costs. This is a conditional algebraic result, not an observation about real brine economics.

The inference makes the next source contact more precise: a claim of cheaper brine recovery needs
an independently justified brine/feedstock and extraction-cost basis, not a second price mechanically
derived from the benchmark being undercut. A quantitative ranking may legitimately show no advantage;
the implementation must not tune the feedstock proxy to force the historical narrative.

Other primary checks retained as secondary leads:

- [Jackson, Michigan, May 15, 2025](https://www.cityofjackson.org/DocumentCenter/View/13594/Bid-Tabulation---2025-Chemicals---WTP-and-WWTPpdf):
  $1725/ton JCI Jones; $1729/ton Alexander. One-page bid tabulation, not proof of award or exact ton definition.
- [Jackson, May 27, 2026](https://www.cityofjackson.org/DocumentCenter/View/14546/Bid-Tabulation---2026-CHEMICALS---WTPpdf):
  $1330/ton JCI Jones; $1624/ton Alexander. Separate freight lines read No Bid, which does not establish
  free delivery. The contemporaneous specification/award was not recovered.
- [Dallas 25-1713A](https://cityofdallas.legistar.com/LegislationDetail.aspx?FullText=1&GUID=F7C14BB0-F372-450B-BBA0-A082152247AD&ID=7410615&Options=&Search=):
  an approved bulk railcar procurement exists, but the opened record gives a contract aggregate without
  the mass denominator. It cannot supply a per-ton figure by guessing annual volume.

## Contact, provenance, and claim ledger

The two source families are **NASA's experimental report** and **Los Fresnos's procurement record**;
they answer different questions. NASA search snippets, PDF text, and page renderings are the same
source, not independent experiments. Los Fresnos's RFP, agenda attachment, and minutes form one
linked transaction family, not three independent price measurements. Jackson is a different buyer
and bid context, so different numbers neither refute nor confirm the Los Fresnos number.

This uses Aletheia source-map discipline: κ is direct document contact after download/rendering;
φ supports the bounded document and arithmetic claims; σ requires the experimental and procurement
contexts to travel with each value; ρ risk is the project's desire to unblock DOW. No probability,
phasor, or physical-quantum claim is involved. Removing the NASA family removes the recovered fit;
removing the Los Fresnos family removes the fully specified price/approval join. Neither conclusion
has independent-source redundancy yet.

| Claim | Status | Boundary / next discriminator |
|---|---|---|
| No Br₂ dissociation primary is directly sourceable | Refuted as a blanket access claim | NASA PDF recovered; model eligibility is separate |
| NASA fit can directly populate first-order survival | Refuted | Wrong order/units; T factor, collider and hold/reverse scope missing |
| No dated absolute Cl₂ primary can be read | Refuted as a blanket access claim | Approved municipal offer recovered |
| Los Fresnos price was actually paid / is a general market quote | UNVERIFIED / unsupported | Executed agreement/invoice; market-basis transport review |
| DOW quantitative ranking and Br₂ survival are unblocked end to end | Not established | Price integration/feedstock and kinetic model work remain |
| A same-benchmark Br-content-derived NaBr proxy can establish an undercut | Refuted under the stated proxy | Stoichiometric mass factors cancel; any positive oxidant cost makes the route more expensive |

No outreach was sent. If actual execution or fee/assay closure becomes necessary, the concrete contact
is Los Fresnos City Secretary through the [published RFP contact](https://cityoflosfresnos.com/community/page/request-proposals-chemicals-0),
requesting the signed 2025/2026 PVS DX agreement and matched invoice/specification. Broader blind searching
is lower value than those exact missing documents.

## Retrieval and reproduction receipts

Scratch artifacts are under `/tmp/smartchem-sourcing-20260907/`; their persistence is not promised.
All reusable URLs, byte counts, SHA-256 hashes, page anchors, raw values, admission boundaries,
and arithmetic are in the committed-candidate JSON. No downloaded PDF is added to the repository.

| Artifact | SHA-256 | Read method |
|---|---|---|
| `nasa1966.pdf` | `c29f0b03e3cf7aec8da1ec9d9ca7055a5e067255f89b158cf44200c2243afdd7` | urllib HTTP 200; pdftotext; rendered PDF pp. 12/14/15 |
| `losfresnos2025.pdf` | `e92ec91dd6e8bffea00d3712063333d2dfa341e2e5de70db26faf28a7126f2a0` | urllib HTTP 200; pdftotext; rendered PDF p. 8 |
| `losfresnos-minutes2025.pdf` | `c33c4cf9f0fc080cdd5e59b4fefa3e92bc5a2ffd754d865a345bd09fbbd74318` | urllib HTTP 200; pdftotext; rendered PDF p. 4 |

Reproduce each receipt with `urllib.request.urlopen(url, timeout=25)`, hash the returned bytes with
`hashlib.sha256`, then `pdftotext -layout source.pdf source.txt`. Render page N using
`pdftoppm -f N -singlefile -scale-to 1800 -png source.pdf page-N` and inspect the resulting PNG.
The PDF page numbering above is one-based; the web screenshot API uses zero-based indexes.

Access failures are instrument-specific: the web tool returned NASA 403 and Jackson redirect-loop
errors while urllib retrieved both PDFs. Beaumont's candidate extension returned web 404 and urllib
403, and the Los Fresnos specification download closed its urllib connection; no values are admitted
from either failed retrieval. Search metadata incorrectly dated some old NASA documents recently;
publication dates here come from document covers, not search crawl labels.
