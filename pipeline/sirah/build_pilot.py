#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pilot DB: satu peristiwa (غزوة بدر الكبرى) + satu shahabat (أبو بكر الصديق) lintas 10 kitab.

Input : data/pages_full.jsonl (verbatim), rentang halaman dari TOC/registry/indeks (di bawah).
Output: data/sirah_pilot.db  (tabel pages, segments, event_map, person_map, sources)
        data/pilot_report.json (cakupan + probe konten)
Rentang = draft rule-based dari TOC; halaman verbatim utuh, tidak dipotong.
"""
import json, pathlib, re, sqlite3

BASE = pathlib.Path(__file__).resolve().parent
PAGES = BASE / "data" / "pages_full.jsonl"
DB = BASE / "data" / "sirah_pilot.db"
REPORT = BASE / "data" / "pilot_report.json"

SOURCES = {
    "hisyam_saqqa":   ("23833", "سيرة ابن هشام ت السقا ورفاقه"),
    "hisyam_thaha":   ("7450",  "سيرة ابن هشام ت طه عبد الرؤوف سعد"),
    "ibn_ishaq":      ("9862",  "سيرة ابن إسحاق = السير والمغازي"),
    "tabaqat":        ("1686",  "الطبقات الكبرى ط العلمية"),
    "tabaqat_tabiin": ("7666",  "الطبقات الكبرى - متمم التابعين"),
    "tarikh_tabari":  ("9783",  "تاريخ الطبري"),
    "ishabah":        ("9767",  "الإصابة في تمييز الصحابة"),
    "usud_ilmiyah":   ("1110",  "أسد الغابة ط العلمية"),
    "usud_rifai":     ("30018", "أسد الغابة ت الرفاعي"),
    "istiab":         ("12288", "الاستيعاب ت البجاوي"),
}

# --- Sumbu A: peristiwa. Rentang [start, end_excl) halaman web; basis = judul TOC / registry.
EVENT = {
    "id": "ghazwah_badr_kubra", "name_ar": "غزوة بدر الكبرى", "name_id": "Perang Badar", "year_h": 2,
    "segments": {
        "hisyam_saqqa":  [(629, 753, "TOC: غزوة بدر الكبرى … s.d. bab berikutnya (registry draft)")],
        "hisyam_thaha":  [],   # tanpa TOC; diisi otomatis via pencarian konten (lihat find_thaha_badr)
        "ibn_ishaq":     [(122, 129, "TOC: اليوم الذي وقعت فيه معركة بدر")],
        "tabaqat":       [(397, 409, "TOC: غزوة بدر"), (687, 1011, "TOC: الطبقة الأولى: أهل بدر (thabaqat Badriyyin)")],
        "tarikh_tabari": [(1032, 1112, "TOC: سنة اثنتين (bagian Badr) — registry draft")],
    },
}

# --- Sumbu B: shahabat. Kunci kanonik = nomor entri Al-Ishabah.
PERSON = {
    "ishabah_id": 4835, "name_ar": "أبو بكر الصديق عبد الله بن عثمان بن عامر", "name_id": "Abu Bakar Ash-Shiddiq",
    "segments": {
        "ishabah":       [(1887, 1893, "Ishabah #4835 عبد الله بن عثمان بن عامر"), (3570, 3571, "Ishabah #9636 (kunya) أبو بكر الصديق")],
        "istiab":        [(956, 971, "Isti'ab #1633")],
        "usud_rifai":    [(1505, 1531, "Usud Rifa'i #3064")],
        "usud_ilmiyah":  [(1567, 1568, "Usud 'Ilmiyah #3066 — rentang TOC dicurigai pendek, lihat probe")],
        "tabaqat":       [(803, 806, "Thabaqat #46 — rentang TOC dicurigai pendek, lihat probe")],
        "tarikh_tabari": [(1458, 1660, "TOC: سنة إحدى عشرة s.d. سنة ثلاث عشرة (khilafah Abu Bakr)")],
    },
}


def load_pages():
    out = {}
    with PAGES.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[(r["source"], r["web_page"])] = r
    return out


def text_of(r):
    return "\n".join(r["paras"])


def find_thaha_badr(pages):
    """Hisyam Thaha (7450) tanpa TOC: cari blok halaman berurutan yang padat 'بدر'."""
    hits = sorted(p for (s, p), r in pages.items() if s == "hisyam_thaha" and "بدر" in text_of(r))
    if not hits:
        return []
    # kelompokkan dengan celah <= 3 halaman, ambil blok terbesar
    blocks, cur = [], [hits[0]]
    for p in hits[1:]:
        if p - cur[-1] <= 3:
            cur.append(p)
        else:
            blocks.append(cur); cur = [p]
    blocks.append(cur)
    best = max(blocks, key=len)
    return [(best[0], best[-1] + 1, f"konten: blok halaman padat 'بدر' ({len(best)} hal ber-'بدر')")]


TASHKEEL = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def norm(s):
    return TASHKEEL.sub("", s)


def toc_end(book_id, toc_i):
    """Batas eksklusif entri TOC = halaman entri berikutnya dengan depth <= depth entri (sub-judul diabaikan)."""
    toc = json.loads((BASE / "data" / "toc" / f"toc_{book_id}.json").read_text(encoding="utf-8"))
    e = toc[toc_i]
    for nxt in toc[toc_i + 1:]:
        if nxt["depth"] <= e["depth"] and nxt["page"] > e["page"]:
            return nxt["page"]
    return e["page"] + 1


def main():
    pages = load_pages()
    print("pages loaded:", len(pages))

    # Hisyam Thaha (7450) tanpa TOC: heading «غزوة بدر الكبرى» di hal. 486 (ج2 ص182); versi elektronik
    # terputus di hal. 589 (ج2 ص286) masih dalam syair Badr → segmen 486–590, ditandai TERPOTONG.
    # (find_thaha_badr sebagai pembanding heuristik; blok terpadat ternyata syair rasa Badr 572–585)
    EVENT["segments"]["hisyam_thaha"] = [(486, 590, "konten: heading غزوة بدر الكبرى hal.486 s.d. akhir versi elektronik (TERPOTONG di ج2 ص286)")]

    # batas entri dari TOC dengan aturan depth (sub-judul entri tidak memotong)
    PERSON["segments"]["usud_ilmiyah"] = [(1567, toc_end("1110", 3267), "Usud 'Ilmiyah #3066 (batas: entri TOC berikutnya se-depth)")]
    PERSON["segments"]["tabaqat"] = [(803, toc_end("1686", 489), "Thabaqat #46 (batas: entri #47 طلحة)")]

    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript("""
    CREATE TABLE sources(source TEXT PRIMARY KEY, book_id TEXT, title_ar TEXT);
    CREATE TABLE pages(source TEXT, web_page INT, printed_juz INT, printed_page INT, url TEXT, text TEXT,
                       PRIMARY KEY(source, web_page));
    CREATE TABLE segments(seg_id INTEGER PRIMARY KEY, source TEXT, start_page INT, end_excl INT, basis TEXT);
    CREATE TABLE events(event_id TEXT PRIMARY KEY, name_ar TEXT, name_id TEXT, year_h INT);
    CREATE TABLE event_map(source TEXT, seg_id INT, event_id TEXT, year_h INT);
    CREATE TABLE persons(ishabah_id INT PRIMARY KEY, name_ar TEXT, name_id TEXT);
    CREATE TABLE person_map(source TEXT, seg_id INT, ishabah_id INT);
    """)
    for s, (bid, t) in SOURCES.items():
        c.execute("INSERT INTO sources VALUES(?,?,?)", (s, bid, t))
    c.execute("INSERT INTO events VALUES(?,?,?,?)", (EVENT["id"], EVENT["name_ar"], EVENT["name_id"], EVENT["year_h"]))
    c.execute("INSERT INTO persons VALUES(?,?,?)", (PERSON["ishabah_id"], PERSON["name_ar"], PERSON["name_id"]))

    report = {"event": {}, "person": {}, "probes": {}}
    inserted = set()

    def add_segments(axis, key, segs):
        for src, lst in segs.items():
            cov = []
            for (a, b, basis) in lst:
                c.execute("INSERT INTO segments(source,start_page,end_excl,basis) VALUES(?,?,?,?)", (src, a, b, basis))
                seg_id = c.lastrowid
                n = 0
                for p in range(a, b):
                    r = pages.get((src, p))
                    if not r:
                        continue
                    if (src, p) not in inserted:
                        c.execute("INSERT INTO pages VALUES(?,?,?,?,?,?)",
                                  (src, p, r["printed_juz"], r["printed_page"], r["url"], text_of(r)))
                        inserted.add((src, p))
                    n += 1
                if axis == "event":
                    c.execute("INSERT INTO event_map VALUES(?,?,?,?)", (src, seg_id, key, EVENT["year_h"]))
                else:
                    c.execute("INSERT INTO person_map VALUES(?,?,?)", (src, seg_id, key))
                cov.append({"start": a, "end_excl": b, "pages": n, "basis": basis})
            report[axis][src] = cov if cov else "ABSEN (tidak ada segmen)"
        for src in SOURCES:
            report[axis].setdefault(src, "ABSEN (tidak ada segmen)")

    add_segments("event", EVENT["id"], EVENT["segments"])
    add_segments("person", PERSON["ishabah_id"], PERSON["segments"])
    con.commit()

    # --- Probe konten (cakupan ≠ kebenaran)
    def seg_text(axis_map, key_col, key):
        rows = c.execute(f"SELECT s.source, s.start_page, s.end_excl FROM segments s JOIN {axis_map} m ON m.seg_id=s.seg_id WHERE m.{key_col}=?", (key,)).fetchall()
        out = {}
        for src, a, b in rows:
            t = norm("\n".join(x[0] for x in c.execute("SELECT text FROM pages WHERE source=? AND web_page>=? AND web_page<? ORDER BY web_page", (src, a, b))))
            out[src] = out.get(src, "") + "\n" + t
        return out

    ev = seg_text("event_map", "event_id", EVENT["id"])
    badr_terms = ["بدر", "أبو جهل", "أبي جهل", "عتبة بن ربيعة", "أمية بن خلف", "العريش", "الأسارى", "النضر بن الحارث"]
    for src, t in ev.items():
        report["probes"][f"badr:{src}"] = {k: t.count(k) for k in badr_terms}
        report["probes"][f"badr:{src}"]["chars"] = len(t)
    pe = seg_text("person_map", "ishabah_id", PERSON["ishabah_id"])
    ab_terms = ["عبد الله بن عثمان", "أبي قحافة", "الصديق", "عتيق", "الغار", "استخلف", "توفي", "خلافة"]
    for src, t in pe.items():
        report["probes"][f"abubakr:{src}"] = {k: t.count(k) for k in ab_terms}
        report["probes"][f"abubakr:{src}"]["chars"] = len(t)

    # guard: apakah halaman terakhir segmen sudah masuk peristiwa/entri lain? (cek heading kurung Ibn Hisyam)
    last = pages.get(("hisyam_saqqa", 752))
    report["probes"]["guard_hisyam_752_head"] = last["paras"][0][:120] if last else None
    nxt = pages.get(("hisyam_saqqa", 753))
    report["probes"]["guard_hisyam_753_head"] = nxt["paras"][0][:120] if nxt else None

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    n_pages = c.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    print("DB:", DB, "| pages:", n_pages, "| segments:", c.execute("SELECT COUNT(*) FROM segments").fetchone()[0])
    print(json.dumps(report, ensure_ascii=False, indent=1))
    con.close()


if __name__ == "__main__":
    main()
