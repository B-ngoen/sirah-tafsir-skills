# Tugas: tulis `build_full_db.py` → `data/sirah_full.db` (SQLite, final untuk skill sirah-lookup)

Path relatif CWD (`pipeline/`). Python 3.12+, stdlib saja, `encoding="utf-8"`. Jangan ubah file lain. Jalankan sampai smoke test lolos.

## Input
- `data/pages_full.jsonl` — 26.123 halaman: `{"source","book_id","web_page","printed_juz","printed_page","url","paras":[...]}`
- `data/events_registry.draft.json` — 175 peristiwa: `{"id","name_ar","name_id","aliases_ar":[...],"era","year_h","year_note",...}`
- `data/event_segments.jsonl` — dari group_events.py: record segmen `{"source","book_id","event_id","year_h","start_page","para_start","last_page","para_end","n_pages","heading_ids","basis"}`, record absen `{"source","event_id","absent":true}`, record tahun Thabari `{"source":"tarikh_tabari","year_seg":true,"year_title","year_h","start_page","last_page","para_start","para_end"}`
- `data/person_segments.jsonl` — segmen entri kamus: `{"source","book_id","entry_num","name","toc_i","start_page","para_start","last_page","para_end","heading_found","next_heading_found","n_pages","basis"}` (abaikan record dengan `name` kosong atau `entry_num` null KECUALI source `ishabah` dengan num — semua ishabah bernomor).
- `data/person_links.jsonl` — `{"source","entry_num","name","ishabah_id","ishabah_name","method","confidence","status","candidates"}`
- (opsional bila ada) `data/person_links_llm.jsonl` — format sama, hasil resolusi LLM untuk yang unresolved; prioritas di atas person_links.

## Normalisasi
`norm`: hapus tasykil (U+0610–061A, U+064B–065F, U+0670, U+06D6–06ED, U+0640), أإآ→ا, ة→ه, ى→ي, rapatkan spasi. Dipakai untuk kolom `*_norm` (pencarian), TEKS ASLI TIDAK DIUBAH.

## Skema (buat ulang DB dari nol)
```sql
CREATE TABLE sources(source TEXT PRIMARY KEY, book_id TEXT, title_ar TEXT, title_id TEXT, role TEXT, note TEXT);
-- pages: SATU BARIS PER PARAGRAF (verbatim), seperti tafsir_full.db
CREATE TABLE pages(source TEXT, web_page INT, para_idx INT, text TEXT, printed_juz INT, printed_page INT, url TEXT,
                   PRIMARY KEY(source, web_page, para_idx));
CREATE TABLE events(event_id TEXT PRIMARY KEY, name_ar TEXT, name_id TEXT, aliases_ar TEXT, era TEXT, year_h INT, year_note TEXT, name_norm TEXT, seq INT);
CREATE TABLE event_segments(seg_id INTEGER PRIMARY KEY, source TEXT, event_id TEXT, from_page INT, from_para INT, to_page INT, to_para INT, n_pages INT, basis TEXT, truncated INT DEFAULT 0);
CREATE TABLE event_absent(source TEXT, event_id TEXT, PRIMARY KEY(source,event_id));
CREATE TABLE year_segments(seg_id INTEGER PRIMARY KEY, source TEXT, year_h INT, year_title TEXT, from_page INT, from_para INT, to_page INT, to_para INT);
CREATE TABLE persons(ishabah_id INT PRIMARY KEY, name_ar TEXT, name_norm TEXT, kunya TEXT, from_page INT, from_para INT, to_page INT, to_para INT);  -- entri kanonik Al-Ishabah
CREATE TABLE person_entries(entry_id INTEGER PRIMARY KEY, source TEXT, entry_num INT, name_ar TEXT, name_norm TEXT, ishabah_id INT, link_status TEXT, link_method TEXT, link_confidence TEXT,
                            from_page INT, from_para INT, to_page INT, to_para INT, n_pages INT, basis TEXT, generation TEXT);
CREATE VIRTUAL TABLE person_fts USING fts5(name_norm, content='person_entries', content_rowid='entry_id');
CREATE VIRTUAL TABLE event_fts USING fts5(name_norm, aliases_norm, content='events', content_rowid='seq');
CREATE INDEX ix_es ON event_segments(event_id, source); CREATE INDEX ix_pe_ish ON person_entries(ishabah_id); CREATE INDEX ix_pe_src ON person_entries(source, entry_num);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
```
Aturan konversi:
- `from_para` = `para_start` (null → 0). `to_page` = `last_page`; `to_para` = `para_end - 1` bila para_end tidak null, selain itu = indeks paragraf terakhir halaman `to_page`.
- `sources`: 10 kitab; `title_id` Indonesia; `role`: `sirah` (23833, 7450, 9862), `tabaqat` (1686), `tabiin` (7666), `tarikh` (9783), `kamus_shahabat` (9767, 1110, 30018, 12288); `note` 7450 = "versi elektronik hanya juz 1–2 dari 4 (terputus)"; 7666 = "generasi tabi'in (bukan shahabat)".
- `truncated=1` untuk segmen `hisyam_thaha` yang `to_page >= 589`.
- `persons` dari person_segments source `ishabah` (satu baris per entry_num; bila num duplikat, ambil yang pertama dan catat di meta `dup_ishabah_nums`). `kunya` = name_ar bila diawali أبو/أبي/أم.
- `person_entries` untuk SEMUA kamus (termasuk ishabah sendiri dengan ishabah_id = entry_num, link_status `canonical`). `generation`: `tabaqat` entri di halaman ≥ 687 (bagian الصحابة) tanpa link → `unknown`; sumber 7666 tidak diproses di sini (tak ada entri terindeks) — cukup ada di `sources`.
- `meta`: `built_at` (ISO), `scrape_date`="2026-08-26", `n_pages`, `n_paras`, `n_events`, `n_event_segments`, `n_persons`, `n_person_entries`, `link_resolved_pct`, `registry_version`="draft-2026-08-26 (175, belum ditinjau owner)".
- FTS diisi (`INSERT INTO person_fts(person_fts) VALUES('rebuild')` dst.), lalu `VACUUM`.

## Smoke test (cetak; gagal → exit 1)
1. `SELECT COUNT(*) FROM pages` = jumlah paragraf total (harus > 500.000).
2. Event `ghazwah_badr_kubra`: ada segmen di 5 sumber sirah/tarikh; Thabari from_page 1046; teks paragraf pertama segmen Thabari memuat "بدر".
3. Person 4835: `persons.name_ar` memuat "عبد الله بن عثمان"; `person_entries` dengan ishabah_id 4835 ≥ 4 sumber; paragraf pertama entri Isti'ab memuat "(١٦٣٣)" atau "1633" (norm).
4. `event_fts` MATCH 'بدر' mengembalikan ≥ 3 event; `person_fts` MATCH 'عمر بن الخطاب' mengembalikan entri di ≥ 3 sumber.
5. Cakupan: cetak tabel event × 5 sumber (jumlah event dengan ≥1 segmen per sumber, jumlah ABSEN), dan persen entri kamus terhubung ke Ishabah per sumber.
6. Ukuran file DB (harapan 150–300 MB).
