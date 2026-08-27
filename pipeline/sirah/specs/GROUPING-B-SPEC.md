# Tugas: tulis `group_persons.py` — segmentasi deterministik entri biografi (Sumbu B: shahabat)

Semua path relatif terhadap CWD (`pipeline/`). Python 3.12+, hanya stdlib. Semua `open()` wajib `encoding="utf-8"`.
Jangan mengubah file lain. Setelah menulis script, JALANKAN `python group_persons.py` dan pastikan lolos, lalu cetak ringkasan.

## Input
1. `data/pages_full.jsonl` — satu record per halaman web: `{"source","book_id","web_page","printed_juz","printed_page","url","paras":[...]}`.
   `paras` = daftar paragraf verbatim berurutan (teks bertasykil di sebagian kitab).
2. `data/toc/toc_{book_id}.json` — daftar entri TOC: `{"i","page","title","depth","parent","end_excl","end_any"}`.
   `end_excl` = halaman entri berikutnya dengan depth ≤ entri (sudah benar; JANGAN hitung ulang), bisa null di entri terakhir.
3. `data/sahabat_index.draft.json` — dict per kamus: `{"ishabah":[...],"istiab":[...],"usud_1110":[...],"usud_30018":[...],"tabaqat":[...]}`;
   tiap item `{"num","name","page","end_excl","toc_i",...}`. `num` = nomor entri cetak (bisa null di usud); `toc_i` = indeks ke toc_{book_id}.json.
   Pemetaan kamus→source→book_id: ishabah→`ishabah`→9767; istiab→`istiab`→12288; usud_1110→`usud_ilmiyah`→1110; usud_30018→`usud_rifai`→30018; tabaqat→`tabaqat`→1686.
   PENTING: ambil `end_excl` dari `toc_{book_id}.json[toc_i]` (yang sudah diperbaiki), bukan dari sahabat_index (usang).

## Normalisasi (fungsi `norm`)
- Hapus tasykil: rentang U+0610–U+061A, U+064B–U+065F, U+0670, U+06D6–U+06ED, dan tatweel U+0640.
- Angka Arab-India ٠١٢٣٤٥٦٧٨٩ → 0-9.
- Samakan hamzah untuk pencocokan nama saja (bukan untuk output): أ إ آ → ا, ة → ه, ى → ي. Rapatkan spasi.

## Pola heading entri (setelah norm) — regex, awal paragraf
- `^\[?\s*\(?\s*(\d+)\s*[-\)\]]\s*(.+)$`  contoh: `[4835- عبد الله بن عثمان]`, `1633) …`, `(1633) …`, `[ (51) الأسود]`, `46 - أبو بكر الصديق`, `3063 - عبد الله …`
- Paragraf catatan kaki: `^\(\d+\)\s` diikuti teks pendek (bukan heading) — mereka SELALU di bagian bawah halaman dan nomornya kecil (restart tiap halaman). Bedakan: heading memiliki nomor == `num` entri (atau tetangga num±3), catatan kaki tidak.
- Tabaqat (1686): bentuk `N - nama.` atau `[N - nama]`; ada juga baris rujukan muhaqqiq `N المغازي (…)` di bagian bawah — bukan heading (tidak ada tanda `-`/`)` setelah nomor).

## Algoritma per entri
1. `start_page` = `page` entri; `end_excl` = dari TOC (fallback: `page+1` bila null).
2. Cari `para_start`: indeks paragraf pertama di `start_page` yang cocok pola heading DAN nomornya == `num` (bila num ada) ATAU nama ter-norm entri (≥ 12 karakter pertama, atau seluruh nama jika lebih pendek) muncul di paragraf. Bila tidak ketemu di `start_page`, coba `start_page-1` dan `start_page+1` (koreksi kelas: TOC shamela kadang meleset satu halaman) — bila ketemu, perbarui `start_page`. Bila tetap tidak ketemu: `para_start=null`, `heading_found=false`.
3. Batas akhir. Entri berikutnya mulai di halaman `end_excl` — sering di TENGAH halaman — sehingga halaman `end_excl` masih memuat EKOR entri ini. Maka:
   - `last_page` = `end_excl` (halaman tempat entri berikutnya mulai) dan `para_end` = indeks paragraf heading entri berikutnya di halaman itu (eksklusif). Cari heading berikutnya dengan pola yang sama (nomor == num berikutnya, atau heading pertama yang cocok pola di halaman itu). Bila entri berikutnya mulai di paragraf 0 → `last_page = end_excl-1`, `para_end = null` (sampai akhir halaman).
   - Bila heading entri berikutnya tidak ditemukan: `last_page=end_excl-1`, `para_end=null`, `next_heading_found=false`.
4. Keluarkan record JSONL ke `data/person_segments.jsonl`:
   `{"source","book_id","entry_num","name","toc_i","start_page","para_start","last_page","para_end","heading_found","next_heading_found","n_pages","basis"}`
   `basis` = string singkat, mis. `"TOC #4835 + heading para 3; end: heading #4836 p1893 para 5"`.
5. Jangan memotong/mengubah teks; hanya indeks. Paragraf catatan kaki di halaman batas ikut halaman (jangan dipindah).

## Validator (wajib, tulis ke `data/person_segments_report.json` dan cetak)
- Per kamus: jumlah entri, % `heading_found`, % `next_heading_found`, jumlah `start_page` dikoreksi ±1, distribusi n_pages (min/median/max), 10 contoh gagal (num, name, page).
- Probe wajib (cetak lulus/gagal): Ishabah #4835 harus start 1887 heading ditemukan; Isti'ab #1633 start 956; Usud 30018 #3064 start 1505 & last_page 1530/1531; Tabaqat #46 start 803, last_page 838 (para_end = heading #47).
- Target: heading_found ≥ 95% tiap kamus. Bila lebih rendah, perbaiki regex/heuristik dan ulangi sebelum selesai.

## Performa
26.123 halaman, 73 MB. Muat `pages_full.jsonl` sekali ke dict `{(source, web_page): paras}` hanya untuk 5 sumber kamus. Selesai < 2 menit.
