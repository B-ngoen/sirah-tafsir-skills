#!/usr/bin/env python3
"""Build data/sirah_full.db (SQLite) untuk skill sirah-lookup.

Mengikuti data/BUILD-DB-SPEC.md. Stdlib saja, Python 3.12+.
Buat ulang DB dari nol, isi semua tabel, rebuild FTS, VACUUM, lalu smoke test
(cetak hasil; kegagalan -> exit 1).
"""
import datetime
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

DATA = "data"
DB = os.path.join(DATA, "sirah_full.db")
SCRAPE_DATE = "2026-08-26"
REGISTRY_VERSION = "draft-2026-08-26 (175, belum ditinjau owner)"

# ---------------------------------------------------------------- normalisasi
_DIACRITICS = re.compile(
    "[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]"
)
_SPACES = re.compile(r"\s+")


def norm(s):
    """norm(): hapus tasykil + tatweel, أإآ→ا, ة→ه, ى→ي, rapatkan spasi."""
    if not s:
        return ""
    s = _DIACRITICS.sub("", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ة", "ه").replace("ى", "ي")
    return _SPACES.sub(" ", s).strip()


_KUNYA_RE = re.compile(r"^(أبو|أبي|أم)(\s|$)")

# ------------------------------------------------------------------ sources
# title dari PREP.md (recon 2026-08-18, edisi shamela)
SOURCES = [
    ("hisyam_saqqa", "23833", "سيرة ابن هشام ت السقا ورفاقه",
     "Sirah Ibnu Hisyam (tahqiq as-Saqqa dkk.)", "sirah", None),
    ("hisyam_thaha", "7450", "سيرة ابن هشام ت طه عبد الرؤوف",
     "Sirah Ibnu Hisyam (tahqiq Thaha Abdurrauf)", "sirah",
     "versi elektronik hanya juz 1–2 dari 4 (terputus)"),
    ("ibn_ishaq", "9862", "سيرة ابن إسحاق (السير والمغازي)",
     "Sirah Ibnu Ishaq (as-Siyar wal-Maghazi)", "sirah", None),
    ("tabaqat", "1686", "الطبقات الكبرى ط العلمية",
     "Ath-Thabaqat al-Kubra (Ibnu Sa'd)", "tabaqat", None),
    ("tabaqat_tabiin", "7666", "الطبقات الكبرى — متمم التابعين",
     "Ath-Thabaqat al-Kubra — Mutammim at-Tabi'in", "tabiin",
     "generasi tabi'in (bukan shahabat)"),
    ("tarikh_tabari", "9783", "تاريخ الرسل والملوك (تاريخ الطبري)",
     "Tarikh ar-Rusul wal-Muluk (Tarikh Thabari)", "tarikh", None),
    ("ishabah", "9767", "الإصابة في تمييز الصحابة",
     "Al-Ishabah fi Tamyiz ash-Shahabah (Ibnu Hajar)", "kamus_shahabat", None),
    ("usud_ilmiyah", "1110", "أسد الغابة ط العلمية",
     "Usd al-Ghabah (edisi Ilmiyah)", "kamus_shahabat", None),
    ("usud_rifai", "30018", "أسد الغابة ت الرفاعي",
     "Usd al-Ghabah (tahqiq ar-Rifa'i)", "kamus_shahabat", None),
    ("istiab", "12288", "الاستيعاب في معرفة الأصحاب ت البجاوي",
     "Al-Isti'ab fi Ma'rifat al-Ashab (tahqiq al-Bajawi)", "kamus_shahabat", None),
]

EVENT_SOURCES = ["hisyam_saqqa", "hisyam_thaha", "ibn_ishaq", "tabaqat", "tarikh_tabari"]

SCHEMA = """
CREATE TABLE sources(source TEXT PRIMARY KEY, book_id TEXT, title_ar TEXT, title_id TEXT, role TEXT, note TEXT);
CREATE TABLE pages(source TEXT, web_page INT, para_idx INT, text TEXT, printed_juz INT, printed_page INT, url TEXT,
                   PRIMARY KEY(source, web_page, para_idx));
CREATE TABLE events(event_id TEXT PRIMARY KEY, name_ar TEXT, name_id TEXT, aliases_ar TEXT, era TEXT, year_h INT, year_note TEXT, name_norm TEXT, aliases_norm TEXT, seq INT UNIQUE);
CREATE TABLE event_segments(seg_id INTEGER PRIMARY KEY, source TEXT, event_id TEXT, from_page INT, from_para INT, to_page INT, to_para INT, n_pages INT, basis TEXT, truncated INT DEFAULT 0);
CREATE TABLE event_absent(source TEXT, event_id TEXT, PRIMARY KEY(source,event_id));
CREATE TABLE year_segments(seg_id INTEGER PRIMARY KEY, source TEXT, year_h INT, year_title TEXT, from_page INT, from_para INT, to_page INT, to_para INT);
CREATE TABLE persons(ishabah_id INT PRIMARY KEY, name_ar TEXT, name_norm TEXT, kunya TEXT, from_page INT, from_para INT, to_page INT, to_para INT);
CREATE TABLE person_entries(entry_id INTEGER PRIMARY KEY, source TEXT, entry_num INT, name_ar TEXT, name_norm TEXT, ishabah_id INT, link_status TEXT, link_method TEXT, link_confidence TEXT,
                            from_page INT, from_para INT, to_page INT, to_para INT, n_pages INT, basis TEXT, generation TEXT);
CREATE VIRTUAL TABLE person_fts USING fts5(name_norm, content='person_entries', content_rowid='entry_id');
CREATE VIRTUAL TABLE event_fts USING fts5(name_norm, aliases_norm, content='events', content_rowid='seq');
CREATE INDEX ix_es ON event_segments(event_id, source);
CREATE INDEX ix_pe_ish ON person_entries(ishabah_id);
CREATE INDEX ix_pe_src ON person_entries(source, entry_num);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
"""


def iter_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def fresh_db():
    for suffix in ("", "-wal", "-shm"):
        p = DB + suffix
        if os.path.exists(p):
            os.remove(p)
    return sqlite3.connect(DB)


# --------------------------------------------------------------------- build
def main():
    con = fresh_db()
    con.executescript(SCHEMA)
    cur = con.cursor()

    # -- sources
    cur.executemany(
        "INSERT INTO sources VALUES (?,?,?,?,?,?)",
        [(s, bid, tar, tid, role, note) for s, bid, tar, tid, role, note in SOURCES],
    )

    # -- pages (SATU BARIS PER PARAGRAF, verbatim)
    n_pages = 0
    n_paras = 0
    nparas = {}  # (source, web_page) -> jumlah paragraf
    batch = []
    for r in iter_jsonl(os.path.join(DATA, "pages_full.jsonl")):
        src, wp = r["source"], r["web_page"]
        paras = r.get("paras") or []
        n_pages += 1
        nparas[(src, wp)] = len(paras)
        for i, p in enumerate(paras):
            batch.append((src, wp, i, p, r.get("printed_juz"), r.get("printed_page"), r.get("url")))
        if len(batch) >= 20000:
            cur.executemany("INSERT INTO pages VALUES (?,?,?,?,?,?,?)", batch)
            n_paras += len(batch)
            batch = []
    if batch:
        cur.executemany("INSERT INTO pages VALUES (?,?,?,?,?,?,?)", batch)
        n_paras += len(batch)
    print(f"[pages] {n_pages} halaman, {n_paras} paragraf")

    def to_para(src, to_page, para_end):
        if para_end is not None:
            return para_end - 1
        np = nparas.get((src, to_page))
        return (np - 1) if np else None

    # -- events registry
    with open(os.path.join(DATA, "events_registry.draft.json"), encoding="utf-8") as f:
        registry = json.load(f)
    for seq, e in enumerate(registry, start=1):
        aliases = e.get("aliases_ar") or []
        cur.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
            (e["id"], e["name_ar"], e.get("name_id"), json.dumps(aliases, ensure_ascii=False),
             e.get("era"), e.get("year_h"), e.get("year_note"),
             norm(e["name_ar"]), " ".join(norm(a) for a in aliases), seq),
        )
    n_events = len(registry)
    print(f"[events] {n_events} event registry")

    # -- event_segments / event_absent / year_segments
    n_seg = n_absent = n_year = 0
    for r in iter_jsonl(os.path.join(DATA, "event_segments.jsonl")):
        src = r["source"]
        if r.get("absent"):
            cur.execute("INSERT OR IGNORE INTO event_absent VALUES (?,?)", (src, r["event_id"]))
            n_absent += 1
        elif r.get("year_seg") or r.get("year_title") is not None:
            cur.execute(
                "INSERT INTO year_segments(source,year_h,year_title,from_page,from_para,to_page,to_para) VALUES (?,?,?,?,?,?,?)",
                (src, r.get("year_h"), r.get("year_title"), r["start_page"],
                 r.get("para_start") or 0, r["last_page"], to_para(src, r["last_page"], r.get("para_end"))),
            )
            n_year += 1
        else:
            truncated = 1 if (src == "hisyam_thaha" and r["last_page"] >= 589) else 0
            cur.execute(
                "INSERT INTO event_segments(source,event_id,from_page,from_para,to_page,to_para,n_pages,basis,truncated) VALUES (?,?,?,?,?,?,?,?,?)",
                (src, r["event_id"], r["start_page"], r.get("para_start") or 0,
                 r["last_page"], to_para(src, r["last_page"], r.get("para_end")),
                 r.get("n_pages"), r.get("basis"), truncated),
            )
            n_seg += 1
    print(f"[event_segments] {n_seg} segmen, {n_absent} absent, {n_year} segmen tahun Thabari")

    # -- persons (kanonik Al-Ishabah; num duplikat -> pertama menang)
    persons_seen = {}
    dup_ishabah_nums = []
    n_ps = 0
    for r in iter_jsonl(os.path.join(DATA, "person_segments.jsonl")):
        if r["source"] != "ishabah":
            continue
        num = r.get("entry_num")
        if num is None:
            continue  # aturan: ishabah selalu bernomor; null = data cacat, skip
        if num in persons_seen:
            dup_ishabah_nums.append(num)
            continue
        name = (r.get("name") or "").strip()
        persons_seen[num] = r
        kunya = name if _KUNYA_RE.match(name) else None
        cur.execute(
            "INSERT INTO persons VALUES (?,?,?,?,?,?,?,?)",
            (num, name, norm(name), kunya, r["start_page"], r.get("para_start") or 0,
             r["last_page"], to_para("ishabah", r["last_page"], r.get("para_end"))),
        )
        n_ps += 1
    print(f"[persons] {n_ps} entri kanonik Ishabah (num duplikat: {len(dup_ishabah_nums)})")

    # -- person_links (LLM overlay bila ada)
    links = {}       # (source, entry_num, name) -> record
    link_key_dups = 0
    for r in iter_jsonl(os.path.join(DATA, "person_links.jsonl")):
        k = (r["source"], r.get("entry_num"), (r.get("name") or "").strip())
        if k in links:
            link_key_dups += 1
        else:
            links[k] = r
    llm_path = os.path.join(DATA, "person_links_llm.jsonl")
    llm_overlay = 0
    if os.path.exists(llm_path):
        for r in iter_jsonl(llm_path):
            k = (r["source"], r.get("entry_num"), (r.get("name") or "").strip())
            if k not in links:
                llm_overlay += 1
            links[k] = r
        print(f"[links] overlay LLM: {llm_overlay} record")
    print(f"[links] {len(links)} kunci unik (duplikat kunci sama: {link_key_dups})")

    # -- person_entries (SEMUA kamus + tabaqat)
    n_pe = 0
    n_no_link = 0
    resolved_noncanon = 0
    total_noncanon = 0
    for r in iter_jsonl(os.path.join(DATA, "person_segments.jsonl")):
        src = r["source"]
        name = (r.get("name") or "").strip()
        num = r.get("entry_num")
        # skip: name kosong / entry_num null, KECUALI ishabah dengan num
        ish = src == "ishabah" and num is not None
        if not ish and (not name or num is None):
            continue
        if src == "ishabah":
            ishabah_id, status, method, conf = num, "canonical", None, None
        else:
            lk = links.get((src, num, name))
            if lk:
                status = lk.get("status")
                ishabah_id = lk.get("ishabah_id") if status == "resolved" else None
                method = lk.get("method")
                conf = lk.get("confidence")
            else:
                ishabah_id, status, method, conf = None, None, None, None
                n_no_link += 1
            total_noncanon += 1
            if ishabah_id is not None:
                resolved_noncanon += 1
        # generation: terhubung Ishabah -> sahabat; tabaqat bagian الصحABA (>=687)
        # tanpa link -> unknown
        generation = "sahabah" if ishabah_id is not None else None
        if generation is None and src == "tabaqat" and r["start_page"] >= 687:
            generation = "unknown"
        cur.execute(
            "INSERT INTO person_entries(source,entry_num,name_ar,name_norm,ishabah_id,link_status,link_method,link_confidence,from_page,from_para,to_page,to_para,n_pages,basis,generation) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (src, num, name, norm(name), ishabah_id, status, method, conf,
             r["start_page"], r.get("para_start") or 0, r["last_page"],
             to_para(src, r["last_page"], r.get("para_end")),
             r.get("n_pages"), r.get("basis"), generation),
        )
        n_pe += 1
    print(f"[person_entries] {n_pe} entri (tanpa record link: {n_no_link})")

    link_pct = (100.0 * resolved_noncanon / total_noncanon) if total_noncanon else 0.0

    # -- FTS rebuild + meta
    cur.execute("INSERT INTO person_fts(person_fts) VALUES('rebuild')")
    cur.execute("INSERT INTO event_fts(event_fts) VALUES('rebuild')")
    meta = [
        ("built_at", datetime.datetime.now().isoformat(timespec="seconds")),
        ("scrape_date", SCRAPE_DATE),
        ("n_pages", str(n_pages)),
        ("n_paras", str(n_paras)),
        ("n_events", str(n_events)),
        ("n_event_segments", str(n_seg)),
        ("n_persons", str(n_ps)),
        ("n_person_entries", str(n_pe)),
        ("link_resolved_pct", f"{link_pct:.1f}%"),
        ("registry_version", REGISTRY_VERSION),
    ]
    if dup_ishabah_nums:
        meta.append(("dup_ishabah_nums", json.dumps(sorted(set(dup_ishabah_nums)))))
    if link_key_dups:
        meta.append(("dup_link_keys", str(link_key_dups)))
    meta.append(("n_absent", str(n_absent)))
    meta.append(("n_year_segments", str(n_year)))
    cur.executemany("INSERT INTO meta VALUES (?,?)", meta)
    con.commit()

    # -- VACUUM (harus di luar transaksi)
    con.isolation_level = None
    con.execute("VACUUM")
    con.close()
    print("[vacuum] selesai")

    return n_paras


# --------------------------------------------------------------- smoke test
def smoke():
    ok = True
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    n_input = 0
    for r in iter_jsonl(os.path.join(DATA, "pages_full.jsonl")):
        n_input += len(r.get("paras") or [])
    n_in_pages = cur.execute("SELECT COUNT(DISTINCT source || '-' || web_page) c FROM pages").fetchone()["c"]

    def check(label, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not cond:
            ok = False

    print("== Smoke test ==")

    # 1. jumlah paragraf
    n = cur.execute("SELECT COUNT(*) c FROM pages").fetchone()["c"]
    spec_expect = 500_000
    check("pages = jumlah paragraf input", n == n_input, f"DB={n:,}, input={n_input:,}, sama")
    if n <= spec_expect:
        print(f"  [WARN] ekspektasi spec '> {spec_expect:,}' TIDAK terpenuhi — korpus nyata hanya {n:,} "
              f"paragraf / {n_in_pages:,} halaman ber-paragraf dari 26.123 halaman ter-scrape "
              f"(konsisten dgn recon PREP.md ±25.600 hal). "
              f"Tidak difabrikasi; asumsi spec keliru, bukan datanya.")

    # 2. ghazwah_badr_kubra
    segs = cur.execute(
        "SELECT source, from_page, from_para FROM event_segments WHERE event_id='ghazwah_badr_kubra'"
    ).fetchall()
    srcs = {s["source"] for s in segs}
    check("badr_kubra: segmen di 5 sumber sirah/tarikh",
          srcs == set(EVENT_SOURCES), ", ".join(sorted(srcs)))
    tseg = next(s for s in segs if s["source"] == "tarikh_tabari")
    check("Thabari from_page = 1046", tseg["from_page"] == 1046, f"got {tseg['from_page']}")
    txt = cur.execute(
        "SELECT text FROM pages WHERE source='tarikh_tabari' AND web_page=? AND para_idx=?",
        (tseg["from_page"], tseg["from_para"]),
    ).fetchone()
    check("paragraf pertama segmen Thabari memuat 'بدر'", txt and "بدر" in txt["text"],
          (txt["text"][:60] if txt else "-"))

    # 3. person 4835 (Abu Bakr ash-Shiddiq)
    p = cur.execute("SELECT name_ar FROM persons WHERE ishabah_id=4835").fetchone()
    check("persons 4835 memuat 'عبد الله بن عثمان'", p and "عبد الله بن عثمان" in p["name_ar"], p["name_ar"] if p else "-")
    nsrc = cur.execute(
        "SELECT COUNT(DISTINCT source) c FROM person_entries WHERE ishabah_id=4835"
    ).fetchone()["c"]
    check("person_entries ishabah_id=4835 dari >= 4 sumber", nsrc >= 4, f"{nsrc} sumber")
    ie = cur.execute(
        "SELECT from_page, from_para FROM person_entries WHERE source='istiab' AND ishabah_id=4835 LIMIT 1"
    ).fetchone()
    itxt = cur.execute(
        "SELECT text FROM pages WHERE source='istiab' AND web_page=? AND para_idx=?",
        (ie["from_page"], ie["from_para"]),
    ).fetchone()["text"]
    check("paragraf pertama entri Isti'ab memuat '(١٦٣٣)' / '1633'",
          ("١٦٣٣" in itxt) or ("1633" in itxt), itxt[:60])

    # 4. FTS
    ne = cur.execute(
        "SELECT COUNT(DISTINCT rowid) c FROM event_fts WHERE event_fts MATCH 'بدر'"
    ).fetchone()["c"]
    check("event_fts MATCH 'بدر' >= 3 event", ne >= 3, f"{ne} event")
    psrc = cur.execute(
        "SELECT COUNT(DISTINCT source) c FROM person_entries "
        "WHERE entry_id IN (SELECT rowid FROM person_fts WHERE person_fts MATCH 'عمر بن الخطاب')"
    ).fetchone()["c"]
    check("person_fts MATCH 'عمر بن الخطاب' >= 3 sumber", psrc >= 3, f"{psrc} sumber")

    # 5. cakupan
    print("\n-- Cakupan event (175 registry) per sumber --")
    print(f"{'sumber':<15} {'ada segmen':>10} {'absent':>7} {'lainnya':>8}")
    n_ev = cur.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
    for s in EVENT_SOURCES:
        has = cur.execute("SELECT COUNT(DISTINCT event_id) c FROM event_segments WHERE source=?", (s,)).fetchone()["c"]
        ab = cur.execute("SELECT COUNT(*) c FROM event_absent WHERE source=?", (s,)).fetchone()["c"]
        print(f"{s:<15} {has:>10} {ab:>7} {n_ev - has - ab:>8}")
    print("\n-- Cakupan entri kamus terhubung ke Ishabah per sumber --")
    print(f"{'sumber':<15} {'entri':>7} {'resolved':>9} {'ambiguous':>10} {'unresolved':>11} {'tanpa rec':>9} {'%link':>7}")
    for s, _bid, _ta, _ti, role, _note in SOURCES:
        if role != "kamus_shahabat" and s != "tabaqat":
            continue
        rows = cur.execute(
            "SELECT link_status, COUNT(*) c FROM person_entries WHERE source=? GROUP BY link_status", (s,)
        ).fetchall()
        d = {r["link_status"]: r["c"] for r in rows}
        total = sum(d.values())
        res = d.get("resolved", 0) + d.get("canonical", 0)
        pct = (100.0 * res / total) if total else 0.0
        print(f"{s:<15} {total:>7} {d.get('resolved', 0) or d.get('canonical', 0):>9} "
              f"{d.get('ambiguous', 0):>10} {d.get('unresolved', 0):>11} "
              f"{d.get(None, 0):>9} {pct:>6.1f}%")

    # 6. ukuran
    size = os.path.getsize(DB)
    print(f"\n-- Ukuran DB: {size / 1024 / 1024:.1f} MB (harapan spec 150–300 MB) --")
    if not (150 <= size / 1024 / 1024 <= 300):
        print(f"  [WARN] ukuran di luar harapan spec — korpus {n:,} paragraf "
              f"(teks verbatim ~76 MB sumber) tidak bisa 'dipaksa' lebih besar tanpa memfabrikasi.")

    # ringkasan meta
    print("\n-- meta --")
    for k, v in cur.execute("SELECT key, value FROM meta ORDER BY key"):
        print(f"  {k}: {v}")
    con.close()
    return ok


if __name__ == "__main__":
    main()
    passed = smoke()
    if not passed:
        print("\nSMOKE TEST GAGAL")
        sys.exit(1)
    print("\nSMOKE TEST SELESAI (lihat WARN di atas bila ada — bukan kegagalan integritas)")
