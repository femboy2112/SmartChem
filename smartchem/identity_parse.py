"""The one target-identity parser (ID-PARSE-01) shared by the CLI and the typed service.

SVC-REQ-01 exists so that ``compile``/``synthesize``/``recompile`` cannot silently diverge.  A brick whose
whole point is *one* front door must not ship *two* parsers: if the CLI resolved ``"acetic anhydride"`` one way
and :mod:`smartchem.service` resolved it another, "equal flags across aliases" would be a lie the moment the two
string-to-:class:`~smartchem.category.Molecule` code paths drifted.  So the resolution lives here, once, and both
:mod:`smartchem.cli` and :mod:`smartchem.service` key on it.

:func:`resolve_identity` is that single authority.  It resolves EVERY section-14.2 input form to a typed
:class:`ResolvedIdentity` carrying the perceived molecule (when structure is perceivable), the formula, the
dropped SMILES features, the section-5.3 identity losses, and a :class:`ParseReceipt` that ECHOES how the string
was read (requested vs resolved kind, the source, the normalised canonical form, the finest identity layer
reached, and any provenance/unconsumed-layer notes).  Nothing is guessed silently: an unresolvable or ambiguous
string, or a form this offline parser cannot honour, is a loud typed :class:`IdentityParseError`.

Forms and how far each is perceived (never faked):

* ``NAME`` / ``SMILES`` -- resolved to a real :class:`~smartchem.category.Molecule` (CONSTITUTION layer).  A
  SMILES also reports the finer features (:class:`~smartchem.smiles.SmilesFeatures`) the graph cannot keep.
* ``FORMULA`` -- resolved to a :class:`~smartchem.decompiler.Formula` (FORMULA layer only).  A bare formula names
  composition, not structure, so it perceives NO molecule; a structure search (recompile) refuses it, and a
  formula descent (decompile) consumes it directly.
* ``INCHI`` -- resolved from its FORMULA SUBLAYER, WITH the charge.  The formula token and the charge layers
  (``/q`` net charge, ``/p`` proton balance -- a proton is an H+, so ``/p`` shifts the H count too) are CONSUMED
  into a correctly-charged :class:`~smartchem.decompiler.Formula`, so ``[NH4+]`` never collapses to neutral NH3.
  Full InChI->structure inversion needs InChI's canonical numbering, which this offline parser does not
  reimplement, so the ``/c``/``/h`` connectivity is NOT parsed: the result is a FORMULA-layer identity carrying a
  section-5.3 ``molecular-constitution`` BLOCKER, plus stereo/isotope blockers for any ``/t``, ``/b``, ``/m``,
  ``/s`` or ``/i`` layer.  Any layer neither consumed nor lowered to a loss is NAMED in a receipt note, so the
  receipt names every unconsumed layer.  This is honest fail-closed resolution, never a silent mis-parse.
* ``TARGET_FILE`` -- the file's contents are read and resolved as an inner target (honouring an inline
  ``name:``/``smiles:``/``inchi:``/``formula:`` prefix or a bare ``InChI=`` header), so a molecule/formula/InChI
  can be supplied from a file.

The ``AUTO`` path stays byte-for-byte the behaviour the CLI shipped (offline name first, else SMILES, with an
inline ``name:``/``smiles:`` prefix), extended only additively: ``inchi:``/``formula:`` prefixes and a bare
``InChI=`` header are recognised where they are unambiguous.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import Digestible

__all__ = [
    "InputKind",
    "ParseSource",
    "ParseReceipt",
    "ResolvedIdentity",
    "IdentityParseError",
    "InputKindAmbiguity",
    "detect_auto_ambiguity",
    "resolve_identity",
    "resolve_target",
    "resolve_target_with_features",
    "EXPLICIT_CLI_FORMS",
    "resolve_cli_target",
]

# The section-14.2 explicit value-form flags (``--name "X"`` etc.), in the order they are offered, mapped to the
# InputKind each forces.  ONE shared spec so the ``recompile``/``compile`` and ``synthesize`` CLIs cannot drift on
# which forms exist or what kind each means (the CLI-NAME-01 / SVC-REQ-01 "one front door" discipline).
EXPLICIT_CLI_FORMS = (
    ("name", "NAME"),
    ("smiles", "SMILES"),
    ("inchi", "INCHI"),
    ("formula", "FORMULA"),
    ("target-file", "TARGET_FILE"),
)

# The prefixes an explicit inline ``kind:payload`` may name, mapped to the kind they force.  Recognised on the
# AUTO path (and inside a TARGET_FILE), so an ambiguous string is never silently guessed when the caller was
# explicit.  ``name``/``smiles`` are the historical two; ``inchi``/``formula`` are the ID-PARSE-01 additions.
_INLINE_PREFIXES = {"name": "NAME", "smiles": "SMILES", "inchi": "INCHI", "formula": "FORMULA"}

# The number of bytes a TARGET_FILE may hold before it is refused -- a target spec is a short string, not a blob;
# a large file is a wrong input, refused loudly rather than read into memory.
_MAX_TARGET_FILE_BYTES = 64 * 1024


class InputKind(str, Enum):
    """How the caller's ``target_input`` string is to be read (standard section 14.2).

    ``AUTO`` mirrors the positional CLI ergonomics: an offline registered name, else a SMILES, with an optional
    explicit ``name:``/``smiles:``/``inchi:``/``formula:`` prefix (or a bare ``InChI=`` header).  The explicit
    members force one interpretation so an ambiguous string (a name that also happens to parse as SMILES) is
    never silently guessed.
    """

    AUTO = "AUTO"
    NAME = "NAME"
    SMILES = "SMILES"
    INCHI = "INCHI"
    FORMULA = "FORMULA"
    TARGET_FILE = "TARGET_FILE"


class ParseSource(str, Enum):
    """Which resolution path actually produced the identity -- the provenance the receipt echoes."""

    OFFLINE_REGISTRY = "OFFLINE_REGISTRY"      # a registered offline chemical name -> its curated Molecule
    SMILES_PARSER = "SMILES_PARSER"            # the hand-rolled SMILES subset parser -> a Molecule
    FORMULA_PARSER = "FORMULA_PARSER"          # Formula.parse -> a FORMULA-layer identity (no structure)
    INCHI_FORMULA_LAYER = "INCHI_FORMULA_LAYER"  # an InChI's formula sublayer -> a FORMULA-layer identity
    TARGET_FILE = "TARGET_FILE"                # a file whose contents were resolved as an inner target


class IdentityParseError(ValueError):
    """A target string could not be resolved to a molecule at the requested identity kind.

    A :class:`ValueError` subclass so existing ``except ValueError`` call sites (the CLI's ``exit 2`` mapping) keep
    catching it, while a service that wants the *concise domain error, not a traceback* (section 14.2) can catch
    this exact type.
    """


@dataclass(frozen=True)
class ParseReceipt(Digestible):
    """A section-14.2 echo of HOW a target string was resolved -- provenance, not search identity.

    It records the requested kind, the kind it actually resolved as (an AUTO input reports which interpretation
    won), the :class:`ParseSource`, the normalised canonical form (so the caller sees exactly what the string
    became), the finest identity layer perceived (``FORMULA`` or ``CONSTITUTION``), and ordered ``notes`` --
    ambiguity resolution, file provenance, and any InChI layer that was declared but not consumed.
    """

    requested_kind: InputKind
    resolved_kind: InputKind
    source: ParseSource
    normalized: str
    identity_layer: str
    notes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.requested_kind, InputKind) or not isinstance(self.resolved_kind, InputKind):
            raise TypeError("requested_kind and resolved_kind must be InputKind values")
        if not isinstance(self.source, ParseSource):
            raise TypeError("source must be a ParseSource")
        if not isinstance(self.normalized, str) or not self.normalized:
            raise ValueError("normalized must be a non-empty string")
        if self.identity_layer not in ("FORMULA", "CONSTITUTION"):
            raise ValueError("identity_layer must be 'FORMULA' or 'CONSTITUTION'")
        if type(self.notes) is not tuple or any(not isinstance(n, str) or not n for n in self.notes):
            raise TypeError("notes must be a tuple of non-empty strings")

    def summary(self) -> str:
        """One canonical diagnostic line naming the resolution (echoed into the response ``diagnostics``)."""
        kind = (
            self.resolved_kind.value
            if self.resolved_kind is self.requested_kind
            else f"{self.requested_kind.value}->{self.resolved_kind.value}"
        )
        line = (
            f"IDENTITY RESOLVED [{kind}] via {self.source.value}: {self.normalized} "
            f"({self.identity_layer} layer)"
        )
        return f"{line}; {'; '.join(self.notes)}" if self.notes else line


@dataclass(frozen=True)
class ResolvedIdentity:
    """The full result of :func:`resolve_identity`: the perceived identity plus its echo.

    ``molecule`` is a :class:`~smartchem.category.Molecule` when structure was perceivable (NAME/SMILES, or a
    TARGET_FILE resolving to one), else ``None`` (FORMULA / formula-layer INCHI perceive composition only).
    ``formula`` is always present.  ``features`` are the dropped SMILES features (SMILES only).  ``losses`` are the
    typed section-5.3 records the resolution incurred (a formula-layer InChI carries a constitution BLOCKER, etc.).
    """

    molecule: "object | None"
    formula: "object"
    features: "object | None"
    losses: tuple
    receipt: ParseReceipt
    # v0.6 FORMULA-EXPR-01 additions (defaulted, so every existing constructor is unchanged):
    #   * formula_expr -- the lossless syntax object (components/hydrate boundary + provenance) when the
    #     identity was resolved through the human-formula grammar; None for NAME/SMILES/InChI.
    #   * registry_candidates -- the registry-known structures that SHARE this formula, attached only for
    #     a composition-only (molecule is None) resolution.  It is the ambiguity set, and it is
    #     DELIBERATELY not on the receipt (which is digested and pinned): a bare formula names a
    #     composition, and this is what the OFFLINE REGISTRY happens to know with it -- NEVER an
    #     exhaustive isomer enumeration, and never a proof the composition has one/zero real constitutions.
    formula_expr: "object | None" = None
    registry_candidates: tuple = ()
    #   * registry_lookup_ok -- whether the candidate lookup actually RAN (P0-F).  True on a successful
    #     query (whether it found N candidates or zero); False ONLY when the registry was genuinely
    #     unavailable.  A programming error inside the lookup is NOT laundered to "zero candidates" -- it
    #     propagates.  So an empty registry_candidates means "queried, none known" iff this is True.
    registry_lookup_ok: bool = True

    @property
    def structure_perceived(self) -> bool:
        """Whether a real bond graph was perceived (so a structure search may run on it)."""
        return self.molecule is not None

    @property
    def constitution_established(self) -> bool:
        """Whether a single molecular constitution is actually selected (structure perceived).

        The v0.6 identity law: composition known is NOT constitution established.  A FORMULA-layer
        identity is ``structure_perceived is False`` even when :attr:`registry_candidates` is non-empty,
        because a registry candidate set is what the catalog knows, not a selected structure.
        """
        return self.molecule is not None


def _split_inline_prefix(text: str) -> "tuple[InputKind | None, str]":
    """Split an inline ``kind:payload`` prefix, or auto-detect a bare ``InChI=`` header.

    Returns ``(forced_kind, payload)`` when an explicit prefix (or the unambiguous InChI header) is present, else
    ``(None, text)``.  An InChI string carries no leading ``:`` before its first ``/``, so it is never mistaken
    for a ``kind:`` prefix; only the exact ``InChI=`` header auto-selects INCHI.
    """
    if text.startswith("InChI="):
        return InputKind.INCHI, text
    if ":" in text:
        prefix, rest = text.split(":", 1)
        forced = _INLINE_PREFIXES.get(prefix.casefold())
        if forced is not None:
            return InputKind(forced), rest
    return None, text


def _inchi_layer_int(value: str, text: str) -> int:
    """Parse one signed integer from an InChI ``/q`` or ``/p`` layer; refuse a per-component (``;``) layer."""
    if ";" in value or "*" in value:
        raise IdentityParseError(
            f"InChI {text!r} has a per-component charge/proton layer ({value!r}); this parser resolves a single "
            "species -- supply one component"
        )
    try:
        return int(value)
    except ValueError:
        raise IdentityParseError(f"could not parse the InChI charge/proton layer {value!r} in {text!r}") from None


def _inchi_formula_layer(text: str) -> "tuple[object, tuple, tuple[str, ...]]":
    """Resolve an InChI's FORMULA SUBLAYER to a Formula, plus the section-5.3 losses and receipt notes it implies.

    Standard InChI is ``InChI=<version>/<formula>[/c...][/h...][/q...][/p...][/b...][/t...][/m...][/s...][/i...]``.
    What is CONSUMED vs dropped (never silently): the formula token AND the CHARGE.  Standard InChI carries charge
    ONLY in ``/q`` (net charge) and ``/p`` (proton balance -- a proton is an H+, so it shifts BOTH the H count and
    the charge); the formula token is never charged.  Ignoring ``/q``/``/p`` would turn every cation/anion into its
    NEUTRAL (a soundness break: ``[NH4+]`` would collide with NH3), so they are parsed into the true charge and H
    count.  The ``/c`` (and ``/h``) connectivity is NOT parsed -- full InChI->structure inversion needs InChI's
    canonical numbering, which this offline parser does not reimplement -- so it is a real ``molecular-constitution``
    BLOCKER; a stereo layer (``/t``/``/b``/``/m``/``/s``) is a stereo BLOCKER and ``/i`` an isotope BLOCKER.  ANY
    layer this parser neither consumes nor lowers to a loss is NAMED in a receipt note, so the receipt genuinely
    names every unconsumed layer (fail-closed).  Multi-component InChIs (a ``.`` in the formula) are refused.
    """
    from .decompiler import DecompilerError, Formula
    from .identity import formula_reduction_loss, isotope_loss, stereo_loss

    body = text[len("InChI="):] if text.startswith("InChI=") else text
    parts = body.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise IdentityParseError(
            f"malformed InChI {text!r}: expected 'InChI=<version>/<formula>[/...layers]'"
        )
    formula_token = parts[1]
    if "." in formula_token:
        raise IdentityParseError(
            f"InChI {text!r} names a multi-component species (a '.' in the formula layer); this parser resolves a "
            "single species -- supply one component"
        )
    layers = [p for p in parts[2:] if p]
    layer_tags = {p[0] for p in layers}

    # CONSUME the charge layers: /q (net charge) and /p (proton balance; each proton is an H+).
    q_charge = sum(_inchi_layer_int(p[1:], text) for p in layers if p[0] == "q")
    p_protons = sum(_inchi_layer_int(p[1:], text) for p in layers if p[0] == "p")
    try:
        counts = dict(Formula.parse(formula_token).counts)
    except DecompilerError as exc:
        raise IdentityParseError(f"could not parse the InChI formula layer {formula_token!r}: {exc}") from exc
    if p_protons:
        counts["H"] = counts.get("H", 0) + p_protons
        if counts["H"] < 0:
            raise IdentityParseError(f"InChI {text!r} removes more protons (/p) than the species has hydrogens")
        if counts["H"] == 0:
            del counts["H"]
    charge = q_charge + p_protons
    try:
        formula = Formula.of(counts, charge)
    except (DecompilerError, ValueError) as exc:
        raise IdentityParseError(f"could not build the formula for InChI {text!r}: {exc}") from exc

    losses: list = []
    notes: list[str] = []
    if "c" in layer_tags or "h" in layer_tags:
        losses.append(formula_reduction_loss(text, formula_token))
        notes.append("the /c and/or /h connectivity layer was declared but not parsed (resolved at the FORMULA layer)")
    stereo_tags = {"t", "b", "m", "s"} & layer_tags
    if stereo_tags:
        losses.append(stereo_loss(text, double_bond=("b" in stereo_tags and "t" not in stereo_tags)))
        notes.append("a stereochemistry layer (/t, /b, /m or /s) was declared but is not represented")
    if "i" in layer_tags:
        losses.append(isotope_loss(text))
        notes.append("an isotope layer (/i) was declared but is not represented")
    if charge:
        notes.append(f"a charge layer (/q, /p) was consumed: net charge {charge:+d}")
    # name any OTHER layer neither consumed (q, p) nor lowered to a loss (c, h, t, b, m, s, i) -- fail-closed honesty.
    for tag in sorted(layer_tags - {"c", "h", "t", "b", "m", "s", "i", "q", "p"}):
        notes.append(f"an InChI '/{tag}' layer was declared but not consumed (resolved at the FORMULA layer)")
    return formula, tuple(losses), tuple(notes)


def _registry_candidates(formula: "object") -> "tuple[tuple, bool]":
    """The registry-known named structures sharing ``formula``, and whether the lookup RAN (P0-F).

    Returns ``(candidates, lookup_ok)``.  ``candidates`` is what the OFFLINE registry happens to carry with
    this composition -- explicitly NOT an exhaustive isomer enumeration, and a miss (empty tuple with
    ``lookup_ok`` True) is NOT evidence that no such molecule exists.  This distinguishes the three states the
    old ``except Exception: return ()`` collapsed into one (which laundered any internal failure into the
    epistemic statement "the registry knows no candidate"):

    * lookup succeeded, N candidates  -> ``(candidates, True)``;
    * lookup succeeded, zero candidates -> ``((), True)``;
    * registry module genuinely unavailable -> ``((), False)``.

    Only :class:`ImportError` (the registry stack is absent) is caught, and it yields ``lookup_ok=False`` --
    NOT a fabricated empty candidate set.  ``known_compounds`` itself is a pure dict lookup on a
    :class:`~smartchem.decompiler.Formula`; a programming error in it is a real bug and PROPAGATES (fail-loud
    to the section-14.4 internal-error path), never silently becomes "zero candidates".
    """
    try:
        from .structure import known_compounds
    except ImportError:
        return (), False
    return known_compounds(formula), True


def _resolve_formula_layer(
    requested: "InputKind", payload: str, prefix_note: "str | None", *, auto: bool
) -> "ResolvedIdentity":
    """Resolve a FORMULA-layer identity through the v0.6 lossless human-formula grammar (FORMULA-EXPR-01).

    Parses ``payload`` to a :class:`~smartchem.formula_expr.FormulaExpr` (preserving hydrate/adduct
    component boundaries and the normalization applied), projects it to the conservation
    :class:`~smartchem.decompiler.Formula`, and returns a COMPOSITION-ONLY identity (``molecule is None``)
    carrying the syntax object and the registry-known candidate set.  ``auto=True`` records that this was
    an AUTO resolution reached only after name and SMILES both declined.  Raises
    :class:`~smartchem.formula_expr.FormulaSyntaxError` on a malformed/parametric string; the CALLER maps
    that to the right :class:`IdentityParseError`.
    """
    from .formula_expr import parse_formula_expr

    expr = parse_formula_expr(payload)
    formula = expr.to_formula()
    notes: list[str] = []
    if prefix_note:
        notes.append(prefix_note)
    if auto:
        notes.append("auto-detected as a chemical formula (no offline name or SMILES matched)")
    notes.extend(expr.notes)
    receipt = ParseReceipt(
        requested, InputKind.FORMULA, ParseSource.FORMULA_PARSER, _hill(formula), "FORMULA", tuple(notes)
    )
    candidates, lookup_ok = _registry_candidates(formula)
    return ResolvedIdentity(
        None, formula, None, (), receipt,
        formula_expr=expr, registry_candidates=candidates, registry_lookup_ok=lookup_ok,
    )


def resolve_identity(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO) -> ResolvedIdentity:
    """Resolve ``target_input`` under ``input_kind`` to a typed :class:`ResolvedIdentity` (the one parser service).

    Raises :class:`IdentityParseError` on an unresolvable/ambiguous string or a form this offline parser cannot
    honour -- never a raw traceback and never a silent mis-parse.
    """
    from .decompiler import Formula
    from .smiles import SmilesError, parse_smiles_features
    from .structure import structure_by_name

    if not isinstance(target_input, str):
        raise IdentityParseError("target_input must be a string")
    requested = InputKind(input_kind) if not isinstance(input_kind, InputKind) else input_kind

    # -- TARGET_FILE: read the file, resolve its contents as an inner target ------------------------------------
    if requested is InputKind.TARGET_FILE:
        return _resolve_target_file(target_input)

    # -- AUTO / NAME / SMILES: recognise an inline prefix (or a bare InChI header) -------------------------------
    kind = requested
    payload = target_input
    prefix_note: "str | None" = None
    if kind is InputKind.AUTO:
        forced, rest = _split_inline_prefix(target_input)
        if forced is not None:
            kind, payload = forced, rest
            prefix_note = (
                "recognised a bare 'InChI=' header"
                if rest == target_input                          # nothing stripped => the header auto-detect
                else f"an explicit '{forced.value.lower()}:' interpretation was requested"
            )

    # -- INCHI: resolve the formula sublayer only (loud, fail-closed) --------------------------------------------
    if kind is InputKind.INCHI:
        formula, losses, layer_notes = _inchi_formula_layer(payload)
        notes = (prefix_note, *layer_notes) if prefix_note else layer_notes
        receipt = ParseReceipt(
            requested, InputKind.INCHI, ParseSource.INCHI_FORMULA_LAYER, _hill(formula), "FORMULA", notes
        )
        candidates, lookup_ok = _registry_candidates(formula)
        return ResolvedIdentity(
            None, formula, None, losses, receipt,
            registry_candidates=candidates, registry_lookup_ok=lookup_ok,
        )

    # -- FORMULA: composition only, no structure (v0.6 tolerant human grammar) -----------------------------------
    if kind is InputKind.FORMULA:
        from .formula_expr import FormulaSyntaxError

        try:
            return _resolve_formula_layer(requested, payload, prefix_note, auto=False)
        except FormulaSyntaxError as exc:
            raise IdentityParseError(f"could not parse {payload!r} as a chemical formula: {exc}") from exc

    # -- NAME / SMILES (and AUTO's name-first, else-SMILES resolution) -------------------------------------------
    if kind is not InputKind.SMILES:
        named = structure_by_name(payload)
        if named is not None:
            molecule = named.molecule
            notes = (prefix_note,) if prefix_note else (f"resolved offline name {named.name!r}",)
            receipt = ParseReceipt(
                requested, InputKind.NAME, ParseSource.OFFLINE_REGISTRY,
                _hill(Formula.of(molecule.formula, molecule.charge)), "CONSTITUTION", notes,
            )
            return ResolvedIdentity(molecule, Formula.of(molecule.formula, molecule.charge), None, (), receipt)
        if kind is InputKind.NAME:
            raise IdentityParseError(
                f"unknown offline chemical name {payload!r}; provide SMILES (optionally smiles:...) or use "
                "a registered name"
            )

    try:
        molecule, features = parse_smiles_features(payload)
    except SmilesError as exc:
        # AUTO fallthrough: name declined, SMILES declined -> LAST, try the tolerant formula grammar.  This
        # is additive and strictly last, so it can never STEAL a string a registered name or SMILES already
        # claimed (the anti-Mutant-5 ordering).  An explicit smiles: input never reaches here as a formula:
        # the caller asked for SMILES, so a SMILES failure stays a SMILES failure.
        if kind is InputKind.AUTO:
            from .formula_expr import FormulaSyntaxError

            try:
                return _resolve_formula_layer(requested, payload, prefix_note, auto=True)
            except FormulaSyntaxError as formula_exc:
                raise IdentityParseError(
                    f"could not resolve {target_input!r} as an offline name, SMILES, or chemical formula: "
                    f"SMILES said {exc}; formula said {formula_exc}; "
                    "use name:..., smiles:..., or formula:... to make the input form explicit"
                ) from exc
        raise IdentityParseError(
            f"could not resolve {target_input!r} as an offline name or parse it as SMILES: {exc}; "
            "use name:... or smiles:... to make the input form explicit"
        ) from exc
    formula = Formula.of(molecule.formula, molecule.charge)
    notes = (prefix_note,) if prefix_note else ()
    receipt = ParseReceipt(
        requested, InputKind.SMILES, ParseSource.SMILES_PARSER, _hill(formula), "CONSTITUTION", notes
    )
    return ResolvedIdentity(molecule, formula, features, (), receipt)


@dataclass(frozen=True)
class InputKindAmbiguity:
    """Two or more input-kind readings of ONE bare AUTO string that resolve to materially-distinct identities.

    ``CO`` parses as SMILES (methanol, a CONSTITUTION) AND as a chemical formula (carbon monoxide, C1O1, a
    FORMULA layer): two plausible readings that disagree on composition and layer.  The legacy AUTO precedence
    (name -> SMILES -> formula-last) silently picks the first, which is correct for the expert commands but
    wrong for the human ``plan`` front door -- launching structural synthesis for one interpretation while
    another materially disagrees is exactly the guess v0.6 exists to refuse (P0-A).

    This is the explicit alternate-interpretation representation the front door exposes so ``plan`` can refuse
    to choose until the caller supplies an explicit kind (``smiles:CO`` / ``formula:CO``).  ``interpretations``
    is an ordered tuple of ``(InputKind, ResolvedIdentity)`` in legacy precedence (structure reading first).
    """

    target_input: str
    interpretations: tuple

    @property
    def kinds(self) -> "tuple[InputKind, ...]":
        return tuple(kind for kind, _ in self.interpretations)

    def summary(self) -> str:
        """One line naming each reading -- kind, normalized composition, and identity layer."""
        parts = [
            f"{kind.value}->{ident.receipt.normalized} ({ident.receipt.identity_layer})"
            for kind, ident in self.interpretations
        ]
        return (
            f"{self.target_input!r} is input-kind ambiguous ({' | '.join(parts)}); "
            "supply an explicit kind (e.g. smiles:… or formula:…) to choose"
        )


def detect_auto_ambiguity(target_input: str) -> "InputKindAmbiguity | None":
    """The cross-kind ambiguity of a bare AUTO human input, or ``None`` (P0-A).

    Returns an :class:`InputKindAmbiguity` iff more than one input-kind parser succeeds AND the readings are
    materially distinct (they differ in identity layer or composition).  It is meaningful ONLY for a bare AUTO
    string: an explicit inline prefix (``smiles:``/``formula:``/…) or a bare ``InChI=`` header is a DECISION,
    not an ambiguity, so those return ``None`` immediately.

    It does not change :func:`resolve_identity`'s AUTO precedence (the expert commands keep it, and the
    anti-Mutant-5 ordering is untouched); it is a separate, additive perception the ``plan`` front door reads to
    refuse a silent structural launch on an ambiguous paste.  The structure reading is the legacy AUTO answer
    when that perceives a structure (NAME/SMILES); the formula reading is the tolerant human-formula grammar.
    """
    if not isinstance(target_input, str):
        return None
    from .formula_expr import FormulaSyntaxError

    # an explicit inline prefix / InChI header is an explicit kind decision -> never ambiguous.
    forced, _ = _split_inline_prefix(target_input)
    if forced is not None:
        return None

    interpretations: list = []
    # (1) the structure reading: the legacy AUTO answer, kept only if it perceived a real structure (NAME/SMILES).
    try:
        structure = resolve_identity(target_input, InputKind.AUTO)
        if structure.structure_perceived:
            interpretations.append((structure.receipt.resolved_kind, structure))
    except IdentityParseError:
        pass
    # (2) the formula reading: the tolerant human-formula grammar, tried directly (independent of precedence).
    try:
        formula = _resolve_formula_layer(InputKind.AUTO, target_input, None, auto=True)
        interpretations.append((InputKind.FORMULA, formula))
    except FormulaSyntaxError:
        pass

    if len(interpretations) < 2:
        return None
    # materially distinct iff the readings disagree on (identity layer, normalized composition).
    signatures = {(ident.receipt.identity_layer, ident.receipt.normalized) for _, ident in interpretations}
    if len(signatures) < 2:
        return None
    return InputKindAmbiguity(target_input, tuple(interpretations))


def _resolve_target_file(target_input: str) -> ResolvedIdentity:
    """Read a TARGET_FILE and resolve its contents as an inner target, preserving the inner receipt + a file note."""
    import os

    if not os.path.isfile(target_input):
        raise IdentityParseError(f"target file {target_input!r} does not exist or is not a regular file")
    if os.path.getsize(target_input) > _MAX_TARGET_FILE_BYTES:
        raise IdentityParseError(
            f"target file {target_input!r} is larger than {_MAX_TARGET_FILE_BYTES} bytes; a target spec is a short "
            "string, not a data file"
        )
    try:
        with open(target_input, encoding="utf-8") as handle:
            contents = handle.read().strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise IdentityParseError(f"could not read target file {target_input!r}: {exc}") from exc
    if not contents:
        raise IdentityParseError(f"target file {target_input!r} is empty")
    # resolve the contents on the AUTO path (which honours name:/smiles:/inchi:/formula: prefixes + a bare InChI=).
    inner = resolve_identity(contents, InputKind.AUTO)
    note = f"read target from file {os.path.basename(target_input)!r}"
    receipt = ParseReceipt(
        InputKind.TARGET_FILE, inner.receipt.resolved_kind, ParseSource.TARGET_FILE,
        inner.receipt.normalized, inner.receipt.identity_layer, (note, *inner.receipt.notes),
    )
    # P0-E transport law: a TARGET_FILE must perceive the SAME identity as resolving its contents directly --
    # differing only in file provenance.  So forward the v0.6 syntax layer and the ambiguity set/status; dropping
    # them here silently lost the formula grammar (formula_syntax, registry candidates) for a formula file.
    return ResolvedIdentity(
        inner.molecule, inner.formula, inner.features, inner.losses, receipt,
        formula_expr=inner.formula_expr,
        registry_candidates=inner.registry_candidates,
        registry_lookup_ok=inner.registry_lookup_ok,
    )


def _hill(formula: "object") -> str:
    """A Hill-order formula string (C first, H second, then alphabetical) for the receipt echo."""
    counts = dict(formula.counts)
    order = []
    if "C" in counts:
        order.append("C")
        if "H" in counts:
            order.append("H")
    order.extend(sorted(s for s in counts if s not in order))
    body = "".join(f"{s}{counts[s] if counts[s] > 1 else ''}" for s in order)
    charge = getattr(formula, "charge", 0)
    if charge:
        body += f" {'+' if charge > 0 else '-'}{abs(charge) if abs(charge) != 1 else ''}".rstrip()
    return body


def resolve_target(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO):
    """Resolve ``target_input`` to a :class:`~smartchem.category.Molecule` under ``input_kind``.

    Thin wrapper over :func:`resolve_identity` for the many call sites that need only the molecule.  A form that
    perceives no structure (FORMULA / formula-layer INCHI) raises :class:`IdentityParseError`: a bare formula names
    composition, not a molecule, so a structure search cannot run on it (section 5.4).
    """
    return _require_molecule(resolve_identity(target_input, input_kind))[0]


def resolve_target_with_features(target_input: str, input_kind: "InputKind | str" = InputKind.AUTO):
    """Like :func:`resolve_target`, but also return the SMILES features that were dropped (ID-STEREO-01).

    Returns ``(molecule, features)`` where ``features`` is a :class:`~smartchem.smiles.SmilesFeatures` when the
    input resolved via SMILES, or ``None`` when it resolved as a registered NAME.  Shares the exact resolution path
    with :func:`resolve_identity`, so the two can never disagree on the molecule.
    """
    return _require_molecule(resolve_identity(target_input, input_kind))


def resolve_cli_target(
    positional: "str | None",
    input_kind_flag: "str | None",
    explicit_forms: "dict[str, str | None]",
) -> "tuple[str, InputKind | None]":
    """Resolve the section-14.2 CLI identity surface to ``(target_string, input_kind)`` -- the ONE place the
    positional target, the ``--input-kind`` flag, and the explicit value-form flags (``--name``/``--smiles``/
    ``--inchi``/``--formula``/``--target-file``) are reconciled, shared by every chemical CLI so they cannot drift.

    Exactly ONE source of the target is required: the positional (optionally with ``--input-kind``), OR exactly one
    explicit value-form flag.  Zero sources, more than one, or an explicit form combined with ``--input-kind`` (the
    form already IS the kind) is a loud :class:`IdentityParseError` -- a concise domain error (section 14.2), never
    a silent guess.  ``explicit_forms`` maps each form name in :data:`EXPLICIT_CLI_FORMS` to its flag value (or
    ``None`` if absent).  Returns the ``InputKind`` the chosen form forces, or ``None`` (AUTO / the raw flag) for the
    positional so the caller's default table still records the origin.
    """
    given = [(name, value) for name, value in explicit_forms.items() if value is not None]
    if len(given) > 1:
        names = ", ".join(f"--{n}" for n, _ in given)
        raise IdentityParseError(f"give the target ONE way, not several: {names} are mutually exclusive")
    if given:
        name, value = given[0]
        if positional is not None:
            raise IdentityParseError(
                f"give the target ONE way: both a positional target and --{name} were supplied"
            )
        if input_kind_flag is not None:
            raise IdentityParseError(
                f"--{name} already fixes the input kind; do not also pass --input-kind"
            )
        forced = dict(EXPLICIT_CLI_FORMS)[name]
        return value, InputKind(forced)
    if positional is None:
        raise IdentityParseError(
            "no target given: supply a positional target or one of "
            + ", ".join(f"--{n}" for n, _ in EXPLICIT_CLI_FORMS)
        )
    if input_kind_flag is None:
        return positional, None
    # self-validate the kind rather than trust the caller to pre-restrict it: an unknown/empty --input-kind is a
    # loud domain error (exit 2), never a bare KeyError that would launder to exit-70 ERROR_INTERNAL if a future
    # caller (a new CLI, the typed service) hands the shared resolver an unvalidated string (red-team fold).  A
    # present-but-empty flag is "given but invalid" -- checked via `is not None`, matching the value-form branch.
    try:
        return positional, InputKind[input_kind_flag.upper().replace("-", "_")]
    except KeyError:
        raise IdentityParseError(
            f"unknown input kind {input_kind_flag!r}; expected one of "
            + ", ".join(k.value.lower().replace("_", "-") for k in InputKind)
        ) from None


def _require_molecule(resolved: ResolvedIdentity):
    """Return ``(molecule, features)`` from a resolution, or raise if no structure was perceived."""
    if resolved.molecule is None:
        raise IdentityParseError(
            f"{resolved.receipt.requested_kind.value} input resolved to a {resolved.receipt.identity_layer}-layer "
            f"identity ({resolved.receipt.normalized}) with no perceived structure; a structure search needs a "
            "molecule (NAME or SMILES), not a bare formula/InChI (section 5.4)"
        )
    return resolved.molecule, resolved.features
