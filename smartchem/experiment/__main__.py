"""``python -m smartchem.experiment`` -- the Experiment Compiler command line (see :mod:`.cli`)."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
