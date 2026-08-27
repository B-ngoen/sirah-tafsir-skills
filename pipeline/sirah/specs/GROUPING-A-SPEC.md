# Tugas: tulis `headings_a.py` (tahap A1) dan `group_events.py` (tahap A3) — Sumbu A: peristiwa/tahun

Path relatif terhadap CWD (`pipeline/`). Python 3.12+, stdlib saja. `open()` wajib `encoding="utf-8"`.
Jangan mengubah file lain (khususnya `group_persons.py`, `build_pilot.py`). Jalankan `python headings_a.py` sampai lolos validator.
`group_events.py` cukup ditulis + diuji dengan file peta contoh (lihat A3) — peta sebenarnya diisi tahap A2 (LLM) di luar tugas ini.

## Konteks
- `data/pages_full.jsonl`: `{"source","book_id","web_page","printed_juz","printed_page","url","paras":[...]}`.
- `data/toc/toc_{book_id}.json`: `{"i","page","title","depth","parent","end_excl","end_any"}` (`end_excl` = entri berikutnya se-depth-atau-lebih-dangkal; sudah benar).
- `data/events_registry.draft.json`: array 175 peristiwa `{"id","name_ar","name_id","aliases_ar","era","year_h","year_note","hisyam_pages","tabari_pages",...}`.
- Sumber sumbu A dan cakupan halaman:
  | source | book_id | cakupan | sumber heading |
  |---|---|---|---|
  | hisyam_saqqa | 23833 | seluruh | TOC depth 0 dan 1 |
  | hisyam_thaha | 7450 | seluruh (589 hal, TOC hanya 6 entri) | PARAGRAF heading (lihat aturan) |
  | ibn_ishaq | 9862 | seluruh | TOC depth 1 |
  | tabaqat | 1686 | hal. 1–687 (bagian sirah, sebelum «الصحابة») | TOC depth 1 dan 2 |
  | tarikh_tabari | 9783 | hal. 880–2623 (مولد النبي s.d. سنة أربعين) | TOC depth 2, 3, 4 |
  Kamus shahabat (ishabah, usud, istiab) TIDAK ikut sumbu A.

## Normalisasi `norm`
Hapus tasykil (U+0610–061A, U+064B–065F, U+0670, U+06D6–06ED, U+0640); angka Arab-India → 0-9; untuk pencocokan: أإآ→ا, ة→ه, ى→ي; rapatkan spasi.

## A1 — `headings_a.py` → `data/headings_a.jsonl`
Satu record per heading kandidat:
`{"hid": "<source>:<n>", "source","book_id","page","para_idx","title","title_norm","depth","end_excl","kind":"toc"|"para"}`
1. Untuk sumber ber-TOC: ambil entri TOC sesuai tabel; `para_idx` = indeks paragraf di halaman `page` yang cocok dengan `title_norm` (awalan ≥ 15 karakter setelah norm, abaikan tanda kurung/titik dua/nomor catatan `[1]` `(1)` `١`) — coba `page`, lalu `page-1`, `page+1` (perbarui `page` bila ketemu). Tidak ketemu → `para_idx=null`.
2. Untuk `hisyam_thaha` (tanpa TOC): heading = paragraf yang (a) ≤ 60 karakter setelah norm, (b) diakhiri `:` ATAU diawali kata `غزوة|سرية|أمر|حديث|ذكر|شأن|قصة|خبر|إسلام|هجرة|وفاة|مقتل|بعث|عمرة|حجة|بيعة|فتح|يوم`, (c) bukan syair (tidak memuat ` ... `), (d) bukan catatan kaki (`^\(?\d+\)`). `depth`: 0 bila diawali kata di (b), selain itu 1. `end_excl` = halaman heading kandidat berikutnya se-depth-atau-lebih-dangkal.
   Wajib ada heading di hal. 486 «غزوة بدر الكبرى» (probe).
3. Validator (cetak + `data/headings_a_report.json`): jumlah heading per sumber; % `para_idx` ditemukan (target ≥ 90% untuk sumber ber-TOC); untuk thaha: jumlah heading depth 0 (harapan 100–300) dan 20 contoh acak untuk ditinjau.
4. Tulis juga `data/headings_a_for_llm/{source}.txt` — daftar ringkas `hid \t page \t depth \t title` (tanpa norm), dipotong per file maks 400 baris (`{source}_01.txt`, `_02.txt`, …) untuk tahap A2.

## A2 (di luar tugas ini — dikerjakan LLM lain)
Menghasilkan `data/event_heading_map.json`: array `{"hid","event_id"|null,"confidence":"high"|"medium"|"low","note"}`.
Satu heading boleh memetakan ke satu event_id; satu event boleh punya banyak heading (bab utama + sub-bab). Heading yang bukan peristiwa (mis. nasab, syair) → `event_id=null`.

## A3 — `group_events.py` → `data/event_segments.jsonl`
Input: `headings_a.jsonl` + `event_heading_map.json` + registry + pages.
1. Kelompokkan heading ter-map per `(source, event_id)`. Untuk tiap kelompok bentuk segmen dari heading BERKELANJUTAN (halaman menyambung: heading berikutnya dalam kelompok memiliki page ≤ end_excl heading sebelumnya); heading terpisah → segmen terpisah (satu event bisa punya >1 segmen per sumber, mis. bab + lampiran syair).
2. Batas segmen: `start_page` = page heading pertama, `para_start` = para_idx-nya (null bila tidak ketemu). `end_excl` = end_excl heading terakhir (halaman heading berikutnya yang lebih dangkal/se-depth di luar kelompok). Seperti sumbu B: halaman `end_excl` masih memuat ekor → `last_page = end_excl`, `para_end` = para_idx heading berikutnya di halaman itu (eksklusif); bila heading berikutnya di para 0 atau tidak ketemu → `last_page=end_excl-1`, `para_end=null`.
3. Record: `{"source","book_id","event_id","year_h","start_page","para_start","last_page","para_end","n_pages","heading_ids":[...],"basis"}`.
   Tambahkan juga record `ABSEN` per (event, source-sumbu-A) yang tidak punya heading ter-map: `{"source","event_id","absent":true}` — kejujuran ketiadaan sumber wajib.
4. Untuk `tarikh_tabari`: SELAIN peta heading, buat segmen TAHUN otomatis dari TOC: setiap entri berjudul `سنة …` (norm diawali `سنه`/`سنة`) → record `{"source":"tarikh_tabari","year_seg":true,"year_title","start_page","last_page","para_start","para_end"}`. Konversi judul tahun ke bilangan (`سنه اثنتين`→2, `سنه احدى عشره`→11, … s.d. 40) dengan tabel angka Arab kata; yang gagal → `year_h=null` + `year_title` tetap.
5. Uji dengan peta contoh yang kamu buat sendiri `data/event_heading_map.sample.json` berisi minimal: Hisyam Saqqa heading «غزوة بدر الكبرى» (+ sub-babnya) → `ghazwah_badr_kubra`; Thabari «ذكر وقعه بدر الكبرى» → `ghazwah_badr_kubra`; Tabaqat «غزوة بدر» → `ghazwah_badr_kubra`; Ibnu Ishaq «اليوم الذي وقعت فيه معركة بدر» → `ghazwah_badr_kubra`; Thaha hal.486 → `ghazwah_badr_kubra`. Probe: segmen Thabari Badr harus 1046 s.d. ±1104; Tabaqat 397–409; Hisyam Saqqa mulai 629/630.
   `group_events.py` menerima argumen path peta (default `data/event_heading_map.json`; uji dengan `.sample.json`).
6. Validator cetak: jumlah segmen per sumber, jumlah ABSEN per sumber, jumlah year_seg Thabari (harapan ±40 untuk 1–40 H), 5 contoh segmen dengan 100 karakter pertama paragraf `para_start`.
