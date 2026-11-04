#!/usr/bin/env python
"""
LexAI CLI & Management Script
==============================
(Migrated from legacy Django to production FastAPI + React stack)
Running 'python manage.py runserver' will start the FastAPI platform.
"""

import sys
import os

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)

    # If runserver is invoked (e.g. from muscle memory or old scripts), launch FastAPI
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        from run import start_backend
        port = 8000
        if len(sys.argv) > 2 and ":" in sys.argv[2]:
            try:
                port = int(sys.argv[2].split(":")[-1])
            except ValueError:
                pass
        start_backend(port=port)
    else:
        # Pass through to run.py
        import run
        run.start_backend()
