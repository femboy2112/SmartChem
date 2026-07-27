"""Acceptance tests for the closed, import-lazy executor registry."""
from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError, fields, replace

import pytest

import smartchem.runtime_registry as registry


REACTION = "smartchem.program/reaction-energy-v1"
WATER_WAVE = "smartchem.water_wave/shallow-water-horizon-v1"
HUMAN_ISOTOPE = "smartchem.human_isotope/identifiability-v1"


def _nominal_subject(descriptor: registry.ExecutorDescriptor) -> tuple[object, object]:
    """Build only the nominal shell this registry is responsible for checking."""
    container_type = descriptor.resolved_container.resolve()
    subject_type = descriptor.subject_type.resolve()
    container = object.__new__(container_type)
    subject = object.__new__(subject_type)
    object.__setattr__(container, descriptor.subject_attribute, subject)
    return container, subject


def test_registry_is_closed_immutable_and_contains_exactly_three_executors():
    assert registry.executor_ids() == tuple(sorted((
        REACTION,
        WATER_WAVE,
        HUMAN_ISOTOPE,
    )))
    descriptors = tuple(registry.descriptor_for(item) for item in registry.executor_ids())
    assert len(descriptors) == 3
    assert not hasattr(registry, "register")
    assert not hasattr(registry, "register_executor")
    with pytest.raises(FrozenInstanceError):
        descriptors[0].executor_id = "third-party/executor"  # type: ignore[misc]
    for descriptor in descriptors:
        assert all(
            not callable(getattr(descriptor, field.name))
            for field in fields(descriptor)
        )


def test_unknown_executor_is_rejected_by_every_public_operation():
    unknown = "third.party/unreviewed-v1"
    with pytest.raises(KeyError, match="no runtime is registered"):
        registry.descriptor_for(unknown)
    with pytest.raises(KeyError, match="no runtime is registered"):
        registry.extract_subject(unknown, object())
    with pytest.raises(KeyError, match="no runtime is registered"):
        registry.validate_output_contract(unknown, object())
    with pytest.raises(KeyError, match="no runtime is registered"):
        registry.resolve_runner(unknown)


@pytest.mark.parametrize("executor_id", (REACTION, WATER_WAVE, HUMAN_ISOTOPE))
def test_exact_resolved_container_and_subject_are_validated_and_extracted(executor_id):
    descriptor = registry.descriptor_for(executor_id)
    container, subject = _nominal_subject(descriptor)

    assert registry.extract_subject(executor_id, container) is subject

    class ContainerSubclass(type(container)):
        pass

    wrong_container = object.__new__(ContainerSubclass)
    object.__setattr__(wrong_container, descriptor.subject_attribute, subject)
    with pytest.raises(TypeError, match="requires exact resolved container"):
        registry.extract_subject(executor_id, wrong_container)

    wrong_subject = object()
    object.__setattr__(container, descriptor.subject_attribute, wrong_subject)
    with pytest.raises(TypeError, match="requires exact subject"):
        registry.extract_subject(executor_id, container)


@pytest.mark.parametrize("executor_id", (REACTION, WATER_WAVE, HUMAN_ISOTOPE))
def test_only_exact_default_output_contract_is_accepted(executor_id):
    descriptor = registry.descriptor_for(executor_id)
    expected = descriptor.default_output_contract()

    assert registry.output_contract_error(executor_id, expected) is None
    registry.validate_output_contract(executor_id, expected)

    changed = replace(
        expected,
        retention=expected.retention + ("unauthorized mutation",),
    )
    assert registry.output_contract_error(executor_id, changed) is not None
    with pytest.raises(ValueError, match="exact default output contract"):
        registry.validate_output_contract(executor_id, changed)


@pytest.mark.parametrize("executor_id", (REACTION, WATER_WAVE, HUMAN_ISOTOPE))
def test_runner_resolves_to_the_exact_declared_module_level_function(executor_id):
    descriptor = registry.descriptor_for(executor_id)
    runner = registry.resolve_runner(executor_id)

    assert callable(runner)
    assert runner.__module__ == descriptor.runner.module
    assert runner.__name__ == descriptor.runner.name


def test_reloading_registry_performs_no_lazy_target_imports(monkeypatch):
    def forbidden_import(_name):
        raise AssertionError("registry import must not resolve target modules")

    monkeypatch.setattr(importlib, "import_module", forbidden_import)
    importlib.reload(registry)


def test_semantic_manifest_and_digest_are_deterministic_and_complete():
    first = registry.semantic_manifest()
    second = registry.semantic_manifest()

    assert first == second
    assert first is not second
    assert first["schema"] == "smartchem.runtime-registry/v1"
    assert tuple(item["executor_id"] for item in first["executors"]) == registry.executor_ids()
    assert all(item["implementation_modules"] for item in first["executors"])
    assert registry.semantic_manifest_digest() == registry.semantic_manifest_digest()
    assert registry.semantic_manifest_digest() == (
        "712d8d73b5d29267c379ac78e1b091083720db77043b0502cd7daf1e87048158"
    )
