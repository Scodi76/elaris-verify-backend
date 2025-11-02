#!/usr/bin/env python3
"""
usb_protection.py – bindet verschlüsselte Dateien an die Volume-Serial des Ziel-Laufwerks.

Verwendung:
  Encrypt (Passwort generieren und anzeigen):
    python usb_protection.py enc --drive D: --out-dir "D:\\System Volume Information" --gen-pass file1 file2 ...
  Encrypt (eigenes Passwort verwenden):
    python usb_protection.py enc --drive D: --out-dir "D:\\protected" --password "MeinPass!" file1 ...
  Decrypt:
    python usb_protection.py dec --drive D: --in-file "D:\\System Volume Information\\file.txt.enc" --password "Passwort"

Hinweise:
- Die erzeugte .enc.meta.json wird fuer Serial-Check und Integritaetspruefung benoetigt.
- Schreibrechte in "System Volume Information" erfordern idR Administrator-Konsole.
"""

import argparse
import os
import json
import secrets
import hashlib
import sys
import getpass
import ctypes
from typing import Optional

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


# -------------------------
# Low-level Hilfsfunktionen
# -------------------------

def get_volume_serial(drive_letter: str) -> str:
    """
    Gibt die Volume-Serial (hex) des Laufwerks zurueck, z.B. "D:" -> "1a2b3c4d".
    Wirft PermissionError bei fehlendem Zugriff.
    """
    drive = drive_letter if drive_letter.endswith("\\") else (drive_letter + "\\")
    kernel32 = ctypes.windll.kernel32
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial_number = ctypes.c_uint(0)
    max_component_length = ctypes.c_uint(0)
    file_system_flags = ctypes.c_uint(0)
    res = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(drive),
        vol_name_buf, ctypes.sizeof(vol_name_buf),
        ctypes.byref(serial_number),
        ctypes.byref(max_component_length),
        ctypes.byref(file_system_flags),
        fs_name_buf, ctypes.sizeof(fs_name_buf)
    )
    if res == 0:
        raise PermissionError("Kein Zugriff auf Laufwerk {}. Rechte pruefen oder anderen Ordner verwenden."
                              .format(drive_letter))
    return format(serial_number.value, "08x")


def derive_key(password: str, volume_serial_hex: str) -> bytes:
    """
    Leitet einen 256-bit Key aus Passwort + Volume-Serial (als Salt) ab.
    """
    salt = bytes.fromhex(volume_serial_hex)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
        backend=default_backend()
    )
    return kdf.derive(password.encode("utf-8"))


def sha256_file(path: str) -> str:
    """
    Berechnet SHA-256 einer Datei (Streaming, 8 KiB).
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def encrypt_file(src_path: str, out_path: str, key: bytes) -> None:
    """
    Verschluesselt src_path mit AES-GCM, schreibt Nonce+Ciphertext nach out_path.
    """
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    with open(src_path, "rb") as f:
        data = f.read()
    ct = aesgcm.encrypt(nonce, data, None)
    with open(out_path, "wb") as fo:
        fo.write(nonce + ct)


def decrypt_file(in_path: str, out_path: str, key: bytes) -> None:
    """
    Entschluesselt in_path (Nonce+Ciphertext) nach out_path.
    """
    with open(in_path, "rb") as f:
        blob = f.read()
    if len(blob) < 13:
        raise ValueError("Cipher-Datei ist zu kurz oder korrupt: {}".format(in_path))
    nonce, ct = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    data = aesgcm.decrypt(nonce, ct, None)
    with open(out_path, "wb") as fo:
        fo.write(data)


def write_json(meta_path: str, meta: dict) -> None:
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def read_json(meta_path: str) -> dict:
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------
# CLI Hauptlogik
# --------------

def cmd_encrypt(drive: str, out_dir: str, files: list, password: Optional[str], gen_pass: bool) -> int:
    if gen_pass:
        password = secrets.token_urlsafe(16)
        print("GENERATED PASSWORD (securely save this):", password)
    elif not password:
        try:
            password = getpass.getpass("Passwort fuer Verschluesselung eingeben: ")
        except Exception:
            password = input("Passwort fuer Verschluesselung eingeben: ")
        if not password:
            print("Fehler: Leeres Passwort ist ungueltig.")
            return 2

    try:
        vserial = get_volume_serial(drive)
    except Exception as e:
        print("Fehler beim Lesen der Volume-Serial:", e)
        return 2

    key = derive_key(password, vserial)

    try:
        os.makedirs(out_dir, exist_ok=True)
    except PermissionError as e:
        print("Keine Berechtigung, im Zielordner zu schreiben:", e)
        return 2

    exit_code = 0
    for f in files:
        if not os.path.isfile(f):
            print("Quelle fehlt oder ist keine Datei:", f)
            exit_code = 1
            continue

        base = os.path.basename(f)
        out_file = os.path.join(out_dir, base + ".enc")
        meta_file = out_file + ".meta.json"

        try:
            encrypt_file(f, out_file, key)
            meta = {
                "original_name": base,
                "sha256_plain": sha256_file(f),
                "volume_serial": vserial,
                "note": "Gebunden an Volume-Serial; Entschluesselung erfordert das gleiche Laufwerk + Passwort"
            }
            write_json(meta_file, meta)
            print("[OK] Verschluesselt:", f, "->", out_file)
        except Exception as e:
            print("[ERROR] Konnte nicht verschluesseln:", f, "Grund:", e)
            exit_code = 1

    return exit_code


def cmd_decrypt(drive: str, in_file: str, out_dir: Optional[str], password: Optional[str]) -> int:
    if not password:
        try:
            password = getpass.getpass("Bitte Entschluesselungs-Passwort eingeben: ")
        except Exception:
            password = input("Passwort: ")
        if not password:
            print("Kein Passwort eingegeben.")
            return 2

    meta_file = in_file + ".meta.json"
    if not os.path.isfile(in_file):
        print("Cipher-Datei fehlt:", in_file)
        return 1
    if not os.path.isfile(meta_file):
        print("Meta-Datei fehlt:", meta_file)
        return 1

    try:
        vserial = get_volume_serial(drive)
    except Exception as e:
        print("Fehler beim Lesen der Volume-Serial:", e)
        return 2

    try:
        meta = read_json(meta_file)
    except Exception as e:
        print("Meta-Datei unlesbar:", e)
        return 1

    if meta.get("volume_serial") != vserial:
        print("FEHLER: Volume-Serial stimmt nicht ueberein. Entschluesselung verweigert.")
        return 3

    key = derive_key(password, vserial)

    base_name = os.path.basename(meta.get("original_name", "restored.txt"))
    target_dir = out_dir if out_dir else os.path.dirname(in_file)
    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, base_name)

    try:
        decrypt_file(in_file, out_path, key)
    except Exception as e:
        print("Entschluesselung fehlgeschlagen:", e)
        return 1

    # Integritaet pruefen
    if os.path.isfile(out_path):
        sha = sha256_file(out_path)
        if sha == meta.get("sha256_plain"):
            print("[OK] Entschluesselt und Integritaet geprueft:", out_path)
            return 0
        else:
            print("[WARN] Entschluesselt, aber SHA-Pruefung fehlgeschlagen. Datei:", out_path)
            return 4

    print("Entschluesselung erzeugte keine Datei.")
    return 1


def main():
    p = argparse.ArgumentParser(description="Verschluesselt/entschluesselt Dateien, gebunden an Volume-Serial.")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Encrypt
    pe = sub.add_parser("enc", help="Dateien verschluesseln und auf Ziel-Laufwerk ablegen")
    pe.add_argument("--drive", required=True, help="Ziel-Laufwerk, z.B. D:")
    pe.add_argument("--out-dir", required=True, help="Zielordner auf dem Laufwerk")
    pe.add_argument("--password", help="Optional: Passwort vorgeben (sonst Eingabeaufforderung)")
    pe.add_argument("--gen-pass", action="store_true", help="Zufaelliges Passwort generieren und ausgeben")
    pe.add_argument("files", nargs="+", help="Quelldateien zum Verschluesseln")

    # Decrypt
    pd = sub.add_parser("dec", help="Eine .enc-Datei vom Ziel-Laufwerk entschluesseln")
    pd.add_argument("--drive", required=True, help="Quelldatei-Laufwerk, z.B. D:")
    pd.add_argument("--in-file", required=True, help="Pfad zur .enc")
    pd.add_argument("--out-dir", required=False, help="Zielordner fuer die entschluesselte Datei (Standard: Ordner der .enc)")
    pd.add_argument("--password", required=False, help="Passwort (wenn leer, wird interaktiv gefragt)")

    args = p.parse_args()

    if args.cmd == "enc":
        rc = cmd_encrypt(args.drive, args.out_dir, args.files, args.password, args.gen_pass)
        sys.exit(rc)

    if args.cmd == "dec":
        rc = cmd_decrypt(args.drive, args.in_file, args.out_dir, args.password)
        sys.exit(rc)


if __name__ == "__main__":
    main()
