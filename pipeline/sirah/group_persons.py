#!/usr/bin/env python3
"""Segmentasi deterministik entri biografi (Sumbu B: shahabat).

Implementasi data/GROUPING-B-SPEC.md:
- muat data/pages_full.jsonl sekali (hanya 5 sumber kamus)
- untuk tiap entri sahabat_index.draft.json, temukan paragraf heading awal
  dan batas akhir (paragraf heading entri berikutnya), tanpa memotong teks
- tulis data/person_segments.jsonl + laporan data/person_segments_report.json

Python 3.12+, stdlib saja. Semua open() pakai encoding="utf-8".
"""

import json
import re
import statistics
import time

PAGES_FILE = "data/pages_full.jsonl"
INDEX_FILE = "data/sahabat_index.draft.json"
OUT_FILE = "data/person_segments.jsonl"
REPORT_FILE = "data/person_segments_report.json"

# key sahabat_index -> (source pages_full, book_id toc)
DICTS = {
    "ishabah": ("ishabah", 9767),
    "istiab": ("istiab", 12288),
    "usud_1110": ("usud_ilmiyah", 1110),
    "usud_30018": ("usud_rifai", 30018),
    "tabaqat": ("tabaqat", 1686),
}

# ---------------------------------------------------------------- normalisasi

# tasykil + tatweel yang dihapus pada norm()
_TASHKEEL = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)
_AR_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
                           "0123456789")
# penyamaan hamzah/ta/alef-maqsura HANYA untuk pencocokan nama
_NAME_UNIFY = str.maketrans({"\u0623": "\u0627", "\u0625": "\u0627",
                             "\u0622": "\u0627", "\u0629": "\u0647",
                             "\u0649": "\u064a"})


def norm(s: str) -> str:
    """Hapus tasykil/tatweel, konversi angka Arab-India -> ASCII."""
    return _TASHKEEL.sub("", s).translate(_AR_DIGITS)


def norm_name(s: str) -> str:
    """norm() + samakan hamzah + rapatkan spasi (khusus pencocokan nama)."""
    return re.sub(r"\s+", " ", norm(s).translate(_NAME_UNIFY)).strip()


HEADING_RE = re.compile(r"^\[?\s*\(?\s*(\d+)\s*[-\)\]]\s*(.+)$")

NAME_PREFIX_LEN = 12


def name_prefix(name: str) -> str:
    n = norm_name(name)
    return n[:NAME_PREFIX_LEN] if len(n) >= NAME_PREFIX_LEN else n


# ---------------------------------------------------------------- penyimpanan

class PageStore:
    """Cache paras per (source, web_page) + norm/norm_name yang dihitung lazy."""

    def __init__(self):
        self._paras: dict[tuple[str, int], list[str]] = {}
        self._norms: dict[tuple[str, int], list[str]] = {}
        self._name_norms: dict[tuple[str, int], list[str]] = {}

    def load(self, pages_file: str, sources: set[str]) -> None:
        with open(pages_file, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r["source"] in sources:
                    self._paras[(r["source"], r["web_page"])] = r["paras"]

    def paras(self, src: str, page: int):
        return self._paras.get((src, page))

    def norms(self, src: str, page: int):
        key = (src, page)
        got = self._norms.get(key)
        if got is None:
            got = [norm(p) for p in self._paras.get(key, [])]
            self._norms[key] = got
        return got

    def name_norms(self, src: str, page: int):
        key = (src, page)
        got = self._name_norms.get(key)
        if got is None:
            got = [norm_name(p) for p in self._paras.get(key, [])]
            self._name_norms[key] = got
        return got


# ---------------------------------------------------------------- algoritma

def find_start(store: PageStore, src: str, page: int, num, name: str,
               num_pages_map: dict):
    """Cari paragraf heading awal entri.

    Urutan halaman kandidat: page, page-1, page+1 (koreksi kelas TOC shamela).
    Dalam satu halaman: (1) pola heading + nomor == num persis,
    (2) nomor dalam +-3 asalkan nomor itu BUKAN num entri lain yang berada
        di halaman +-1 (heading milik entri lain tidak boleh direbut),
    lalu (3) nama ter-norm muncul di paragraf.
    Return (start_page, para_start|None, found: bool, basis_hint|None).
    """
    order = [page]
    if page - 1 >= 1:
        order.append(page - 1)
    order.append(page + 1)
    pfx = name_prefix(name)
    for pg in order:
        paras = store.paras(src, pg)
        if not paras:
            continue
        norms = store.norms(src, pg)
        if num is not None:
            # pass 1: nomor persis
            for i, np in enumerate(norms):
                m = HEADING_RE.match(np)
                if m and int(m.group(1)) == num:
                    return pg, i, True, f"heading #{m.group(1)} para {i}"
            # pass 2: nomor +-3 yang bukan milik entri lain di halaman +-1
            for i, np in enumerate(norms):
                m = HEADING_RE.match(np)
                if not m:
                    continue
                cand = int(m.group(1))
                if abs(cand - num) > 3:
                    continue
                owner = num_pages_map.get(cand)
                if owner is not None and owner != num \
                        and abs(owner - pg) <= 1:
                    continue  # heading milik entri cand, jangan direbut
                return pg, i, True, f"heading #{m.group(1)} para {i} (num drift)"
        if pfx:
            nnorms = store.name_norms(src, pg)
            for i, nnp in enumerate(nnorms):
                if pfx in nnp:
                    return pg, i, True, f"name-match para {i}"
    return page, None, False, None


def find_end(store: PageStore, src: str, end_page: int, next_entry,
             num_pages_map: dict):
    """Cari batas akhir: paragraf heading entri berikutnya di halaman end_page.

    Return (last_page, para_end|None, next_heading_found: bool, basis_end).
    - heading next di para 0 -> entri ini berakhir di halaman sebelumnya.
    """
    paras = store.paras(src, end_page)
    if not paras:
        return end_page - 1, None, False, "no page"
    norms = store.norms(src, end_page)
    nnum = next_entry.get("num")
    npfx = name_prefix(next_entry.get("name", ""))

    def finish(i: int, how: str):
        if i == 0:
            return end_page - 1, None, True, f"{how} p{end_page} para 0->prev page"
        return end_page, i, True, f"{how} p{end_page} para {i}"

    def claimable(cand: int) -> bool:
        """Kandidat +-3 sah bila bukan num entri lain di halaman +-1."""
        owner = num_pages_map.get(cand)
        return owner is None or owner == nnum or abs(owner - end_page) > 1

    if nnum is not None:
        for i, np in enumerate(norms):
            m = HEADING_RE.match(np)
            if m and int(m.group(1)) == nnum:
                return finish(i, f"heading #{m.group(1)}")
        for i, np in enumerate(norms):
            m = HEADING_RE.match(np)
            if m:
                cand = int(m.group(1))
                if abs(cand - nnum) <= 3 and claimable(cand):
                    return finish(i, f"heading #{m.group(1)} (num drift)")
    if npfx:
        for i, nnp in enumerate(store.name_norms(src, end_page)):
            if npfx in nnp:
                return finish(i, "name-match")
    # fallback terakhir: heading pertama apa pun yang cocok pola di halaman itu
    for i, np in enumerate(norms):
        if HEADING_RE.match(np):
            return finish(i, "first-pattern")
    return end_page - 1, None, False, "not found"


def process_dict(store: PageStore, key: str, entries: list, toc: list):
    src, book_id = DICTS[key]
    # peta num -> page (draft) untuk mendeteksi heading milik entri lain
    num_pages_map = {}
    for e in entries:
        if e.get("num") is not None:
            num_pages_map[e["num"]] = e["page"]
    out = []
    n = len(entries)
    for pos, e in enumerate(entries):
        toc_e = toc[e["toc_i"]]
        page = e["page"]
        end_excl = toc_e.get("end_excl")
        if end_excl is None:
            end_excl = page + 1

        sp, ps, found, hint = find_start(store, src, page, e.get("num"),
                                         e.get("name", ""), num_pages_map)

        next_e = entries[pos + 1] if pos + 1 < n else None
        if next_e is not None:
            lp, pe, nh_found, end_hint = find_end(store, src, end_excl,
                                                  next_e, num_pages_map)
        else:
            lp, pe, nh_found, end_hint = end_excl - 1, None, False, "last entry"

        n_pages = lp - sp + 1
        label = e.get("num") if e.get("num") is not None else e.get("name", "")
        basis = (f"TOC #{label} p{page}"
                 + (f" + {hint}" if found else "; heading NOT found")
                 + f"; end: {end_hint}")
        out.append({
            "source": src,
            "book_id": book_id,
            "entry_num": e.get("num"),
            "name": e.get("name", ""),
            "toc_i": e["toc_i"],
            "start_page": sp,
            "para_start": ps,
            "last_page": lp,
            "para_end": pe,
            "heading_found": found,
            "next_heading_found": nh_found,
            "n_pages": n_pages,
            "basis": basis,
        })
    return out


# ---------------------------------------------------------------- validator

def summarize(records: list) -> dict:
    n = len(records)
    hf = sum(1 for r in records if r["heading_found"])
    nhf = sum(1 for r in records if r["next_heading_found"])
    corrected = sum(1 for r in records if r["heading_found"]
                    and r["toc_page"] != r["start_page"])
    pages_list = [r["n_pages"] for r in records]
    fails = [{"entry_num": r["entry_num"], "name": r["name"],
              "page": r["toc_page"]} for r in records if not r["heading_found"]]
    return {
        "n_entries": n,
        "heading_found": hf,
        "heading_found_pct": round(100.0 * hf / n, 2) if n else 0.0,
        "next_heading_found": nhf,
        "next_heading_found_pct": round(100.0 * nhf / n, 2) if n else 0.0,
        "start_corrected_pm1": corrected,
        "n_pages_min": min(pages_list),
        "n_pages_median": statistics.median(pages_list),
        "n_pages_max": max(pages_list),
        "failed_examples": fails[:10],
        "n_failed_total": len(fails),
    }


def run_probes(segments: dict, store: PageStore) -> list:
    def rec(key, num):
        for r in segments[key]:
            if r["entry_num"] == num:
                return r
        return None

    probes = []

    r = rec("ishabah", 4835)
    ok = bool(r) and r["start_page"] == 1887 and r["heading_found"]
    probes.append(("Ishabah #4835 start 1887 & heading found",
                   ok, {"start_page": r and r["start_page"],
                        "para_start": r and r["para_start"],
                        "heading_found": r and r["heading_found"]}))

    r = rec("istiab", 1633)
    ok = bool(r) and r["start_page"] == 956 and r["heading_found"]
    probes.append(("Isti'ab #1633 start 956 & heading found",
                   ok, {"start_page": r and r["start_page"],
                        "para_start": r and r["para_start"],
                        "heading_found": r and r["heading_found"]}))

    r = rec("usud_30018", 3064)
    ok = bool(r) and r["start_page"] == 1505 and r["last_page"] in (1530, 1531)
    probes.append(("Usud 30018 #3064 start 1505 & last 1530/1531",
                   ok, {"start_page": r and r["start_page"],
                        "last_page": r and r["last_page"],
                        "para_end": r and r["para_end"]}))

    r = rec("tabaqat", 46)
    ok = bool(r) and r["start_page"] == 803 and r["last_page"] == 838
    if ok:
        # para_end harus menunjuk paragraf heading #47 di halaman 838
        pe = r["para_end"]
        if pe is None:
            ok = False
        else:
            m = HEADING_RE.match(store.norms("tabaqat", 838)[pe])
            ok = bool(m) and int(m.group(1)) == 47
    probes.append(("Tabaqat #46 start 803, last 838, para_end = heading #47",
                   ok, {"start_page": r and r["start_page"],
                        "last_page": r and r["last_page"],
                        "para_end": r and r["para_end"]}))
    return probes


# ---------------------------------------------------------------- main

def main():
    t0 = time.time()
    store = PageStore()
    store.load(PAGES_FILE, {src for src, _ in DICTS.values()})
    print(f"pages loaded: {len(store._paras)} ({time.time()-t0:.1f}s)")

    with open(INDEX_FILE, encoding="utf-8") as f:
        index = json.load(f)

    all_segments = {}
    with open(OUT_FILE, "w", encoding="utf-8") as fout:
        for key, (src, book_id) in DICTS.items():
            with open(f"data/toc/toc_{book_id}.json", encoding="utf-8") as f:
                toc = json.load(f)
            entries = index[key]
            recs = process_dict(store, key, entries, toc)
            # simpan toc_page untuk laporan koreksi
            for r, e in zip(recs, entries):
                r["toc_page"] = e["page"]
            all_segments[key] = recs
            for r in recs:
                r_out = {k: v for k, v in r.items() if k != "toc_page"}
                fout.write(json.dumps(r_out, ensure_ascii=False) + "\n")
            hf = sum(1 for r in recs if r["heading_found"])
            print(f"{key}: {len(recs)} entries, heading_found {hf} "
                  f"({100.0*hf/len(recs):.1f}%) [{time.time()-t0:.1f}s]")

    # ---- validator
    report = {"per_dict": {k: summarize(v) for k, v in all_segments.items()},
              "probes": []}

    probes = run_probes(all_segments, store)
    report["probes"] = [{"probe": p, "pass": ok, "detail": d}
                        for p, ok, d in probes]

    target_ok = all(v["heading_found_pct"] >= 95.0
                    for v in report["per_dict"].values())
    report["target_heading_found_95"] = target_ok

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ---- cetak ringkasan
    print("\n" + "=" * 72)
    print("RINGKASAN VALIDATOR — data/person_segments_report.json")
    print("=" * 72)
    print(f"{'dict':<12}{'n':>7}{'head%':>8}{'next%':>8}{'korr±1':>8}"
          f"{'min':>5}{'median':>8}{'max':>6}{'fail':>6}")
    for k, v in report["per_dict"].items():
        print(f"{k:<12}{v['n_entries']:>7}{v['heading_found_pct']:>8.2f}"
              f"{v['next_heading_found_pct']:>8.2f}{v['start_corrected_pm1']:>8}"
              f"{v['n_pages_min']:>5}{v['n_pages_median']:>8}"
              f"{v['n_pages_max']:>6}{v['n_failed_total']:>6}")
    print("-" * 72)
    for p, ok, d in probes:
        print(f"[{'LULUS' if ok else 'GAGAL'}] {p} -> {d}")
    print("-" * 72)
    print(f"Target heading_found >= 95% tiap kamus: "
          f"{'TERCAPAI' if target_ok else 'BELUM'}")
    if not target_ok:
        print("Contoh gagal per kamus:")
        for k, v in report["per_dict"].items():
            if v["heading_found_pct"] < 95.0:
                print(f"  {k}:")
                for ex in v["failed_examples"]:
                    print(f"    num={ex['entry_num']} page={ex['page']} "
                          f"name={ex['name'][:50]}")
    print(f"\nSelesai dalam {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
