# Claude — Desktop, web (claude.ai), dan Claude Code

Semua jalur Claude membaca basis data langsung lewat `lookup.py` → hasil paling akurat (verbatim + juz/halaman).

## Claude Desktop / claude.ai — sudah diuji pemilik repo
Pemasangan hanya bisa dari **PC** (claude.ai di browser atau aplikasi desktop); aplikasi HP belum punya menu unggah skill. Setelah terpasang, skill ikut tersedia saat Anda bertanya dari aplikasi HP.
1. Di PC, unduh berkas skill (klik langsung):
   - [tafsir-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/tafsir-lookup.skill)
   - [sirah-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/sirah-lookup.skill)
2. **Settings → Capabilities → Skills → Upload skill** → pilih berkas (ulangi untuk skill kedua).
3. Percakapan baru → bertanya biasa. Pemakaian pertama mengunduh basis data (17–18 MB) ke sandbox di sisi Claude (±1 menit) — berjalan di server, jadi sama saja dipakai dari HP Android/iPhone, desktop, atau web. Paket gratis tetap bisa; materi panjang dikirim per bagian (ketik **lanjut**).

Contoh: *"Tafsir QS 2:255 menurut Thabari dan Ibnu Katsir, teks Arabnya"* · *"Kisah Perang Uhud lengkap dari semua kitab"* · *"Siapa Abu Bakar menurut al-Ishabah?"*

## Claude Desktop — mode Cowork / Code (satu kalimat)
Claude Desktop punya mode **Cowork** (atau *Code*) yang bisa menjalankan perintah di komputer Anda. Buka mode itu, lalu tempel:
> Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.

Claude membaca `INSTALL.md`, menjalankan `python install.py` (skill ke `~/.claude/skills/`, basis data diunduh sekali ke cache), lalu siap. Skill yang terpasang di sini juga terbaca di percakapan biasa Claude Desktop dan aplikasi HP (akun yang sama), jadi tidak perlu mengunggah `.skill` lagi.

## Claude Code (terminal)
Tempel satu kalimat:
> Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.

Atau manual: `python install.py` (pasang ke `~/.claude/skills/`). Di Claude Code berbayar, skill otomatis memakai subagent paralel untuk materi panjang.

## Tanpa memasang (sekali pakai)
Tempel tautan repo di chat: *"pelajari repo ini dan pakai untuk percakapan ini"* — Claude membaca `skills/<nama>/SKILL.md` dan menjalankan scriptnya di sandbox.
