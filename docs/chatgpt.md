# ChatGPT — aplikasi (desktop/HP) atau web

ChatGPT bisa menjalankan program pencari basis data (lewat fitur *Code Interpreter*), jadi hasilnya sama akuratnya dengan Claude: teks Arab apa adanya + juz/halaman. Butuh paket **Plus/Team** (paket gratis tidak bisa mengunggah berkas ke Project/GPT).

## Yang perlu diunduh (sekali)
| | Tafsir | Sirah & Shahabat |
|---|---|---|
| Program pencari | [lookup.py](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/lookup.py) | [lookup.py](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/sirah/lookup.py) |
| Basis data | [tafsir_full.db.xz](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/tafsir-v1/tafsir_full.db.xz) (18 MB) | [sirah_full.db.xz](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/sirah-v1/sirah_full.db.xz) (17 MB) |
| Teks petunjuk | [instructions.md](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/instructions.md) | [instructions.md](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/sirah/instructions.md) |

(Klik kanan → *Save link as* bila browser menampilkan isinya alih-alih mengunduh.)

## Cara termudah — ChatGPT → "Work" (Project)
Siapkan dari **PC** (chatgpt.com di browser atau aplikasi desktop) — aplikasi HP belum bisa membuat Project dengan berkas; setelah jadi, Project-nya bisa dipakai dari HP.
1. Di PC, buka chatgpt.com atau aplikasi ChatGPT desktop → klik **Work** / **Projects** → **Project baru**, beri nama "Sirah Verbatim" (atau "Tafsir Verbatim").
2. **Files** → unggah dua berkas: `lookup.py` dan `*_full.db.xz` yang sesuai.
3. **Instructions** → tempel seluruh isi `instructions.md` yang sesuai.
4. Mulai chat **di dalam Project**, bertanya biasa: *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*. Pemakaian pertama tiap sesi butuh ±1 menit (ChatGPT mengekstrak basis data).

Buat dua Project terpisah bila ingin keduanya (tafsir & sirah).

## Cara lain — Custom GPT (bisa dibagikan lewat tautan)
Panduan langkah-per-langkah: [chatgpt/README-GPT.md](../chatgpt/README-GPT.md). Isinya sama (dua berkas ke *Knowledge*, petunjuk ke *Instructions*, nyalakan *Code Interpreter*, matikan *Web Search*).

## Catatan
- Sandbox ChatGPT tidak punya internet — basis data harus diunggah, tidak bisa diunduh otomatis.
- Materi panjang dikirim per bagian ≤8.000 karakter; ketik **lanjut** untuk bagian berikutnya.
