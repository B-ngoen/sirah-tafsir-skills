#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A1 — Kandidat heading Sumbu A (peristiwa/tahun) -> data/headings_a.jsonl

Sumber sumbu A dan cakupan halaman (web_page):
  hisyam_saqqa    23833  seluruh, TOC depth 0-1
  hisyam_thaha    7450   seluruh (589 hal), heading PARAGRAF (TOC hanya 6 entri)
  ibn_ishaq       9862   seluruh, TOC depth 1
  tabaqat         1686   hal < 687 (bagian sirah, sebelum «الصحابة»), TOC depth 1-2
  tarikh_tabari   9783   880 <= hal < 2623 (مولد النبي s.d. سنة أربعين), TOC depth 2-4

Output per heading: {"hid","source","book_id","page","para_idx","title","title_norm",
                     "depth","end_excl","kind":"toc"|"para"}
+ data/headings_a_report.json (validator) + data/headings_a_for_llm/{source}[_NN].txt (tahap A2).
"""
import json
import pathlib
import random
import re
import sys
from collections import defaultdict

BASE = pathlib.Path(__file__).resolve().parent
DATA = BASE / "data"
PAGES_FP = DATA / "pages_full.jsonl"
OUT_FP = DATA / "headings_a.jsonl"
REPORT_FP = DATA / "headings_a_report.json"
FOR_LLM_DIR = DATA / "headings_a_for_llm"

# source -> (book_id, depths | None=aturan paragraf, (min_page, max_page_excl) | None)
SOURCES = {
    "hisyam_saqqa":  ("23833", {0, 1}, None),
    "hisyam_thaha":  ("7450", None, None),
    "ibn_ishaq":     ("9862", {1}, None),
    "tabaqat":       ("1686", {1, 2}, (1, 687)),     # «الصحابة» mulai hal 687
    "tarikh_tabari": ("9783", {2, 3, 4}, (880, 2623)),  # s.d. sebelum «سنة إحدى وأربعين»
}

TOC_DIR = DATA / "toc"

# Aturan heading paragraf hisyam_thaha
THAHA_KEY_WORDS = {
    "غزوة", "سرية", "أمر", "حديث", "ذكر", "شأن", "قصة", "خبر", "إسلام", "هجرة",
    "وفاة", "مقتل", "بعث", "عمرة", "حجة", "بيعة", "فتح", "يوم",
}
THAHA_MAX_LEN = 60
SYAIR_MARK = re.compile(r"\s\.\.\.\s")
FOOTNOTE_START = re.compile(r"^\(?[0-9٠-٩]+\)")

# ---------------------------------------------------------------- normalisasi
TASHKEEL = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
# tanda baca + kurung + ligatur hiasan yang dibuang saat MENCOCOKKAN (bukan di title_norm)
MATCH_STRIP = re.compile(r"[\(\)\[\]«»\{\}:،؛.,!؟?\-–—_ـ\uFD3E\uFD3F\uFDF0-\uFDFF]")


def norm(s):
    """Normalisasi dasar: hapus tasykil/tatweel, angka Arab-India -> 0-9, rapatkan spasi."""
    s = TASHKEEL.sub("", s)
    s = s.translate(AR_DIGITS)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def mkey(s):
    """Kunci pencocokan: norm + أإآ->ا, ة->ه, ى->ي; buang tanda baca/angka catatan."""
    s = MATCH_STRIP.sub(" ", norm(s))
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ة", "ه").replace("ى", "ي")
    s = re.sub(r"[0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------- memuat data
def load_pages(want_sources):
    out = {}
    with PAGES_FP.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["source"] in want_sources:
                out[(r["source"], r["web_page"])] = r
    return out


# ---------------------------------------------------------------- matcher para
def para_matches(pkey, tkey):
    """Cocok bila awalan setelah kunci sepakat >= 15 karakter (atau seluruh judul bila lebih pendek)."""
    k = min(len(tkey), 15)
    if k == 0:
        return False
    return pkey[:k] == tkey[:k]


def find_para(paras, tkey, start=0):
    for i in range(start, len(paras)):
        pkey = mkey(paras[i])
        if pkey and para_matches(pkey, tkey):
            return i
    return None


def locate_heading(pages, source, page, tkey, last_on_page):
    """Cari para_idx di page, lalu page-1, page+1. Return (page, para_idx) atau (page, None)."""
    for cand in (page, page - 1, page + 1):
        rec = pages.get((source, cand))
        if not rec:
            continue
        start = 0
        if cand == page and last_on_page is not None:
            start = last_on_page + 1  # jaga urutan dokumen bila beberapa entri TOC sehalaman
        idx = find_para(rec["paras"], tkey, start)
        if idx is None and start > 0:
            idx = find_para(rec["paras"], tkey, 0)  # fallback tanpa konstrain monotonic
        if idx is not None:
            return cand, idx
    return page, None


# ---------------------------------------------------------------- sumber ber-TOC
def collect_toc(source, book_id, depths, page_range, pages):
    toc = json.loads((TOC_DIR / f"toc_{book_id}.json").read_text(encoding="utf-8"))
    lo, hi = page_range if page_range else (None, None)
    heads = []
    last_by_page = {}  # page -> para_idx terakhir yang ketemu (urutan TOC = urutan dokumen)
    for e in toc:
        if e["depth"] not in depths:
            continue
        if lo is not None and e["page"] < lo:
            continue
        if hi is not None and e["page"] >= hi:
            continue
        tkey = mkey(e["title"])
        page, idx = locate_heading(pages, source, e["page"], tkey, last_by_page.get(e["page"]))
        if idx is not None:
            last_by_page[page] = idx
        heads.append({
            "source": source, "book_id": book_id, "page": page, "para_idx": idx,
            "title": e["title"].strip(), "title_norm": norm(e["title"]),
            "depth": e["depth"], "end_excl": e["end_excl"], "kind": "toc",
        })
    return heads


# ---------------------------------------------------------------- hisyam_thaha
def collect_thaha(pages, source="hisyam_thaha", book_id="7450"):
    max_page = max(p for (s, p) in pages if s == source)
    cands = []  # (page, para_idx, depth, title)
    for page in sorted(p for (s, p) in pages if s == source):
        for i, para in enumerate(pages[(source, page)]["paras"]):
            n = norm(para)
            if not n:
                continue
            starts_kw = bool(n.split()) and n.split()[0] in THAHA_KEY_WORDS
            # teks heading: paragraf berawalan kata kunci sering judul + isi menyatu
            # dalam satu paragraf (judul di depan ":") -> potong di ":" pertama.
            if starts_kw and ":" in para:
                head_txt = para.split(":", 1)[0].strip()
                n_head = norm(head_txt)
            else:
                head_txt, n_head = para.strip(), n
            if not n_head or len(n_head) > THAHA_MAX_LEN:
                continue
            if SYAIR_MARK.search(para):
                continue
            if FOOTNOTE_START.match(para):
                continue
            ends_colon = n.endswith(":")
            if not (ends_colon or starts_kw):
                continue
            depth = 0 if starts_kw else 1
            cands.append((page, i, depth, head_txt))
    # end_excl = halaman kandidat berikutnya se-depth-atau-lebih-dangkal
    heads = []
    for j, (page, para_idx, depth, title) in enumerate(cands):
        end = None
        for k in range(j + 1, len(cands)):
            if cands[k][2] <= depth:
                end = cands[k][0]
                break
        if end is None:
            end = max_page + 1
        heads.append({
            "source": source, "book_id": book_id, "page": page, "para_idx": para_idx,
            "title": title, "title_norm": norm(title),
            "depth": depth, "end_excl": end, "kind": "para",
        })
    return heads


# ---------------------------------------------------------------- probe
PROBES = [
    # (source, page, substring pada title)
    ("hisyam_saqqa", 629, "بدر الكبرى"),
    ("hisyam_thaha", 486, "بدر الكبرى"),
    ("tarikh_tabari", 1046, "بدر"),
    ("tabaqat", 397, "غزوة بدر"),
    ("ibn_ishaq", 122, "بدر"),
]


def run_probes(all_heads):
    res = {}
    ok = True
    for source, page, needle in PROBES:
        hit = [h for h in all_heads
               if h["source"] == source and h["page"] == page and needle in h["title"]]
        res[f"{source}@{page}:{needle}"] = bool(hit)
        ok &= bool(hit)
    return res, ok


# ---------------------------------------------------------------- tulis output
def write_for_llm(all_heads):
    FOR_LLM_DIR.mkdir(parents=True, exist_ok=True)
    for fp in FOR_LLM_DIR.glob("*.txt"):
        fp.unlink()
    by_src = defaultdict(list)
    for h in all_heads:
        by_src[h["source"]].append(h)
    n_files = {}
    for source, heads in by_src.items():
        lines = [f"{h['hid']}\t{h['page']}\t{h['depth']}\t{h['title']}" for h in heads]
        if len(lines) <= 400:
            fps = [FOR_LLM_DIR / f"{source}.txt"]
        else:
            fps = [FOR_LLM_DIR / f"{source}_{i:02d}.txt"
                   for i in range(1, (len(lines) + 399) // 400 + 1)]
        for i, fp in enumerate(fps):
            fp.write_text("\n".join(lines[i * 400:(i + 1) * 400]) + "\n", encoding="utf-8")
        n_files[source] = [fp.name for fp in fps]
    return n_files


def main():
    sources_axis = set(SOURCES)
    pages = load_pages(sources_axis)

    all_heads = []
    for source, (book_id, depths, page_range) in SOURCES.items():
        if depths is None:
            heads = collect_thaha(pages, source, book_id)
        else:
            heads = collect_toc(source, book_id, depths, page_range, pages)
        for n, h in enumerate(heads, 1):
            h["hid"] = f"{source}:{n}"
        all_heads.extend(heads)
        print(f"{source:14s} kind={'para' if depths is None else 'toc ':<4} n={len(heads)}")

    with OUT_FP.open("w", encoding="utf-8") as f:
        for h in all_heads:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    # ---- validator
    report = {"sources": {}, "probes": {}}
    ok = True
    random.seed(42)
    for source, (book_id, depths, page_range) in SOURCES.items():
        heads = [h for h in all_heads if h["source"] == source]
        info = {"n": len(heads), "kind": "para" if depths is None else "toc"}
        if depths is None:
            d0 = [h for h in heads if h["depth"] == 0]
            info["n_depth0"] = len(d0)
            info["n_depth1"] = len(heads) - len(d0)
            info["harapan_depth0"] = "100-300"
            ok &= 100 <= len(d0) <= 300
            info["depth0_ok"] = 100 <= len(d0) <= 300
            info["contoh_depth0"] = random.sample(d0, min(20, len(d0)))
            print(f"  {source}: depth0={len(d0)} depth1={info['n_depth1']} (harapan depth0 100-300)")
        else:
            found = sum(1 for h in heads if h["para_idx"] is not None)
            pct = 100.0 * found / len(heads) if heads else 0.0
            info["found"] = found
            info["pct_found"] = round(pct, 1)
            info["target_pct"] = 90
            info["pct_ok"] = pct >= 90
            ok &= pct >= 90
            print(f"  {source}: para_idx ketemu {found}/{len(heads)} = {pct:.1f}% (target >= 90%)")
        report["sources"][source] = info

    report["probes"], probes_ok = run_probes(all_heads)
    ok &= probes_ok
    for k, v in report["probes"].items():
        print(f"  probe {k}: {'OK' if v else 'GAGAL'}")

    report["for_llm_files"] = write_for_llm(all_heads)
    report["ok"] = ok
    REPORT_FP.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {OUT_FP.name}: {len(all_heads)} heading; laporan: {REPORT_FP.name}; "
          f"for-LLM: {sum(len(v) for v in report['for_llm_files'].values())} file")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
