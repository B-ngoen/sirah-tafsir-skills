---
name: sirah-lookup
description: Look up VERBATIM Arabic source text on the Prophet's biography (Sirah Nabawiyah) and the Companions (Shahabat) from 10 classical works — Ibn Hisham (2 editions), Ibn Ishaq, Ibn Sa'd's Tabaqat (+ Tabi'in volume), Tarikh at-Tabari, Al-Ishabah, Usud al-Ghabah (2 editions), Al-Isti'ab — organized by EVENT/YEAR (Badr, Uhud, Hijrah, Hudaibiyah, year N H…) and by COMPANION (canonical key = Al-Ishabah entry), each source in its own column with exact print citations (juz/page/URL), zero hallucination. Use this whenever the user asks about any sirah event, ghazwah/sariyyah, what happened in year N Hijriah, a companion's biography/virtues/traits/role, "apa kata Ibnu Hisyam/Thabari/Ibnu Sa'd tentang…", "riwayat tentang Abu Bakar/Umar/Khalid…", who took part in Badr, or wants Arabic source text on early Islamic history — even if they don't say "sirah" or "shahabat".
---

# sirah-lookup — Sirah & Shahabat Verbatim 10 Sumber

Query teks klasik **verbatim** langsung dari SQLite DB hasil scrape shamela.ws (26.123 halaman, 10 kitab) — bukan dari ingatan model. Dua sumbu: **peristiwa/tahun** (registry 175 peristiwa, kunci `event_id`) dan **shahabat** (kunci kanonik = nomor entri Al-Ishabah; entri Usud/Isti'ab/Thabaqat ditautkan ke sana).

## Sumber Tunggal — tidak ada sumber lain

Satu-satunya sumber jawaban adalah **keluaran `scripts/lookup.py` pada percakapan ini**. Ini berlaku juga untuk model dengan mode *thinking/reasoning*: apa pun yang Anda "ingat" dari kitab lain, hadis, artikel, situs, atau terjemahan **tidak boleh** masuk ke jawaban — bukan sebagai kutipan, bukan sebagai sitasi, bukan sebagai "tambahan untuk konteks". Alasannya: pengguna memakai skill ini justru karena ingatan model sering keliru dan tidak bisa diverifikasi; satu sitasi luar yang salah merusak kepercayaan pada seluruh jawaban.

- Nama kitab yang boleh muncul sebagai sumber hanya 10 kitab di bagian **Sumber** (Ibnu Hisyam 2 edisi, Ibnu Ishaq, Thabaqat Ibnu Sa'd, Tarikh ath-Thabari, al-Ishabah, Usud al-Ghabah 2 edisi, al-Isti'ab). Nama lain (Shahih Bukhari, Muslim, ar-Rahiq al-Makhtum, Zadul Ma'ad, tafsir lain, Wikipedia, dorar.net, dsb.) **dilarang** muncul sebagai sumber.
- Tidak ada pencarian web, tidak ada pembacaan berkas lain, tidak ada "menurut riwayat yang masyhur" tanpa kutipan dari script.
- Bila pengguna bertanya sesuatu yang tidak ada di basis data, jawab: *"Tidak ada dalam 10 kitab basis data ini"* — lalu berhenti. Jangan mengisi kekosongan dari ingatan. Hanya bila pengguna **secara eksplisit** meminta pendapat/pengetahuan umum, boleh menjawab di bagian terpisah berjudul **"Di luar basis data (dari ingatan model, tidak terverifikasi)"** — tanpa kutipan Arab dan tanpa sitasi juz/halaman.
- **Jawaban tanpa blok kutipan Arab yang disalin dari keluaran script — lengkap dengan baris `— Sumber: juz X hal Y · URL` — bukan jawaban skill ini.** Jangan pernah menulis uraian sirah/tafsir "bersitasi" dari ingatan (contoh kebocoran nyata: *"Tarikh ath-Thabari, jilid 14, hlm. 143"* dan *"Shahih al-Bukhari 7207"* — nomor jilid/hadis itu tidak ada di keluaran script; basis data hanya memakai juz/hal + URL shamela). Bila script belum dijalankan, jalankan dulu; bila tidak bisa dijalankan (tidak ada akses terminal/Python), katakan itu dan berhenti — jangan menjawab dari ingatan sebagai pengganti.
- Tanda kebocoran yang harus Anda hapus sebelum mengirim: sitasi tanpa URL shamela; "jilid/hlm." yang tidak tercetak di keluaran; nomor hadis; "menurut riwayat yang masyhur"; "para sejarawan/historiografi Sunni–Syiah"; nama kitab/situs di luar daftar Sumber; nama ulama atau periwayat yang tidak muncul dalam teks yang dikutip.
- **Pemeriksaan sebelum mengirim** (lakukan diam-diam): (1) setiap baris Arab yang dikutip ada persis di keluaran script; (2) setiap sitasi menunjuk kitab dari daftar Sumber dengan juz/hal yang tercetak di keluaran; (3) tidak ada nama kitab/situs lain di mana pun dalam jawaban; (4) parafrase Anda ditandai. Ada yang gagal → hapus bagian itu, jangan diperhalus.

## Cara Pakai

SELALU jalankan script; JANGAN menjawab pertanyaan sirah/shahabat dari ingatan model:

```
python scripts/lookup.py search بدر                  # cari event & orang (Arab atau Indonesia), dapat id
python scripts/lookup.py event ghazwah_badr_kubra    # semua kitab, kolom terpisah (markdown)
python scripts/lookup.py event badar -s hisyam_saqqa,tarikh_tabari
python scripts/lookup.py event --list                # daftar 175 peristiwa kronologis
python scripts/lookup.py person "أبو بكر"            # kandidat → pilih ishabah_id
python scripts/lookup.py person 4835 --max-chars 0   # entri Abu Bakr di semua kamus, teks penuh
python scripts/lookup.py year 2                      # segmen "سنة اثنتين" Thabari + peristiwa tahun 2 H
python scripts/lookup.py event ghazwah_uhud --toc         # daftar isi: sub-bab, rentang, ~kchar, [syair]/[nasab]
python scripts/lookup.py event ghazwah_uhud --seg 44 --subbab "مقتل حمزة"   # satu sub-bab penuh
python scripts/lookup.py event ghazwah_uhud --seg 44 --paras 0-59 --exclude-poetry > uhud_a.md
python scripts/lookup.py coverage event              # cakupan per sumber
python scripts/lookup.py info                        # provenance, meta DB
```

Alur yang benar: `search` dulu bila belum tahu id → `event`/`person` dengan id. Kandidat ganda → script keluar dengan exit 2 dan daftar kandidat; pilih berdasarkan nasab/nisbah, jangan menebak. `--format json` untuk pemrosesan; default `--max-chars 6000` per sumber (potong di batas paragraf; `0` = penuh).

DB dicari otomatis: env `SIRAH_DB` → folder skill → cwd → upload Cowork → path laptop → auto-download (GitHub release → server privat owner). Exit code: 0 sukses, 2 input/kandidat ganda, 3 DB hilang.

## Dua Mode — pilih dulu sebelum menjalankan script

Ringkasan hanya lapisan penyajian; konteks Anda harus tetap utuh. Karena itu tentukan mode dari niat pengguna:

| | **Mode RUJUKAN** (default) | **Mode MATERI / LENGKAP** |
|---|---|---|
| Pemicu | pertanyaan faktual, "apa kata X tentang Y", verifikasi satu riwayat | "kisah lengkap", "materi/kajian/ceramah", "uraikan", "narasi kronologis", "elaborasi", "bahan mengajar" |
| Script | `--max-chars 2500` per segmen | `--toc` dulu (tiap sub-bab tampil rentang paragraf, `~kchar`, penanda `[syair]`/`[nasab]`/`[catatan]`), lalu baca sub-bab demi sub-bab: `--seg <id> --subbab <idx|judul>` (boleh diulang; `--exclude-poetry` untuk melewati bait dengan penanda jujur), atau `--paras A-B` bila perlu rentang bebas — sampai habis; jangan mengelaborasi dari potongan |
| Keluaran | Ringkasan ≤100 kata → verbatim terpilih → Catatan | Ringkasan → **narasi kronologis** (parafrase Anda, boleh panjang, tiap paragraf bersitasi `[kitab, juz/hal]`) → **lampiran verbatim** per kitab, dipecah per sub-bab (judul dari `--toc`); untuk teks sangat panjang tawarkan lanjutan per bab agar tidak meledak |

Bila ragu, tanya satu kalimat: "Rujukan singkat atau materi lengkap?" — jangan menebak ke arah ringkas.

Disiplin Mode MATERI (pelajaran dari uji coba):
- `--toc` menampilkan SEMUA segmen sebuah peristiwa per kitab (mis. Badr Ibnu Hisyam = segmen "غزوة بدر" + segmen "ما نزل في الأسارى والمغانم"). Jangan mengabaikan segmen berdasarkan dugaan judul — intip 10 paragraf pertamanya (`--seg X --paras 0-9`) lalu putuskan; bagian yang diminta pengguna (mis. "tawanan") sering ada di segmen kedua.
- Lampiran verbatim disusun **per sub-bab** memakai judul dari `--toc` (`### <judul sub-bab> — juz X hal Y`), bukan potongan per 60 paragraf dengan header berulang. Paging hanya cara membaca, bukan struktur jawaban.
- Batasi satu jawaban ±40–60 ribu karakter: kirim Bagian 1 (narasi lengkap + lampiran sub-bab yang paling penting), lalu tutup dengan daftar sub-bab yang belum dilampirkan dan tawaran eksplisit "ketik *lanjut* untuk Bagian 2" — pengguna memutuskan, bukan Anda yang memangkas diam-diam.
- Daftar nasab peserta dan syair tetap bagian sah dari kitab; sebutkan keberadaannya (judul + rentang paragraf) walau tidak dilampirkan.
- Output `--seg/--paras` besar (>30 KB) selalu **redirect ke file** (`> uhud_seg44_a.md`) lalu baca file itu — jangan mengandalkan pratinjau terminal yang terpotong.
- **Permintaan multi-peristiwa** (mis. "wafat Nabi + Saqifah + pasukan Usamah"): jalankan `--toc` untuk SEMUA event terkait dulu, lalu baca hanya sub-bab yang menjawab (`--subbab`, `--exclude-poetry`) — jangan menelan segmen 1.000+ paragraf utuh. Bila lebih dari ±1.500 paragraf tetap perlu dibaca, bagi pekerjaan: satu pembaca per kitab (subagent/langkah terpisah) yang menghasilkan berkas ekstrak per sub-bab, lalu satu penyusun narasi.
- **Tulis keluaran bertahap**: susun jawaban di berkas dengan beberapa kali *append* (narasi dulu, lalu lampiran per kitab), bukan satu tulisan raksasa — keluaran tunggal >±50 ribu karakter bisa gagal di batas token model. Bagian 1 tetap ≤60 ribu karakter.

## Protokol Bagian — untuk semua model, termasuk paket gratis tanpa subagent

Banyak pengguna memakai model dengan batas keluaran kecil dan tanpa subagent, tetapi meminta materi panjang. Karena itu:

**Deteksi kemampuan (lakukan dulu, tanpa bertanya ke pengguna):**
- **Punya tool subagent?** (Claude Code: tool `Agent`/`Task` ada di daftar tool; Codex/agen lain: kemampuan spawn sub-task.) → **Jalur MAKSIMAL**: untuk mode MATERI multi-kitab, luncurkan satu *pembaca* per kitab secara paralel (tiap pembaca: `--toc` → `--subbab` terpilih → berkas ekstrak ≤45.000 karakter, verbatim + sitasi + 1–2 kalimat isi), lalu Anda menyusun narasi dari berkas ekstrak. Bagian boleh sampai ±40.000 karakter.
- **Tanpa subagent tetapi keluaran besar** (Claude Code/Codex tanpa Agent tool): jalur tunggal, Bagian ≤25.000 karakter, baca-tulis mengalir.
- **Sandbox chat / model gratis / batas keluaran kecil** (claude.ai web, ChatGPT, atau Anda tahu batas Anda kecil): Bagian ≤12.000 (≤8.000 bila sangat kecil).
Kalau ragu, ambil jalur di bawahnya — lebih baik dua bagian rapi daripada satu jawaban gagal di tengah. Sebutkan jalur yang dipakai dalam satu kalimat di Catatan.

1. **Rencana dulu, lalu Bagian 1.** Pada mode MATERI, jawaban pertama memuat *Daftar Bagian* (disusun dari `--toc`: Bagian 1 narasi, Bagian 2 lampiran kitab A sub-bab …, dst.) dan langsung Bagian 1.
2. **Ukuran bagian** mengikuti hasil deteksi di atas (40k / 25k / 12k / 8k karakter). Pengguna boleh meminta "bagian panjang" atau "bagian pendek".
3. **Baca-tulis mengalir**: baca satu sub-bab (`--subbab`), tulis, baru baca berikutnya. Jangan menumpuk semua bacaan lalu menulis sekaligus — itu yang membuat keluaran meledak dan gagal.
4. **Penutup baku tiap bagian** (tulis persis):
   > — Bagian N dari M selesai. Ketik **lanjut** untuk Bagian N+1 (‹judul bagian berikutnya›). *Ini batas keluaran per jawaban, bukan akhir materi.*
5. **Baris status** di baris terakhir agar "lanjut" selalu bisa dijalankan walau percakapan sudah panjang:
   `[lanjut: event=<id> seg=<id> berikutnya=<judul/indeks sub-bab>; bagian=<N+1>/<M>]`
   Saat pengguna mengetik "lanjut", baca baris status terakhir, jalankan script dari titik itu, hasilkan Bagian berikutnya — tanpa mengulang yang sudah dikirim.
6. Jalur paralel (subagent) dipakai otomatis bila terdeteksi; protokol bagian tetap berlaku di semua jalur.

## Format Jawaban (SELALU sama, agar konsisten dan hemat token)

Pengguna skill ini adalah pembaca lanjut yang butuh teks sumber, tetapi tetap ingin orientasi singkat. Gunakan template ini persis, dalam urutan ini:

```
# <Judul: peristiwa / nama shahabat / tahun>

**Ringkasan (parafrase saya, bukan kutipan):** 3–5 baris — apa/kapan/siapa, kitab mana yang memuat & mana yang absen, satu-dua perbedaan mencolok antar sumber. Tanpa kutipan Arab di sini.

## <Kitab 1 — nama Arab (edisi)>
- Segmen: hal.web A–B (juz X hal Y) · <URL>
<paragraf verbatim, utuh, sesuai urutan>
— Sumber: juz X hal Y · URL

## <Kitab 2 …>   (satu bagian per kitab; sumber absen ditulis satu baris "tidak tersedia di sumber ini")

**Catatan:** TERPOTONG / tautan entitas medium-low / batas segmen / saran `--max-chars 0` bila ingin teks penuh.
```

Kendali token: ringkasan maksimal ±100 kata; kutipan verbatim adalah isi utama — jangan digandakan dalam tabel. Pilih paragraf yang menjawab pertanyaan (mis. untuk "keutamaan" ambil bagian fadha'il, bukan seluruh entri); bila sumber >3 atau entri panjang, jalankan script dengan `--max-chars 2500` per sumber lalu sebutkan jumlah paragraf total dan tawarkan `--max-chars 0`. Jangan menambahkan tabel perbandingan, glosarium, atau analisis panjang kecuali diminta.

## Aturan Mutlak Anti-Halusinasi

1. **Kutip hanya output script, verbatim** — teks Arab tidak diubah satu karakter pun (termasuk tasykil, catatan kaki muhaqqiq `[١]`, sanad). Kutip paragraf UTUH; jangan menyingkat di tengah kalimat dengan `…`/`[...]` — kalau perlu ringkas, pilih paragraf yang lebih sedikit, bukan memotong paragraf. Tabel perbandingan/ringkasan boleh, tetapi isinya adalah parafrase Anda (tandai demikian); kutipan verbatim taruh di blok per kitab.
2. **Sitasi wajib tiap kutipan**: kitab + edisi, juz/halaman cetak, URL shamela — semuanya ada di output.
3. **Sumber absen dikatakan absen.** Baris "tidak tersedia di sumber ini" DILARANG diisi dari sumber lain atau ingatan.
4. **Parafrase/terjemahan AI ditandai** ("Parafrase saya: …"), terpisah dari blok verbatim.
5. **Label batas segmen dijelaskan**: segmen dibentuk dari heading bab/entri (rule-based + LLM), halaman utuh disimpan dengan offset paragraf. Bila output menandai `TERPOTONG` (edisi elektronik Ibnu Hisyam ت طه berhenti di juz 2) atau `tautan entitas: medium/low`, sampaikan ke user.
6. **Kamus shahabat ≠ narasi peristiwa**: Ishabah/Usud/Isti'ab hanya di sumbu shahabat; peristiwa hanya dari Ibnu Hisyam, Ibnu Ishaq, Thabaqat (bab maghazi), Thabari. Jangan memaksa satu sumbu menjawab sumbu lain — pakai `search` untuk menemukan nama dalam narasi.

## Sumber

| source | Kitab | Peran | Catatan |
|---|---|---|---|
| `hisyam_saqqa` | سيرة ابن هشام ت السقا ورفاقه | sirah primer | lengkap 2 juz |
| `hisyam_thaha` | سيرة ابن هشام ت طه عبد الرؤوف سعد | edisi pembanding | versi elektronik hanya juz 1–2 dari 4 (TERPOTONG setelah Badr) |
| `ibn_ishaq` | سيرة ابن إسحاق = السير والمغازي | lapisan tertua (fragmen) | 287 hal. |
| `tabaqat` | الطبقات الكبرى ط العلمية (ابن سعد) | sirah (bab maghazi) + biografi | entri bernomor; memuat juga tabi'in |
| `tabaqat_tabiin` | الطبقات الكبرى — متمم التابعين | generasi tabi'in | bukan shahabat |
| `tarikh_tabari` | تاريخ الطبري | tulang punggung tahun (سنة N) | seluruh 11 juz; sub-heading peristiwa |
| `ishabah` | الإصابة في تمييز الصحابة (ابن حجر) | KUNCI KANONIK shahabat | 9.725 entri bernomor |
| `usud_ilmiyah` | أسد الغابة ط العلمية | kamus shahabat, edisi 1 | |
| `usud_rifai` | أسد الغابة ت الرفاعي | kamus shahabat, edisi 2 | |
| `istiab` | الاستيعاب ت البجاوي (ابن عبد البر) | kamus shahabat | 3.635 entri |

## Provenance

- Scrape 26 Agustus 2026 dari shamela.ws (0 gagal); parse + grouping 27 Agustus 2026.
- Registry peristiwa: draft 175 entri (dari TOC Ibnu Hisyam + heading Thabari, disusun GLM, dasar disetujui owner; koreksi menyusul).
- Tautan entitas kamus→Ishabah: heuristik nasab + LLM; status/confidence tersimpan per entri — sampaikan bila bukan `high`.
- DB: `sirah_full.db` — tabel `pages` (per paragraf verbatim), `events`, `event_segments`, `event_absent`, `year_segments`, `persons`, `person_entries`, FTS.
