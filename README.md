# sirah-tafsir-skills

*English version: [README-EN.md](README-EN.md)*

Skill agar asisten AI (Claude, ChatGPT, dan agen lain) **mengutip teks Arab asli, apa adanya (verbatim)** dari kitab tafsir dan sirah klasik — lengkap dengan juz/halaman cetak dan tautan Maktabah Syamilah — bukan dari "ingatan" AI yang sering keliru. Gratis, wakaf, non-komersial. *Semoga menjadi amal jariyah bagi siapa pun yang menyusun, merawat, membagikan, dan memakainya.*

| Skill | Status | Kitab |
|---|---|---|
| **tafsir-lookup** | ✅ siap | Tafsir ath-Thabari · al-Maraghi · Shafwat at-Tafasir (ash-Shabuni) · Tafsir Ibnu Katsir (2 edisi) — 6.236/6.236 ayat · **baru:** Asbabun Nuzul *Lubab an-Nuqul* (as-Suyuthi) |
| **hadith-lookup** | ✅ siap (baru) | Shahih al-Bukhari · Shahih Muslim · Sunan Abu Dawud · Sunan an-Nasa'i · Sunan at-Tirmidzi · Sunan Ibnu Majah · al-Muwaththa' · Musnad Ahmad · Sunan ad-Darimi · Bulughul Maram · Riyadhus Shalihin (+ tahqiq al-Albani) — ±70.900 hadits, cari per nomor, teks Arab, atau judul bab; derajat hanya yang tertulis di edisi (al-Albani, al-Arna'uth, az-Zuhairi, Husain Asad, at-Tirmidzi) |
| **sirah-lookup** | ✅ siap | Sirah Ibnu Hisyam (2 edisi) · Ibnu Ishaq · Thabaqat Ibnu Sa'd · Tarikh ath-Thabari · al-Ishabah · Usud al-Ghabah (2 edisi) · al-Isti'ab — 175 peristiwa/tahun & ±9.700 shahabat |

---

## Cara pasang — pilih asisten AI yang Anda pakai

| Asisten | Yang dilakukan | Akurasi | Panduan |
|---|---|---|---|
| **Claude** — claude.ai / aplikasi desktop (paket gratis pun bisa); **pasang lewat PC**, setelah itu bisa dipakai juga di aplikasi HP | Di PC: unduh [tafsir-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/tafsir-lookup.skill) , [sirah-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/sirah-lookup.skill), dan/atau [hadith-lookup.skill](https://github.com/B-ngoen/sirah-tafsir-skills/raw/main/release/hadith-lookup.skill) → *Settings → Capabilities → Skills → Upload skill*. Basis data diunduh otomatis di sisi Claude saat pertama dipakai — sama saja dipakai dari HP maupun desktop. | ★★★ membaca basis data langsung | [docs/claude.md](docs/claude.md) |
| **Claude Desktop — mode Cowork / Code** (punya akses terminal) | Tempel di Cowork: *"Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill."* Skill masuk ke `~/.claude/skills/` dan ikut terbaca di chat biasa Claude Desktop/HP. | ★★★ | [docs/claude.md](docs/claude.md) |
| **Claude Code** (terminal) | Tempel: *"Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill."* | ★★★ | [docs/claude.md](docs/claude.md) |
| **ChatGPT** — **hanya mode Work** di aplikasi desktop (chat biasa & HP tidak bisa) | Di Work, tempel kalimat yang sama seperti Claude Code: *"Tolong pelajari https://github.com/B-ngoen/sirah-tafsir-skills dan install sebagai skill."* Tersedia juga sebagai plugin Codex siap pasang (folder `codex-plugin/`). | ★★★ | [docs/chatgpt.md](docs/chatgpt.md) |
| **Gemini** — lewat **NotebookLM** (gratis), lalu Gem bila mau | Unggah paket teks kitab ke NotebookLM → tempel petunjuk → bertanya. Ingin di aplikasi Gemini: buat Gem yang sumbernya notebook itu. | ★★ pencarian teks (bab panjang bisa tidak utuh) | [docs/gemini.md](docs/gemini.md) |
| **Hermes Agent** | `hermes skills install B-ngoen/sirah-tafsir-skills/skills/sirah-lookup` (dan `.../tafsir-lookup`, `.../hadith-lookup`) | ★★★ | [docs/hermes.md](docs/hermes.md) |
| **pi**, Codex, Gemini CLI, agen ber-terminal lain | Kalimat yang sama seperti Claude Code, atau `python install.py --target pi` / `codex` / `gemini` | ★★★ | [docs/pi.md](docs/pi.md) |

Setelah terpasang tinggal bertanya biasa, contoh:
- "Tafsir QS Al-Baqarah 255 menurut Thabari dan Ibnu Katsir, teks Arabnya."
- "Buatkan materi kajian tafsir QS Al-Fatihah yang lengkap dari semua kitab."
- "Kisah Perang Badar menurut Ibnu Hisyam dan Thabari, teks Arabnya."
- "Siapa Abu Bakar ash-Shiddiq menurut al-Ishabah dan Usud al-Ghabah?"
- "Asbabun nuzul QS 'Abasa ayat 1 menurut Lubab an-Nuqul."
- "Tampilkan HR. Muslim no. 8 lengkap dengan teks Arabnya." · "Apakah hadits Abu Dawud 1 shahih? Kutip penilaian muhaqqiq-nya."
- "Buatkan materi lengkap wafatnya Nabi ﷺ dan Saqifah dari semua kitab."

Basis data (±17–18 MB untuk tafsir/sirah, ±41 MB untuk hadits) diunduh sekali saat pertama dipakai. Ingin tanpa AI? `python install.py` (unduh berkasnya dari repo ini) — tidak perlu git.

---

## Yang membedakan skill ini

1. **Verbatim** — teks kitab tidak diubah satu huruf pun (harakat, catatan kaki muhaqqiq, sanad ikut).
2. **Sitasi wajib** — nama kitab + edisi, juz/halaman cetak, tautan shamela.ws pada setiap kutipan.
3. **Yang tidak ada dikatakan tidak ada** — tidak ditambal dari kitab lain atau dari ingatan AI.
4. **Ringkasan AI selalu ditandai** dan dipisah dari kutipan asli.
5. **Dua mode** — *Rujukan* (jawaban ringkas + kutipan terpilih) dan *Materi lengkap* (AI membaca seluruh bab bagian demi bagian, lalu menyusun uraian runtut + lampiran kutipan per sub-bab).
6. **Ramah paket gratis** — materi panjang dikirim per bagian; tiap bagian ditutup dengan "Ketik **lanjut** untuk Bagian berikutnya" karena setiap model punya batas panjang jawaban. Cukup ketik *lanjut*, materi berlanjut tanpa mengulang.

## Sumber, atribusi, lisensi

- Teks bersumber dari **Maktabah Syamilah (shamela.ws)**, diambil halaman demi halaman beserta nomor juz/halaman edisi cetak yang dipakai Syamilah. Tafsir (18 Agustus 2026): Tafsir ath-Thabari (ط دار التربية والتراث) · Tafsir al-Maraghi · Shafwat at-Tafasir · Tafsir Ibnu Katsir (ط أولاد الشيخ) · Tafsir Ibnu Katsir (ط دار ابن الجوزي). Sirah (26 Agustus 2026): Sirah Ibnu Hisyam (ط السقا & ط طه) · Sirah Ibnu Ishaq · ath-Thabaqat al-Kubra (Ibnu Sa'd) · Tarikh ath-Thabari · al-Ishabah · Usud al-Ghabah (2 edisi) · al-Isti'ab. Asbabun Nuzul & hadits (1 Oktober 2026): Lubab an-Nuqul (ط دار الكتب العلمية) · Shahih al-Bukhari (ط السلطانية، ترقيم عبد الباقي) · Shahih Muslim (ت عبد الباقي) · Sunan Abi Dawud (ت محيي الدين عبد الحميد) · Sunan an-Nasa'i (ط الرسالة) · Sunan at-Tirmidzi (ت شاكر) · Sunan Ibnu Majah (ت عبد الباقي) · al-Muwaththa' riwayat Yahya (ت عبد الباقي) · Musnad Ahmad (ط الرسالة) · Musnad/Sunan ad-Darimi (ت حسين أسد) · Bulugh al-Maram (ت الزهيري) · Riyadh ash-Shalihin (ت الأرنؤوط) & tahqiq al-Albani (المكتب الإسلامي). Jazahumullah khairan para muhaqqiq dan tim Syamilah.
- **Teks kitab klasik adalah milik umum.** Catatan kaki muhaqqiq disertakan apa adanya demi keaslian edisi; bila pemegang hak suatu edisi berkeberatan, sampaikan lewat *Issues* — bagian itu akan dihapus pada rilis berikutnya.
- Kode (skrip, skill): **MIT** — lihat [LICENSE](LICENSE). Basis data: wakaf non-komersial; dilarang diperjualbelikan.

## Keterbatasan

- Shafwat at-Tafasir: edisi elektronik terpotong (surah 114 tidak ada). Ibnu Katsir ط ابن الجوزي: akhir mushaf terpotong (113–114 hanya pembuka gabungan).
- Batas segmen dibentuk dari judul bab (aturan + AI); bila kutipan berlabel rentang ayat ("249–280"), AI akan menjelaskannya.
- Sirah: daftar 175 peristiwa/tahun masih draf (koreksi diterima); tautan nama shahabat antar-kamus ±78 % (status tersimpan per entri dan disampaikan AI). Sirah Ibnu Hisyam ط طه edisi elektroniknya terpotong (bab Badar tidak lengkap; AI menandainya).
- Hadits: nomor mengikuti edisi cetak di Syamilah. Salah cetak nomor yang jelas dikoreksi dan **selalu** ditampilkan bersama nomor tercetaknya; rujukan balik Muslim (hadits diulang dengan nomor lamanya) dibiarkan sesuai cetakan. Muwaththa' edisi ini tanpa nomor global → dirujuk *kitab/nomor* (mis. 1/1). Riyadhus Shalihin tahqiq al-Albani di Syamilah hanya memuat hadits yang dikomentari beliau (94 entri) dan penomorannya berbeda 1–9 dari edisi al-Arna'uth (dipasangkan lewat kemiripan teks).
- Asbabun Nuzul: riwayat lanjutan ("وأخرج … نحوه") dilekatkan ke entri di atasnya; 17 riwayat tingkat-surah tanpa kutipan ayat ditandai *intro*.

## Kontribusi

Koreksi batas segmen, daftar peristiwa, atau tautan shahabat sangat diterima lewat *Issues/PR*. Mohon jaga tiga hal: verbatim, sitasi, non-komersial.
