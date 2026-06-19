import os
import sys

# Make the `app` package importable when running `pytest` from services/api.
sys.path.insert(0, os.path.dirname(__file__))
