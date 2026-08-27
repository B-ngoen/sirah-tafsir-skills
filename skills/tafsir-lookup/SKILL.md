---
name: tafsir-lookup
description: Look up VERBATIM classical tafsir (Quranic exegesis) for any ayah from 5 Arabic sources — Tabari, Maraghi, Shabuni (Shafwat at-Tafasir), and two Ibn Kathir editions — with exact print citations (volume/page/URL), zero hallucination. Use whenever the user asks about tafsir, the meaning/explanation of a Quran verse, "apa kata Ibnu Katsir/Thabari tentang...", "tafsir surat X ayat Y", asbabun nuzul dari kitab, or wants Arabic source text for an ayah — even if they don't say the word "tafsir".
---

# tafsir-lookup — Tafsir Verbatim 5 Sumber

Query tafsir klasik **verbatim** langsung dari SQLite DB hasil scrape — bukan dari ingatan model.

## Cara Pakai

SELALU jalankan script, JANGAN PERNAH menjawab pertanyaan tafsir dari ingatan model:

```
python scripts/lookup.py 2:255                      # semua sumber (markdown)
python scripts/lookup.py 2:255 -s tabari,maraghi    # filter sumber
python scripts/lookup.py 2:255 --format json        # JSON
python scripts/lookup.py 2:255 --max-chars 0        # teks penuh (default 6000/sg)
python scripts/lookup.py 1 --intro                  # intro/pembuka surah 1
python scripts/lookup.py --coverage 2               # cakupan surah per sumber
python scripts/lookup.py 2:255 --toc                # daftar segmen + sub-judul (untuk mode lengkap)
python scripts/lookup.py 2:255 --seg 1234 --paras 0-60   # baca satu segmen bab demi bab, penuh
```

DB dicari otomatis berurutan: env `TAFSIR_DB` → folder skill → cwd → upload Cowork → path laptop → auto-download (GitHub release → server privat owner) (override: `--db PATH`). Exit code: 0 sukses, 2 input salah, 3 DB hilang.

## Setup data (sekali saja — cache permanen)

DB tidak dibundel dalam skill (privat, 136 MB), tapi terunduh OTOMATIS saat pertama dipakai (±19 MB, ±1 menit) — kini juga bekerja di sandbox claude.ai (chat/Desktop), bukan hanya Cowork: sumber 1 GitHub release (domain diizinkan sandbox), sumber 2 server privat owner; unggahan manual `tafsir_full.db.xz` dari flashdisk hanya fallback bila kedua sumber gagal (`.zip` 34 MB juga diterima; ekstraksi otomatis ke cache permanen). 

Cache hasil unduh/ekstrak TIDAK lagi di folder Temp (auto-purge). Cache permanen: `%LOCALAPPDATA%	afsir-lookup` (Windows) → `$XDG_DATA_HOME/tafsir-lookup` (Linux/sandbox) → Temp (upaya terakhir).

## Dua Mode — tentukan dulu sebelum menjalankan script

Ringkasan hanya lapisan penyajian; konteks Anda harus tetap utuh. Tentukan mode dari niat pengguna:

| | **Mode RUJUKAN** (default) | **Mode MATERI / LENGKAP** |
|---|---|---|
| Pemicu | "apa tafsir ayat ini", verifikasi satu pendapat, asbabun nuzul singkat | "materi/kajian/ceramah", "uraikan tafsir lengkap", "bandingkan semua mufassir secara rinci", "bahan mengajar", "narasi" |
| Script | default `--max-chars 6000` (atau 2500 bila >3 sumber) | `--toc` dulu, lalu baca segmen **penuh** bagian demi bagian: `--seg <id> --paras A-B` (±60 paragraf per langkah) sampai habis — jangan mengelaborasi dari potongan |
| Keluaran | Ringkasan ≤100 kata (parafrase, ditandai) → verbatim terpilih per sumber → Catatan | Ringkasan → **uraian sistematis** (parafrase Anda, boleh panjang, tiap paragraf bersitasi `[kitab, juz/hal]`) → **lampiran verbatim** per sumber, dipecah per sub-bagian (judul dari `--toc`); teks sangat panjang → tawarkan lanjutan per bagian |

Bila ragu, tanya satu kalimat: "Rujukan singkat atau materi lengkap?" — jangan menebak ke arah ringkas.

Disiplin Mode MATERI:
- `--toc` menampilkan semua segmen per sumber (satu ayat bisa >1 segmen: blok ayat, intro surah). Jangan mengabaikan segmen berdasarkan dugaan label — intip 10 paragraf pertamanya (`--seg X --paras 0-9`) lalu putuskan.
- Lampiran verbatim disusun **per sub-bagian** memakai judul dari `--toc` (`### <judul> — juz X hal Y`), bukan potongan per 60 paragraf dengan header berulang. Paging hanya cara membaca, bukan struktur jawaban.
- Batasi satu jawaban ±40–60 ribu karakter: kirim Bagian 1 (uraian lengkap + lampiran sub-bagian terpenting), tutup dengan daftar sub-bagian yang belum dilampirkan dan tawaran eksplisit "ketik *lanjut* untuk Bagian 2" — pengguna yang memutuskan, bukan Anda yang memangkas diam-diam.

## Protokol Bagian — untuk semua model, termasuk paket gratis tanpa subagent

Banyak pengguna memakai model dengan batas keluaran kecil dan tanpa subagent, tetapi meminta materi panjang. Karena itu:

1. **Rencana dulu, lalu Bagian 1.** Pada mode MATERI, jawaban pertama memuat *Daftar Bagian* (dari `--toc`: Bagian 1 uraian, Bagian 2 lampiran kitab A bagian …, dst.) dan langsung Bagian 1.
2. **Ukuran bagian aman**: ≤12.000 karakter per jawaban (≈4–5 ribu token). Bila batas keluaran Anda kecil (model gratis), pakai ≤8.000. Pengguna boleh meminta "bagian panjang".
3. **Baca-tulis mengalir**: baca satu bagian (`--seg --paras`), tulis, baru baca berikutnya. Jangan menumpuk semua bacaan lalu menulis sekaligus.
4. **Penutup baku tiap bagian** (tulis persis):
   > — Bagian N dari M selesai. Ketik **lanjut** untuk Bagian N+1 (‹judul bagian berikutnya›). *Ini batas keluaran per jawaban, bukan akhir materi.*
5. **Baris status** di baris terakhir: `[lanjut: ref=<S:A> seg=<id> berikutnya=<paragraf/sub-judul>; bagian=<N+1>/<M>]` — saat pengguna mengetik "lanjut", baca baris ini, jalankan script dari titik itu, tanpa mengulang yang sudah dikirim.
6. Subagent/paralel hanya bila tersedia; protokol ini tidak bergantung padanya.

## Format Jawaban (konsisten, hemat token)

`# <QS S:A — judul>` → **Ringkasan (parafrase saya, bukan kutipan)** 3–5 baris → `## <kitab>` per sumber: baris segmen/label, paragraf verbatim utuh (jangan disingkat dengan `…`/`[...]` di tengah paragraf; kurangi jumlah paragraf, bukan memotongnya), `— Sumber: juz X hal Y · URL`; sumber absen satu baris "tidak tersedia di sumber ini" → **Catatan** (label rentang, potongan, saran `--max-chars 0`). Tanpa tabel perbandingan/glosarium kecuali diminta.

## Aturan Mutlak Anti-Halusinasi

1. **Kutip hanya output script, verbatim.** Teks Arab/Inggris tidak boleh diubah satu karakter pun — termasuk tanpa "perbaikan" ejaan atau tanda baca.
2. **Sitasi wajib tiap kutipan**: nama kitab + edisi, juz/hal cetak + URL shamela. Semua sudah ada di output script.
3. **Sumber absen dikatakan absen.** Baris "tidak tersedia di sumber ini (keterbatasan edisi/situs)" DILARANG diisi dari sumber lain atau dari ingatan model.
4. **Terjemahan/ringkasan buatan AI wajib ditandai** sebagai parafrase ("Parafrase saya: ..."), terpisah jelas dari blok verbatim.
5. **Label rentang dijelaskan ke user**: bila output menyatakan "Segmen ini mencakup ayat 249-280", sampaikan bahwa kutipan itu tafsir blok ayat 249-280 yang memuat ayat yang diminta — bukan tafsir khusus ayat itu saja.

## Sumber & Cakupan

| source | Kitab | Cakupan |
|---|---|---|
| `tabari` | Tafsir ath-Thabari (Jami' al-Bayan), ed. Dar at-Tarbiyah wat-Turats | 100% |
| `maraghi` | Tafsir al-Maraghi | 100% |
| `shabuni` | Shafwat at-Tafasir (ash-Shabuni) | 99,49% — edisi terpotong, surah 114 absen |
| `ibnkathir_awlad` | Tafsir Ibnu Katsir, ed. Awlad asy-Syaikh | 99,98% — hanya 2:1 absen |
| `ibnkathir_jawzi` | Tafsir Ibnu Katsir, ed. Dar Ibnul Jauzi | 99,81% — edisi terpotong akhir mushaf; 113-114 hanya pembuka gabungan |

Lima sumber Arab dari shamela.ws. Cakupan gabungan: 6236/6236 ayat (100%).

## Provenance

- Scrape: **18 Agustus 2026** dari shamela.ws (teks verbatim per halaman cetak + paragraf). Edisi publik ini TIDAK memuat Dorar (EN) karena hak cipta.
- DB publik: `tafsir_full.db` (GitHub Release `tafsir-v1`, aset `tafsir_full.db.xz` ±18 MB) — 10.326 segmen, 37.574 pemetaan ayah→segmen (5 kitab).
- Struktur: `pages` (teks per halaman), `segments` (blok tafsir per label ayat/intro), `ayah_map` (surah:ayah → seg_id).

## Catatan Output

- Satu ayat bisa memetakan ke >1 segmen (mis. shabuni jendela pasase) — semua segmen ditampilkan; bandingkan label & sitasinya.
- Default teks dipotong 6000 karakter per sumber di batas paragraf; pesan "…dipotong, N paragraf total, pakai --max-chars 0" menandainya. Untuk kutip penuh, rerun dengan `--max-chars 0`.
- Segmen `intro` = pembuka surah (muqaddimah, fadl surah), bukan tafsir ayat — cocok untuk konteks asbabun nuzul umum.
