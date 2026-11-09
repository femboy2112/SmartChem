# SmartChem developer shortcuts -- thin wrappers over the repo's existing conventions.
# Assumes an activated venv; override the interpreter with e.g. `make test-quick PY=.venv/bin/python`.
PY   ?= python
RUFF ?= ruff

.DEFAULT_GOAL := help
.PHONY: help install doctor test-quick test test-sandbox lint clean

help:  ## list targets
	@echo "SmartChem make targets (PY=$(PY)):"
	@echo "  help          this list"
	@echo "  install       pip install -e '.[dev]'"
	@echo "  doctor        environment diagnostic (python -m smartchem doctor)"
	@echo "  test-quick    fast smoke: identity + v1.0 public contract"
	@echo "  test          full suite via scripts/run_suite.sh (batched; never bare pytest)"
	@echo "  test-sandbox  sandbox research tests"
	@echo "  lint          ruff check smartchem/"
	@echo "  clean         remove build/caches"

install:
	$(PY) -m pip install -e '.[dev]'

doctor:
	$(PY) -m smartchem doctor

test-quick:
	$(PY) -m pytest -q -p no:cacheprovider tests/test_identity.py tests/test_v1_0_public_contract.py

test:
	./scripts/run_suite.sh

test-sandbox:
	$(PY) -m pytest experiments/sandbox_foundation/tests -q -p no:cacheprovider

lint:
	$(RUFF) check smartchem/

clean:
	rm -rf build .pytest_cache .ruff_cache
	find . -name '*.egg-info' -prune -exec rm -rf {} +
	find . -name '__pycache__' -prune -exec rm -rf {} +
