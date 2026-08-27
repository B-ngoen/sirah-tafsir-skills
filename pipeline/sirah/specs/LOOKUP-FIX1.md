# lookup.py perbaikan 1
1. `person <nama>` daftar kandidat: urutkan menurun berdasarkan jumlah sumber tertaut (n_sumber), lalu ishabah_id; tampilkan maks 15 kandidat + baris "…N kandidat lain, persempit kata kunci". Untuk "أبو بكر", entri 4835 (عبد الله بن عثمان — 5 sumber) harus muncul paling atas. Cari juga pada `person_entries.name_norm` semua kamus (bukan hanya `persons`) dan kelompokkan ke ishabah_id.
2. `person` ambigu tetap exit 2, tetapi bila kandidat teratas punya ≥4 sumber DAN kandidat kedua ≤2 sumber, tambahkan baris saran "Kemungkinan besar: <id> — jalankan `person <id>`".
3. Uji: `person "أبو بكر"` (4835 di atas), `person "عمر بن الخطاب"`, `person "خالد بن الوليد"`, `person 4835 --max-chars 300`. Jangan ubah perilaku lain.
