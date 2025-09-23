import sys
from pathlib import Path

if __name__ == "__main__" or __package__ is None:
    _project_root = str(Path(__file__).resolve().parents[1])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import assets.burn
import assets.injection


def injection(port):
    assets.injection.main(port)


def burn(port):
    assets.burn.main(port)


if __name__ == '__main__':
    burn()
