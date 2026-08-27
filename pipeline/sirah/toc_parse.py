#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse فهرس الموضوعات (div.betaka-index, nested <ul><li>) dari HTML indeks shamela
di ../recon/shamela_{id}.html -> data/toc/toc_{id}.json

Tiap entri: {"i": urutan, "page": halaman web, "title": teks, "depth": kedalaman,
             "parent": indeks entri induk atau null, "end_excl": halaman entri berikutnya
             pada level manapun (batas atas eksklusif, heuristik)}
"""
import json, pathlib, re, sys
from bs4 import BeautifulSoup

BASE = pathlib.Path(__file__).resolve().parent
RECON = BASE.parent / "recon"
OUT = BASE / "data" / "toc"
OUT.mkdir(parents=True, exist_ok=True)

BOOKS = ["23833", "7450", "9862", "1686", "7666", "9783", "9767", "1110", "30018", "12288"]


def walk(ul, bid, depth, parent, acc):
    for li in ul.find_all("li", recursive=False):
        a = None
        for cand in li.find_all("a", recursive=False):
            href = cand.get("href", "")
            if f"/book/{bid}/" in href:
                a = cand
                break
        if a is None:
            continue
        m = re.search(rf"/book/{bid}/(\d+)", a["href"])
        page = int(m.group(1))
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        idx = len(acc)
        acc.append({"i": idx, "page": page, "title": title, "depth": depth, "parent": parent})
        for sub in li.find_all("ul", recursive=False):
            walk(sub, bid, depth + 1, idx, acc)


def parse_book(bid):
    fp = RECON / f"shamela_{bid}.html"
    soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
    idx = soup.find("div", class_="betaka-index")
    if idx is None:
        print(f"{bid}: betaka-index tidak ada", file=sys.stderr)
        return []
    top = idx.find("ul")
    acc = []
    walk(top, bid, 0, None, acc)
    # end_excl = halaman entri berikutnya dengan depth <= depth entri (sub-judul entri TIDAK memotong);
    # end_any = entri berikutnya di kedalaman manapun (untuk sub-bab). Fallback None.
    for k, e in enumerate(acc):
        e["end_excl"] = None
        e["end_any"] = None
        for nxt in acc[k + 1:]:
            if nxt["page"] > e["page"]:
                if e["end_any"] is None:
                    e["end_any"] = nxt["page"]
                if nxt["depth"] <= e["depth"]:
                    e["end_excl"] = nxt["page"]
                    break
    return acc


def main():
    summary = {}
    for bid in BOOKS:
        acc = parse_book(bid)
        (OUT / f"toc_{bid}.json").write_text(json.dumps(acc, ensure_ascii=False, indent=0), encoding="utf-8")
        depths = {}
        for e in acc:
            depths[e["depth"]] = depths.get(e["depth"], 0) + 1
        summary[bid] = {"entries": len(acc), "max_page": max((e["page"] for e in acc), default=0), "by_depth": depths}
        print(bid, summary[bid])
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
