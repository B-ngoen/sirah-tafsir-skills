# INSTALL.md — petunjuk untuk AI/agen yang diminta "pelajari dan install ini sebagai skill"

Jika Anda adalah asisten AI (Claude Code, ChatGPT Work, Codex, pi, Hermes, opencode, atau agen lain dengan akses terminal) dan pengguna memberi tautan repo ini sambil meminta memasangnya sebagai skill, lakukan ini — tanpa bertanya balik kecuali ada kegagalan:

1. Jalankan pemasang satu-perintah (tanpa git):
   ```bash
   python -c "import urllib.request;exec(urllib.request.urlopen('https://raw.githubusercontent.com/B-ngoen/sirah-tafsir-skills/main/install.py').read().decode())"
   ```
   atau, bila repo sudah di-clone: `python install.py`
   - Memasang `tafsir-lookup` dan `sirah-lookup` sekaligus (`python install.py tafsir` / `sirah` untuk salah satu).
   - Pemasang mendeteksi folder skill Anda (Claude Code `~/.claude/skills/`; ChatGPT Work/Codex `~/.agents/skills/` (+ Codex lama `~/.codex/skills/`) + catatan di `AGENTS.md`; pi `~/.pi/agent/skills/`; Hermes `~/.hermes/skills/`; Gemini CLI `~/.gemini/skills/`). Paksa dengan `--target claude|chatgpt|codex|pi|hermes|gemini|dir:<folder>`.
   - Hermes juga bisa: `hermes skills install B-ngoen/sirah-tafsir-skills/skills/sirah-lookup`; Gemini CLI: `gemini skills install https://github.com/B-ngoen/sirah-tafsir-skills --path skills/sirah-lookup`.
   - Basis data (±17–18 MB terkompresi per skill) diunduh sekali ke cache permanen.
2. Verifikasi (sesuaikan path; Windows: `%USERPROFILE%\.claude\skills\...`): `python ~/.claude/skills/tafsir-lookup/scripts/lookup.py 2:255 -s tabari --max-chars 300` harus mencetak teks Arab + sitasi juz/halaman; sirah: `python ~/.claude/skills/sirah-lookup/scripts/lookup.py search بدر`. Di Windows, bila muncul `UnicodeEncodeError`, jalankan dengan `PYTHONIOENCODING=utf-8` (PowerShell: `$env:PYTHONIOENCODING='utf-8'`).
3. Beri tahu pengguna: skill aktif pada percakapan berikutnya; contoh pertanyaan: "tafsir QS 2:255 menurut Thabari, teks Arabnya", "kisah Perang Badar menurut Ibnu Hisyam, teks Arabnya".
4. Bila Anda TIDAK punya akses terminal/berkas permanen (mis. claude.ai web, ChatGPT tanpa mode Work):
   - Untuk percakapan ini saja: baca `skills/tafsir-lookup/SKILL.md` / `skills/sirah-lookup/SKILL.md` dan jalankan `scripts/lookup.py` di sandbox kode bila tersedia (DB diunduh otomatis dari GitHub Release).
   - Gemini web/ChatGPT tanpa terminal: lihat `docs/gemini.md` / `docs/chatgpt.md` (paket teks Knowledge & Custom GPT).
   - Untuk pemasangan permanen: arahkan pengguna ke bagian "Cara pasang" di README.md — berkas `.skill` siap unduh: `https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/tafsir-lookup.skill` dan `https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/sirah-lookup.skill` (unggah di claude.ai: Settings → Capabilities → Skills), atau tautan Custom GPT di ChatGPT.
   - Bila Anda agen yang memasang skill dari berkas `.skill` (zip berisi `<nama>/SKILL.md` + `scripts/lookup.py`): unduh URL di atas, ekstrak ke folder skill Anda.

Aturan pemakaian skill ada di `skills/<nama>/SKILL.md` — verbatim, sitasi wajib, sumber absen dikatakan absen, parafrase ditandai, dua mode (rujukan / materi lengkap).
