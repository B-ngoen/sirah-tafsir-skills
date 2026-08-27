# -*- coding: utf-8 -*-
"""Parse cached HTML shamela (10 kitab sirah/shahabat) -> data/pages_full.jsonl

Optimasi untuk 22-core CPU:
- Process pool = CPU count - 1
- Batch processing per file
- Minimal data transfer between processes

Usage:
    python parse_mp.py [n_workers]
    Default n_workers = os.cpu_count() - 1
"""
import json, pathlib, re, sys
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
from functools import partial

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "cache"  # pc_local/cache (konvensi tunggal, lihat sync_vps_to_pc.sh)
OUT = ROOT / "data" / "pages_full.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

BOOKS = {
    "23833": ("hisyam_saqqa", "سيرة ابن هشام ت السقا"),
    "7450":  ("hisyam_thaha", "سيرة ابن هشام ت طه عبد الرؤوف"),
    "9862":  ("ibn_ishaq", "سيرة ابن إسحاق"),
    "1686":  ("tabaqat", "الطبقات الكبرى ط العلمية"),
    "7666":  ("tabaqat_tabiin", "الطبقات الكبرى متمم التابعين"),
    "9783":  ("tarikh_tabari", "تاريخ الطبري"),
    "9767":  ("ishabah", "الإصابة في تمييز الصحابة"),
    "1110":  ("usud_ilmiyah", "أسد الغابة ط العلمية"),
    "30018": ("usud_rifai", "أسد الغابة ت الرفاعي"),
    "12288": ("istiab", "الاستيعاب ت البجاوي"),
}

TITLE_RE = re.compile(r"ج(\d+)\s*-\s*ص(\d+)")


def parse_shamela(book_id, fp: pathlib.Path):
    """Parse single shamela HTML file."""
    try:
        soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        nass = soup.find("div", class_="nass")
        if nass is None:
            return None
        title = soup.title.get_text() if soup.title else ""
        m = TITLE_RE.search(title)
        juz = int(m.group(1)) if m else None
        # strip copy-buttons; keep verbatim text per paragraph
        for a in nass.find_all("a", class_="btn_tag"):
            a.decompose()
        paras = []
        for p in nass.find_all("p"):
            t = p.get_text(" ", strip=True)
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                paras.append(t)
        return {
            "source": BOOKS[book_id][0],
            "book_id": book_id,
            "web_page": int(fp.stem),
            "printed_juz": juz,
            "printed_page": int(nass.get("data-page-num") or 0) or None,
            "url": f"https://shamela.ws/book/{book_id}/{fp.stem}",
            "paras": paras,
        }
    except Exception as e:
        print(f"ERROR parsing {fp}: {e}", file=sys.stderr)
        return None


def parse_dorar(fp: pathlib.Path):
    """Parse single dorar HTML file."""
    try:
        soup = BeautifulSoup(fp.read_text(encoding="utf-8"), "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        art = soup.find("article") or soup
        paras = []
        for p in art.find_all("p"):
            t = p.get_text(" ", strip=True)
            t = re.sub(r"\s+", " ", t).strip()
            if t and "ALDORAR" not in t and "copyright" not in t.lower():
                paras.append(t)
        return {
            "source": "dorar_en",
            "book_id": "dorar",
            "web_page": int(fp.stem),
            "title": title,
            "url": f"https://dorar.net/en/tafseer/{fp.stem}",
            "paras": paras,
        }
    except Exception as e:
        print(f"ERROR parsing {fp}: {e}", file=sys.stderr)
        return None


def parse_file(task):
    """Worker function: parse single file. task = (type, book_id_or_none, fp)."""
    ftype, bid, fp = task
    if ftype == "shamela":
        rec = parse_shamela(bid, fp)
    elif ftype == "dorar":
        rec = parse_dorar(fp)
    else:
        return None
    if rec:
        return json.dumps(rec, ensure_ascii=False)
    return None


def main():
    import time
    t0 = time.time()

    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else (cpu_count() - 1)
    print(f"Using {n_workers} workers (CPU count: {cpu_count()})")

    # Build task list
    tasks = []
    for d in sorted(CACHE.glob("shamela_*")):
        bid = d.name.split("_")[1]
        for fp in sorted(d.glob("*.html"), key=lambda p: int(p.stem)):
            tasks.append(("shamela", bid, fp))

    dorar_dir = CACHE / "dorar"
    if dorar_dir.exists():
        for fp in sorted(dorar_dir.glob("*.html"), key=lambda p: int(p.stem)):
            tasks.append(("dorar", None, fp))

    print(f"Total files to parse: {len(tasks)}")

    # Process pool
    n = 0
    with Pool(n_workers) as pool:
        with OUT.open("w", encoding="utf-8") as w:
            for result in pool.imap(parse_file, tasks, chunksize=50):
                if result:
                    w.write(result + "\n")
                    n += 1
                if n % 1000 == 0:
                    elapsed = time.time() - t0
                    rate = n / elapsed if elapsed > 0 else 0
                    print(f"Progress: {n}/{len(tasks)} ({rate:.1f} files/s)")

    elapsed = time.time() - t0
    print(f"Done: {n} records written in {elapsed:.1f}s ({n/elapsed:.1f} files/s)")
    print(f"Output: {OUT} ({OUT.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()