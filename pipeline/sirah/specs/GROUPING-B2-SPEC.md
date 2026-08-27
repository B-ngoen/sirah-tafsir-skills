# Tugas B2: tulis `resolve_persons.py` — resolusi entitas lintas kamus → kunci kanonik Al-Ishabah

Path relatif CWD (`pipeline/`). Python 3.12+, stdlib saja, `encoding="utf-8"`. Jangan ubah file lain. Jalankan sampai validator lolos.

## Input
`data/person_segments.jsonl` — satu record per entri: `{"source","book_id","entry_num","name","toc_i","start_page","para_start","last_page","para_end",...}`.
Sumber: `ishabah` (kanonik, 9.725 entri), `istiab` (3.635), `usud_ilmiyah` (7.142), `usud_rifai` (7.503), `tabaqat` (4.771; memuat juga tabi'in & entri struktural "الطبقة…" — abaikan entri tanpa entry_num atau nama kosong).
Juga `data/pages_full.jsonl` untuk mengambil paragraf heading + 2 paragraf pertama entri (nasab lengkap ada di sana, bukan hanya di judul).

## Normalisasi nama (`norm_name`)
Hapus tasykil (U+0610–061A, U+064B–065F, U+0670, U+06D6–06ED, U+0640); أإآ→ا; ة→ه; ى→ي; hapus tanda baca `[]()«»:،.-` dan nomor; hapus kata penghormatan (`رضي الله عنه`, `رضى الله عنه`, `﵁`, `ﷺ`, `صلى الله عليه وسلم`); rapatkan spasi.
Tokenisasi nasab: pisah pada ` بن `/` ابن `/` بنت `. Kunya = token diawali `ابو`/`ابي`/`ام`. Nisbah = token diawali `ال` di akhir.

## Algoritma
1. Bangun indeks Ishabah: kunci = norm_name(judul) dan juga norm_name(judul tanpa nisbah), plus kunci dari 2 paragraf pertama badan entri (ambil frasa nasab pertama `X بن Y بن Z…` hingga 6 token).
2. Untuk tiap entri kamus lain, kandidat Ishabah:
   a. `exact`: norm_name sama persis (judul vs judul) → match, confidence `high`.
   b. `nasab3`: tiga token nasab pertama sama (nama, ayah, kakek) → `high` bila unik, `medium` bila >1 kandidat (pilih yang nisbah/kunya cocok; bila tetap ambigu → tulis semua kandidat di `candidates`, `ishabah_id=null`, `status="ambiguous"`).
   c. `nasab2`: dua token pertama sama + (nisbah ATAU kunya sama) → `medium`.
   d. `kunya_only`: entri berjudul kunya (أبو فلان) — cocokkan ke entri Ishabah kunya di bagian الكنى (judul berawalan ابو/ام) dengan norm sama; bila di paragraf pertama disebut "اسمه X بن Y" gunakan nasab itu ke aturan b.
   e. tidak ada → `status="unresolved"`.
3. Usud 'Ilmiyah (1110) dan Usud Rifa'i (30018) adalah kitab yang sama: pasangkan dulu antar keduanya (nomor entri sering sama/bergeser ≤ 5, judul norm sama) → `usud_pair`; resolusi ke Ishabah cukup sekali per pasangan dan disalin ke pasangannya.
4. Output `data/person_links.jsonl`: `{"source","entry_num","name","ishabah_id","ishabah_name","method","confidence","status":"resolved|ambiguous|unresolved","candidates":[...]}`.
   Output `data/person_links_unresolved.txt`: baris `source \t entry_num \t name \t nasab_paragraf(150 char)` untuk yang ambiguous/unresolved — akan diserahkan ke LLM.

## Validator (cetak + `data/person_links_report.json`)
- Per sumber: n, resolved %, ambiguous %, unresolved %; per method count.
- Probe wajib (lulus/gagal): istiab #1633 → ishabah 4835; usud_rifai #3064 → 4835; usud_ilmiyah #3066 → 4835; tabaqat #46 (أبو بكر الصديق) → 4835 (via kunya/lakab: "الصديق" + paragraf "عبد الله بن عثمان"); istiab: cari entri عمر بن الخطاب → Ishabah entri عمر بن الخطاب; usud: عائشة بنت أبي بكر → Ishabah عائشة بنت أبي بكر.
- Target resolved ≥ 70% untuk istiab/usud; tabaqat lebih rendah wajar (banyak tabi'in). Bila di bawah target, perbaiki heuristik (mis. buang token `ابن` vs `بن`, varian `عبد الله` vs `عبدالله`) dan ulangi.
