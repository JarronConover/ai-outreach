import os
import sys

# Ensure the project root (ai-outreach/) is on sys.path so that
# `from schemas.crm import …` resolves to the global schemas package
# regardless of how this package is imported (main.py, tests, REPL, etc.)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
