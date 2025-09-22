#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pack_collection_with_extractor.py — Concatène une collection Ansible en un bundle texte
Le bundle généré inclut automatiquement le script d’extraction en tête.
"""

import os
import sys
import base64
import fnmatch
import hashlib
from datetime import datetime, timezone

# === Script d’extraction à insérer en tête du bundle ===
EXTRACTOR_SCRIPT = r'''
#####################################################################
# Script de décompression (unpack_collection.py)
# Copiez ce bloc dans un fichier `unpack_collection.py` puis exécutez :
#   python3 unpack_collection.py --bundle bundle.txt --dest ./cd60.nce-restored
#####################################################################
import argparse, base64, os, sys, hashlib
from pathlib import Path
def write_file(dest_root, rel_path, data, mode_str):
    out_path = dest_root / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    try:
        if mode_str.startswith("0o"):
            os.chmod(out_path, int(mode_str, 8))
    except Exception:
        pass
def parse_bundle(bundle_path, list_only, dest):
    with open(bundle_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    i = 0
    files = []
    while i < len(lines):
        line = lines[i]
        if not line.startswith("### FILE:"):
            i += 1
            continue
        rel_path = line.split(":", 1)[1].strip()
        meta = {"TYPE": "", "ENCODING": "utf-8", "MODE": "0o644", "SIZE": "", "SHA256": ""}
        i += 1
        while i < len(lines) and lines[i].startswith("### "):
            l = lines[i].strip()
            if l.startswith("### TYPE:"):
                meta["TYPE"] = l.split(":", 1)[1].strip()
            elif l.startswith("### ENCODING:"):
                meta["ENCODING"] = l.split(":", 1)[1].strip()
            elif l.startswith("### MODE:"):
                meta["MODE"] = l.split(":", 1)[1].strip()
            elif l.startswith("### SIZE:"):
                meta["SIZE"] = l.split(":", 1)[1].strip()
            elif l.startswith("### SHA256:"):
                meta["SHA256"] = l.split(":", 1)[1].strip()
            i += 1
            if i < len(lines) and lines[i].strip() == "### END FILE":
                content_lines = []
                break
        content_lines = []
        while i < len(lines) and lines[i].strip() != "### END FILE":
            content_lines.append(lines[i])
            i += 1
        if i < len(lines) and lines[i].strip() == "### END FILE":
            i += 1
        if i < len(lines) and lines[i].strip() == "":
            i += 1
        raw = "".join(content_lines)
        if meta["ENCODING"] == "base64":
            data = base64.b64decode(raw.encode("ascii"))
        else:
            data = raw.encode("utf-8")
        files.append((rel_path, meta, data))
        if not list_only and dest is not None:
            write_file(Path(dest), rel_path, data, meta.get("MODE", "0o644"))
    return files
def main():
    ap = argparse.ArgumentParser(description="Unpack bundle.")
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--dest")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    files = parse_bundle(args.bundle, args.list, args.dest)
    if args.list or not args.dest:
        for rel_path, m, _ in files:
            print(f"{rel_path}  [{m.get('TYPE','text')}, {m.get('ENCODING','utf-8')}, {m.get('SIZE','?')} bytes]")
    else:
        print(f"[OK] Unpacked {len(files)} file(s) into: {args.dest}")
if __name__ == "__main__":
    main()
#####################################################################
'''

README = '''
### INSTRUCTIONS
# 1. Ce fichier bundle contient tous les fichiers de la collection, suivis du script d’extraction.
# 2. Pour extraire les fichiers :
#    a) Copiez le script de décompression (bloc ci-dessus) dans `unpack_collection.py`
#    b) Exécutez : python3 unpack_collection.py --bundle bundle.txt --dest ./cd60.nce-restored
# 3. Les fichiers seront extraits dans ./cd60.nce-restored/ avec leur arborescence d’origine
'''

DEFAULT_EXCLUDES = [
    ".git/*", ".git/**", "__pycache__/*", "__pycache__/**",
    "*.pyc", "*.pyo", "*.pyd", ".tox/*", ".tox/**", ".venv/*", ".venv/**",
    ".idea/*", ".idea/**", ".vscode/*", ".vscode/**", "build/*", "build/**",
    "dist/*", "dist/**", "*.zip", "*.tar", "*.tar.gz", "*.tgz",
]

def is_excluded(rel_path, patterns):
    rel_norm = rel_path.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(rel_norm, pat):
            return True
    return False

def iter_files(root, includes, excludes):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        pruned = []
        for d in dirnames:
            rel = os.path.relpath(os.path.join(dirpath, d), root).replace("\\", "/")
            if not is_excluded(rel + "/", excludes):
                pruned.append(d)
        dirnames[:] = pruned
        for f in filenames:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if is_excluded(rel, excludes):
                continue
            if includes:
                if any(fnmatch.fnmatch(rel, pat) for pat in includes):
                    yield full
            else:
                yield full

def read_file_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()

def detect_text_or_binary(data):
    if b"\x00" in data:
        import base64
        b64 = base64.b64encode(data).decode("ascii")
        return "binary", "base64", b64
    try:
        txt = data.decode("utf-8")
        return "text", "utf-8", txt
    except UnicodeDecodeError:
        import base64
        b64 = base64.b64encode(data).decode("ascii")
        return "binary", "base64", b64

def file_mode_str(path):
    import stat
    try:
        st = os.stat(path)
        return oct(stat.S_IMODE(st.st_mode))
    except Exception:
        return "0o644"

def sha256_hex(data):
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Pack une collection en un bundle texte avec script d’extraction inclus.")
    ap.add_argument("--root", required=True, help="Racine à empaqueter (répertoire de la collection).")
    ap.add_argument("--output", "-o", default="-", help="Fichier de sortie (par défaut stdout).")
    ap.add_argument("--include", "-I", action="append", default=[],
                    help="Motifs d'inclusion (glob) relatifs à root. Peut être répété.")
    ap.add_argument("--exclude", "-E", action="append", default=[],
                    help="Motifs d'exclusion (glob). Peut être répété. Des valeurs par défaut sont déjà actives.")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    excludes = DEFAULT_EXCLUDES + args.exclude
    files = sorted(iter_files(root, args.include, excludes))

    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8", newline="\n")
    try:
        # 1. Script d’extraction
        print(EXTRACTOR_SCRIPT.strip(), file=out)
        print(README.strip(), file=out)
        print("", file=out)

        # 2. Bundle des fichiers
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"### BUNDLE: {os.path.basename(root)}", file=out)
        print(f"### VERSION: 1", file=out)
        print(f"### GENERATED: {generated}", file=out)
        print(f"### ROOT: {root}", file=out)
        print(f"### COUNT: {len(files)}", file=out)
        print("", file=out)

        for full in files:
            rel = os.path.relpath(full, root).replace("\\", "/")
            data = read_file_bytes(full)
            size = len(data)
            ftype, enc, payload = detect_text_or_binary(data)
            mode = file_mode_str(full)
            digest = sha256_hex(data)
            print(f"### FILE: {rel}", file=out)
            print(f"### TYPE: {ftype}", file=out)
            print(f"### ENCODING: {enc}", file=out)
            print(f"### MODE: {mode}", file=out)
            print(f"### SIZE: {size}", file=out)
            print(f"### SHA256: {digest}", file=out)
            if enc == "utf-8":
                if payload and not payload.endswith("\n"):
                    payload += "\n"
                out.write(payload)
            elif enc == "base64":
                out.write(payload)
                if not payload.endswith("\n"):
                    out.write("\n")
            print(f"### END FILE", file=out)
            print("", file=out)
        print(f"### END BUNDLE", file=out)
    finally:
        if out is not sys.stdout:
            out.close()

if __name__ == "__main__":
    main()
