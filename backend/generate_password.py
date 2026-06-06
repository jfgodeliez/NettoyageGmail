#!/usr/bin/env python3
"""Génère APP_PASSWORD_HASH pour le fichier .env."""

import getpass
import hashlib
import secrets

password = getpass.getpass("Mot de passe : ")
confirm = getpass.getpass("Confirmer : ")

if password != confirm:
    print("Les mots de passe ne correspondent pas.")
    raise SystemExit(1)

salt = secrets.token_hex(16)
h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
print(f"\nAjoutez dans .env :\nAPP_PASSWORD_HASH={salt}:{h.hex()}")
