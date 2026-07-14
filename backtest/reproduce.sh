#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest tests -q
python scripts/verify.py
python scripts/make_vault_spec.py
echo "OK: tests pass, snapshot verified, spec emitted."
