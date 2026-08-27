# Tugas: draft events_registry.json (registry peristiwa kanonik Sirah Nabawiyah + Khulafa Rasyidin)

Input (baca semuanya, path relatif dari CWD):
- data/toc/hisyam_chapters.txt  — kolom: halaman_web \t end_excl \t judul bab (Sirah Ibnu Hisyam ت السقا, book 23833, 222 bab)
- data/toc/tabari_years.txt     — kolom: halaman_web \t end_excl \t judul "سنة N" (Tarikh Thabari, book 9783); pakai hanya sampai halaman 2623 (سنة أربعين)
- data/toc/tabari_sirah_headings.txt — kolom: halaman_web \t judul (Thabari, hal. 880–2623, depth<=2)

Output: TULIS file data/events_registry.draft.json — array JSON, ±150–200 entri, urut kronologis. Skema tiap entri:
{
 "id": "slug_ascii_snake",            // mis. "ghazwah_badr"
 "name_ar": "غزوة بدر الكبرى",
 "name_id": "Perang Badar",            // Bahasa Indonesia
 "aliases_ar": ["بدر", "يوم بدر", "وقعة بدر"],  // varian nama yang mungkin dipakai kitab lain
 "era": "pra_bitsah|makkah|madinah|khulafa",
 "year_h": 2,                          // tahun Hijriah bilangan bulat, null bila pra-hijrah
 "year_note": "Ramadhan 2 H",          // teks bebas; untuk pra-hijrah tulis mis. "tahun ke-5 bi'tsah" / "±570 M"
 "hisyam_pages": [560, 640],           // [start, end_excl] halaman web 23833 dari hisyam_chapters.txt; null bila tak ada bab
 "tabari_pages": [1130, 1163],         // [start, end_excl] halaman web 9783 dari heading Thabari; null bila tak ada
 "hisyam_titles": ["..."],             // judul bab persis yang dijadikan dasar
 "tabari_titles": ["..."]
}
Aturan:
1. Sumber nama & halaman = file input (jangan mengarang halaman). Tahun & nama Indonesia dari pengetahuan sejarah baku (Ibnu Hisyam/Thabari/Ibnu Sa'd).
2. Gabungkan bab-bab kecil Ibnu Hisyam yang satu peristiwa (mis. beberapa bab syair pasca-Badr → satu entri Badr) — hisyam_pages mencakup rentang gabungan.
3. Sertakan: nasab & kelahiran Nabi, peristiwa masa kecil, Hilful Fudhul, pernikahan Khadijah, bangunan Ka'bah, bi'tsah, dakwah sirriyah/jahriyah, hijrah Habasyah 1&2, boikot, 'Amul Huzn, Tha'if, Isra' Mi'raj, Aqabah 1&2, Hijrah, semua ghazwah & sariyyah besar, Bai'atur Ridhwan/Hudaibiyah, surat kepada raja-raja, Khaibar, Umrah Qadha, Mu'tah, Fathu Makkah, Hunain, Tha'if, Tabuk, tahun delegasi, Haji Wada', wafat Nabi, Saqifah, Riddah, penaklukan besar, wafat Abu Bakar, Umar, syura, Utsman, fitnah, Jamal, Shiffin, Tahkim, Nahrawan, syahid Ali (40 H). Untuk era khulafa cukup satu entri per tahun Thabari + entri peristiwa besar.
4. Bila ragu tahun, tetap isi year_h dengan pendapat jumhur dan catat alternatif di year_note.
5. Output HANYA file JSON valid (UTF-8, ensure_ascii=false). Setelah selesai, cetak jumlah entri.
