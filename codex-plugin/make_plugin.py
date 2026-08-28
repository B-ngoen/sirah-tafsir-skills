#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_plugin.py — bangun plugin Codex/ChatGPT Work `tafsir-sirah-lookup` dari skills/ repo.

    python codex-plugin/make_plugin.py          # tulis codex-plugin/plugins/tafsir-sirah-lookup/

Struktur mengikuti plugin-creator resmi Codex:
  plugins/<nama>/.codex-plugin/plugin.json  + plugins/<nama>/skills/<skill>/...
  .agents/plugins/marketplace.json           (marketplace lokal bernama sirah-tafsir-skills)
Pasang: codex plugin marketplace add <path-ke-folder-codex-plugin>
        codex plugin add tafsir-sirah-lookup@sirah-tafsir-skills
"""
import io, json, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "codex-plugin"
PLUGIN = OUT / "plugins" / "tafsir-sirah-lookup"
SKILLS = ["tafsir-lookup", "sirah-lookup"]

manifest = {
    "name": "tafsir-sirah-lookup",
    "version": "1.0.0",
    "description": "Kutipan verbatim tafsir (5 kitab) dan sirah/shahabat (10 kitab) dari Maktabah Syamilah, dengan juz/halaman.",
    "author": {"name": "B-ngoen", "url": "https://github.com/B-ngoen/sirah-tafsir-skills"},
    "skills": "./skills/",
    "interface": {
        "displayName": "Tafsir & Sirah Lookup",
        "shortDescription": "Teks Arab verbatim tafsir & sirah dengan sitasi juz/halaman.",
        "longDescription": "Memasang skill tafsir-lookup (Thabari, Ibnu Katsir 2 edisi, Maraghi, Shabuni) dan sirah-lookup (Ibnu Hisyam 2 edisi, Ibnu Ishaq, Thabaqat, Tarikh Thabari, Ishabah, Usud al-Ghabah 2 edisi, Isti'ab). Basis data diunduh otomatis saat pertama dipakai. Wakaf non-komersial.",
        "developerName": "B-ngoen",
        "category": "Productivity",
        "capabilities": [],
        "defaultPrompt": "Tafsir QS 2:255 menurut Thabari, teks Arabnya.",
    },
}
marketplace = {
    "name": "sirah-tafsir-skills",
    "interface": {"displayName": "Sirah & Tafsir Skills"},
    "plugins": [{
        "name": "tafsir-sirah-lookup",
        "source": {"source": "local", "path": "./plugins/tafsir-sirah-lookup"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }],
}

if PLUGIN.exists():
    shutil.rmtree(PLUGIN)
(PLUGIN / ".codex-plugin").mkdir(parents=True)
io.open(PLUGIN / ".codex-plugin" / "plugin.json", "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
for s in SKILLS:
    shutil.copytree(ROOT / "skills" / s, PLUGIN / "skills" / s)
mp = OUT / ".agents" / "plugins"
mp.mkdir(parents=True, exist_ok=True)
io.open(mp / "marketplace.json", "w", encoding="utf-8", newline="\n").write(json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n")
n = sum(len(f) for _, _, f in os.walk(PLUGIN))
print(f"plugin ditulis: {PLUGIN} ({n} berkas); marketplace: {mp / 'marketplace.json'}")
