"""1.7.0 : les calculs de l'animation du dernier vote du public (frontend/src/lib/dernier.js), testés par node."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not shutil.which("node"), reason="node absent")
def test_dernier_js():
    r = subprocess.run(["node", "--test", str(RACINE / "frontend/src/lib/dernier.test.mjs")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "# fail 0" in r.stdout
