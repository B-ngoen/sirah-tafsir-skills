# ChatGPT — Custom GPT atau Project (aplikasi & web)

ChatGPT bisa menjalankan `lookup.py` lewat **Code Interpreter** (Python), jadi hasilnya verbatim + juz/halaman seperti di Claude. Syarat: paket Plus/Team/Enterprise (paket gratis tidak bisa membuat GPT/Project dengan berkas).

## Cara 1 — Custom GPT (dibagikan lewat tautan)
Panduan langkah-per-langkah: [chatgpt/README-GPT.md](../chatgpt/README-GPT.md).
Ringkasnya, untuk tiap skill buat satu GPT:

| | Tafsir | Sirah |
|---|---|---|
| Instructions | `chatgpt/instructions.md` | `chatgpt/sirah/instructions.md` |
| Knowledge (2 berkas) | `chatgpt/lookup.py` + `tafsir_full.db.xz` ([unduh](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/tafsir-v1/tafsir_full.db.xz)) | `chatgpt/sirah/lookup.py` + `sirah_full.db.xz` ([unduh](https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/sirah-v1/sirah_full.db.xz)) |
| Capabilities | ✅ Code Interpreter; matikan Web Search | sama |

Tautan Custom GPT publik akan dicantumkan di README utama setelah diterbitkan.

## Cara 2 — Project (mode kerja di aplikasi ChatGPT)
1. Sidebar → **Projects → New project** → beri nama.
2. **Files**: unggah `lookup.py` (versi ChatGPT, folder `chatgpt/` atau `chatgpt/sirah/`) dan `*_full.db.xz`.
3. **Instructions**: tempel isi `instructions.md` yang sesuai.
4. Mulai chat di dalam Project; ChatGPT menjalankan `python /mnt/data/lookup.py …` sendiri. Eksekusi pertama tiap sesi mengekstrak DB (±1 menit).

## Catatan
- Sandbox ChatGPT biasanya tanpa internet — DB harus diunggah, tidak bisa diunduh otomatis.
- Materi panjang dikirim per bagian ≤8.000 karakter; ketik **lanjut**.
