# Tafsir Pipeline — PC Local (22-Core CPU)

**Tujuan**: Jalankan parsing & grouping di PC lokal untuk kecepatan 10-15x
lebih cepat dibanding VPS. File kanonik grouping = `grouping_mp.py`
(`grouping_batch.py` DEPRECATED — referensi saja).

---

## Struktur Direktori

```
memory/projects/tafsir-verbatim-pipeline/pc_local/
├── README.md                    (file ini)
├── sync_vps_to_pc.sh            (sync cache dari VPS2; fallback tar-over-ssh)
├── parse_mp.py                  (multiprocessing parser; cache = pc_local/cache/)
├── verse_index.py               (verse index dari maraghi display blocks)
├── grouping_mp.py               (grouping KANONIK: 5 buku, guard + validator)
├── grouping_dorar.py            (grouping dorar EN via title, deterministik)
├── grouping_batch.py            (DEPRECATED — referensi, jangan dijalankan)
├── build_db_full.py             (build tafsir_full.db: 114 surah, 6 sumber)
├── toc_full.json                (dari VPS, sudah di-copy)
├── cache/                       (cache HTML dari VPS; SATU-SATUNYA lokasi cache)
└── data/
    ├── pages_full.jsonl         (hasil parse)
    ├── verse_index.json         (hasil verse index)
    ├── ayat_count.json
    ├── tafsir_full.db           (hasil build_db_full.py)
    └── grouping_full/           (hasil grouping: {book}_{sn:03d}.rb.json / .FAIL.json)
```

Semua path di semua script relatif ke folder `pc_local/` ini — tidak ada
hardcoded path VPS, semua `open()` eksplisit `encoding='utf-8'`.

---

## Quick Start

### 1. Sync Cache dari VPS

```bash
cd memory/projects/tafsir-verbatim-pipeline/pc_local
bash sync_vps_to_pc.sh
```

VPS2 = `<user>@<vps>` (alias SSH: `<vps2>`). Kalau `rsync` tidak
ada (Git Bash Windows), script otomatis fallback `tar czf - | ssh`.
Estimasi: 2.1GB via SSH → 5-10 menit tergantung bandwidth.

### 2. Parse (Multiprocessing)

```bash
python parse_mp.py            # default CPU-1 workers
python parse_mp.py 21         # override jumlah workers
```

Baca `cache/`, output `data/pages_full.jsonl`. Estimasi 10-15 menit.

### 3. Verse Index

```bash
python verse_index.py
```

Output `data/verse_index.json` + `data/ayat_count.json` (dipakai tabari/shabuni).

### 4. Grouping — 5 buku Arab + dorar

```bash
python grouping_mp.py maraghi
python grouping_mp.py tabari
python grouping_mp.py shabuni     # butuh verse_index.json
python grouping_mp.py awlad
python grouping_mp.py jawzi
python grouping_dorar.py          # dorar EN via title (butuh pages_full.jsonl)
```

Semua metode sudah ada di `grouping_mp.py` (maraghi header-rentang, tabari
quote-monotonik, shabuni siklus seksi label rentang, awlad/jawzi blok quote
bernomor). GUARD surah berikutnya + validator per surah aktif: gagal validasi
→ `{book}_{sn:03d}.FAIL.json` (berisi alasan), bukan `.rb.json`.

**Catatan toc (2026-08-18):** `toc_full.json` untuk `ibnkathir_awlad` /
`ibnkathir_jawzi` mengandung range mundur/overlap (mis. awlad surah 2
start 190 < surah 1 start 233; jawzi surah 1 sampai web_page 1014 padahal
Fatihah berakhir ~283). Surah dengan range rusak akan keluar sebagai FAIL —
`toc_full.json` perlu diregenerasi di VPS (toc_parse.py). Guard heading
sudah memotong sebagian besar spill secara otomatis.

Hasil = DRAFT rule-based (`*.rb.json`), bukan kanonik — cross-check/verified
menyusul sesuai QC-RB.md.

### 5. Build DB Final

```bash
python build_db_full.py
```

Generalisasi build_db pilot: loop 114 surah, 6 sumber (5 buku + dorar_en),
ekspansi label rentang per ayat, `out_of_scope` dibuang, smoke test lookup
acak (seed tetap). Output: `data/tafsir_full.db`.

### 6. Sync Hasil ke VPS

```bash
# contoh (rsync hasil grouping + DB ke VPS2):
rsync -avz --progress data/ <user>@<vps>:/home/deploy/tafsir-pipeline/data_pc/
```

---

## Requirements

```bash
pip install beautifulsoup4
```

---

## Troubleshooting

**Out of memory**: kurangi workers — `python parse_mp.py 10`
**SSH timeout**: `rsync --partial --append --progress ...`
**Windows UnicodeDecodeError**: sudah ditangani (semua open pakai utf-8);
jangan kembalikan `open()` tanpa encoding.

---

## Update ke Vault

Setelah semua selesai:

```bash
cd memory/projects/tafsir-verbatim-pipeline
git add pc_local/data/
git commit -m "PC local: parse + grouping + build_db_full complete"
git push
```

---

## Ringkasan Perbandingan

| Task | VPS (4 vCPU) | PC (22 Core) |
|------|-------------|--------------|
| Parse | 1-2 jam | 10-15 menit |
| Verse Index | 30-45 menit | 5-10 menit |
| Grouping (5 buku + dorar) | 3-5 jam | 30-60 menit |
| Build DB | - | 5-10 menit |
| **Total** | **4.5-7.5 jam** | **~1-1.5 jam** |
