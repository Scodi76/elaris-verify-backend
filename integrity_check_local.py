# integrity_check_local.py
# Lokales Integritätsprüfmodul für den Elaris-Gatekeeper

import hashlib
import os
from datetime import datetime

def hash_file(path):
    """Erstellt SHA256-Hash einer Datei."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def check_file(filename: str):
    """
    Prüft, ob die Datei existiert und erzeugt eine einfache Integritätssignatur.
    Diese Funktion simuliert die Integritätsprüfung, bis der echte Prüfkatalog eingebunden wird.
    """
    result = {
        "file": filename,
        "timestamp": datetime.utcnow().isoformat(),
        "verified": False,
        "hash": None
    }

    if not os.path.exists(filename):
        return result

    file_hash = hash_file(filename)
    result["hash"] = file_hash

    # Beispielhafte Vergleichslogik (später durch echten Referenzhash ersetzen)
    reference_hash = os.environ.get("ELARIS_REF_HASH", "").strip().lower()
    if reference_hash and reference_hash == file_hash.lower():
        result["verified"] = True
    else:
        # Wenn kein Referenzhash gesetzt, prüfen wir nur, ob Datei > 0 Byte
        result["verified"] = os.path.getsize(filename) > 0

    return result
