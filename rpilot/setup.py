from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(['stim/sound/jackclient.pyx'],  # Python code file with primes_python_compiled() function
                          annotate=False),        # enables generation of the html annotation file
)