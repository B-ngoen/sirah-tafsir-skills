# LINK-LLM-SPEC — instruksi LLM pemroses batch

Baca file batch. Untuk tiap blok `### Q`, putuskan: `ishabah_id` dari daftar kandidat yang orangnya SAMA (nama, ayah, kakek, kabilah/nisbah, kunya harus konsisten; bukan sekadar mirip), atau null bila tidak ada yang sama/tidak yakin. Keluarkan file JSON `data/link_results/<nama_batch>.json`: array `{"source","entry_num","ishabah_id"|null,"confidence":"high|medium|low","reason":"<≤15 kata>"}` — satu objek per blok, jangan ada yang terlewat. Jangan mengarang id di luar kandidat.
