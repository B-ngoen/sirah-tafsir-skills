---
name: tafsir-lookup
description: Look up VERBATIM classical tafsir (Quranic exegesis) for any ayah — Tabari, Maraghi, Shabuni, two Ibn Kathir editions — plus Asbab an-Nuzul (as-Suyuti, Lubab an-Nuqul) — with exact print citations, zero hallucination. Use whenever the user asks about tafsir, the meaning of a Quran verse, "apa kata Ibnu Katsir/Thabari tentang...", "tafsir surat X ayat Y", "asbabun nuzul / sebab turun ayat", or Arabic source text for an ayah — even without the word "tafsir".
---

# tafsir-lookup — Tafsir Verbatim 5 Sumber + Asbabun Nuzul

Query tafsir klasik **verbatim** langsung dari SQLite DB hasil scrape — bukan dari ingatan model.

## Sumber Tunggal — tidak ada sumber lain

Satu-satunya sumber jawaban adalah **keluaran `scripts/lookup.py` pada percakapan ini**. Ini berlaku juga untuk model dengan mode *thinking/reasoning*: apa pun yang Anda "ingat" dari kitab lain, hadis, artikel, situs, atau terjemahan **tidak boleh** masuk ke jawaban — bukan sebagai kutipan, bukan sebagai sitasi, bukan sebagai "tambahan untuk konteks". Alasannya: pengguna memakai skill ini justru karena ingatan model sering keliru dan tidak bisa diverifikasi; satu sitasi luar yang salah merusak kepercayaan pada seluruh jawaban.

- Nama kitab yang boleh muncul sebagai sumber hanya 6 kitab di bagian **Sumber** (Tafsir ath-Thabari, Ibnu Katsir 2 edisi, al-Maraghi, Shafwat at-Tafasir, Lubab an-Nuqul as-Suyuthi). Nama lain (Shahih Bukhari, Muslim, ar-Rahiq al-Makhtum, Zadul Ma'ad, tafsir lain, Wikipedia, dorar.net, dsb.) **dilarang** muncul sebagai sumber.
- Tidak ada pencarian web, tidak ada pembacaan berkas lain, tidak ada "menurut riwayat yang masyhur" tanpa kutipan dari script.
- Bila pengguna bertanya sesuatu yang tidak ada di basis data, jawab: *"Tidak ada dalam 6 kitab basis data ini"* — lalu berhenti. Jangan mengisi kekosongan dari ingatan. Hanya bila pengguna **secara eksplisit** meminta pendapat/pengetahuan umum, boleh menjawab di bagian terpisah berjudul **"Di luar basis data (dari ingatan model, tidak terverifikasi)"** — tanpa kutipan Arab dan tanpa sitasi juz/halaman.
- **Jawaban tanpa blok kutipan Arab yang disalin dari keluaran script — lengkap dengan baris `— Sumber: juz X hal Y · URL` — bukan jawaban skill ini.** Jangan pernah menulis uraian sirah/tafsir "bersitasi" dari ingatan (contoh kebocoran nyata: *"Tarikh ath-Thabari, jilid 14, hlm. 143"* dan *"Shahih al-Bukhari 7207"* — nomor jilid/hadis itu tidak ada di keluaran script; basis data hanya memakai juz/hal + URL shamela). Bila script belum dijalankan, jalankan dulu; bila tidak bisa dijalankan (tidak ada akses terminal/Python), katakan itu dan berhenti — jangan menjawab dari ingatan sebagai pengganti.
- Tanda kebocoran yang harus Anda hapus sebelum mengirim: sitasi tanpa URL shamela; "jilid/hlm." yang tidak tercetak di keluaran; nomor hadis; "menurut riwayat yang masyhur"; "para sejarawan/historiografi Sunni–Syiah"; nama kitab/situs di luar daftar Sumber; nama ulama atau periwayat yang tidak muncul dalam teks yang dikutip.
- **Dilarang memakai alat web/browse/search/fetch dalam skill ini**, apa pun alasannya — termasuk saat DB gagal ditemukan atau diunduh (exit 3). Exit 3 → sampaikan pesan error script + langkah perbaikan (pasang ulang: `python install.py`, atau set `SIRAH_DB`/`TAFSIR_DB`), lalu **berhenti**. Kebocoran nyata: saat DB tidak ada, model mengutip sunnah.com, masaha.org, ablibrary.net, Ansab al-Asyraf — semuanya pelanggaran.
- **Pemeriksaan sebelum mengirim** (lakukan diam-diam): (1) setiap baris Arab yang dikutip ada persis di keluaran script; (2) setiap sitasi menunjuk kitab dari daftar Sumber dengan juz/hal yang tercetak di keluaran; (3) tidak ada nama kitab/situs lain di mana pun dalam jawaban; (4) parafrase Anda ditandai. Ada yang gagal → hapus bagian itu, jangan diperhalus.

## Cara Pakai

SELALU jalankan script, JANGAN PERNAH menjawab pertanyaan tafsir dari ingatan model:

```
python scripts/lookup.py 2:255                      # semua sumber (markdown)
python scripts/lookup.py 2:255 -s tabari,maraghi    # filter sumber
python scripts/lookup.py 33:37 -s asbab              # asbabun nuzul saja (alias: asbab = asbab_suyuti)
python scripts/lookup.py 108 --intro -s asbab       # riwayat tingkat-surah (tak terikat satu ayat)
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

**Deteksi kemampuan (lakukan dulu, tanpa bertanya ke pengguna):**
- **Punya tool subagent?** (Claude Code: tool `Agent`/`Task` ada di daftar tool; Codex/agen lain: kemampuan spawn sub-task.) → **Jalur MAKSIMAL**: untuk mode MATERI multi-kitab, luncurkan satu *pembaca* per kitab secara paralel (tiap pembaca: `--toc` → `--subbab` terpilih → berkas ekstrak ≤45.000 karakter, verbatim + sitasi + 1–2 kalimat isi), lalu Anda menyusun narasi dari berkas ekstrak. Bagian boleh sampai ±40.000 karakter.
- **Tanpa subagent tetapi keluaran besar** (Claude Code/Codex tanpa Agent tool): jalur tunggal, Bagian ≤25.000 karakter, baca-tulis mengalir.
- **Sandbox chat / model gratis / batas keluaran kecil** (claude.ai web, ChatGPT, atau Anda tahu batas Anda kecil): Bagian ≤12.000 (≤8.000 bila sangat kecil).
Kalau ragu, ambil jalur di bawahnya — lebih baik dua bagian rapi daripada satu jawaban gagal di tengah. Sebutkan jalur yang dipakai dalam satu kalimat di Catatan.

1. **Rencana dulu, lalu Bagian 1.** Pada mode MATERI, jawaban pertama memuat *Daftar Bagian* (dari `--toc`: Bagian 1 uraian, Bagian 2 lampiran kitab A bagian …, dst.) dan langsung Bagian 1.
2. **Ukuran bagian** mengikuti hasil deteksi di atas (40k / 25k / 12k / 8k karakter). Pengguna boleh meminta "bagian panjang" atau "bagian pendek".
3. **Baca-tulis mengalir**: baca satu bagian (`--seg --paras`), tulis, baru baca berikutnya. Jangan menumpuk semua bacaan lalu menulis sekaligus.
4. **Penutup baku tiap bagian** (tulis persis):
   > — Bagian N dari M selesai. Ketik **lanjut** untuk Bagian N+1 (‹judul bagian berikutnya›). *Ini batas keluaran per jawaban, bukan akhir materi.*
5. **Baris status** di baris terakhir: `[lanjut: ref=<S:A> seg=<id> berikutnya=<paragraf/sub-judul>; bagian=<N+1>/<M>]` — saat pengguna mengetik "lanjut", baca baris ini, jalankan script dari titik itu, tanpa mengulang yang sudah dikirim.
6. Jalur paralel (subagent) dipakai otomatis bila terdeteksi; protokol bagian tetap berlaku di semua jalur.

## Format Jawaban (konsisten, hemat token)

`# <QS S:A — judul>` → **Ringkasan (parafrase saya, bukan kutipan)** 3–5 baris → `## <kitab>` per sumber: baris segmen/label, paragraf verbatim utuh (jangan disingkat dengan `…`/`[...]` di tengah paragraf; kurangi jumlah paragraf, bukan memotongnya), `— Sumber: juz X hal Y · URL`; sumber absen satu baris "tidak tersedia di sumber ini" → **Catatan** (label rentang, potongan, saran `--max-chars 0`). Tanpa tabel perbandingan/glosarium kecuali diminta.

**Baris Cakupan (wajib di setiap jawaban, tepat sebelum Catatan):** sebutkan KEENAM kitab dengan status masing-masing — `dikutip` / `ada, belum dikutip (N paragraf; minta "lengkap" atau sebut kitabnya)` / `tidak ada di sumber ini`. Khusus Lubab an-Nuqul, ayat tanpa entri BUKAN kegagalan: sebagian besar ayat memang tak punya asbabun nuzul — katakan persis *"tidak ada riwayat asbabun nuzul untuk ayat ini di Lubab an-Nuqul"* (jangan mengisinya dari ingatan). Alasan: keluaran script yang terpotong atau panjang membuat model diam-diam melewatkan kitab yang sebenarnya ada (kejadian nyata: An-Nasr — Maraghi dan dua Ibnu Katsir tidak dikutip tanpa keterangan sampai pengguna bertanya). Baris Cakupan membuat kelalaian itu terlihat sebelum dikirim. Pertanyaan pendek pun tetap wajib memuatnya (satu baris).

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
| `asbab_suyuti` | Lubab an-Nuqul fi Asbab an-Nuzul (as-Suyuthi), ed. Dar al-Kutub al-'Ilmiyyah | SELEKTIF — hanya ayat yang punya riwayat (±650 ayat berlabel pasti; QS 1 tak dimuat); satu jilid (sitasi `hal X`, tanpa juz) |

Enam sumber Arab dari shamela.ws. Cakupan lima kitab tafsir gabungan: 6236/6236 ayat (100%); Lubab an-Nuqul selektif (bukan tafsir ayat-demi-ayat).

## Provenance

- Scrape: **18 Agustus 2026** dari shamela.ws (teks verbatim per halaman cetak + paragraf). Edisi publik ini TIDAK memuat Dorar (EN) karena hak cipta.
- DB v4 (`tafsir_full_v4.db`; skill ini mensyaratkan DB v4): + sumber `asbab_suyuti` (shamela 2247, 218 hlm web) — baris 5 kitab lain tidak diubah.
- DB publik: `tafsir_full.db` (GitHub Release `tafsir-v1`, aset `tafsir_full.db.xz` ±18 MB) — 10.326 segmen, 37.574 pemetaan ayah→segmen (5 kitab).
- Struktur: `pages` (teks per halaman), `segments` (blok tafsir per label ayat/intro), `ayah_map` (surah:ayah → seg_id).

## Catatan Output

- Satu ayat bisa memetakan ke >1 segmen (mis. shabuni jendela pasase) — semua segmen ditampilkan; bandingkan label & sitasinya.
- Default teks dipotong 6000 karakter per sumber di batas paragraf; pesan "…dipotong, N paragraf total, pakai --max-chars 0" menandainya. Untuk kutip penuh, rerun dengan `--max-chars 0`.
- Segmen `intro` = pembuka surah (muqaddimah, fadl surah), bukan tafsir ayat — cocok untuk konteks asbabun nuzul umum.
- **Lubab an-Nuqul (`asbab_suyuti`) — cara membaca label:** `33:37` / `1-6` = entri dicocokkan ke ayat itu lewat kanonik (awalan ayat, atau frasa di dalam ayat yang unik, atau kutipan ayat di isi entri; rentang hanya bila tertulis eksplisit: "الآيتين", "إلى آخر السورة", "إلى قوله …" atau entri mengutip beberapa ayat berdekatan). Label `a,b` = beberapa ayat kandidat berawalan sama yang tak bisa dibedakan teks entri. Label `~a-b` (jarang/tidak ada) = posisi hanya DIINTERPOLASI di antara entri tetangga. Keduanya: sampaikan ke pengguna bahwa ini bukan pencocokan pasti dan baca isinya dulu. Riwayat lanjutan ("وأخرج ...") ditampilkan menyatu dengan entri sebelumnya, mengikuti gaya Suyuthi. Segmen `intro` asbab = riwayat tingkat-surah yang tak bisa dikaitkan ke satu ayat (`lookup.py S --intro -s asbab`); bila ayat tanpa entri tapi surahnya punya intro, script menyebutkannya. Nama perawi/kitab (Bukhari, Muslim, dst.) BOLEH dikutip hanya sebagai isi teks Suyuthi yang ditampilkan script, bukan sebagai sumber Anda.
- Edisi ini tidak bertashkil dan mempertahankan penanda editor (mis. `[٧٣]` nomor ayat, `(ك)`) — itu bagian teks sumber, jangan dibuang.
