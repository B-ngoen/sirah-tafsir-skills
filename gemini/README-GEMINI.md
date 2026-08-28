# Gemini (aplikasi web/HP) — Gem "Tafsir Verbatim" & "Sirah Verbatim"

Gemini web tidak bisa menjalankan `lookup.py` atas basis data SQLite. Karena itu untuk Gemini kami sediakan **teks kitab dalam berkas .txt per kitab** (diekspor dari basis data yang sama, tiap halaman diawali baris penanda `### [kitab] juz X hal Y | shamela: URL`) supaya Gemini mengutip langsung dari berkas dan tetap menyebut juz/halaman.

Dua cara pakai:

## A. Gem dengan Knowledge (paling nyaman; butuh Google AI Pro/Ultra)
1. Unduh paket teks dari [Releases → gemini-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/gemini-v1):
   - `gemini-knowledge-tafsir.zip` (5 kitab, 6 berkas, ±103 MB) dan/atau
   - `gemini-knowledge-sirah.zip` (10 kitab, 8 berkas, ±74 MB).
   Ekstrak zip-nya.
2. Buka [gemini.google.com](https://gemini.google.com) → menu kiri **Gems** → **Gem baru**.
3. Nama: `Tafsir Verbatim` (atau `Sirah Verbatim`).
4. **Instruksi**: salin seluruh isi `instructions-tafsir.md` (atau `instructions-sirah.md`) dari folder ini, tempel.
5. **Knowledge**: unggah semua berkas `.txt` hasil ekstrak (maks 10 berkas per Gem — paket sudah disesuaikan).
6. Simpan, lalu tanya seperti biasa: *"Tafsir QS Al-Baqarah 255 menurut Thabari, teks Arabnya"* / *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*.

## B. Tanpa Gem (gratis): lampirkan berkas di chat
1. Unduh & ekstrak paket yang sama.
2. Percakapan baru → klik **+** → unggah berkas `.txt` kitab yang dibutuhkan (maks 10 berkas, tiap berkas ≤100 MB).
3. Tempel isi `instructions-*.md` sebagai pesan pertama, lalu ajukan pertanyaan.
Berkas hanya berlaku untuk percakapan itu.

## Keterbatasan (jujur)
- Gemini mengambil potongan berkas lewat *retrieval*, bukan membaca basis data terstruktur. Untuk pertanyaan singkat hasilnya baik; untuk "materi lengkap satu bab" ada kemungkinan sebagian halaman tidak terambil. Instruksi Gem sudah meminta Gemini mengatakan bila hasil tidak lengkap.
- Verbatim bergantung pada kepatuhan model: bandingkan kutipan dengan berkas bila ragu (cari baris penanda `###` yang disebut).
- Untuk hasil paling akurat (baca basis data langsung), pakai Claude (Code/Desktop/web) atau ChatGPT Custom GPT — lihat README utama.

## Membuat sendiri paket teks (opsional)
`python gemini/export_knowledge.py sirah sirah_full.db out/sirah` — berkas dipecah otomatis ±25 MB, ≤10 berkas. Basis data `.db` didapat dengan mengekstrak `*.db.xz` dari Releases.
