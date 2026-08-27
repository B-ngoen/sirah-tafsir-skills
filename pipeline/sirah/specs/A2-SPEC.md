# Tugas A2: petakan heading kitab ke ID peristiwa registry

Input:
- `data/registry_compact.txt` — 175 baris: `event_id \t nama_arab \t alias \t era \t tahun_h`.
- `data/headings_a_for_llm/<FILE>.txt` — baris: `hid \t halaman \t depth \t judul_heading` (dari satu kitab sirah/tarikh).

Output: TULIS file `data/event_heading_map/<FILE>.json` — array JSON, satu objek PER BARIS heading input (jangan ada yang terlewat):
`{"hid": "...", "event_id": "<id registry>" | null, "confidence": "high"|"medium"|"low", "note": "<opsional, singkat>"}`

Aturan:
1. `event_id` HANYA dari kolom pertama registry_compact.txt. Jangan mengarang id baru.
2. Heading sub-bab (depth ≥1) mewarisi peristiwa bab induknya bila isinya bagian dari peristiwa itu (mis. "رؤيا عاتكة", "شعر حسان في يوم بدر" → ghazwah_badr_kubra). Syair/rats'a tentang peristiwa → peristiwa itu.
3. Heading yang bukan peristiwa (nasab umum, pengantar muhaqqiq, fihris, kaidah bahasa) → `event_id: null`.
4. Heading tahun Thabari «سنة N» → entri registry tahun tersebut (mis. `tahun_39_h`) bila ada; peristiwa bernama di bawah tahun → peristiwa spesifik bila ada di registry, kalau tidak → entri tahun.
5. Bila heading mencakup dua peristiwa, pilih yang dominan dan tulis yang lain di `note`.
6. Output hanya file JSON valid UTF-8 (ensure_ascii=false). Setelah selesai cetak jumlah baris input vs objek output (harus sama).
