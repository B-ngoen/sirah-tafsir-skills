# Claude — Desktop, web (claude.ai), dan Claude Code

Semua jalur Claude membaca basis data langsung lewat `lookup.py` → hasil paling akurat (verbatim + juz/halaman).

## Claude Desktop / claude.ai (web & HP) — sudah diuji pemilik repo
1. Unduh berkas skill (klik langsung):
   - [tafsir-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/tafsir-lookup.skill)
   - [sirah-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/sirah-lookup.skill)
2. **Settings → Capabilities → Skills → Upload skill** → pilih berkas (ulangi untuk skill kedua).
3. Percakapan baru → bertanya biasa. Pemakaian pertama mengunduh basis data ke sandbox (±1 menit); paket gratis tetap bisa, materi panjang dikirim per bagian (ketik **lanjut**).

Contoh: *"Tafsir QS 2:255 menurut Thabari dan Ibnu Katsir, teks Arabnya"* · *"Kisah Perang Uhud lengkap dari semua kitab"* · *"Siapa Abu Bakar menurut al-Ishabah?"*

## Claude Code (terminal)
Tempel satu kalimat:
> Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.

Atau manual: `python install.py` (pasang ke `~/.claude/skills/`). Di Claude Code berbayar, skill otomatis memakai subagent paralel untuk materi panjang.

## Tanpa memasang (sekali pakai)
Tempel tautan repo di chat: *"pelajari repo ini dan pakai untuk percakapan ini"* — Claude membaca `skills/<nama>/SKILL.md` dan menjalankan scriptnya di sandbox.
