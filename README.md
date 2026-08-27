# sirah-tafsir-skills

**ID** · Skill untuk Claude (Code / claude.ai / aplikasi), ChatGPT (Custom GPT), dan agen lain agar mengutip **teks Arab VERBATIM** kitab tafsir dan sirah klasik — lengkap dengan sitasi juz/halaman cetak + tautan Maktabah Syamilah — tanpa halusinasi. Wakaf, gratis, non-komersial. *Semoga menjadi amal jariyah bagi siapa pun yang menyusun, merawat, dan memakainya.*

**EN** · Skills that let Claude, ChatGPT (Custom GPT), and other agents quote classical **Arabic tafsir and sīrah sources VERBATIM** with exact printed volume/page citations and Maktabah Shamela links — zero hallucination. Free, non-commercial waqf.

| Skill | Status | Sumber / Sources | DB |
|---|---|---|---|
| [`skills/tafsir-lookup`](skills/tafsir-lookup) | ✅ rilis | Tafsir ath-Thabari · al-Maraghi · Shafwat at-Tafasir (ash-Shabuni) · Ibnu Katsir (2 edisi) — 6.236/6.236 ayat | [`tafsir_full.db.xz`](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/tafsir-v1) ±18 MB |
| `skills/sirah-lookup` | 🔜 segera | Sirah Ibnu Hisyam (2 edisi) · Ibnu Ishaq · Thabaqat Ibnu Sa'd · Tarikh ath-Thabari · al-Ishabah · Usud al-Ghabah (2 edisi) · al-Isti'ab — 175 peristiwa/tahun + 9.700 shahabat | menyusul |

## Cara pakai / How to use

**Claude Code** — salin folder skill ke `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`):
```bash
git clone https://github.com/B-ngoen/sirah-tafsir-skills.git
cp -r sirah-tafsir-skills/skills/tafsir-lookup ~/.claude/skills/
```
Lalu bertanya seperti biasa ("tafsir QS 2:255 menurut Thabari, teks Arabnya"). DB (±18 MB) terunduh otomatis dari Release saat pertama dipakai dan di-cache permanen.

**claude.ai / aplikasi Claude** — unggah file `tafsir-lookup.skill` dari [Releases](https://github.com/B-ngoen/sirah-tafsir-skills/releases) di *Settings → Capabilities → Skills*. DB juga terunduh otomatis di sandbox.

**ChatGPT (Custom GPT + Code Interpreter)** — ikuti [`chatgpt/README-GPT.md`](chatgpt/README-GPT.md): tempel `chatgpt/instructions.md`, unggah `chatgpt/lookup.py` + `tafsir_full.db.xz` sebagai Knowledge.

**Codex / pi / opencode / agen lain** — jalankan `python skills/tafsir-lookup/scripts/lookup.py 2:255` dan tempel isi `SKILL.md` ke instruksi agen (AGENTS.md).

```
python lookup.py 2:255                       # semua kitab, markdown
python lookup.py 2:255 -s tabari,maraghi     # pilih kitab
python lookup.py 2:255 --toc                 # daftar segmen + sub-judul (mode materi lengkap)
python lookup.py 2:255 --seg 7928 --paras 0-60   # baca satu segmen bagian demi bagian
python lookup.py 1 --intro                   # pembuka surah
python lookup.py --coverage 2                # cakupan surah per kitab
```

## Prinsip

1. **Verbatim** — teks tidak diubah satu huruf pun (tasykil, catatan kaki muhaqqiq, sanad ikut).
2. **Sitasi wajib** — kitab + edisi, juz/halaman cetak, URL shamela per kutipan.
3. **Absen dikatakan absen** — tidak diisi dari kitab lain atau ingatan model.
4. **Parafrase ditandai** — ringkasan AI selalu terpisah dari blok verbatim.
5. **Dua mode** — *Rujukan* (ringkas) dan *Materi/Lengkap* (`--toc` → baca segmen penuh bagian demi bagian).

## Sumber, atribusi, lisensi

- Teks diambil dari **Maktabah Syamilah (shamela.ws)**, 18 Agustus 2026, halaman demi halaman (tabel `pages`), dengan nomor juz/halaman edisi cetak yang dipakai Syamilah:
  Tafsir ath-Thabari (ط دار التربية والتراث) · Tafsir al-Maraghi · Shafwat at-Tafasir · Tafsir Ibnu Katsir (ط أولاد الشيخ) · Tafsir Ibnu Katsir (ط دار ابن الجوزي). Jazahumullah khairan para muhaqqiq dan tim Syamilah.
- **Teks kitab klasik adalah milik umum.** Apparatus muhaqqiq (catatan kaki) disertakan apa adanya demi keaslian edisi; bila pemegang hak edisi tertentu berkeberatan, hubungi kami — bagian itu akan dihapus dari rilis berikutnya.
- Edisi publik **tidak memuat** sumber berhak cipta modern (mis. terjemah Dorar EN).
- Kode (skrip, skill, pipeline): **MIT** — lihat [LICENSE](LICENSE). Basis data: dibagikan sebagai wakaf non-komersial; dilarang diperjualbelikan.
- Dibangun dengan Claude Code + GLM/MiniMax via `pi`; pipeline lengkap (scrape → parse → grouping → build) ada di [`pipeline/`](pipeline/) agar bisa direproduksi.

## Keterbatasan yang jujur

- Shafwat at-Tafasir: edisi elektronik terpotong (surah 114 absen). Ibnu Katsir ط ابن الجوزي: akhir mushaf terpotong (113–114 hanya pembuka gabungan).
- Batas segmen dibentuk dari heading (rule-based + LLM) — label rentang ayat ("249–280") dijelaskan di output.
- Sirah: registry 175 peristiwa masih draf; tautan entitas antar-kamus shahabat ±78% (status/confidence tersimpan per entri).

## Kontribusi

Koreksi batas segmen, registry peristiwa, atau tautan shahabat sangat diterima lewat *Issues/PR*. Mohon jaga tiga hal: verbatim, sitasi, non-komersial.
