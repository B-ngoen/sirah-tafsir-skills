---
name: hadith-lookup
description: Look up VERBATIM Arabic hadith (with muhaqqiq footnotes, stored grade and exact print citation) from 12 classical books — Bukhari, Muslim, Abu Dawud, Nasai, Tirmidhi, Ibn Majah, Muwatta Malik, Musnad Ahmad, Darimi, Bulughul Maram, Riyadhus Shalihin (+al-Albani). Use for "hadits", "riwayat Bukhari/Muslim", "HR. Abu Dawud no. X", derajat/takhrij, "apakah hadits ini shahih", Arabic hadith text, kitab/bab search — zero hallucination.
---

# hadith-lookup — Hadits Verbatim 12 Kitab

Query hadits **verbatim** dari SQLite DB hasil scrape (shamela.ws) — bukan dari ingatan model.

## Sumber Tunggal — tidak ada sumber lain

Satu-satunya sumber jawaban adalah **keluaran `scripts/lookup.py` pada percakapan ini** (berlaku juga untuk model dengan mode *thinking*). Apa pun yang "diingat" dari kitab lain, situs hadits (sunnah.com, dorar.net, dsb.), terjemahan, atau Wikipedia **tidak boleh** masuk ke jawaban — bukan sebagai kutipan, sitasi, maupun "tambahan konteks". Satu hadits atau derajat yang keliru dari ingatan merusak kepercayaan pada seluruh jawaban.

- Nama kitab yang boleh muncul sebagai sumber hanya kitab di tabel **Sumber** di bawah. Nomor hadits/halaman/juz hanya yang tercetak di keluaran script.
- **Dilarang** memakai alat web/browse/search/fetch dalam skill ini, termasuk saat DB gagal (exit 3). Exit 3 → sampaikan pesan error script + langkah perbaikan (unggah `hadith_full.db.xz`, atau set `HADITH_DB`), lalu **berhenti**.
- Bila hadits/nomor/kata kunci tidak ada di keluaran: katakan **"Tidak ada di basis data ini"** lalu berhenti. Hanya bila pengguna *eksplisit* meminta pengetahuan umum, tulis di bagian terpisah **"Di luar basis data (dari ingatan model, tidak terverifikasi)"** — tanpa kutipan Arab, tanpa nomor, tanpa derajat.
- **Jawaban tanpa blok teks Arab yang disalin dari keluaran script, lengkap dengan baris `— Sumber: … juz X hal Y · URL`, bukan jawaban skill ini.** Script tidak bisa dijalankan → katakan itu dan berhenti.
- Pemeriksaan diam-diam sebelum kirim: (1) tiap baris Arab ada persis di keluaran script; (2) tiap sitasi punya kitab+edisi+juz/hal+URL dari keluaran; (3) tidak ada nama kitab/situs/perawi di luar keluaran; (4) parafrase ditandai. Ada yang gagal → hapus bagiannya.

## Cara Pakai

SELALU jalankan script; JANGAN menjawab dari ingatan.

```
python scripts/lookup.py bukhari:1                       # satu hadits (nomor cetak edisi)
python scripts/lookup.py muslim:8 "abu dawud:4"          # banyak rujukan; alias Latin/Indonesia/Arab
python scripts/lookup.py bukhari:1,2,5-7                 # daftar / rentang
python scripts/lookup.py --search "انما الاعمال بالنيات"  # FTS semua kitab (harakat/ejaan alif-ya-ta marbuta diabaikan)
python scripts/lookup.py --search "..." -b bukhari,muslim --limit 10
python scripts/lookup.py --bab bukhari "الجنب يتوضأ"      # cari judul bab/kitab
python scripts/lookup.py --list-books                    # kitab & cakupan di DB
  opsi: --format json | --max-chars N (default 8000, 0 = penuh) | --offset K | --no-notes | --db PATH
```

Memetakan permintaan pengguna: "HR. Abu Dawud no. 4" → `"abu dawud:4"`; "Bulughul Maram 299" → `"bulughul maram:299"`; "Riyadhus Shalihin hadits 1" → `riyadh:1` (tampil juga entri al-Albani bila ada xref). Nomor = nomor cetak edisi di DB (lihat `num_label`), **bukan** penomoran kitab/edisi lain — bila pengguna memakai penomoran lain (mis. Fathul Bari, Syamilah, Muslim Abdul-Baqi vs sub-nomor) dan hasil tidak cocok dengan teks yang dimaksud, katakan ada kemungkinan beda penomoran lalu cari dengan `--search`.

**Muwatta tidak punya nomor global** di edisi ini: rujuk `muwatta:K/N` (K = nomor kitab, N = nomor hadits dalam kitab; juga `malik:K/N`). `muwatta:N` polos TIDAK memilih satu hadits — script mendaftar semua kitab yang memuat nomor itu ("AMBIGU"); tampilkan daftar ke pengguna dan minta ia menentukan kitabnya, jangan menebak.

**Satu nomor bisa banyak baris** (varian/riwayat tambahan: sub-nomor `م`, `(أ)`, `/١`, "مكرر"; Muslim ±6,5 ribu baris varian): semua ditampilkan berurutan, dipaginasi dengan `--max-chars`/`--offset`. Baris rentang ("N - M", mis. Bulugh `١٨٩ - و ١٩٠`) cocok untuk nomor N maupun M. Bila muncul baris "Nomor tercetak di edisi: …; nomor baku … ditetapkan dari urutan (alasan: …)", sampaikan apa adanya — itu penetapan nomor oleh pembangun DB atas salah cetak, bukan bagian edisi. `riyadh:N` menampilkan entri al-Albani yang terhubung (xref berbasis kemiripan teks, bukan kesamaan nomor): sebut nomor al-Albani-nya sendiri dan metode xref yang tercetak.

Pengguna hanya punya teks Arab/terjemah? Jalankan `--search` dengan 2–5 kata Arab kunci (tanpa harakat) → baca hasil → ambil teks penuh dengan `kitab:nomor`. Pencarian memakai frasa persis lalu semua-kata; tambahkan `--any` bila perlu. Hasil kosong ≠ hadits tidak ada di kitab lain — nyatakan hanya "tidak ditemukan di DB ini". Redaksi sering berbeda antar kitab (mis. "بالنيات" di Bukhari 1 vs "بالنية" di Muslim 1907/Nasai 75/Ahmad 168): bila mencari semua jalur riwayat, ulangi `--search` dengan varian kata kunci/kata yang lebih sedikit sebelum menyimpulkan.

DB dicari otomatis: env `HADITH_DB` → `assets/` skill → cwd → upload Cowork → folder lokal pemilik → unduh otomatis (`hadith_full.db.xz`, cache permanen) → exit 3. Exit: 0 sukses (termasuk "TIDAK ADA di DB", dinyatakan di keluaran), 2 input salah, 3 DB hilang.

## Format Jawaban

`# <kitab edisi — nomor>` → **Ringkasan (parafrase saya, bukan kutipan)** 1–3 baris → untuk tiap hadits: blok teks Arab **verbatim utuh** (jangan dipotong/`…`/diperbaiki harakatnya) → bila ada, **catatan muhaqqiq verbatim** diberi label "Catatan muhaqqiq (bukan bagian teks hadits)" → baris derajat → `— Sumber: kitab، edisi · juz X hal Y · URL`. Tanpa tabel/glosarium kecuali diminta. Penanda halaman inline seperti `⦗٦٦⦘` dan nomor catatan `(١)` di teks adalah bagian verbatim — biarkan.

Bila hasil >1 hadits (rentang/pencarian): tampilkan hanya yang relevan, sebut berapa yang dilewati. Keluaran terpotong (`--max-chars`) → tulis baris penutup baku:
> — Ditampilkan N dari M hadits. Ketik **lanjut** untuk sisanya. *Ini batas keluaran per jawaban, bukan akhir.*

Saat pengguna mengetik "lanjut": jalankan ulang perintah yang sama dengan `--offset K` (K tercetak di keluaran script).

## Mode

| | **RUJUKAN** (default) | **MATERI / LENGKAP** |
|---|---|---|
| Pemicu | "teks hadits X", "siapa perawinya", verifikasi satu riwayat | "kumpulkan hadits tentang…", bahan kajian/khutbah, bandingkan banyak kitab |
| Cara | `kitab:nomor` / `--search` dengan default | `--search` → daftar kandidat → baca penuh yang relevan (`--max-chars 0`, per beberapa hadits) |
| Keluaran | ringkasan ≤60 kata (ditandai) + verbatim + sitasi | uraian sistematis (parafrase ditandai, tiap paragraf bersitasi `[kitab no., juz/hal]`) + lampiran verbatim; >±25 ribu karakter → bagi per bagian dengan "ketik **lanjut**" |

Ragu → tanya satu kalimat: "Rujukan singkat atau materi lengkap?"

## Derajat & "apakah hadits ini shahih?"

Skill ini **tidak menilai hadits**. Jawab hanya dari yang tercetak:
1. Jalankan script. Baca baris **Derajat** dan **Catatan muhaqqiq** verbatim.
2. Bila ada derajat tersimpan → kutip persis beserta **otoritas yang tertulis** (mis. "ضعيف — الألباني", "إسناده صحيح — محقق Musnad Ahmad"). Jangan menambah/mengubah/memperkuat; jangan menyamakan derajat sanad ("إسناده صحيح") dengan derajat matan.
3. Bila script menyatakan "edisi ini tidak mencantumkan derajat" → katakan persis itu. **Jangan** mengisi dari ingatan ("hadits ini shahih menurut…", nama Albani/Ibnu Hajar yang tak ada di keluaran). Bila ada catatan muhaqqiq tanpa kata derajat, katakan "catatan tidak menyebut derajat".
4. Bukhari/Muslim: script menambah satu baris "Keterangan umum (BUKAN kutipan dari edisi ini)". Sampaikan sebagai keterangan umum yang dilabeli demikian, bukan sebagai kutipan kitab.
5. Otoritas tertulis di baris Derajat: `الألباني` (Abu Dawud/Tirmidzi/Ibnu Majah, dari "[حكم الألباني]"), `الترمذي` (hukum at-Tirmidzi sendiri, bagian teks kitabnya), `الأرنؤوط` (Nasai/Ahmad), `الزهيري` (Bulugh), `حسين سليم أسد` (Darimi). Sebut otoritas persis seperti tercetak; satu hadits Tirmidzi bisa bergelar at-Tirmidzi sementara Albani berbeda — jangan digabung.
6. Hadits tidak ditemukan di DB ≠ hadits lemah/palsu. Katakan hanya "tidak ada di DB ini".

## Aturan Mutlak Anti-Halusinasi

1. **Kutip hanya keluaran script, verbatim** — satu huruf/harakat pun tak diubah (termasuk "salah ketik" edisi).
2. **Sitasi wajib tiap kutipan**: kitab + edisi, juz/hal cetak + URL shamela, nomor sebagaimana tercetak (`num_label`).
3. **Yang tidak ada dikatakan tidak ada** ("TIDAK ADA di DB", kitab belum terpasang, derajat tidak dicantumkan) — dilarang diisi dari sumber lain atau ingatan.
4. **Terjemahan/ringkasan/penjelasan buatan AI wajib ditandai** ("Parafrase saya: …") dan dipisah dari blok verbatim. Terjemahan Indonesia atas teks Arab = parafrase; jangan menyebutnya terjemahan resmi.
5. **Catatan muhaqqiq ≠ hadits.** Selalu bedakan teks hadits (sanad+matan) dari catatan kaki/takhrij editor; jangan memasukkan isi catatan ke dalam teks hadits atau sebaliknya.
6. Catatan yang dipotong (`…catatan dipotong`) diberitahukan ke pengguna; tawarkan `--max-chars 0`.

## Sumber & Cakupan

| key | Kitab | Edisi / keterangan |
|---|---|---|
| `bukhari` | Shahih al-Bukhari | ط السلطانية، ترقيم عبد الباقي |
| `muslim` | Shahih Muslim | ت عبد الباقي (nomor + sub-nomor; lihat `num_label`) |
| `abudawud` | Sunan Abi Dawud | ت محيي الدين عبد الحميد |
| `nasai` | Sunan an-Nasa'i (al-Mujtaba) | ط الرسالة العالمية، ترقيم أبو غدة |
| `tirmidhi` | Sunan at-Tirmidzi | ت أحمد شاكر وآخرون (matan, bukan syarah) |
| `ibnmajah` | Sunan Ibn Majah | ت عبد الباقي |
| `muwatta` | Muwatta' Malik (riwayat Yahya) | ت عبد الباقي |
| `ahmad` | Musnad Ahmad | ط الرسالة، ت الأرنؤوط وآخرون |
| `darimi` | Musnad/Sunan ad-Darimi | ت حسين سليم أسد |
| `bulugh` | Bulughul Maram | ت سمير الزهيري، دار الفلق ط7 (derajat di catatan muhaqqiq) |
| `riyadh_arnaut` | Riyadhus Shalihin | ت الأرنؤوط، الرسالة ط3 (nomor ganda "urutan-dalam-bab/nomor-global") |
| `riyadh_albani` | Tahqiq Riyadhus Shalihin (al-Albani) | selektif: hanya hadits yang dikomentari al-Albani; tampil via xref dari `riyadh` |

Cakupan nyata per kitab: `python scripts/lookup.py --list-books` (rentang nomor di DB). Semua teks = **matan asli**, bukan syarah. Edisi menentukan penomoran — nomor di sini adalah nomor edisi tersebut.

## Provenance

- Scrape dari shamela.ws (teks verbatim per halaman cetak + paragraf); DB `hadith_full.db` (skema: `pages`, `hadith`, `hadith_fts`, `books`, `xref`). Teks tidak pernah disunting — normalisasi hanya di indeks pencarian.
- Derajat hanya yang tertulis eksplisit pada teks/catatan edisi (kolom `grade`, otoritas di `grade_by`); selain itu kosong.
