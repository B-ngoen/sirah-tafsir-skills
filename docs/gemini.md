# Gemini (aplikasi web/HP) — lewat NotebookLM

Gemini tidak bisa menjalankan program pencari basis data seperti Claude/ChatGPT. Jalan yang **terbukti bekerja**: masukkan teks kitab ke **NotebookLM** (gratis), lalu bertanya di sana — atau, kalau ingin memakai aplikasi Gemini biasa, buat **Gem** yang sumbernya adalah notebook tadi.

## Yang perlu diunduh
Dari [Releases → gemini-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/gemini-v1):
- `gemini-knowledge-sirah.zip` — 10 kitab sirah/shahabat, 22 berkas teks + `PETUNJUK-tempel.txt`
- `gemini-knowledge-tafsir.zip` — 5 kitab tafsir, 28 berkas teks + `PETUNJUK-tempel.txt`

Ekstrak zip-nya. Tiap berkas ≤6 MB dan ≤490 ribu kata (batas NotebookLM per sumber), dipecah di awal bab supaya satu kisah tidak terbelah.

## Langkah 1 — NotebookLM (wajib)
1. Buka [notebooklm.google.com](https://notebooklm.google.com) → **Buat notebook**, beri nama "Sirah Verbatim" (atau "Tafsir Verbatim").
2. **Tambahkan sumber** → unggah **semua** berkas `.txt` hasil ekstrak (22 atau 28 berkas; batas gratis 50 sumber per notebook). Tunggu sampai semua selesai diproses.
3. Di kotak chat, tempel isi `PETUNJUK-tempel.txt` sebagai pesan pertama, lalu bertanya. Contoh:
   - *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*
   - *"Tafsir QS Al-Baqarah 255 menurut Thabari, teks Arabnya"*
   Sebutkan juga istilah Arabnya bila hasil kurang lengkap (mis. «غزوة بدر», «سقيفة بني ساعدة») — pencarian jadi lebih tepat.

Sampai di sini sudah bisa dipakai. NotebookLM menyebut nomor sumber; petunjuk meminta teks Arab apa adanya + juz/halaman dari baris penanda `[kitab] juz X hal Y`.

## Langkah 2 — Gem di aplikasi Gemini (pilihan)
Gem hanya menerima 10 berkas, jadi jangan unggah teksnya langsung; pakai notebook dari Langkah 1 sebagai sumbernya:
1. [gemini.google.com](https://gemini.google.com) → **Gems** → **Gem baru**; nama "Sirah Verbatim".
2. **Petunjuk**: tempel isi `PETUNJUK-tempel.txt`.
3. **Alat default**: pilih *tanpa alat* (bukan Deep Research — itu mencari internet).
4. **Informasi** → `+` → pilih sumber **Gemini Notebook** → tunjuk notebook Langkah 1.
5. Biarkan "Nonaktifkan Kutipan Informasi" **tidak** dicentang → Simpan.
Kerjanya memang dua kali, tetapi begitulah caranya sekarang.

## Keterbatasan
- Hasilnya *retrieval* (mengambil potongan teks yang cocok), bukan membaca basis data terstruktur; untuk "materi lengkap satu bab" sebagian halaman bisa tidak terambil — petunjuk meminta Gemini mengatakannya. Untuk akurasi tertinggi pakai Claude atau ChatGPT.
- Petunjuk sudah memuat aturan: jawab hanya dalam Bahasa Indonesia kecuali diminta lain; kutipan tetap Arab.

## Gemini CLI (terminal, untuk yang teknis)
`gemini skills install https://github.com/B-ngoen/sirah-tafsir-skills --path skills/sirah-lookup` (dan `.../tafsir-lookup`), atau `python install.py --target gemini`. Ini membaca basis data langsung seperti Claude Code.
