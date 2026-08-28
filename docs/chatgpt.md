# ChatGPT — hanya lewat mode **Work** (aplikasi desktop)

Skill ini perlu menjalankan program pencari (Python) dan membaca basis data lokal. Di ChatGPT, kemampuan itu hanya ada di **mode Work** pada aplikasi desktop (Windows/macOS), yang punya akses terminal ke komputer Anda (berbasis Codex). **Chat biasa — di web, di aplikasi desktop, maupun di HP — tidak bisa** menjalankannya walau skill sudah terpasang; ChatGPT akan menjawab "tidak bisa". Jadi: pasang **dan** pakai keduanya di Work.

## Cara 1 — satu kalimat di Work (termudah)
1. Buka aplikasi ChatGPT desktop → **Work** → thread baru.
2. Tempel:
   > **Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.**
3. ChatGPT membaca [INSTALL.md](../INSTALL.md), menjalankan pemasang (`python install.py --target chatgpt` → skill ke `~/.agents/skills/`), mengunduh basis data (±17–18 MB per skill, sekali, ke cache permanen), lalu memverifikasi. Setujui perintah yang diminta.
4. Buka **thread baru** agar skill terbaca, lalu bertanya biasa: *"Kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya"*.

## Cara 2 — sebagai plugin Codex (bisa dinonaktifkan/diperbarui dari menu)
Repo ini menyertakan plugin siap pasang di folder `codex-plugin/` (struktur mengikuti skill resmi `plugin-creator`). Di Work, tempel:
> Tolong unduh https://github.com/B-ngoen/sirah-tafsir-skills, pasang plugin dari folder `codex-plugin`-nya (`codex plugin marketplace add <folder codex-plugin>` lalu `codex plugin add tafsir-sirah-lookup@sirah-tafsir-skills`), kemudian jalankan `python install.py --target chatgpt` untuk mengunduh basis datanya.

Atau minta ChatGPT membuat plugin sendiri dari skill yang sudah terpasang lewat Cara 1: *"Ubah skill tafsir-lookup dan sirah-lookup menjadi plugin dengan `$plugin-creator`."* Hasilnya setara.

## Cara 3 — Project / Custom GPT (tanpa Work; belum diuji penuh)
Unggah `chatgpt/lookup.py` (atau `chatgpt/sirah/lookup.py`) + `*_full.db.xz` ke *Files/Knowledge*, tempel `instructions.md` yang sesuai, nyalakan *Code Interpreter*. Panduan: [chatgpt/README-GPT.md](../chatgpt/README-GPT.md). Perlu paket Plus/Team; sandbox tanpa internet sehingga basis data harus diunggah.

## Catatan
- Basis data disimpan di cache permanen (`%LOCALAPPDATA%\tafsir-lookup\`, `%LOCALAPPDATA%\sirah-lookup\` di Windows) agar tidak ikut terhapus saat skill/plugin diperbarui.
- Materi panjang dikirim per bagian; ketik **lanjut** untuk bagian berikutnya.
