import sys

if sys.version_info < (3, 11, 5):
    print("Chaanbot requires at least Python 3.11.5.")
    sys.exit(1)

__version__ = "3.1.1"
