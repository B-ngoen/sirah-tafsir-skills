# ChatGPT — mode Work (termudah), Project, atau Custom GPT

ChatGPT bisa menjalankan program pencari basis data, jadi hasilnya sama akuratnya dengan Claude: teks Arab apa adanya + juz/halaman.

## Cara 1 — mode Work (aplikasi ChatGPT desktop): satu kalimat
Mode **Work** punya akses terminal ke komputer Anda (berbasis Codex; skill dibaca dari `~/.agents/skills/`). Cukup tempel:

> **Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.**

ChatGPT membaca [INSTALL.md](../INSTALL.md), menjalankan pemasang (`python install.py --target chatgpt`), mengunduh basis data (±17–18 MB per skill, sekali saja), lalu siap. Setujui perintah yang diminta saat muncul. Setelah itu bertanya biasa: *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*.

Manual (tanpa AI): `python install.py --target chatgpt` dari folder repo yang diunduh.

## Cara 2 — Project atau Custom GPT (tanpa mode Work; Plus/Team)
## Yang perlu diunduh (sekali)
| | Tafsir | Sirah & Shahabat |
|---|---|---|
| Program pencari | [lookup.py](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/lookup.py) | [lookup.py](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/sirah/lookup.py) |
| Basis data | [tafsir_full.db.xz](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/tafsir-v1/tafsir_full.db.xz) (18 MB) | [sirah_full.db.xz](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/sirah-v1/sirah_full.db.xz) (17 MB) |
| Teks petunjuk | [instructions.md](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/instructions.md) | [instructions.md](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/chatgpt/sirah/instructions.md) |

(Klik kanan → *Save link as* bila browser menampilkan isinya alih-alih mengunduh.)

### Project
Siapkan dari PC (chatgpt.com atau aplikasi desktop); setelah jadi, Project-nya bisa dipakai dari HP.
1. **Projects** → **Project baru**, beri nama "Sirah Verbatim" (atau "Tafsir Verbatim").
2. **Files** → unggah dua berkas: `lookup.py` dan `*_full.db.xz` yang sesuai.
3. **Instructions** → tempel seluruh isi `instructions.md` yang sesuai.
4. Mulai chat **di dalam Project**, bertanya biasa: *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*. Pemakaian pertama tiap sesi butuh ±1 menit (ChatGPT mengekstrak basis data).

Buat dua Project terpisah bila ingin keduanya (tafsir & sirah).

### Custom GPT (bisa dibagikan lewat tautan)
Panduan langkah-per-langkah: [chatgpt/README-GPT.md](../chatgpt/README-GPT.md). Isinya sama (dua berkas ke *Knowledge*, petunjuk ke *Instructions*, nyalakan *Code Interpreter*, matikan *Web Search*).

## Catatan
- Sandbox ChatGPT tidak punya internet — basis data harus diunggah, tidak bisa diunduh otomatis.
- Materi panjang dikirim per bagian ≤8.000 karakter; ketik **lanjut** untuk bagian berikutnya.
