# -*- coding: utf-8 -*-
"""Checkpointed fetcher for shamela.ws + dorar.net.

Cache = checkpoint: cache/{book}/{page}.html — existing files skipped, so the
script can be killed and resumed at any time.
"""
import json, pathlib, random, sys, time
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

DELAY_MIN, DELAY_MAX = 1.0, 2.5


def fetch(session, url, dest: pathlib.Path, retries=3):
    if dest.exists() and dest.stat().st_size > 1000:
        return "cached"
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200 and len(r.text) > 1000:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(r.text, encoding="utf-8")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                return "ok"
            time.sleep(5 + attempt * 10)
        except requests.RequestException:
            time.sleep(5 + attempt * 10)
    return "fail"


def main():
    toc = json.loads((ROOT / "data" / "pilot_toc.json").read_text(encoding="utf-8"))
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "ar,en;q=0.8"})

    jobs = []  # (dest, url)
    for name, info in toc.items():
        bid = info["book_id"]
        for p in range(info["fatihah_start"], info["fatihah_end_excl"] + 1):
            jobs.append((CACHE / f"shamela_{bid}" / f"{p}.html",
                         f"https://shamela.ws/book/{bid}/{p}"))
    for did in [1233, 1]:  # Fatihah intro + Fatihah 1-7
        jobs.append((CACHE / "dorar" / f"{did}.html",
                     f"https://dorar.net/en/tafseer/{did}"))

    total, done, failed = len(jobs), 0, []
    for dest, url in jobs:
        st = fetch(s, url, dest)
        done += 1
        if st == "fail":
            failed.append(url)
        if done % 20 == 0 or done == total:
            print(f"[{done}/{total}] last={url} status={st}", flush=True)
    print("FAILED:", len(failed))
    for u in failed:
        print("  ", u)
    (ROOT / "data" / "pilot_fetch_report.json").write_text(
        json.dumps({"total": total, "failed": failed}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
