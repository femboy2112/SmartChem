"""FORMULA-EXPR-01: the lossless human-formula syntax layer (v0.6 Human Chemical Front Door).

:class:`~smartchem.decompiler.Formula` is an atom-count multiset -- the correct *conservation*
quotient, but too early a quotient for tolerant human input.  ``CuSO4.5H2O`` and its Unicode
twin ``CuSO4·5H2O`` both name copper(II) sulfate pentahydrate: five distinct water molecules
loosely held to one sulfate.  Project straight to atoms and that structure is gone -- ``Cu H10 O9 S``
remembers nothing about the hydrate boundary that a chemist, a supplier, or a preprocessing step
still cares about.

So this module inserts one representation *before* :class:`Formula`:

    raw spelling  ->  FormulaExpr (components + charge + provenance)  ->  Formula (atom multiset)

:class:`FormulaExpr` preserves the component/adduct/hydrate boundaries, the original spelling, and
the normalization that was applied to reach a machine-clean form.  :meth:`FormulaExpr.to_formula`
is the *forgetful* projection to the conservation quotient: deterministic and conservation-correct
by construction (it never invents or drops an atom).

Two laws this layer refuses to break, because breaking them is the whole failure mode v0.6 exists
to kill:

* **Formula -> structure is a RELATION, not a function.**  A composition is not a constitution; this
  layer perceives composition and NOTHING about the bond graph.  It never guesses a structure.
* **Never silently coerce syntax you do not understand.**  A parametric/polymer form (``(C2H4)n``,
  ``MxOy``, an interval ``C6H(12±2)O6``) is *refused with a typed reason*
  (:class:`ParametricFormulaError`), never flattened into a concrete count that lies about what was
  meant.  Malformed input is refused (:class:`FormulaSyntaxError`); it never normalizes into an
  unrelated valid formula.

The grammar is deliberately finite -- the smallest durable thing that eats the "copy a formula off
Wikipedia" surface.  What is *supported* (and every one is pinned by a committed test):
ASCII formulas, Unicode subscript counts, a Unicode middle-dot (``·``) or a SPACED ASCII-dot
(``CuSO4 . 5 H2O``) hydrate separator with a leading component multiplier, harmless whitespace, nested
``()`` and ``[]`` grouping, and the charge spellings ``NH4+``, ``[NH4]+``, ``SO4^2-``, ``SO4²⁻``
(Unicode superscript), ``[Fe(CN)6]4-``.  Everything else is one of the typed refusals above.  Nothing
here needs RDKit or any network.

What this layer's IDENTITY (digest / equality) preserves, precisely -- it is lossless for these and NOT
more, so nothing here overclaims:

* the **component / hydrate-adduct boundary** (``CuSO4·5H2O`` keeps its two components; a flatten is a
  different :class:`FormulaExpr`);
* the exact **composition** and supported **charge**;
* the raw and normalized **spelling**, as ``compare=False`` provenance (so Unicode/ASCII twins are equal).

What it deliberately **quotients away** is *intra-component* grouping: ``(NH4)2SO4`` and ``N2H8SO4`` are the
SAME :class:`FormulaExpr` because they name one composition, and v0.6 does NOT establish a constitution --
promoting a parenthesization to an identity distinction would smuggle in exactly the bond-graph claim this
layer refuses to make.  Grouping stays *visible* in ``original``/``source`` provenance; a
grouping-as-identity (a MaterialBucket) is a later-version (0.9) boundary, and ``tests/test_formula_expr.py``
pins the quotient explicitly so it is a documented decision, not a silent loss.

Ambiguous ASCII flattenings are refused rather than guessed, because guessing is exactly the v0.6 failure
mode: a compact ``digit.digit`` (a decimal, which the Unicode/spaced hydrate separators are not -- P0-C, and
checked after subscript folding so ``C₁.5H₂`` cannot slip past) and a bare-sign ion whose trailing digits
could be an atom count or the charge magnitude -- a single-element body (``Fe3+``/``O2-``) or any ``>=2``-digit
trailing run (``SO42-``/``PO43-``) (:class:`AmbiguousChargeError` -- P0-B); both name the unambiguous spelling
to use instead.  A leading whole-expression coefficient (``5H2O``) is refused too: it is a stoichiometric
quantity, not one molecular identity (P0-D).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import Digestible
from .decompiler import DecompilerError, Formula

__all__ = [
    "FormulaSyntaxError",
    "ParametricFormulaError",
    "AmbiguousChargeError",
    "FormulaComponent",
    "FormulaExpr",
    "normalize_formula_text",
    "parse_formula_expr",
]

# -- guards: a pasted chemical identity is a SHORT string, not a program --------------------------
# The user is pasting an identity, not submitting a blob; a pathological input is a wrong input,
# refused loudly rather than allowed to drive a backtracking/exponential grammar.  These bounds are
# generous for any real formula (the longest ordinary hydrate is a few dozen characters) and cheap
# to check, so they can never be the reason a genuine paste fails.
_MAX_INPUT_LEN = 512
_MAX_NESTING_DEPTH = 32

# Unicode subscript digits -> ASCII count digits (C₈H₁₀N₄O₂ -> C8H10N4O2).
_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
# Unicode superscript digits/signs -> ASCII, used ONLY inside a charge suffix (SO₄²⁻ -> SO4^2-).
_SUPERSCRIPTS = str.maketrans(
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-"
)
_SUPERSCRIPT_CHARS = frozenset("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
# Every glyph a source uses for the hydrate/adduct dot; all normalize to one canonical ASCII '.' for parsing.
# The degree sign '°' is NOT here (P0-C): it is a temperature/angle glyph, never a hydrate dot, and admitting
# it silently turned 'CuSO4°5H2O' into a valid adduct.  Only genuine dot glyphs are separators.
_SEPARATOR_CHARS = "·⋅•∙"  # middle dot, dot operator, bullet, bullet operator
_CANONICAL_SEP = "."  # the internal parse separator (normalize folds every dot glyph to this)
_RENDER_SEP = "·"     # the canonical RENDER separator (a middle-dot, never an ambiguous compact ASCII '.')
_ASCII_DIGITS = "0123456789"

# Markers that make an expression PARAMETRIC (a family of molecules, not one) -- refused, not coerced.
# 'n'/'m'/'x'/'y' as a *standalone count position* is a variable subscript; '±'/'~' is an interval.
_INTERVAL_CHARS = "±~"


class FormulaSyntaxError(ValueError):
    """A string is not admissible under the finite v0.6 human-formula grammar.

    A :class:`ValueError` subclass so the identity front door's existing ``except (ValueError, ...)``
    mapping keeps catching it, while a caller that wants the exact typed refusal can catch this class.
    """


class ParametricFormulaError(FormulaSyntaxError):
    """The string is well-formed but PARAMETRIC -- it names a family, not one concrete molecule.

    ``(C2H4)n``, ``C6H(12±2)O6``.  A *subclass* of :class:`FormulaSyntaxError` (so a plain
    ``except FormulaSyntaxError`` still catches it), raised as its own type so a consumer can tell
    "outside the grammar because parametric" apart from "malformed".  It is NEVER downgraded to a
    concrete count: coercing ``(C2H4)n`` to ``C2H4`` would be a fabricated identity.  (``MxOy`` is
    refused as a plain :class:`FormulaSyntaxError` -- its ``Mx``/``Oy`` read as unknown 2-letter element
    symbols, indistinguishable at the syntax layer from a genuine typo, so it fails as an unknown element.)
    """


class AmbiguousChargeError(FormulaSyntaxError):
    """An ASCII ion spelling whose two readings materially differ -- refused, not guessed (P0-B).

    Two cases are ambiguous because a flattened ASCII cannot say whether a trailing digit is an atom count or
    (part of) the charge magnitude: (1) a **single-element** body with a trailing digit run before a *bare*
    sign (``Fe3+`` → ``Fe3``±1 vs ``Fe``±3; also ``Ca2+``, ``O2-``, ``C60-``); and (2) **any** body whose
    trailing run before a bare sign is **two or more digits** (``SO42-`` → ``SO4``+``2-`` vs ``SO42``+``1-``;
    also ``PO43-``, ``CO32-``, ``Cr2O72-``) -- accepting it would fail open to an absurd 42-oxygen composition.
    A **multi-element** body with a **single** trailing digit (``NH4+``, ``NO3-``) is unambiguous -- that digit
    is the last element's count and the bare sign is ±1 -- and is accepted.  A *subclass* of
    :class:`FormulaSyntaxError`, so the identity front door's
    ``except FormulaSyntaxError`` maps it to a typed :class:`~smartchem.identity_parse.IdentityParseError`,
    while a caller can catch this exact type.  The message names the unambiguous spellings (caret, Unicode
    superscript, or bracket ion) that resolve it -- fail-closed over a silent mis-charge.
    """


@dataclass(frozen=True)
class FormulaComponent(Digestible):
    """One component of a (possibly multi-part) formula expression: ``multiplier × formula``.

    In ``CuSO4.5H2O`` the two components are ``(1, CuSO4)`` and ``(5, H2O)``.  The component is the
    unit the hydrate/adduct boundary is drawn around; :attr:`multiplier` is the leading stoichiometric
    count after a separator.  :attr:`formula` is the neutral atom multiset of ONE unit of this
    component (charge lives on the whole :class:`FormulaExpr`, since v0.6 resolves a single species).

    Identity is ``(multiplier, formula)``; :attr:`source` is the raw spelling and is provenance only,
    excluded from the digest and equality so two spellings of the same component collapse.
    """

    multiplier: int
    formula: Formula
    source: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if type(self.multiplier) is not int or self.multiplier <= 0:
            raise FormulaSyntaxError(f"component multiplier must be a positive int, got {self.multiplier!r}")
        if not isinstance(self.formula, Formula):
            raise TypeError("component formula must be a Formula")


@dataclass(frozen=True)
class FormulaExpr(Digestible):
    """A lossless syntax-level formula: ordered components, an overall charge, and its provenance.

    Identity (digest / equality) is ``(components, charge)`` -- the syntax structure that MATTERS.
    ``original``/``normalized``/``notes`` are provenance (``compare=False``): the raw spelling, the
    machine-clean spelling it was normalized to, and ordered notes naming every non-trivial thing the
    normalizer did (Unicode translated, a charge consumed, multiple components seen).  Because they do
    not enter the digest, ``CuSO4.5H2O`` and ``CuSO4·5H2O`` are the SAME :class:`FormulaExpr`.
    """

    components: tuple[FormulaComponent, ...]
    charge: int = 0
    original: str = field(default="", compare=False)
    normalized: str = field(default="", compare=False)
    notes: tuple[str, ...] = field(default=(), compare=False)

    def __post_init__(self) -> None:
        if type(self.components) is not tuple or not self.components:
            raise FormulaSyntaxError("a formula expression must have at least one component")
        if any(not isinstance(c, FormulaComponent) for c in self.components):
            raise TypeError("components must be FormulaComponent values")
        if type(self.charge) is not int:
            raise TypeError("charge must be an integer number of elementary charges")

    @property
    def is_multi_component(self) -> bool:
        """True iff a hydrate/adduct boundary is present (more than one component)."""
        return len(self.components) > 1

    def to_formula(self) -> Formula:
        """Project to the atom-count :class:`Formula` -- the deterministic, conservation-correct quotient.

        Sums ``multiplier * atoms`` across every component and attaches the overall charge.  This is the
        FORGETFUL map: the component/hydrate boundary is dropped here (and only here), which is exactly
        why :class:`FormulaExpr` retains it upstream.  Every atom is conserved by construction -- nothing
        is invented, nothing is dropped.
        """
        totals: dict[str, int] = {}
        for component in self.components:
            for symbol, count in component.formula.counts:
                totals[symbol] = totals.get(symbol, 0) + count * component.multiplier
        return Formula.of(totals, self.charge)

    def render(self) -> str:
        """A canonical rendering that reparses (via :func:`parse_formula_expr`) to an equal expression.

        Components joined by the canonical ``.`` separator, each ``[multiplier]body``, then the charge
        suffix in caret form (``^2-``) so it round-trips unambiguously.
        """
        parts = []
        for component in self.components:
            body = _render_formula_body(component.formula)
            parts.append(f"{component.multiplier}{body}" if component.multiplier != 1 else body)
        # join with the middle-dot, never a compact ASCII '.' -- a rendered 'CuSO4·5H2O' reparses cleanly,
        # whereas the compact 'CuSO4.5H2O' would be caught by the decimal guard (P0-C) and fail to round-trip.
        text = _RENDER_SEP.join(parts)
        if self.charge:
            mag = abs(self.charge)
            text += f"^{mag if mag != 1 else ''}{'+' if self.charge > 0 else '-'}"
        return text


def _render_formula_body(formula: Formula) -> str:
    """Hill-ish element string for one component (C, H, then alphabetical), no charge."""
    counts = dict(formula.counts)
    order: list[str] = []
    if "C" in counts:
        order.append("C")
        if "H" in counts:
            order.append("H")
    order.extend(sorted(s for s in counts if s not in order))
    return "".join(f"{s}{counts[s] if counts[s] > 1 else ''}" for s in order)


def normalize_formula_text(text: str) -> str:
    """Normalize a human formula spelling to a machine-clean ASCII form, losslessly for composition.

    Idempotent (``normalize(normalize(x)) == normalize(x)``).  It: translates Unicode subscript digits
    to ASCII counts; converts a Unicode superscript charge run (``²⁻``) to caret form (``^2-``) so the
    subscript/superscript distinction that ASCII would otherwise lose is PRESERVED; folds every
    middle-dot variant to a single ``.`` separator; and strips whitespace that surrounds a separator
    and collapses interior runs.  It does NOT decide validity -- that is :func:`parse_formula_expr` --
    it only produces the canonical spelling that parser reads.
    """
    if not isinstance(text, str):
        raise FormulaSyntaxError("formula text must be a string")
    if len(text) > _MAX_INPUT_LEN:
        raise FormulaSyntaxError(
            f"formula text is {len(text)} chars; a pasted chemical identity must be <= {_MAX_INPUT_LEN}"
        )
    work = text.strip()
    if not work:
        raise FormulaSyntaxError("formula text must be a non-empty string")

    # 1) subscript counts -> ASCII digits.
    work = work.translate(_SUBSCRIPTS)

    # 2) superscript charge run -> caret form.  A maximal run of superscript glyphs is a charge suffix;
    #    emit it as '^' + its ASCII translation so '²⁻' becomes '^2-' (never merged into the count digits).
    out: list[str] = []
    i, n = 0, len(work)
    while i < n:
        ch = work[i]
        if ch in _SUPERSCRIPT_CHARS:
            j = i
            while j < n and work[j] in _SUPERSCRIPT_CHARS:
                j += 1
            out.append("^")
            out.append(work[i:j].translate(_SUPERSCRIPTS))
            i = j
        else:
            out.append(ch)
            i += 1
    work = "".join(out)

    # 3) every separator glyph -> canonical '.'
    for sep in _SEPARATOR_CHARS:
        work = work.replace(sep, _CANONICAL_SEP)

    # 4) whitespace: drop it around a separator, collapse interior runs to nothing between atoms but
    #    keep a boundary where a digit meets a following capital (so "5 H2O" -> "5H2O", "CuSO4 . 5 H2O"
    #    -> "CuSO4.5H2O").  A formula has no meaningful internal spaces once separators are canonical, so
    #    all remaining whitespace is removed; the separator carries the only real boundary.
    work = "".join(work.split())
    return work


def _looks_parametric(text: str) -> "str | None":
    """Return a reason string iff ``text`` is a parametric/polymer/interval form, else ``None``.

    Detects the family markers v0.6 refuses rather than coerces: an interval (``±``/``~``), a
    polymer suffix (a group ``)``/``]`` immediately followed by a lowercase variable like ``n``), and a
    bare variable subscript (a lowercase letter sitting where a count belongs, e.g. ``MxOy``).  This is a
    positive detector for a WELL-FORMED-but-parametric string; genuinely malformed input is left to the
    parser to reject.
    """
    for ch in _INTERVAL_CHARS:
        if ch in text:
            return f"interval/uncertain count ({ch!r}) -- names a family of compositions, not one"
    # polymer suffix: ')n', ']m', etc. -- a closing group followed by a lone lowercase letter.
    for k in range(1, len(text)):
        if text[k].islower() and text[k - 1] in ")]":
            # a lowercase letter can never legally begin a token (element symbols start uppercase);
            # after a group close it is a repeat-unit variable, i.e. a polymer.
            return f"polymer/repeat-unit variable {text[k]!r} after a group -- names a repeat family"
    return None


def _parse_body(text: str, source: str) -> Formula:
    """Parse a neutral formula body (no charge, no separators) supporting nested ``()`` and ``[]``.

    A stricter cousin of :meth:`Formula.parse`: it rejects empty groups ``()``/``[]``, bare counts with
    no element, variable subscripts (a lowercase letter where a token must start), and enforces a nesting
    depth guard.  Bracket kinds must match ``(``↔``)`` / ``[``↔``]``.  On success returns the
    :class:`Formula`; on any defect raises :class:`FormulaSyntaxError` (or :class:`ParametricFormulaError`
    for a variable subscript) -- so a malformed body can never silently normalize to a valid neighbour.
    """
    if not text:
        raise FormulaSyntaxError(f"empty formula body in {source!r}")
    stack: list[dict[str, int]] = [{}]
    open_kinds: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "([":
            open_kinds.append(c)
            if len(open_kinds) > _MAX_NESTING_DEPTH:
                raise FormulaSyntaxError(f"formula {source!r} nests deeper than {_MAX_NESTING_DEPTH}")
            stack.append({})
            i += 1
        elif c in ")]":
            want = "(" if c == ")" else "["
            if not open_kinds:
                raise FormulaSyntaxError(f"unbalanced {c!r} in formula {source!r}")
            if open_kinds[-1] != want:
                raise FormulaSyntaxError(f"mismatched bracket {c!r} in formula {source!r}")
            open_kinds.pop()
            i += 1
            j = i
            while j < n and text[j].isdigit():
                j += 1
            mult = int(text[i:j]) if j > i else 1
            if mult == 0:
                raise FormulaSyntaxError(f"zero group multiplier in formula {source!r}")
            i = j
            group = stack.pop()
            if not group:
                raise FormulaSyntaxError(f"empty group in formula {source!r}")
            for sym, k in group.items():
                stack[-1][sym] = stack[-1].get(sym, 0) + k * mult
        elif c.isupper():
            j = i + 1
            if j < n and text[j].islower():
                j += 1
            symbol = text[i:j]
            i = j
            k = i
            while k < n and text[k].isdigit():
                k += 1
            mult = int(text[i:k]) if k > i else 1
            if mult == 0:
                raise FormulaSyntaxError(f"zero count for {symbol!r} in formula {source!r}")
            i = k
            stack[-1][symbol] = stack[-1].get(symbol, 0) + mult
        elif c.islower():
            # a token can only START with an uppercase element letter or a bracket; a lowercase here is
            # prose or a stray glyph (an element's optional lowercase 2nd letter is consumed WITH its
            # uppercase above, so it never reaches this branch).  Malformed, not parametric -- a genuine
            # variable subscript form like (C2H4)n / an interval is caught upstream by _looks_parametric.
            raise FormulaSyntaxError(
                f"unexpected lowercase {c!r} in {source!r} (an element symbol must start uppercase)"
            )
        elif c.isdigit():
            raise FormulaSyntaxError(f"count {c!r} with no preceding element in formula {source!r}")
        else:
            raise FormulaSyntaxError(f"unexpected character {c!r} in formula {source!r}")
    if open_kinds:
        raise FormulaSyntaxError(f"unbalanced {open_kinds[-1]!r} in formula {source!r}")
    if not stack[0]:
        raise FormulaSyntaxError(f"formula {source!r} names no atoms")
    try:
        return Formula.of(stack[0])
    except DecompilerError as exc:
        # unknown element, etc. -- surface as a syntax refusal (fail-closed), keeping the original message.
        raise FormulaSyntaxError(f"in {source!r}: {exc}") from exc


def _extract_charge(text: str) -> "tuple[str, int, str]":
    """Split a trailing charge suffix off ``text``; return ``(body, charge, note)``.

    Recognized charge spellings, in unambiguity order:

    * caret form ``^2-`` / ``^-`` / ``^+`` -- any magnitude, always unambiguous;
    * a bracket-ion charge ``]4-`` / ``]+`` -- digits+sign right after a closing ``]``, the digits are
      the magnitude (a bracket already delimited the atom body);
    * a bare trailing sign ``+`` / ``-`` -- magnitude 1, and any digits before it stay in the BODY
      (``NH4+`` -> ``NH4`` charge +1; the ``4`` is H's count).

    ``note`` is non-empty only when a digit immediately precedes a *bare* sign (``NH4+``, ``Ca2+``): the
    reading is fixed at magnitude 1 and the note says a magnitude needs the caret form, so a ``Ca2+``
    that the writer meant as +2 is flagged rather than silently mis-charged.  A charge is never guessed.
    """
    if not text:
        return text, 0, ""
    # caret form: '...^<digits><sign>' -- unambiguous magnitude.
    caret = text.rfind("^")
    if caret != -1:
        suffix = text[caret + 1:]
        sign = suffix[-1:] if suffix[-1:] in "+-" else ""
        if not sign:
            raise FormulaSyntaxError(f"caret charge in {text!r} has no sign (+/-)")
        mag_text = suffix[:-1]
        if mag_text and not mag_text.isdigit():
            raise FormulaSyntaxError(f"malformed caret charge {suffix!r} in {text!r}")
        mag = int(mag_text) if mag_text else 1
        if mag == 0:
            raise FormulaSyntaxError(f"zero charge magnitude in {text!r}")
        return text[:caret], mag if sign == "+" else -mag, ""
    last = text[-1]
    if last in "+-":
        # digits immediately before the sign (if any).
        j = len(text) - 1
        d = j
        while d - 1 >= 0 and text[d - 1].isdigit():
            d -= 1
        digits = text[d:j]
        preceding = text[:d]
        if digits and preceding.endswith("]"):
            # bracket-ion: the bracket delimited the body, so the digits ARE the magnitude ([Fe(CN)6]4-).
            mag = int(digits)
            if mag == 0:
                raise FormulaSyntaxError(f"zero charge magnitude in {text!r}")
            return preceding, mag if last == "+" else -mag, ""
        # A bare sign with a trailing digit run is ambiguous in two cases (P0-B), and both are refused rather
        # than guessed -- the digits could be an atom count or (part of) the charge magnitude:
        #   * a SINGLE-element body (Fe3+, Ca2+, O2-, C60-): count (Fe3, +-1) vs magnitude (Fe, +-3);
        #   * ANY body with a >=2-digit trailing run (SO42-, PO43-, CO32-, Cr2O72-): it is unclear how to split
        #     the run into count and magnitude (SO4 + 2- vs SO42 + 1-), so this fails OPEN to an absurd 42-oxygen
        #     composition if accepted -- exactly the "silent mis-charge" P0-B forbids.
        # A MULTI-element body with a SINGLE trailing digit (NH4+, NO3-) is unambiguous -- the digit is the last
        # element's count and the bare sign is +-1 -- and falls through to the reading below.  Element count =
        # uppercase letters; brackets are handled above.  n_elements == 0 (e.g. '3+') is left to the body parser.
        if digits:
            body_with_digits = text[:-1]
            n_elements = sum(1 for ch in body_with_digits if ch.isupper())
            if n_elements == 1 or len(digits) >= 2:
                raise AmbiguousChargeError(
                    f"{text!r} is an ambiguous ASCII ion: it is unclear whether the trailing digits {digits!r} "
                    f"are an atom count or the charge magnitude (or how to split them). Write the charge "
                    f"unambiguously with a caret (e.g. Fe^3+, SO4^2-), a Unicode superscript (Fe³⁺, SO₄²⁻), or a "
                    f"bracket ion (e.g. [Fe]3+, [SO4]2-)."
                )
        # bare sign: magnitude 1, digits (if any) belong to the body (NH4+ -> NH4, +1; multi-element only).
        note = ""
        if digits:
            note = (
                f"bare charge sign read as {'+1' if last == '+' else '-1'}; the trailing '{digits}' is the last "
                "element's count. A charge magnitude > 1 must use the caret form (e.g. SO4^2-) or a bracket ion "
                "(e.g. [Fe(CN)6]4-)"
            )
        return text[:-1], 1 if last == "+" else -1, note
    return text, 0, ""


def parse_formula_expr(text: str) -> FormulaExpr:
    """Parse a human formula spelling into a lossless :class:`FormulaExpr` (the v0.6 front-door grammar).

    Pipeline: normalize (:func:`normalize_formula_text`) -> reject parametric families
    (:class:`ParametricFormulaError`) -> strip a trailing charge suffix -> split on the canonical ``.``
    into components -> parse each component's leading multiplier and bracketed atom body.  Raises
    :class:`FormulaSyntaxError` on any malformed input; the result's ``notes`` name every non-trivial
    normalization so nothing is silently altered.
    """
    original = text if isinstance(text, str) else repr(text)

    # P0-C: a compact ASCII 'digit.digit' is a DECIMAL point, not a hydrate separator -- refuse it (v0.6 has
    # no decimal stoichiometry).  This is checked on a PARTIALLY-normalized spelling: subscript digits are
    # folded to ASCII FIRST (so 'C₁.5H₂' is seen as the decimal '1.5', not bypassed -- the subscript-adjacent
    # leak an adversary found), but separators are NOT yet folded and whitespace is NOT yet stripped (so a
    # Unicode 'CuSO4·5H2O' still shows '·' and a spaced 'CuSO4 . 5 H2O' still shows its spaces, and neither
    # trips as a decimal).  Doing it here rather than inside normalize keeps normalize idempotent on a folded
    # hydrate 'CuSO4.5H2O'.  Only the ambiguous COMPACT ASCII period between two ASCII digits is a decimal.
    if isinstance(text, str):
        raw = text.strip().translate(_SUBSCRIPTS)
        for k in range(1, len(raw) - 1):
            if raw[k] == "." and raw[k - 1] in _ASCII_DIGITS and raw[k + 1] in _ASCII_DIGITS:
                raise FormulaSyntaxError(
                    f"{original!r} contains a decimal point ('{raw[k - 1]}.{raw[k + 1]}'); v0.6 does not support "
                    "decimal stoichiometry. Use integer counts, a middle-dot hydrate (e.g. CuSO4·5H2O), or a "
                    "spaced component boundary (e.g. CuSO4 . 5 H2O)."
                )

    normalized = normalize_formula_text(text)

    reason = _looks_parametric(normalized)
    if reason is not None:
        raise ParametricFormulaError(f"{original!r} is parametric: {reason}")

    body, charge, charge_note = _extract_charge(normalized)
    if not body:
        raise FormulaSyntaxError(f"{original!r} has a charge but no formula")

    raw_components = body.split(_CANONICAL_SEP)
    if any(part == "" for part in raw_components):
        # a leading/trailing/doubled separator: 'CuSO4.', '.H2O', 'A..B' -- dangling, not a hydrate.
        raise FormulaSyntaxError(f"{original!r} has a dangling '{_CANONICAL_SEP}' separator (no component)")

    components: list[FormulaComponent] = []
    for idx, part in enumerate(raw_components):
        # optional leading integer multiplier: '5H2O' -> mult 5, body 'H2O'.  It is a HYDRATE/ADDUCT multiplier,
        # valid ONLY after a component separator (idx > 0).  A leading multiplier on the FIRST component (P0-D)
        # -- '5H2O', '2NaCl' -- is a whole-expression stoichiometric COEFFICIENT (a quantity of a species), not
        # the identity of one molecular species, so it is refused at the identity front door rather than folded
        # into composition.
        m = 0
        while m < len(part) and part[m].isdigit():
            m += 1
        mult_text, body_text = part[:m], part[m:]
        if mult_text and idx == 0:
            raise FormulaSyntaxError(
                f"{original!r} has a leading coefficient {mult_text!r}: a whole-expression multiplier is a "
                "stoichiometric quantity, not one molecular identity. Drop it -- a component multiplier is valid "
                "only AFTER a separator (e.g. the '5' in CuSO4·5H2O)."
            )
        multiplier = int(mult_text) if mult_text else 1
        if multiplier == 0:
            raise FormulaSyntaxError(f"zero component multiplier in {original!r}")
        formula = _parse_body(body_text, original)
        components.append(FormulaComponent(multiplier, formula, source=part))

    notes: list[str] = []
    if normalized != original.strip():
        notes.append(f"normalized {original.strip()!r} -> {normalized!r}")
    if len(components) > 1:
        boundary = " + ".join(
            f"{c.multiplier}x {_render_formula_body(c.formula)}" if c.multiplier != 1
            else _render_formula_body(c.formula)
            for c in components
        )
        notes.append(f"multi-component (hydrate/adduct) boundary retained: {boundary}")
    if charge:
        notes.append(f"charge suffix consumed: net {charge:+d}")
    if charge_note:
        notes.append(charge_note)

    return FormulaExpr(tuple(components), charge, original=original, normalized=normalized, notes=tuple(notes))
