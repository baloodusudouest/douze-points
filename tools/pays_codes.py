"""1.12 : recopie la table des noms de pays de l'interface (frontend/src/lib/pays.js, CODES) dans app/pays_codes.json,
pour que le serveur reconnaisse « notre pays » même quand la liste collée n'a pas de drapeau.
À relancer après toute modification de pays.js : python tools/pays_codes.py (un test compare les deux)."""
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def lire_js() -> dict[str, str]:
    texte = (RACINE / "frontend/src/lib/pays.js").read_text(encoding="utf-8")
    bloc = re.search(r"const CODES = (\{.*?\n\})", texte, re.S).group(1)
    return json.loads(bloc)


if __name__ == "__main__":
    codes = lire_js()
    (RACINE / "app/pays_codes.json").write_text(json.dumps(codes, ensure_ascii=False, sort_keys=True, indent=0) + "\n",
                                                encoding="utf-8")
    print(len(codes), "noms de pays recopiés")
