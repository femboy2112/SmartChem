"""
Test configuration.

Slow and backend-dependent tests are opt-in. Declaring a marker in ``pyproject.toml`` does
not skip anything by itself -- it only registers the name -- so the gate has to live here.

    pytest                  fast suite: the categorical laws, the frozen baseline
    pytest --runslow        adds the real oracle calls (minutes, needs PySCF)

The split matters for honesty as much as for speed: a suite that takes an hour stops being
run, and a law that is never checked is a law that is not enforced.
"""
from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run tests that make real quantum-chemistry oracle calls",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="needs --runslow (real oracle calls)")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(autouse=True)
def _fresh_enumeration_cache():
    """0.9.5 (barrier section 4): the process-level enumeration cache is keyed on argument VALUES + the registry's
    content digest -- a test that monkeypatches a provider changes behaviour without changing any key, so every test
    starts (and ends) with an empty cache.  Production never patches; the key is complete there."""
    from smartchem.verification import ENUMERATION_CACHE

    ENUMERATION_CACHE.clear()
    yield
    ENUMERATION_CACHE.clear()
