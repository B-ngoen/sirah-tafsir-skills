# sirah-tafsir-skills

*English version: [README-EN.md](README-EN.md)*

Skill agar asisten AI (Claude, ChatGPT, dan agen lain) **mengutip teks Arab asli, apa adanya (verbatim)** dari kitab tafsir dan sirah klasik — lengkap dengan juz/halaman cetak dan tautan Maktabah Syamilah — bukan dari "ingatan" AI yang sering keliru. Gratis, wakaf, non-komersial. *Semoga menjadi amal jariyah bagi siapa pun yang menyusun, merawat, membagikan, dan memakainya.*

| Skill | Status | Kitab |
|---|---|---|
| **tafsir-lookup** | ✅ siap | Tafsir ath-Thabari · al-Maraghi · Shafwat at-Tafasir (ash-Shabuni) · Tafsir Ibnu Katsir (2 edisi) — 6.236/6.236 ayat |
| **sirah-lookup** | ✅ siap | Sirah Ibnu Hisyam (2 edisi) · Ibnu Ishaq · Thabaqat Ibnu Sa'd · Tarikh ath-Thabari · al-Ishabah · Usud al-Ghabah (2 edisi) · al-Isti'ab — 175 peristiwa/tahun & ±9.700 shahabat |

---

## Cara pasang (pilih yang paling mudah untuk Anda)

### 1) Cukup satu kalimat — untuk Claude Code, Codex, dan asisten ber-terminal lain
Buka asisten Anda, tempel kalimat ini:

> **Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill.**

Asisten akan membaca [INSTALL.md](INSTALL.md), menjalankan pemasang, mengunduh basis data (±18 MB per skill, sekali saja), lalu memberi tahu Anda sudah siap. Setelah itu tinggal bertanya biasa, contoh:
- "Tafsir QS Al-Baqarah 255 menurut Thabari dan Ibnu Katsir, teks Arabnya."
- "Buatkan materi kajian tafsir QS Al-Fatihah yang lengkap dari semua kitab."
- "Kisah Perang Badar menurut Ibnu Hisyam dan Thabari, teks Arabnya."
- "Siapa Abu Bakar ash-Shiddiq menurut al-Ishabah dan Usud al-Ghabah?"
- "Buatkan materi lengkap wafatnya Nabi ﷺ dan Saqifah dari semua kitab."

Ingin tanpa AI? Jalankan sendiri: `python install.py` (unduh berkasnya dari repo ini) — tidak perlu git.

### 2) claude.ai (web) dan aplikasi Claude
1. Unduh berkas **`tafsir-lookup.skill`** ([rilis tafsir-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/tafsir-v1)) dan/atau **`sirah-lookup.skill`** ([rilis sirah-v1](https://github.com/B-ngoen/sirah-tafsir-skills/releases/tag/sirah-v1)).
2. Di claude.ai: **Settings → Capabilities → Skills → Upload skill**, pilih berkas itu (ulangi untuk skill kedua).
3. Mulai percakapan baru dan bertanya seperti biasa. Basis data diunduh otomatis di dalam sandbox Claude saat pertama dipakai (±1 menit).

Belum bisa lewat satu kalimat di sini karena Claude web tidak bisa memasang skill dari dalam percakapan; tetapi Anda bisa menempel tautan repo ini di chat dan berkata "pelajari dan pakai untuk percakapan ini" — Claude akan memakainya sementara.

### 3) ChatGPT
Cara termudah: pakai **Custom GPT** yang sudah jadi (tautan akan dicantumkan di sini setelah diterbitkan).  
Ingin membuat sendiri? Ikuti panduan bergambar-langkah di [chatgpt/README-GPT.md](chatgpt/README-GPT.md): tempel `instructions.md`, unggah `lookup.py` + `tafsir_full.db.xz`, nyalakan *Code Interpreter*. ±5 menit. (Paket ChatGPT untuk sirah menyusul.)

### 4) Agen lain (pi, opencode, dsb.)
Tempel isi `skills/tafsir-lookup/SKILL.md` / `skills/sirah-lookup/SKILL.md` ke instruksi agen (mis. `AGENTS.md`) dan jalankan `python skills/tafsir-lookup/scripts/lookup.py 2:255` atau `python skills/sirah-lookup/scripts/lookup.py search بدر`.

---

## Yang membedakan skill ini

1. **Verbatim** — teks kitab tidak diubah satu huruf pun (harakat, catatan kaki muhaqqiq, sanad ikut).
2. **Sitasi wajib** — nama kitab + edisi, juz/halaman cetak, tautan shamela.ws pada setiap kutipan.
3. **Yang tidak ada dikatakan tidak ada** — tidak ditambal dari kitab lain atau dari ingatan AI.
4. **Ringkasan AI selalu ditandai** dan dipisah dari kutipan asli.
5. **Dua mode** — *Rujukan* (jawaban ringkas + kutipan terpilih) dan *Materi lengkap* (AI membaca seluruh bab bagian demi bagian, lalu menyusun uraian runtut + lampiran kutipan per sub-bab).
6. **Ramah paket gratis** — materi panjang dikirim per bagian; tiap bagian ditutup dengan "Ketik **lanjut** untuk Bagian berikutnya" karena setiap model punya batas panjang jawaban. Cukup ketik *lanjut*, materi berlanjut tanpa mengulang.

## Sumber, atribusi, lisensi

- Teks bersumber dari **Maktabah Syamilah (shamela.ws)**, diambil halaman demi halaman beserta nomor juz/halaman edisi cetak yang dipakai Syamilah. Tafsir (18 Agustus 2026): Tafsir ath-Thabari (ط دار التربية والتراث) · Tafsir al-Maraghi · Shafwat at-Tafasir · Tafsir Ibnu Katsir (ط أولاد الشيخ) · Tafsir Ibnu Katsir (ط دار ابن الجوزي). Sirah (26 Agustus 2026): Sirah Ibnu Hisyam (ط السقا & ط طه) · Sirah Ibnu Ishaq · ath-Thabaqat al-Kubra (Ibnu Sa'd) · Tarikh ath-Thabari · al-Ishabah · Usud al-Ghabah (2 edisi) · al-Isti'ab. Jazahumullah khairan para muhaqqiq dan tim Syamilah.
- **Teks kitab klasik adalah milik umum.** Catatan kaki muhaqqiq disertakan apa adanya demi keaslian edisi; bila pemegang hak suatu edisi berkeberatan, sampaikan lewat *Issues* — bagian itu akan dihapus pada rilis berikutnya.
- Edisi publik **tidak memuat** karya modern berhak cipta (mis. terjemah Dorar EN).
- Kode (skrip, skill): **MIT** — lihat [LICENSE](LICENSE). Basis data: wakaf non-komersial; dilarang diperjualbelikan.

## Keterbatasan

- Shafwat at-Tafasir: edisi elektronik terpotong (surah 114 tidak ada). Ibnu Katsir ط ابن الجوزي: akhir mushaf terpotong (113–114 hanya pembuka gabungan).
- Batas segmen dibentuk dari judul bab (aturan + AI); bila kutipan berlabel rentang ayat ("249–280"), AI akan menjelaskannya.
- Sirah: daftar 175 peristiwa/tahun masih draf (koreksi diterima); tautan nama shahabat antar-kamus ±78 % (status tersimpan per entri dan disampaikan AI). Sirah Ibnu Hisyam ط طه edisi elektroniknya terpotong (bab Badar tidak lengkap; AI menandainya).

## Kontribusi

Koreksi batas segmen, daftar peristiwa, atau tautan shahabat sangat diterima lewat *Issues/PR*. Mohon jaga tiga hal: verbatim, sitasi, non-komersial.
