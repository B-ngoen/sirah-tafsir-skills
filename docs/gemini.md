# Gemini — aplikasi web/HP (Gems) dan Gemini CLI

## Gemini web/HP (untuk kebanyakan pengguna)
Gemini web tidak dapat menjalankan `lookup.py`, jadi disediakan **teks kitab per berkas** yang dibaca Gemini langsung. Panduan lengkap: [gemini/README-GEMINI.md](../gemini/README-GEMINI.md).

Ringkas:
1. Unduh `gemini-knowledge-tafsir.zip` / `gemini-knowledge-sirah.zip` dari [Releases → gemini-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/gemini-v1), ekstrak.
2. **Gem** (Google AI Pro/Ultra): Gems → Gem baru → Instruksi = isi `gemini/instructions-tafsir.md` atau `instructions-sirah.md` → Knowledge = semua `.txt` → simpan.
3. **Gratis, tanpa Gem**: percakapan baru → unggah `.txt` kitab yang dibutuhkan (maks 10) → tempel instruksi sebagai pesan pertama → bertanya.

Keterbatasan: pengambilan bagian panjang bersifat retrieval, bisa tidak utuh; instruksi meminta Gemini mengatakannya. Untuk akurasi tertinggi pakai Claude/ChatGPT.

## Gemini CLI (terminal)
```
gemini skills install https://github.com/B-ngoen/sirah-tafsir-skills --path skills/sirah-lookup
gemini skills install https://github.com/B-ngoen/sirah-tafsir-skills --path skills/tafsir-lookup
```
atau `python install.py --target gemini`. Basis data diunduh otomatis saat pertama dipakai.
