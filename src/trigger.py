import os

from oct2py import Oct2Py


def injection():
    os.environ['OCTAVE_EXECUTABLE'] = \
        r'C:\Program Files\GNU Octave\Octave-10.2.0\mingw64\bin\octave.exe'
    os.chdir('assets')  # change path if necessary
    print("Running injection")
    Oct2Py().eval('injection')


def burn():
    # TODO
    print("Running burn")


if __name__ == '__main__':
    injection()
