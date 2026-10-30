"""Drift guard for EVENT-SEARCH-01 (:mod:`experiments.event_search_probe`).

The committed probe freezes the bounded typed-event search's verdicts over its corpus; if the search's behaviour
changes silently, ``content_hash()`` moves and this test fails LOUD, forcing a deliberate re-freeze."""
from __future__ import annotations

from experiments import event_search_probe as probe


def test_event_search_probe_validates():
    probe.validate()


def test_event_search_probe_hash_is_frozen():
    assert probe.content_hash() == probe.FROZEN_HASH, (
        "event-search probe drift: the typed-event search changed behaviour. Re-run "
        "`.venv/bin/python -m experiments.event_search_probe`, confirm the change is intended, and re-freeze."
    )
