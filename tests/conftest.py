import sys, pathlib
# Phase 0 lives in core/; Phase 1 promotes this to a real package.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "core"))
