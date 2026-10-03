# Security Policy

SmartChem is research software. It has two distinct classes of "security" report, and
they travel through different channels. Please read which one applies before filing.

## Supported versions

| Version | Supported |
| ------- | --------- |
| latest 1.x | ✅ |
| < 1.0 (alphas, pre-release tags) | ❌ |

Security fixes are made against the latest 1.x release line.

## 1. Software security vulnerabilities

A software security vulnerability is a defect that lets untrusted input compromise the
host or another user: for example arbitrary code execution while parsing a molecule or
a `--target-file`, a path-traversal or deserialization flaw, a denial-of-service that a
crafted input triggers, or a dependency with a known exploited CVE.

**Report these privately. Do not open a public issue.**

Use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab → **Advisories** → **Report a vulnerability**
   (direct link: <https://github.com/femboy2112/SmartChem/security/advisories/new>).
2. Describe the class of problem, the affected version, and the smallest input or steps
   that reproduce it. A proof-of-concept is welcome; a weaponized exploit is not required.

Please do not post credentials, tokens, or a working exploit path into a public issue or
pull request. If you believe a secret was ever committed to this repository's history,
report it privately through the same channel.

## 2. Scientific correctness and overclaim

SmartChem's core promise is epistemic: it must never *vouch* for something it cannot
support. A failure of that promise is a **correctness bug**, not usually a software
security vulnerability — but it is treated as high priority, because a confident wrong
answer is worse than an honest `UNKNOWN`.

Examples, all explicitly in scope:

- **Identity hallucination** — the compiler reports a molecule/graph/route identity that
  is not what the input actually denotes.
- **False vouch** — a route, step, or value is admitted/VOUCHED when the evidence does
  not support it.
- **False `CAPABILITY_FIT`** — a route is reported runnable under a capability profile it
  cannot actually satisfy.
- **False completeness / false readiness** — the search claims it exhausted the admitted
  space, or claims a route is bench-ready, when it did not / is not.
- **Provenance or source mismatch** — a cited number, rate, or fact does not match its
  stated source, or a "derived" estimate lacks its method and uncertainty.

**Report these publicly** using the **Scientific correctness** issue form — the public
record is valuable for other users and these reports do not expose an exploitable host.
If a correctness report also happens to depend on sensitive or private data, route it
through the private advisory channel instead.

## What this policy is not

`CAPABILITY_FIT` is not a safety certification, and a formally admitted route is not a
validated bench procedure. See [COMPATIBILITY.md](COMPATIBILITY.md) for the scope of what
the compiler does and does not guarantee.
