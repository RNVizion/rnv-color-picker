"""
Root-level conftest.py for the RNV Color Picker test suite.

Inserts the project root into sys.path so test files can do
`from core.foo import Bar` etc. This file should stay minimal —
do not add fixtures, hooks, or Qt-touching imports here. The inner
tests/conftest.py is where shared fixtures live.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
