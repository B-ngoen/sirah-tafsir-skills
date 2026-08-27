# Tugas: tulis `skill/scripts/lookup.py` — CLI query verbatim `sirah_full.db` (skill `sirah-lookup`)

Path relatif CWD (`pipeline/`). Tulis ke `skill/scripts/lookup.py`. Stdlib saja (sqlite3, argparse, json, os, sys, glob, lzma, zipfile, urllib, tempfile, pathlib). `sys.stdout.reconfigure(encoding="utf-8")`.
Contoh pola yang WAJIB ditiru untuk resolusi DB, cache permanen, auto-download, ekstrak xz/zip, exit code, dan gaya output: `../ref/tafsir_lookup_reference.py` (salin fungsi `_cache_dir`, `find_db`, `download_db`, `_download_from_url`, `extract_*`, `open_db`, `truncate`, `render_json` dengan penyesuaian nama: env `SIRAH_DB`, `SIRAH_LOOKUP_SKIP_LOCAL`, nama file `sirah_full.db`, cache dir `sirah-lookup`, LOCAL_DB `D:\Pribadi\AI\MyLab\Skill\sirah-skill\pipeline\data\sirah_full.db`, AUTO_DL_URLS = dua URL placeholder `https://github.com/B-ngoen/refdb/releases/download/v1/sirah_full.db.xz` dan `http://87.106.165.0:8447/0494205b9b5577de58e6b1eefa427588dd3557584c6cd256/sirah_full.db.xz`; URL tidak boleh dicetak ke log/error).

## Skema DB (lihat data/BUILD-DB-SPEC.md) — tabel: sources, pages(per paragraf), events, event_segments, event_absent, year_segments, persons, person_entries, person_fts, event_fts, meta.

## Sub-perintah
```
python lookup.py event <query|event_id> [-s src,src] [--format json] [--max-chars N] [--list]
python lookup.py person <nama|ishabah_id> [-s ...] [--format json] [--max-chars N] [--list]
python lookup.py year <N> [--format json] [--max-chars N]            # segmen "سنة N" Thabari + semua event registry tahun N
python lookup.py search <kata>                                        # cari event & person (FTS + LIKE pada norm), tampilkan kandidat + id
python lookup.py coverage [event|person]                              # ringkasan cakupan per sumber
python lookup.py info                                                 # meta DB, daftar sumber, provenance
```
Resolusi query:
- `event`: bila argumen persis `event_id` → pakai; selain itu normalisasi (strip tasykil, أإآ→ا, ة→ه, ى→ي) lalu cari di `events.name_norm`, `aliases_norm`, dan `name_id` (case-insensitive, Indonesia, mis. "badar"/"perang badar"); bila >1 kandidat dan bukan `--list`, tampilkan kandidat (id, nama Arab, Indonesia, tahun) dan exit 2 dengan pesan "pilih event_id". `--list` = daftar semua event urut kronologis (id, Arab, Indonesia, era, tahun).
- `event` dengan id `tahun_N_h` (rollup tahunan; tidak punya event_segments) → tampilkan `year_segments` Thabari tahun N (sama seperti sub-perintah `year N`), plus daftar event registry bertahun N sebagai rujukan silang.
- `person`: angka → ishabah_id; teks → cari `persons.name_norm` LIKE dan `person_fts`; kandidat >1 → tampilkan kandidat (ishabah_id, nama, jumlah sumber) dan exit 2. Output = entri kanonik Ishabah + entri semua kamus lain yang terhubung (link_status, confidence) + Thabaqat + (bila ada) segmen Thabari/sirah yang memuat nama (hanya via `search`, bukan default).
- Urutan tampilan sumber: hisyam_saqqa, hisyam_thaha, ibn_ishaq, tabaqat, tarikh_tabari, ishabah, usud_ilmiyah, usud_rifai, istiab, tabaqat_tabiin.

## Output markdown (pola tafsir-lookup)
`# <judul query>` → per sumber `## <title_ar> — <title_id>` → baris meta: `- Segmen: seg_id, hal.web from–to, basis` → paragraf verbatim → `…dipotong, N paragraf total, pakai --max-chars 0` bila terpotong → `— Sumber: juz X hal Y · URL` (URL halaman pertama segmen). Sumber tanpa segmen: `tidak tersedia di sumber ini (keterbatasan edisi/situs/cakupan registry).` Segmen `truncated=1`: tambahkan catatan "edisi elektronik terputus di sini". Untuk entri person dengan `link_confidence` medium/low: catatan "tautan entitas: medium — verifikasi nasab". Default `--max-chars 6000` per sumber (potong di batas paragraf); JSON memuat semua field.

## Uji (jalankan, semua harus sukses; DB di data/sirah_full.db)
`event ghazwah_badr_kubra`, `event badar`, `event "غزوة بدر"`, `person 4835`, `person "أبو بكر"` (harus menampilkan kandidat atau hasil), `year 2`, `search خندق`, `coverage event`, `info`, dan `event xyz` (exit 2 rapi), `--db /tidak/ada` (exit 3 rapi).
