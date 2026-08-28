#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install.py — pasang skill tafsir-lookup / sirah-lookup dengan SATU perintah (tanpa git).

    python install.py                 # pasang semua skill yang tersedia ke folder skill agen yang terdeteksi
    python install.py tafsir          # hanya tafsir-lookup
    python install.py --target claude # paksa target: claude | chatgpt | codex | pi | hermes | gemini | dir:<folder>
    python install.py --no-db         # jangan pra-unduh basis data (akan diunduh saat pertama dipakai)

Yang dilakukan:
1. Mengunduh isi folder skills/<nama>/ dari GitHub (raw), tanpa git.
2. Menyalin ke folder skill agen: Claude Code -> ~/.claude/skills/<nama>/ ; Codex -> ~/.codex/skills/<nama>/ (+ catatan AGENTS.md).
3. Pra-unduh basis data (.xz) ke cache permanen agar pemakaian pertama tidak menunggu.
Stdlib saja. Aman diulang (idempoten).
"""
import argparse, io, json, lzma, os, sys, urllib.request
from pathlib import Path

try:  # Windows console cp1252: hindari UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = "B-ngoen/sirah-tafsir-skills"
BRANCH = "main"
SKILLS = {
    "tafsir-lookup": {
        "files": ["SKILL.md", "scripts/lookup.py"],
        "db_url": f"https://github.com/{REPO}/releases/download/tafsir-v1/tafsir_full.db.xz",
        "db_name": "tafsir_full.db", "cache": "tafsir-lookup",
    },
    "sirah-lookup": {
        "files": ["SKILL.md", "scripts/lookup.py"],
        "db_url": f"https://github.com/{REPO}/releases/download/sirah-v1/sirah_full.db.xz",
        "db_name": "sirah_full.db", "cache": "sirah-lookup",
    },
}
ALIAS = {"tafsir": "tafsir-lookup", "sirah": "sirah-lookup"}
UA = {"User-Agent": "sirah-tafsir-skills-installer/1"}


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def detect_targets(force=None):
    home = Path.home()
    known = {
        "claude": ("Claude Code", home / ".claude" / "skills"),
        "chatgpt": ("ChatGPT Work / Codex", home / ".agents" / "skills"),
        "codex": ("Codex (lama)", home / ".codex" / "skills"),
        "pi": ("pi", home / ".pi" / "agent" / "skills"),
        "hermes": ("Hermes", home / ".hermes" / "skills"),
        "gemini": ("Gemini CLI", home / ".gemini" / "skills"),
    }
    if force:
        if force in known:
            return [known[force]]
        if force.startswith("dir:"):
            return [("Folder", Path(force[4:]))]
        sys.exit(f"target tidak dikenal: {force} (pilihan: {', '.join(known)}, dir:<folder>)")
    out = []
    for key, (label, path) in known.items():
        probe = {"pi": path.parent, "chatgpt": home / ".agents", "codex": home / ".codex"}.get(key, home / f".{key}")
        if probe.is_dir():
            out.append((label, path))
    if not out:  # default: Claude Code (folder dibuat)
        out.append(("Claude Code", home / ".claude" / "skills"))
    return out


def cache_dir(name):
    cands = []
    if os.environ.get("LOCALAPPDATA"):
        cands.append(Path(os.environ["LOCALAPPDATA"]) / name)
    xdg = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    cands.append(Path(xdg) / name)
    for c in cands:
        try:
            c.mkdir(parents=True, exist_ok=True)
            return c
        except OSError:
            continue
    return cands[-1]


def install_skill(name, targets, want_db):
    meta = SKILLS[name]
    base = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/skills/{name}/"
    files = {}
    for f in meta["files"]:
        try:
            files[f] = fetch(base + f)
        except Exception as e:
            print(f"  ! gagal mengunduh {f}: {type(e).__name__} — skill {name} mungkin belum dirilis")
            return False
    for label, root in targets:
        dst = root / name
        for f, content in files.items():
            p = dst / f
            p.parent.mkdir(parents=True, exist_ok=True)
            io.open(p, "w", encoding="utf-8", newline="\n").write(content)
        print(f"  OK {name} dipasang ke {label}: {dst}")
        if label.startswith("Codex") or label.startswith("ChatGPT"):
            agents = Path.home() / (".codex" if label.startswith("Codex") else ".agents") / "AGENTS.md"
            note = f"\n\n## Skill {name}\nBaca dan ikuti `{dst / 'SKILL.md'}` setiap kali pengguna bertanya topik terkait; jalankan `python {dst / 'scripts' / 'lookup.py'} ...`.\n"
            try:
                cur = io.open(agents, encoding="utf-8").read() if agents.exists() else ""
                if name not in cur:
                    io.open(agents, "a", encoding="utf-8").write(note)
                    print(f"  OK catatan ditambahkan ke {agents}")
            except OSError:
                pass
    if want_db:
        cdir = cache_dir(meta["cache"])
        db = cdir / meta["db_name"]
        if db.exists() and db.stat().st_size > 50 * 1024 * 1024:
            print(f"  OK basis data sudah ada: {db}")
        else:
            print(f"  ... mengunduh basis data (±17 MB) ke {cdir} — sekali saja")
            try:
                raw = fetch(meta["db_url"], binary=True)
                with lzma.open(io.BytesIO(raw)) as src, open(db, "wb") as out:
                    while True:
                        chunk = src.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
                print(f"  OK basis data siap: {db} ({db.stat().st_size / 1e6:.0f} MB)")
            except Exception as e:
                print(f"  ! unduh DB gagal ({type(e).__name__}); skill tetap terpasang dan akan mengunduh saat pertama dipakai")
        # ChatGPT Work / Codex menjalankan script di sandbox yang sering tidak bisa membaca
        # cache pengguna maupun internet -> salin DB ke <skill>/assets/ (dicek lookup.py paling dulu).
        if db.exists():
            for label, root in targets:
                if not (label.startswith("ChatGPT") or label.startswith("Codex")):
                    continue
                adir = root / name / "assets"
                adst = adir / meta["db_name"]
                if adst.exists() and adst.stat().st_size == db.stat().st_size:
                    continue
                try:
                    adir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copyfile(db, adst)
                    print(f"  OK salinan DB untuk sandbox {label}: {adst}")
                except OSError as e:
                    print(f"  ! gagal menyalin DB ke {adst}: {e}")
    return True


def main():
    ap = argparse.ArgumentParser(description="Pasang skill tafsir-lookup / sirah-lookup.")
    ap.add_argument("skills", nargs="*", help="tafsir | sirah (kosong = semua yang tersedia)")
    ap.add_argument("--target", help="claude | chatgpt | codex | pi | hermes | gemini | dir:<folder>")
    ap.add_argument("--no-db", action="store_true")
    a = ap.parse_args()
    names = [ALIAS.get(s, s) for s in a.skills] or [n for n, m in SKILLS.items() if m.get("released", True)]
    targets = detect_targets(a.target)
    print("Target:", ", ".join(f"{l} ({p})" for l, p in targets))
    ok = 0
    for n in names:
        if n not in SKILLS:
            print(f"  ! skill tidak dikenal: {n}")
            continue
        if not SKILLS[n].get("released", True) and not a.skills:
            continue
        if not SKILLS[n].get("released", True):
            print(f"[{n}] belum dirilis — nantikan di README")
            continue
        print(f"[{n}]")
        ok += bool(install_skill(n, targets, not a.no_db))
    print(f"Selesai: {ok} skill terpasang. Mulai percakapan baru, lalu bertanya seperti biasa (mis. 'tafsir QS 2:255 menurut Thabari, teks Arabnya').")


if __name__ == "__main__":
    main()
