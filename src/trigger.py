import sys
from pathlib import Path

# from oct2py import Oct2Py

if __name__ == "__main__" or __package__ is None:
    _project_root = str(Path(__file__).resolve().parents[1])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

import assets.burn
import assets.injection


def injection():
    assets.injection.main()

    # os.environ['OCTAVE_EXECUTABLE'] = \
    #     r'C:\Program Files\GNU Octave\Octave-10.2.0\mingw64\bin\octave.exe'
    # os.chdir(r'C:\Users\CROPPS-in-Box\Documents\cropps main folder\cropps-img\assets')  # change path if necessary
    # print("Running injection")
    # Oct2Py().eval('injection')


def burn():
    assets.burn.main()


if __name__ == '__main__':
    burn()
