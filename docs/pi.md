# pi (coding agent, terminal)

pi memuat skill dari `~/.pi/agent/skills/<nama>/SKILL.md`.

Cara termudah — tempel di sesi pi:
> Pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill (ikuti INSTALL.md).

pi akan menjalankan pemasang. Manual:
```
python -c "import urllib.request;exec(urllib.request.urlopen('https://raw.githubusercontent.com/B-ngoen/sirah-tafsir-skills/main/install.py').read().decode())" --target pi
```
Lalu mulai sesi pi baru dan bertanya, mis. *"kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*. Basis data (±17 MB) diunduh otomatis saat pertama dipakai.

Tanpa pemasangan: tempel isi `skills/<nama>/SKILL.md` ke `AGENTS.md` proyek dan jalankan `python skills/<nama>/scripts/lookup.py …`.
