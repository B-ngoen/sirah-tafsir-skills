# Tugas B3: tulis `link_candidates.py` — siapkan batch resolusi entitas untuk LLM

Path relatif CWD. Stdlib saja, utf-8. Jangan ubah file lain. Jalankan sampai selesai.

## Input
- `data/person_links.jsonl` (status resolved/ambiguous/unresolved), `data/person_segments.jsonl`, `data/pages_full.jsonl`.
- Fungsi normalisasi & tokenisasi nasab: tiru yang ada di `resolve_persons.py` (impor bila bisa: `from resolve_persons import norm_name, ...`; kalau tidak, salin).

## Keluaran
1. `data/link_batches/<source>_<NNN>.txt` — untuk SETIAP entri kamus non-Ishabah berstatus `ambiguous` atau `unresolved` (istiab, usud_ilmiyah, usud_rifai, tabaqat; untuk pasangan usud yang sudah di-pair cukup satu perwakilan — usud_rifai — dan salin hasil ke pasangannya nanti). Maks 120 entri per file. Format per entri:
   ```
   ### Q <source>#<entry_num>
   judul: <name>
   nasab: <paragraf heading + paragraf berikutnya dari pages_full (para_start .. para_start+1), maks 300 karakter, tasykil dihapus>
   kandidat:
     [<ishabah_id>] <nama Ishabah> | <120 karakter pertama badan entri Ishabah, tasykil dihapus>
     ...(maks 8 kandidat)
   ```
   Kandidat = entri Ishabah dengan skor tertinggi: +3 token nama diri sama (token pertama), +2 tiap token nasab (ayah, kakek) sama pada posisi sama, +1 tiap token nasab/nisbah/kunya sama di posisi manapun, +2 lakab unik sama (الصديق, الفاروق, dll), toleransi edit ≤1 untuk token ≥4 huruf. Sertakan `candidates` ronde sebelumnya bila ada. Bila skor tertinggi 0 → tulis "kandidat: (tidak ada)".
2. `data/link_batches/INDEX.json` — daftar file + jumlah entri.
3. `data/LINK-LLM-SPEC.md` — instruksi untuk LLM pemroses batch (tulis persis):
   "Baca file batch. Untuk tiap blok `### Q`, putuskan: `ishabah_id` dari daftar kandidat yang orangnya SAMA (nama, ayah, kakek, kabilah/nisbah, kunya harus konsisten; bukan sekadar mirip), atau null bila tidak ada yang sama/tidak yakin. Keluarkan file JSON `data/link_results/<nama_batch>.json`: array `{"source","entry_num","ishabah_id"|null,"confidence":"high|medium|low","reason":"<≤15 kata>"}` — satu objek per blok, jangan ada yang terlewat. Jangan mengarang id di luar kandidat."
4. Cetak: jumlah entri per sumber yang dibatch, jumlah file, distribusi jumlah kandidat (0 / 1–3 / 4–8), dan 3 contoh blok.
