# lookup.py perbaikan 4 — peringkat hasil `search`
Masalah: `search أحد` mengembalikan 31 event karena substring "احد" cocok ke "احدى عشره" (tahun 11–19 H); event yang benar (غزوة أحد) tidak dibedakan dari derau.
Perbaikan (event & person):
1. Skor peringkat: (a) query ter-norm == name_norm / salah satu alias_norm / name_id (case-insens.) → skor 100; (b) cocok sebagai KATA UTUH (batas spasi/tanda baca) di name/alias → 60; (c) awalan kata → 40; (d) substring bebas → 10. Urutkan menurun; tampilkan skor implisit lewat pengelompokan: "Cocok persis", "Cocok kata", "Cocok sebagian".
2. Entri rollup `tahun_N_h` hanya ditampilkan bila query mengandung kata "سنة/سنه/tahun" atau berupa angka; selain itu disembunyikan dengan baris "(N entri tahun disembunyikan — pakai `year N`)".
3. Batasi 15 hasil per kelompok (event/person) + baris "…N lagi, persempit kata kunci".
4. Person: kelompokkan menurut ishabah_id, urut jumlah sumber menurun di dalam kelompok skor yang sama (pertahankan perilaku FIX1).
5. Uji: `search أحد` (ghazwah_uhud teratas, tahun disembunyikan), `search بدر` (3 event Badr teratas), `search "عمر بن الخطاب"` (5752 teratas), `search tahun 11`/`search 11` (rollup tampil), `search خندق`; regresi uji FIX1–FIX3 tetap lulus.
