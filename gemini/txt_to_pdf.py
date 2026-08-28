#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""txt_to_pdf.py — ubah berkas teks kitab (hasil export_knowledge.py) menjadi PDF Arab (RTL)
lewat Chromium headless (patchright/playwright), dipecah ≤ MAX_CHARS per PDF agar aman untuk
batas Gem / NotebookLM (±500 ribu kata per sumber).

    python txt_to_pdf.py <folder_txt> <folder_pdf> [MAX_CHARS=3000000]
"""
import html, io, os, sys, time
from pathlib import Path

MAX_CHARS = int(sys.argv[3]) if len(sys.argv) > 3 else 3_000_000

CSS = """
@page { size: A4; margin: 14mm 12mm; }
body { font-family: 'Amiri', 'Noto Naskh Arabic', serif; font-size: 12.5pt; line-height: 1.7; direction: rtl; }
h1 { font-size: 15pt; direction: rtl; }
.m { direction: ltr; text-align: left; font-family: Consolas, monospace; font-size: 8.5pt; color: #444;
     border-top: 1px solid #999; margin: 10px 0 4px; padding-top: 2px; }
p { margin: 0 0 4px; text-align: justify; }
.note { direction: ltr; font-family: sans-serif; font-size: 9pt; color: #333; }
"""


def to_html(title, lines, part, nparts):
    out = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>",
           f"<h1>{html.escape(title)}</h1>",
           f"<p class='note'>Bagian {part}/{nparts}. Sumber: Maktabah Syamilah (shamela.ws), verbatim. "
           f"Baris abu-abu = penanda halaman: [kitab] juz X hal Y | URL. Kutip apa adanya dan sebut juz/hal.</p>"]
    for ln in lines:
        if ln.startswith("### "):
            out.append(f"<div class='m'>{html.escape(ln[4:])}</div>")
        elif ln.startswith("# "):
            continue
        elif ln.strip():
            out.append(f"<p>{html.escape(ln)}</p>")
    out.append("</body></html>")
    return "\n".join(out)


def chunks(lines):
    """Pecah pada batas penanda halaman agar tiap PDF mulai dengan sitasi."""
    total = sum(len(l) for l in lines)
    n = max(1, -(-total // MAX_CHARS))  # ceil
    target = total / n  # bagian sama rata, bukan 3,0 + 0,3 juta
    cur, size = [], 0
    for ln in lines:
        if ln.startswith("### ") and size >= target:
            yield cur
            cur, size = [], 0
        cur.append(ln)
        size += len(ln)
    if cur:
        yield cur


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    from patchright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for txt in sorted(src.glob("*.txt")):
            lines = io.open(txt, encoding="utf-8").read().split("\n")
            title = next((l[2:] for l in lines if l.startswith("# ")), txt.stem)
            parts = list(chunks(lines))
            for i, part in enumerate(parts, 1):
                name = f"{txt.stem}-{i:02d}of{len(parts):02d}.pdf" if len(parts) > 1 else f"{txt.stem}.pdf"
                pdf = dst / name
                if pdf.exists():
                    continue
                t = time.time()
                page.set_content(to_html(title, part, i, len(parts)), wait_until="load")
                page.pdf(path=str(pdf), format="A4", print_background=False)
                print(f"{pdf.name}: {sum(len(l) for l in part)/1e6:.1f} Mchar -> {pdf.stat().st_size/1e6:.1f} MB, {time.time()-t:.0f}s", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
