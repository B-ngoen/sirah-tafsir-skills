#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""export_knowledge.py — ubah tafsir_full.db / sirah_full.db menjadi berkas teks per kitab
untuk *Knowledge* Gem (Gemini web) atau lampiran chat Gemini/ChatGPT/Claude.

Setiap halaman cetak diawali baris penanda sitasi:
    ### [kitab] juz X hal Y | shamela: URL
sehingga AI dapat mengutip verbatim DAN menyebut juz/halaman.

    python export_knowledge.py sirah  sirah_full.db  out/sirah
    python export_knowledge.py tafsir tafsir_full.db out/tafsir

Batas per berkas ±25 MB (dipecah _1, _2 bila lebih); ≤10 berkas per paket agar
muat batas Gemini (10 lampiran/Knowledge). Stdlib saja.
"""
import io, os, sqlite3, sys
from pathlib import Path

MAX_BYTES = int(float(os.environ.get("KNOWLEDGE_MAX_MB", "25")) * 1024 * 1024)

# nama berkas (tanpa ekstensi) -> daftar source di DB (kitab kecil digabung)
GROUPS = {
    "sirah": [
        ("01_sirah_ibnu_hisyam_saqqa", ["hisyam_saqqa"], "سيرة ابن هشام ت السقا"),
        ("02_sirah_ibnu_hisyam_thaha_dan_ibnu_ishaq", ["hisyam_thaha", "ibn_ishaq"], "سيرة ابن هشام ت طه + سيرة ابن إسحاق"),
        ("03_thabaqat_ibnu_saad", ["tabaqat", "tabaqat_tabiin"], "الطبقات الكبرى لابن سعد"),
        ("04_tarikh_thabari", ["tarikh_tabari"], "تاريخ الطبري"),
        ("05_al_ishabah_ibnu_hajar", ["ishabah"], "الإصابة في تمييز الصحابة"),
        ("06_usud_al_ghabah_ilmiyah", ["usud_ilmiyah"], "أسد الغابة ط العلمية"),
        ("07_usud_al_ghabah_rifai", ["usud_rifai"], "أسد الغابة ت الرفاعي"),
        ("08_al_istiab_ibnu_abdil_barr", ["istiab"], "الاستيعاب في معرفة الأصحاب"),
    ],
    "tafsir": [
        ("01_tafsir_thabari", ["tabari"], "تفسير الطبري (جامع البيان)"),
        ("02_tafsir_ibnu_katsir_awlad", ["ibnkathir_awlad"], "تفسير ابن كثير ط أولاد الشيخ"),
        ("03_tafsir_ibnu_katsir_jawzi", ["ibnkathir_jawzi"], "تفسير ابن كثير ط دار ابن الجوزي"),
        ("04_tafsir_maraghi", ["maraghi"], "تفسير المراغي"),
        ("05_shafwat_at_tafasir_shabuni", ["shabuni"], "صفوة التفاسير للصابوني"),
    ],
}
# Karya modern berhak cipta (Dorar EN) sengaja tidak diekspor.

HEADER = (
    "# {title}\n"
    "# Sumber: Maktabah Syamilah (shamela.ws), teks verbatim per halaman cetak.\n"
    "# Setiap halaman diawali baris '### [{key}] juz X hal Y | shamela: URL'.\n"
    "# Kutip teks apa adanya dan sebutkan juz/hal dari baris penanda di atasnya.\n\n"
)


def source_title(con, src, fallback):
    try:
        r = con.execute("select title_ar from sources where source=?", (src,)).fetchone()
        if r and r[0]:
            return r[0]
    except sqlite3.OperationalError:
        pass
    return fallback


def export(kind, db, outdir):
    con = sqlite3.connect(db)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    made = []
    for fname, sources, title in GROUPS[kind]:
        part, buf, size = 1, [], 0
        path = outdir / f"{fname}.txt"

        def flush(final):
            nonlocal part, buf, size
            if not buf:
                return
            p = path if (final and part == 1) else outdir / f"{fname}_{part}.txt"
            io.open(p, "w", encoding="utf-8", newline="\n").write("".join(buf))
            made.append((p.name, os.path.getsize(p)))
            part += 1
            buf, size = [], 0

        for src in sources:
            t = source_title(con, src, title)
            head = HEADER.format(title=t, key=src)
            buf.append(head); size += len(head.encode())
            rows = con.execute(
                "select web_page, printed_juz, printed_page, url, para_idx, text from pages "
                "where source=? order by web_page, para_idx", (src,))
            cur_page = None
            for web_page, juz, hal, url, para_idx, text in rows:
                if web_page != cur_page:
                    jz = juz if juz is not None else "-"
                    hl = hal if hal is not None else "-"
                    mark = f"\n### [{src}] juz {jz} hal {hl} | shamela: {url}\n"
                    buf.append(mark); size += len(mark.encode())
                    cur_page = web_page
                line = (text or "").strip() + "\n"
                buf.append(line); size += len(line.encode())
                if size >= MAX_BYTES:
                    flush(final=False)
        flush(final=True)
    total = sum(s for _, s in made)
    for n, s in made:
        print(f"{s/1e6:6.1f} MB  {n}")
    print(f"{len(made)} berkas, total {total/1e6:.1f} MB -> {outdir}")
    if len(made) > 10:
        print("PERINGATAN: >10 berkas; Gemini membatasi 10 lampiran/Knowledge")


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in GROUPS:
        sys.exit(__doc__)
    export(sys.argv[1], sys.argv[2], sys.argv[3])
