from ._external import *
from .python import *

python_numpy = HeaderChecker(
                   name='python_numpy',
                   # libs='npymath',
                   header='numpy/numpyconfig.h',
                   language='c',
                   dependencies=[python])

