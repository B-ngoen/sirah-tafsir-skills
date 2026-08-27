# INSTALL.md — petunjuk untuk AI/agen yang diminta "pelajari dan install ini sebagai skill"

Jika Anda adalah asisten AI (Claude Code, Codex, pi, opencode, atau agen lain dengan akses terminal) dan pengguna memberi tautan repo ini sambil meminta memasangnya sebagai skill, lakukan ini — tanpa bertanya balik kecuali ada kegagalan:

1. Jalankan pemasang satu-perintah (tanpa git):
   ```bash
   python -c "import urllib.request;exec(urllib.request.urlopen('https://raw.githubusercontent.com/B-ngoen/sirah-tafsir-skills/main/install.py').read().decode())"
   ```
   atau, bila repo sudah di-clone: `python install.py`
   - Pemasang mendeteksi folder skill Anda (Claude Code: `~/.claude/skills/`; Codex: `~/.codex/skills/` + catatan di `AGENTS.md`). Paksa lokasi lain dengan `--target dir:<folder>`.
   - Basis data (±18 MB terkompresi) diunduh sekali ke cache permanen.
2. Verifikasi: `python ~/.claude/skills/tafsir-lookup/scripts/lookup.py 2:255 -s tabari --max-chars 300` harus mencetak teks Arab + sitasi juz/halaman.
3. Beri tahu pengguna: skill aktif pada percakapan berikutnya; contoh pertanyaan: "tafsir QS 2:255 menurut Thabari, teks Arabnya".
4. Bila Anda TIDAK punya akses terminal/berkas permanen (mis. claude.ai web, ChatGPT):
   - Untuk percakapan ini saja: baca `skills/tafsir-lookup/SKILL.md` dan jalankan `scripts/lookup.py` di sandbox kode bila tersedia (DB diunduh otomatis dari GitHub Release).
   - Untuk pemasangan permanen: arahkan pengguna ke bagian "Cara pasang" di README.md (unggah berkas `.skill` di claude.ai, atau tautan Custom GPT di ChatGPT).

Aturan pemakaian skill ada di `skills/<nama>/SKILL.md` — verbatim, sitasi wajib, sumber absen dikatakan absen, parafrase ditandai, dua mode (rujukan / materi lengkap).
