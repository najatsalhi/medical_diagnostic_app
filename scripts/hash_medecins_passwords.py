#!/usr/bin/env python3
"""
Simple migration script to hash plaintext passwords in data/medecins.json

Usage (from project root):
  python scripts/hash_medecins_passwords.py

This will replace any password value that does not look like a Werkzeug hash
with a generated hash using Werkzeug's `generate_password_hash`.
"""
import json
import os
from werkzeug.security import generate_password_hash


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'medecins.json')


def is_hashed(pwd: str) -> bool:
    if not isinstance(pwd, str):
        return False
    return pwd.startswith('pbkdf2:') or pwd.startswith('argon2:')


def main():
    if not os.path.exists(DATA_PATH):
        print(f"File not found: {DATA_PATH}")
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changed = False
    for username, info in data.items():
        pwd = info.get('password')
        if pwd is None:
            continue
        if not is_hashed(pwd):
            new_hash = generate_password_hash(str(pwd))
            data[username]['password'] = new_hash
            changed = True
            print(f"Hashed password for {username}")

    if changed:
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Updated {DATA_PATH} with hashed passwords.")
    else:
        print("No plaintext passwords found; no changes made.")


if __name__ == '__main__':
    main()
