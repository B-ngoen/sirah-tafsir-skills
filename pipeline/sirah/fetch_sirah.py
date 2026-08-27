#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checkpointed fetcher shamela.ws untuk proyek Sirah & Shahabat (10 kitab).

Cache = checkpoint: cache/shamela_{book_id}/{page}.html — file yang sudah ada
dilewati, aman di-kill/resume kapan saja. Partisi PER BUKU antar host:
  SIRAH_PARTITION=vps2  -> 9767, 9783, 23833, 7450, 9862   (~13.1rb halaman)
  SIRAH_PARTITION=vps1  -> 1686, 1110, 30018, 12288, 7666  (~13.0rb halaman)
  SIRAH_PARTITION=all   -> semua (untuk run lokal / pilot)
Opsional: SIRAH_BOOKS="23833,9767" membatasi buku; SIRAH_PAGES="23833:400-520"
membatasi rentang halaman (pilot).
Selesai -> data/fetch_done_{partition}.flag
"""
import json, os, pathlib, random, time
import requests

BASE = pathlib.Path(__file__).resolve().parent
CACHE = BASE / "cache"
DATA = BASE / "data"
LOGS = BASE / "logs"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DELAY_MIN, DELAY_MAX = 1.0, 2.5
MAX_RUNTIME = int(os.environ.get("SIRAH_MAX_RUNTIME", "14400"))
PARTITION = os.environ.get("SIRAH_PARTITION", "all")

# key -> (book_id, halaman web maksimum menurut indeks shamela, recon 2026-08-18)
BOOKS = {
    "hisyam_saqqa":   ("23833", 1403),
    "hisyam_thaha":   ("7450",   589),
    "ibn_ishaq":      ("9862",   287),
    "tabaqat":        ("1686",  3026),
    "tabaqat_tabiin": ("7666",   472),
    "tarikh_tabari":  ("9783",  6430),
    "ishabah":        ("9767",  4405),
    "usud_ilmiyah":   ("1110",  3698),
    "usud_rifai":     ("30018", 3855),
    "istiab":         ("12288", 1958),
}

SPLIT = {
    "vps2": ["ishabah", "tarikh_tabari", "hisyam_saqqa", "hisyam_thaha", "ibn_ishaq"],
    "vps1": ["tabaqat", "usud_ilmiyah", "usud_rifai", "istiab", "tabaqat_tabiin"],
    "all": list(BOOKS),
}


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOGS / "fetch_sirah.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_cached(dest: pathlib.Path):
    return dest.exists() and dest.stat().st_size > 1000


def fetch(session, url, dest: pathlib.Path, retries=3):
    if is_cached(dest):
        return "cached"
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200 and len(r.text) > 1000 and 'class="nass"' in r.text:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(r.text, encoding="utf-8")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                return "ok"
            elif r.status_code == 429:
                wait = 60 * (attempt + 1)
                log(f"429 backoff {wait}s: {url}")
                time.sleep(wait)
            elif r.status_code == 404:
                return "404"
            else:
                log(f"status {r.status_code} attempt {attempt+1}: {url}")
                time.sleep(5 + attempt * 10)
        except requests.RequestException as e:
            log(f"retry {attempt+1}: {type(e).__name__} {url}")
            time.sleep(5 + attempt * 10)
    return "fail"


def parse_pages_filter():
    """SIRAH_PAGES='23833:400-520,9767:1-50' -> {book_id: set(pages)}"""
    spec = os.environ.get("SIRAH_PAGES", "").strip()
    out = {}
    if not spec:
        return out
    for part in spec.split(","):
        bid, rng = part.strip().split(":")
        a, b = rng.split("-")
        out.setdefault(bid, set()).update(range(int(a), int(b) + 1))
    return out


def build_jobs():
    keys = SPLIT[PARTITION]
    only = os.environ.get("SIRAH_BOOKS", "").strip()
    if only:
        ids = {x.strip() for x in only.split(",")}
        keys = [k for k in keys if BOOKS[k][0] in ids]
    pages_filter = parse_pages_filter()
    jobs = []
    for k in keys:
        bid, maxp = BOOKS[k]
        rng = range(1, maxp + 1)
        if bid in pages_filter:
            rng = sorted(p for p in pages_filter[bid] if 1 <= p <= maxp)
        for p in rng:
            jobs.append((CACHE / f"shamela_{bid}" / f"{p}.html",
                         f"https://shamela.ws/book/{bid}/{p}"))
    return jobs


def write_state(jobs, pending, done, failed, t0, n404):
    rem = sum(1 for d, u in pending if not is_cached(d))
    (DATA / f"state_{PARTITION}.json").write_text(json.dumps({
        "partition": PARTITION,
        "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_duration_s": round(time.time() - t0, 1),
        "fetched_this_run": done,
        "failed_this_run": len(failed),
        "not_found_404": n404,
        "remaining_jobs": rem,
        "total_jobs": len(jobs),
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    return rem


def main():
    t0 = time.time()
    for d in (DATA, LOGS, CACHE):
        d.mkdir(exist_ok=True)

    jobs = build_jobs()
    n404_path = DATA / f"not_found_{PARTITION}.json"
    known404 = set(json.loads(n404_path.read_text(encoding="utf-8"))) if n404_path.exists() else set()
    pending = [(d, u) for d, u in jobs if not is_cached(d) and u not in known404]
    log(f"RUN START [{PARTITION}] | total {len(jobs)} | pending {len(pending)} | known404 {len(known404)}")

    if not pending:
        log(f"[{PARTITION}] SEMUA SELESAI")
        (DATA / f"fetch_done_{PARTITION}.flag").write_text("done", encoding="utf-8")
        write_state(jobs, pending, 0, [], t0, len(known404))
        return

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"})

    done, failed = 0, []
    for dest, url in pending:
        if time.time() - t0 > MAX_RUNTIME:
            log(f"[{PARTITION}] TIME LIMIT — stop bersih. run ini: {done}")
            break
        st = fetch(s, url, dest)
        done += 1
        if st == "fail":
            failed.append(url)
            log(f"FAIL: {url}")
        elif st == "404":
            known404.add(url)
            n404_path.write_text(json.dumps(sorted(known404), indent=0), encoding="utf-8")
        if done % 50 == 0:
            log(f"[{PARTITION}] progress run: {done}/{len(pending)} | {((time.time()-t0)/60):.0f}m")
            write_state(jobs, pending, done, failed, t0, len(known404))

    remaining = write_state(jobs, pending, done, failed, t0, len(known404))
    with open(LOGS / "failures.log", "a", encoding="utf-8") as f:
        for u in failed:
            f.write(u + "\n")
    if remaining - len(known404) <= 0 or all(is_cached(d) or u in known404 for d, u in pending):
        (DATA / f"fetch_done_{PARTITION}.flag").write_text("done", encoding="utf-8")
        log(f"[{PARTITION}] SEMUA SELESAI (flag ditulis)")
    log(f"RUN END [{PARTITION}] | fetched {done} | fail {len(failed)} | remaining {remaining}/{len(jobs)}")


if __name__ == "__main__":
    main()
