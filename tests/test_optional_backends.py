"""Optional dependencies must be absent cleanly, without hiding SmartChem import bugs."""
from __future__ import annotations

import subprocess
import sys
import textwrap


def test_pyscf_configuration_imports_when_backend_is_absent():
    script = textwrap.dedent(
        """
        import builtins

        real_import = builtins.__import__
        def without_pyscf(name, *args, **kwargs):
            if name == "pyscf" or name.startswith("pyscf."):
                raise ModuleNotFoundError("blocked for test", name="pyscf")
            return real_import(name, *args, **kwargs)
        builtins.__import__ = without_pyscf

        from smartchem.category import Molecule
        from smartchem.oracle.pyscf_oracle import PYSCF_AVAILABLE, PySCFOracle
        assert PYSCF_AVAILABLE is False
        oracle = PySCFOracle("CCSD(T)", "cc-pVTZ", tight_d=False)
        try:
            oracle.energy(Molecule.atom("H"))
        except ImportError as error:
            assert "smartchem[qc]" in str(error)
        else:
            raise AssertionError("a real calculation did not report the missing backend")

        from smartchem.oracle import available_oracles
        assert not any(name.startswith("ccsdt") for name in available_oracles())
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
