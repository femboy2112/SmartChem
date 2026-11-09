"""Example 01 -- parse SMILES, read the identity, and meet the formula/structure boundary.

Shows: parse_smiles gives a pure graph Molecule (formula is a dict); resolve_identity reports how the input
was read; resolve_target REFUSES a bare formula (a composition is not a structure).
Ooh yeah, can do!  Needs only the base install.
"""
from smartchem.identity_parse import IdentityParseError, resolve_identity, resolve_target
from smartchem.smiles import parse_smiles


def main() -> int:
    for label, smiles in (("ethanol", "CCO"), ("acetic acid", "CC(=O)O")):
        mol = parse_smiles(smiles)
        ident = resolve_identity(f"smiles:{smiles}")
        print(f"{label:11s} smiles={smiles:8s} formula={mol.formula} atoms={len(mol.atoms)}")
        print(f"{'':11s} identity layer={ident.receipt.identity_layer} via {ident.receipt.source.value}")
    # The boundary: a bare formula names a composition, NOT a structure, so a structure search refuses it.
    try:
        resolve_target("C2H6O")
    except IdentityParseError as exc:
        print("resolve_target('C2H6O') REFUSED:", exc)
        return 0
    print("unexpected: bare formula was accepted")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
