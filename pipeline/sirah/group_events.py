#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A3 — Segmen peristiwa Sumbu A dari peta heading -> data/event_segments.jsonl

Input : data/headings_a.jsonl  (A1)
        peta heading (argumen 1; default data/event_heading_map.json) hasil tahap A2
        data/events_registry.draft.json
        data/pages_full.jsonl (teks untuk validator)
        data/toc/toc_9783.json (segmen TAHUN Thabari)

Aturan segmen: heading ter-map dikelompokkan per (source, event_id); heading berurutan
(page berikut <= end_excl heading sebelumnya) membentuk satu segmen. Batas bawah:
last_page = end_excl bila heading pemotong di halaman itu ketemu pada para > 0,
selain itu last_page = end_excl - 1. Event tanpa heading ter-map -> record ABSEN.
Thabari tambahan: segmen TAHUN otomatis dari entri TOC «سنة ...» (cakupan sirah
880-2623), tahun 1-40 H dikonversi dari angka kata Arab.

Pemakaian: python group_events.py [path_peta]
"""
import json
import pathlib
import sys

from headings_a import mkey, find_para, para_matches

BASE = pathlib.Path(__file__).resolve().parent
DATA = BASE / "data"
HEADINGS_FP = DATA / "headings_a.jsonl"
REGISTRY_FP = DATA / "events_registry.draft.json"
PAGES_FP = DATA / "pages_full.jsonl"
OUT_FP = DATA / "event_segments.jsonl"
TOC_TABARI_FP = DATA / "toc" / "toc_9783.json"

AXIS_SOURCES = ["hisyam_saqqa", "hisyam_thaha", "ibn_ishaq", "tabaqat", "tarikh_tabari"]
TABARI_MIN, TABARI_MAX_EXCL = 880, 2623  # cakupan sirah: s.d. sebelum «سنة إحدى وأربعين»

# --- konversi judul tahun Thabari («سنة أربعين» dst.) ke bilangan
# kunci kata = bentuk mkey (ى->ي, ة->ه, أ->ا)
UNITS = {"واحده": 1, "احدي": 1, "اثنتين": 2, "اثنتي": 2, "اثنين": 2, "ثلاث": 3,
         "اربع": 4, "خمس": 5, "ست": 6, "سبع": 7, "ثمان": 8, "ثماني": 8, "تسع": 9,
         "عشر": 10}
TENS = {"عشرين": 20, "ثلاثين": 30, "اربعين": 40}


def year_of_title(title):
    """«سنه اثنتى عشره من الهجره» -> 12; gagal -> None (cukup s.d. 40 H)."""
    words = mkey(title).split()
    # bentuk tahun 1–3 H: «ذكر ما كان … في اول سنه من الهجره», «السنه الثانيه من الهجره», «السنه الثالثه من الهجره»
    ORD = {"الاولي": 1, "الثانيه": 2, "الثالثه": 3, "الرابعه": 4, "الخامسه": 5, "السادسه": 6,
           "السابعه": 7, "الثامنه": 8, "التاسعه": 9, "العاشره": 10}
    if "السنه" in words:
        j = words.index("السنه")
        if j + 1 < len(words) and words[j + 1] in ORD and "الهجره" in words:
            return ORD[words[j + 1]]
    if "اول" in words and "سنه" in words and "الهجره" in words and words[0] != "سنه":
        return 1
    if not words or words[0] != "سنه":
        return None
    val, i = 0, 1
    while i < len(words):
        w = words[i]
        if w == "و":
            i += 1
            continue
        if len(w) > 1 and w.startswith("و"):  # "وعشرين" = و + عشرين menempel
            w = w[1:]
        if w in UNITS:
            val += UNITS[w]
            i += 1
            if i < len(words) and words[i] == "عشره":
                val += 10
                i += 1
        elif w in TENS:
            val += TENS[w]
            i += 1
        else:
            break
    return val if 1 <= val <= 40 else None


# ---------------------------------------------------------------- pemuatan
def load_headings():
    by_src = {s: [] for s in AXIS_SOURCES}
    with HEADINGS_FP.open(encoding="utf-8") as f:
        for line in f:
            h = json.loads(line)
            if h["source"] in by_src:
                by_src[h["source"]].append(h)
    # urutan dokumen: halaman, lalu para (yang tak ketemu ditaruh belakang)
    for s in by_src:
        by_src[s].sort(key=lambda h: (h["page"], h["para_idx"] is None,
                                      h["para_idx"] if h["para_idx"] is not None else 0))
    return by_src


def load_pages():
    out = {}
    with PAGES_FP.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["source"] in AXIS_SOURCES:
                out[(r["source"], r["web_page"])] = r
    return out


def load_map(fp):
    entries = json.loads(pathlib.Path(fp).read_text(encoding="utf-8"))
    return {e["hid"]: e for e in entries}


# ---------------------------------------------------------------- batas segmen
def segment_tail(source_heads, group_hids, end_excl, max_page):
    """Return (last_page, para_end) untuk batas segmen.

    Halaman end_excl masih memuat ekor bab sebelumnya: bila heading pemotong di
    halaman itu ketemu pada para_idx > 0 -> last_page=end_excl, para_end=para_idx
    (eksklusif); bila di para 0 / tak ketemu -> last_page=end_excl-1, para_end=None.
    """
    if end_excl is None:
        return max_page, None
    cands = [h for h in source_heads
             if h["page"] == end_excl and h["hid"] not in group_hids
             and h["para_idx"] is not None]
    if cands:
        best = min(cands, key=lambda h: h["para_idx"])
        if best["para_idx"] > 0:
            return end_excl, best["para_idx"]
    return end_excl - 1, None


# ---------------------------------------------------------------- segmen event
def build_segments(by_src, hmap, registry):
    segs, absent = [], []
    year_by_event = {e["id"]: e.get("year_h") for e in registry}

    for source in AXIS_SOURCES:
        heads = by_src[source]
        max_page = max((h["page"] for h in heads), default=0)
        # kelompok heading ter-map per event (pertahankan urutan dokumen)
        groups = {}
        for h in heads:
            e = hmap.get(h["hid"])
            if e and e.get("event_id"):
                groups.setdefault(e["event_id"], []).append(h)
                if e["event_id"] not in year_by_event:
                    print(f"  PERINGATAN: event_id tak dikenal {e['event_id']} ({h['hid']})")

        for event_id in sorted(groups):
            hs = groups[event_id]
            # pecah menjadi segmen heading berkelanjutan
            runs, cur = [], [hs[0]]
            for h in hs[1:]:
                if h["page"] <= cur[-1]["end_excl"]:
                    cur.append(h)
                else:
                    runs.append(cur)
                    cur = [h]
            runs.append(cur)
            for run in runs:
                hids = {h["hid"] for h in run}
                last_page, para_end = segment_tail(heads, hids, run[-1]["end_excl"], max_page)
                segs.append({
                    "source": source,
                    "book_id": run[0]["book_id"],
                    "event_id": event_id,
                    "year_h": year_by_event.get(event_id),
                    "start_page": run[0]["page"],
                    "para_start": run[0]["para_idx"],
                    "last_page": last_page,
                    "para_end": para_end,
                    "n_pages": last_page - run[0]["page"] + 1,
                    "heading_ids": [h["hid"] for h in run],
                    "basis": f"{len(run)} heading: {run[0]['title'][:60]}",
                })

        # kejujuran ketiadaan sumber: record ABSEN
        for event_id in sorted(year_by_event):
            if event_id not in groups:
                absent.append({"source": source, "event_id": event_id, "absent": True})
    return segs, absent


# ---------------------------------------------------------------- segmen tahun Thabari
def build_year_segments(by_src, pages):
    toc = json.loads(TOC_TABARI_FP.read_text(encoding="utf-8"))
    heads = by_src["tarikh_tabari"]
    max_page = max((h["page"] for h in heads), default=0)
    all_hids = {h["hid"] for h in heads}
    segs = []
    for e in toc:
        if not (TABARI_MIN <= e["page"] < TABARI_MAX_EXCL):
            continue
        k = mkey(e["title"])
        if not (k.startswith("سنه") or k.startswith("سنة") or year_of_title(e["title"]) is not None):
            continue
        if e["depth"] > 2:  # tahun selalu depth 1–2; hindari sub-bab berjudul «سنة» di dalam tahun
            continue
        rec = pages.get(("tarikh_tabari", e["page"]))
        para_start = find_para(rec["paras"], k) if rec else None
        last_page, para_end = segment_tail(heads, set(), e["end_excl"], max_page)
        segs.append({
            "source": "tarikh_tabari",
            "year_seg": True,
            "year_title": e["title"].strip(),
            "year_h": year_of_title(e["title"]),
            "start_page": e["page"],
            "last_page": last_page,
            "para_start": para_start,
            "para_end": para_end,
        })
    return segs


# ---------------------------------------------------------------- validator
def validate(segs, absent, year_segs, pages):
    ok = True
    print("== segmen per sumber ==")
    for s in AXIS_SOURCES:
        n = sum(1 for x in segs if x["source"] == s)
        print(f"  {s:14s} segmen={n}  ABSEN={sum(1 for x in absent if x['source'] == s)}")
    print(f"  year_seg Thabari = {len(year_segs)} (harapan ±40 utk 1-40 H)")
    known = [y for y in year_segs if y["year_h"] is not None]
    print(f"    tahun terkonversi: {len(known)}; contoh: " +
          ", ".join(f"{y['year_h']}H@{y['start_page']}" for y in known[:6]))

    print("== contoh segmen (100 karakter pertama paragraf para_start) ==")
    shown = 0
    for x in segs:
        if x["para_start"] is None or shown >= 5:
            continue
        rec = pages.get((x["source"], x["start_page"]))
        if not rec:
            continue
        txt = rec["paras"][x["para_start"]][:100]
        print(f"  [{x['source']}:{x['event_id']} hal {x['start_page']}-{x['last_page']}] {txt}")
        shown += 1

    print("== probe Badr ==")
    badr = [x for x in segs if x["event_id"] == "ghazwah_badr_kubra"]
    for x in badr:
        print(f"  {x['source']:14s} hal {x['start_page']}-{x['last_page']} "
              f"(para {x['para_start']}..{x['para_end']}, {x['n_pages']} hal)")
    checks = []
    tab = [x for x in badr if x["source"] == "tarikh_tabari"]
    checks.append(("tabari 1046 s.d. ±1104", tab and tab[0]["start_page"] == 1046
                   and 1100 <= tab[0]["last_page"] <= 1105))
    tbq = [x for x in badr if x["source"] == "tabaqat"]
    checks.append(("tabaqat 397-409", tbq and tbq[0]["start_page"] == 397
                   and 407 <= tbq[0]["last_page"] <= 409))
    sq = [x for x in badr if x["source"] == "hisyam_saqqa"]
    checks.append(("hisyam_saqqa mulai 629/630", sq and sq[0]["start_page"] in (629, 630)))
    th = [x for x in badr if x["source"] == "hisyam_thaha"]
    checks.append(("hisyam_thaha mulai 486", th and th[0]["start_page"] == 486))
    ii = [x for x in badr if x["source"] == "ibn_ishaq"]
    checks.append(("ibn_ishaq ada segmen", bool(ii)))
    for name, passed in checks:
        print(f"  {'OK ' if passed else 'GAGAL'} {name}")
        ok &= bool(passed)
    checks_year = 30 <= len(year_segs) <= 50
    print(f"  {'OK ' if checks_year else 'GAGAL'} jumlah year_seg dalam 30-50")
    ok &= checks_year
    return ok


def main():
    map_fp = sys.argv[1] if len(sys.argv) > 1 else DATA / "event_heading_map.json"
    hmap = load_map(map_fp)
    registry = json.loads(REGISTRY_FP.read_text(encoding="utf-8"))
    by_src = load_headings()

    segs, absent = build_segments(by_src, hmap, registry)
    pages = load_pages()
    year_segs = build_year_segments(by_src, pages)

    with OUT_FP.open("w", encoding="utf-8") as f:
        for x in segs + absent + year_segs:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"peta: {map_fp}")
    print(f"-> {OUT_FP.name}: {len(segs)} segmen, {len(absent)} ABSEN, "
          f"{len(year_segs)} year_seg")

    ok = validate(segs, absent, year_segs, pages)
    print("VALIDATOR:", "LOLOS" if ok else "GAGAL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
