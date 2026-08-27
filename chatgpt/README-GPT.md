# README — Membuat Custom GPT "Tafsir Verbatim 5 Kitab"

Paket ini berisi tiga file:
- `instructions.md` — teks instruksi Custom GPT (tempel ke field Instructions).
- `lookup.py` — CLI query tafsir (versi ChatGPT: DB dicari di `/mnt/data` — lokasi mount file Knowledge — paling dulu; cache ekstrak ke `/tmp/tafsir-lookup/`; auto-download dicoba paling akhir).
- `tafsir_full.db.xz` — TIDAK ada di folder ini; unduh dari GitHub Release (lihat langkah 3).

## Langkah membuat GPT

1. **Buka builder.** ChatGPT → sidebar kiri: *Explore GPTs* → *Create* (butuh paket Plus/Team). Masuk ke tab **Configure** (jangan sekadar chat di tab Create).

2. **Identitas GPT.**
   - Name: `Tafsir Verbatim 5 Kitab`
   - (Opsional) logo: gambar kitab/kubah sederhana.

3. **Knowledge — unggah 2 file:**
   - `lookup.py` (dari folder ini);
   - `tafsir_full.db.xz` (18,7 MB) — unduh dari GitHub Release: `https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/v1/tafsir_full.db.xz`, lalu unggah hasil unduhannya.
   - Setelah keduanya masuk, kolom Knowledge harus menampilkan dua file. File inilah yang dimount Code Interpreter di `/mnt/data/`.

4. **Instructions.** Buka `instructions.md`, salin SELURUH isinya, tempel ke field besar **Instructions** di tab Configure. (±5.000 karakter — jauh di bawah batas 8.000.)

5. **Capabilities.** Aktifkan ✅ **Code Interpreter**; matikan Web Search, Image Generation, dan DALL·E (tidak dipakai, mencegah GPT mencari tafsir di internet). Bila ada pilihan *Code Interpreter & Analysis* vs *Advanced Data Analysis* — pilih bawaan saja.

6. **Conversation starters** (isi 3):
   - `Tafsir 2:255 menurut Thabari`
   - `Bandingkan pendapat mufassir untuk 2:152`
   - `Materi lengkap tafsir surah Al-Fatihah untuk kajian`

7. **Uji coba** (masih di builder, panel Preview):
   - Ketik: `tafsir 2:255 menurut Thabari`
   - Yang benar: GPT menjalankan `python /mnt/data/lookup.py 2:255 -s tabari` via Code Interpreter; eksekusi pertama ±1 menit (ekstraksi xz 18,7 MB → 136 MB di /tmp); lalu menjawab dengan Ringkasan (parafrase, ditandai) → verbatim Arab + sitasi juz/hal → Catatan.
   - Uji juga: `materi lengkap tafsir 1:1-7` — harus mulai dari `--toc` lalu membaca segmen bertahap.

8. **Publish.** *Create* → pilih visibilitas (hanya Anda / link / publik). Selesai.

## Cara kerja di belakang layar (untuk pemilik)

- File Knowledge dimount Code Interpreter di `/mnt/data/`, jadi `lookup.py` dan `tafsir_full.db.xz` tersedia di sana. `find_db()` versi ChatGPT memeriksa `/mnt/data/tafsir_full.db{,.xz,.zip}` PALING DULU, sebelum env `TAFSIR_DB`, folder skill, cwd, jalur Cowork, path laptop, dan auto-download.
- Eksekusi `--toc`/`--seg`/`--paras`/`--intro`/`--coverage`/`--format json`/`-s`/`--max-chars` identik dengan versi skill.
- Bila eksekusi langsung dari `/mnt/data` gagal (kasus langka), instruksi menyuruh GPT menyalin `lookup.py` ke `/tmp` dulu (`!cp /mnt/data/lookup.py /tmp/`).

## Batasan & catatan

- **Ukuran file Knowledge ≤ 512 MB per file** — `tafsir_full.db.xz` 18,7 MB aman; `tafsir_full.db` mentah (136 MB) juga lolos, tapi xz lebih cepat diunggah.
- **Sandbox tanpa internet** — Code Interpreter umumnya tidak bisa keluar jaringan; karena itu DB WAJIB diunggah ke Knowledge. Auto-download di `lookup.py` tetap dicoba paling akhir sebagai cadangan, jangan diandalkan.
- **Ekstraksi ±1 menit pertama kali per sesi** — isi `/tmp` tidak persisten antar percakapan, jadi run pertama tiap sesi baru mengekstrak ulang; run berikutnya dalam sesi yang sama memakai cache `/tmp/tafsir-lookup/`.
- **Percakapan baru setelah mengganti file Knowledge** — GPT kadang masih memakai salinan lama dalam percakapan yang sudah berjalan.
- Jumlah maksimum file Knowledge 20 — paket ini hanya 2.
