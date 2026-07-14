"""Run every test_*.py without needing pytest:  python tests/run_all.py"""
import sys
import importlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


def main() -> int:
    failed = []
    for f in sorted(HERE.glob("test_*.py")):
        mod = importlib.import_module(f.stem)
        for name in dir(mod):
            if name.startswith("test_"):
                fn = getattr(mod, name)
                if callable(fn):
                    try:
                        fn()
                        print(f"  OK  {f.stem}.{name}")
                    except Exception as e:  # noqa: BLE001
                        failed.append(f"{f.stem}.{name}: {e}")
                        print(f"  XX  {f.stem}.{name}: {e}")
    print("\n" + ("ALL TESTS PASSED" if not failed else f"{len(failed)} FAILED"))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
