"""``python -m smartchem`` -- the unified command line (see :mod:`smartchem.cli`)."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
