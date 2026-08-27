# lookup.py perbaikan 2 — anggaran per segmen
Masalah: `event ghazwah_badr_kubra -s hisyam_saqqa --max-chars 2500` — sumber punya 2 segmen (629–697 dan 699–781); anggaran 2500 habis di segmen 1 sehingga segmen 2 tampil tanpa teks sama sekali.
Perbaikan:
1. Anggaran `--max-chars N` berlaku PER SEGMEN (bukan per sumber). Bila satu sumber punya k segmen, tiap segmen dapat N karakter (potong di batas paragraf), sehingga tiap segmen minimal memuat paragraf heading + paragraf berikutnya.
2. Bila `--max-chars 0` → penuh (tak berubah).
3. Pesan potong per segmen: "…dipotong, N paragraf total di segmen ini, pakai --max-chars 0".
4. Perbarui teks bantuan/README di docstring. Uji: `event ghazwah_badr_kubra -s hisyam_saqqa --max-chars 2500` (kedua segmen ada teks), `person 4835 --max-chars 1500` (tiap entri/kamus ada teks), regresi semua uji lama.
