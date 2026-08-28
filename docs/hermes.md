# Hermes Agent

Hermes punya pemasang skill bawaan (repo ini sudah terindeks di skills.sh):
```
hermes skills install B-ngoen/sirah-tafsir-skills/skills/sirah-lookup
hermes skills install B-ngoen/sirah-tafsir-skills/skills/tafsir-lookup
```
Pratinjau dulu tanpa memasang: `hermes skills inspect B-ngoen/sirah-tafsir-skills/skills/sirah-lookup`.

Atau lewat percakapan: minta Hermes *"pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill"* — Hermes membaca `INSTALL.md` dan menjalankan pemasang (`python install.py --target hermes` → `~/.hermes/skills/`).

Setelah terpasang, bertanya seperti biasa; basis data diunduh otomatis saat pertama dipakai (±17 MB per skill).
