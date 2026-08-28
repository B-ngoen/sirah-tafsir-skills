#!/usr/bin/env python3
"""lookup.py — CLI query tafsir verbatim dari tafsir_full.db.

Usage:
    python lookup.py 2:255                        # semua sumber (markdown)
    python lookup.py 2:255 -s tabari,maraghi      # filter sumber
    python lookup.py 2:255 --format json          # output JSON
    python lookup.py 2:255 --max-chars 3000       # batas potong per sumber (0 = penuh)
    python lookup.py 1 --intro                    # segmen intro/pembuka surah 1
    python lookup.py --coverage 2                 # ringkasan cakupan surah 2 per sumber

    python lookup.py 2:255 --toc                    # daftar segmen + sub-heading
    python lookup.py 1 --intro --toc                # toc segmen intro surah 1
    python lookup.py 2:255 --seg 7928 --paras 0-30  # paragraf 0-30 segmen, teks
                                                     # penuh + penanda ganti halaman

Exit codes: 0 sukses, 2 input salah, 3 DB tidak ditemukan/error DB.
Stdlib only: sqlite3, argparse, json, os, re, sys, glob, tempfile,
zipfile, lzma, urllib.request.

Portabel: DB dicari otomatis (env TAFSIR_DB -> assets skill -> cwd ->
upload Cowork/claude.ai -> path laptop -> unduh otomatis dua sumber:
GitHub release, lalu server privat owner); bila ketemu .zip/.xz
diekstrak sekali ke cache temp.
Lihat find_db(), download_db(), extract_zip_db(), extract_xz_db().
"""

import argparse
import glob
import json
import lzma
import os
import re
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# --- Resolusi DB (portabel: laptop / Cowork claude.ai / cwd / upload sesi) ---
SKILL_DIR = Path(__file__).resolve().parent.parent
LOCAL_DB = os.environ.get("TAFSIR_LOCAL_DB", "")  # opsional: path DB lokal pemilik
COWORK_DIRS = ("/mnt/user-data/uploads", "/mnt/user-data", str(Path.home() / "uploads"))
VAULT_DIR = Path(os.environ.get("TAFSIR_CACHE_ROOT") or "/nonexistent")  # opsional: root cache khusus


def _cache_dir() -> Path:
    """Folder cache PERMANEN untuk DB hasil unduh/ekstrak.

    JANGAN pakai tempfile.gettempdir(): Temp diberesi Windows/Storage Sense
    dan sandbox membuang isinya tiap sesi -> DB 136 MB terunduh ulang terus.
    Urutan: vault (laptop pemilik) -> LOCALAPPDATA (Windows) -> XDG data
    (sandbox/Linux) -> tempdir (upaya terakhir, tidak permanen).
    """
    cands = []
    if str(VAULT_DIR) not in ("", ".") and VAULT_DIR.is_dir():
        cands.append(VAULT_DIR / ".cache" / "tafsir-lookup")
    if os.environ.get("LOCALAPPDATA"):
        cands.append(Path(os.environ["LOCALAPPDATA"]) / "tafsir-lookup")
    xdg = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    cands.append(Path(xdg) / "tafsir-lookup")
    fallback = Path(tempfile.gettempdir()) / "tafsir-lookup"
    cands.append(fallback)
    for c in cands:
        try:
            c.mkdir(parents=True, exist_ok=True)
            return c
        except OSError:
            continue
    return fallback


CACHE_DIR = _cache_dir()
ZIP_CACHE_DB = CACHE_DIR / "tafsir_full.db"

# Migrasi sekali jalan: cache lama di Temp dipindahkan, bukan diunduh ulang.
_LEGACY_DB = Path(tempfile.gettempdir()) / "tafsir-lookup" / "tafsir_full.db"
if _LEGACY_DB != ZIP_CACHE_DB and _LEGACY_DB.exists() and not ZIP_CACHE_DB.exists():
    try:
        os.replace(_LEGACY_DB, ZIP_CACHE_DB)
    except OSError:
        pass
CACHE_MIN_BYTES = 100 * 1024 * 1024  # cache hasil ekstrak dianggap valid bila > 100 MB
# Auto-download: dua URL dicoba berurutan — sumber 1 GitHub release
# (domain diizinkan sandbox claude.ai; urllib otomatis mengikuti redirect
# 302 ke CDN objects.githubusercontent.com), sumber 2 server privat owner
# (fallback). URL TIDAK boleh dicetak ke pesan error/log — cukup sebut
# "sumber unduhan 1/2".
AUTO_DL_URLS = (
    "https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/tafsir-v1/tafsir_full.db.xz",
    "https://github.com/B-ngoen/refdb/releases/download/v1/tafsir_full.db.xz",
)
AUTO_DL_TIMEOUT = 15  # detik, timeout koneksi
AUTO_DL_XZ = CACHE_DIR / "tafsir_full.db.xz"  # unduhan sementara (dihapus usai ekstrak)

# Jumlah ayat per surah (riwayat Hafs) — 114 surah, total 6236.
AYAT_COUNT = {
    1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109,
    11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110, 19: 98,
    20: 135, 21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227, 27: 93, 28: 88,
    29: 69, 30: 60, 31: 34, 32: 30, 33: 73, 34: 54, 35: 45, 36: 83, 37: 182,
    38: 88, 39: 75, 40: 85, 41: 54, 42: 53, 43: 89, 44: 59, 45: 37, 46: 35,
    47: 38, 48: 29, 49: 18, 50: 45, 51: 60, 52: 49, 53: 62, 54: 55, 55: 78,
    56: 96, 57: 29, 58: 22, 59: 24, 60: 13, 61: 14, 62: 11, 63: 11, 64: 18,
    65: 12, 66: 12, 67: 30, 68: 52, 69: 52, 70: 44, 71: 28, 72: 28, 73: 20,
    74: 56, 75: 40, 76: 31, 77: 50, 78: 40, 79: 46, 80: 42, 81: 29, 82: 19,
    83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20, 91: 15,
    92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11,
    101: 11, 102: 8, 103: 3, 104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6,
    110: 3, 111: 5, 112: 4, 113: 5, 114: 6,
}

# Urutan tampilan output.
BOOKS = {
    "tabari": "Tafsir ath-Thabari (Jami' al-Bayan), ed. Dar at-Tarbiyah wat-Turats",
    "maraghi": "Tafsir al-Maraghi",
    "shabuni": "Shafwat at-Tafasir (ash-Shabuni)",
    "ibnkathir_awlad": "Tafsir Ibnu Katsir, ed. Awlad asy-Syaikh",
    "ibnkathir_jawzi": "Tafsir Ibnu Katsir, ed. Dar Ibnul Jauzi",
}

VALID_SOURCES = set(BOOKS)


class InputError(Exception):
    """Kesalahan input pengguna -> exit code 2."""


def fail(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_ref(ref):
    """Parse 'S' atau 'S:A' -> (surah, ayah_or_None)."""
    try:
        if ":" in ref:
            s_part, a_part = ref.split(":", 1)
            surah, ayah = int(s_part), int(a_part)
        else:
            surah, ayah = int(ref), None
    except ValueError:
        raise InputError(
            f"referensi '{ref}' tidak valid — format: SURAH:AYAT (mis. 2:255) atau SURAH (mis. 2)"
        )
    if not 1 <= surah <= 114:
        raise InputError(f"surah {surah} di luar rentang 1-114")
    if ayah is not None:
        n = AYAT_COUNT[surah]
        if not 1 <= ayah <= n:
            raise InputError(f"surah {surah} hanya memiliki {n} ayat (Hafs) — ayat {ayah} tidak ada")
    return surah, ayah


def parse_sources(spec):
    if not spec:
        return list(BOOKS)
    chosen = [s.strip() for s in spec.split(",") if s.strip()]
    if not chosen:
        raise InputError("daftar sumber kosong")
    unknown = [s for s in chosen if s not in VALID_SOURCES]
    if unknown:
        raise InputError(
            f"sumber tidak dikenal: {', '.join(unknown)} — valid: {', '.join(BOOKS)}"
        )
    # pertahankan urutan tampilan baku
    return [s for s in BOOKS if s in set(chosen)]


def fail_db_missing(path=None, autodl_failed=False):
    """Exit 3 dengan pesan menuntun dua skenario (Cowork vs laptop)."""
    msg = "DB tafsir tidak ditemukan"
    if path:
        msg += f": {path}"
    if autodl_failed:
        msg += "\n(auto-download dari kedua sumber juga gagal — server mati atau tidak ada internet)"
    msg += (
        "\n- Di Cowork/claude.ai: unggah file tafsir_full.db.xz (±18 MB, dari GitHub Release"
        " repo sirah-tafsir-skills; .zip juga diterima) ke sesi ini, lalu jalankan ulang."
        "\n- Di komputer sendiri: letakkan tafsir_full.db(.xz) di folder skill/assets atau cwd,"
        " atau set env TAFSIR_DB / TAFSIR_LOCAL_DB."
    )
    fail(msg, code=3)


def find_db():
    """Cari tafsir_full.db / .zip / .xz berurutan; return Path kandidat pertama (atau None).

    Urutan: (a) env TAFSIR_DB — autoritatif, bila di-set tapi file tidak ada
    maka open_db() exit 3; (b) assets di folder skill; (c) cwd;
    (d) folder upload Cowork/claude.ai (glob tafsir_full.db*);
    (e) path laptop pemilik; (f) auto-download — GitHub release lalu
    server privat owner (jalur terakhir sebelum fail_db_missing).
    Env TAFSIR_LOOKUP_SKIP_LOCAL=1 melewati jalur b-e dan langsung ke (f) —
    untuk testing/simulasi Cowork.
    """
    env = os.environ.get("TAFSIR_DB", "").strip()
    if env:
        return Path(env)  # bisa .db atau .zip; keberadaan divalidasi open_db()
    if os.environ.get("TAFSIR_LOOKUP_SKIP_LOCAL", "").strip():
        return download_db()  # testing: langsung auto-download
    candidates = [
        SKILL_DIR / "assets" / "tafsir_full.db",
        SKILL_DIR / "assets" / "tafsir_full.db.zip",
        SKILL_DIR / "assets" / "tafsir_full.db.xz",
        Path("tafsir_full.db"),
        Path("tafsir_full.db.zip"),
        Path("tafsir_full.db.xz"),
    ]
    for d in COWORK_DIRS:
        candidates += [Path(x) for x in sorted(glob.glob(os.path.join(d, "tafsir_full.db*")))]
    if LOCAL_DB:
        candidates +=[Path(LOCAL_DB), Path(LOCAL_DB + ".zip"), Path(LOCAL_DB + ".xz")]
    for c in candidates:
        if c.is_file():
            return c
    return download_db()  # jalur terakhir sebelum fail_db_missing()


def download_db():
    """Unduh tafsir_full.db.xz ke cache dari dua sumber berurutan, lalu ekstrak.

    Sumber dicoba berurutan — sumber 1 GitHub release (domain diizinkan
    sandbox claude.ai), sumber 2 server privat owner; sumber pertama yang
    sukses dipakai. Return Path DB cache, atau None bila semua gagal
    (server mati / tanpa internet). Chunked 1 MB, progress tiap 25% ke
    stderr, timeout koneksi 15 detik. URL tidak pernah dicetak ke
    stderr/log — pesan hanya "sumber unduhan 1/2".
    """
    if ZIP_CACHE_DB.is_file() and ZIP_CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return ZIP_CACHE_DB  # cache hasil unduhan/ekstrak sebelumnya masih valid
    for idx, url in enumerate(AUTO_DL_URLS, 1):
        db = _download_from_url(url, idx, len(AUTO_DL_URLS))
        if db is not None:
            return db
    return None


def _download_from_url(url, idx, n_sources):
    """Unduh dari satu sumber (idx/n_sources); return Path DB cache atau None.

    urllib otomatis mengikuti redirect (GitHub release = 302 ke CDN) dan
    mengembalikan response akhir — status 4xx/5xx ter-raise sebagai
    HTTPError, jadi cukup baca response akhir tanpa cek kode manual.
    """
    print(f"[auto-download] mengunduh DB dari sumber unduhan {idx}/{n_sources} (±19 MB)…", file=sys.stderr)
    part = Path(str(AUTO_DL_XZ) + ".part")
    try:
        ZIP_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "tafsir-lookup/1"})
        with urllib.request.urlopen(req, timeout=AUTO_DL_TIMEOUT) as resp:
            try:
                total = int(resp.headers.get("Content-Length") or 0)
            except ValueError:
                total = 0
            done, mark = 0, 25
            with open(part, "wb") as dst:
                while True:
                    chunk = resp.read(1024 * 1024)  # 1 MB
                    if not chunk:
                        break
                    dst.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = min(100, done * 100 // total)
                        if pct >= mark:
                            print(
                                f"[auto-download] {pct}% "
                                f"({done // (1024 * 1024)} MB / {total // (1024 * 1024)} MB)",
                                file=sys.stderr,
                            )
                            mark += 25
        os.replace(part, AUTO_DL_XZ)
    except (urllib.error.URLError, OSError) as e:
        part.unlink(missing_ok=True)
        tail = (
            "coba sumber berikutnya…"
            if idx < n_sources
            else "semua sumber gagal — server mati atau tidak ada internet?"
        )
        print(
            f"[auto-download] sumber unduhan {idx}/{n_sources} gagal ({type(e).__name__}) — {tail}",
            file=sys.stderr,
        )
        return None
    db = extract_xz_db(AUTO_DL_XZ)  # jalur lzma yang sama; cache > 100 MB dipakai ulang
    AUTO_DL_XZ.unlink(missing_ok=True)  # unduhan sementara — DB cache sudah jadi
    return db


def extract_zip_db(zip_path):
    """Ekstrak tafsir_full.db dari zip sekali ke cache temp; return path hasil ekstrak.

    Run berikutnya langsung pakai cache bila sudah ada dan ukurannya > 100 MB.
    """
    if ZIP_CACHE_DB.is_file() and ZIP_CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return ZIP_CACHE_DB
    try:
        ZIP_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith(".db")]
            if not names:
                fail(f"zip {zip_path} tidak memuat file .db", code=3)
            entry = min(names, key=len)  # entry .db paling dekat root
            with zf.open(entry) as src, open(ZIP_CACHE_DB, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
    except (zipfile.BadZipFile, OSError) as e:
        fail(f"gagal mengekstrak zip {zip_path}: {e}", code=3)
    return ZIP_CACHE_DB


def extract_xz_db(xz_path):
    """Ekstrak tafsir_full.db dari .xz sekali ke cache temp; return path hasil ekstrak.

    Cache sama dengan zip: dipakai ulang bila sudah ada dan > 100 MB.
    Dekompresi chunked 4 MB via stdlib lzma.
    """
    if ZIP_CACHE_DB.is_file() and ZIP_CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return ZIP_CACHE_DB
    try:
        ZIP_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with lzma.open(xz_path, "rb") as src, open(ZIP_CACHE_DB, "wb") as dst:
            while True:
                chunk = src.read(4 * 1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    except (lzma.LZMAError, EOFError, OSError) as e:
        fail(f"gagal mengekstrak xz {xz_path}: {e}", code=3)
    return ZIP_CACHE_DB


def open_db(db_path):
    if not os.path.isfile(db_path):
        fail_db_missing(db_path)
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.execute("SELECT COUNT(*) FROM segments")  # smoke test
        return con
    except sqlite3.Error as e:
        fail(f"gagal membuka DB {db_path}: {e}", code=3)


def get_segments_for_ayah(cur, source, surah, ayah):
    rows = cur.execute(
        "SELECT DISTINCT s.seg_id, s.label, s.section, s.from_page, s.from_para,"
        " s.to_page, s.to_para"
        " FROM ayah_map m JOIN segments s ON s.seg_id = m.seg_id"
        " WHERE m.source = ? AND m.surah = ? AND m.ayah = ?"
        " ORDER BY s.seg_id",
        (source, surah, ayah),
    ).fetchall()
    return rows


def get_intro_segments(cur, source, surah):
    return cur.execute(
        "SELECT seg_id, label, section, from_page, from_para, to_page, to_para"
        " FROM segments WHERE source = ? AND surah = ? AND section = 'intro'"
        " ORDER BY seg_id",
        (source, surah),
    ).fetchall()


def fetch_paragraphs_raw(cur, source, seg):
    """Return [(web_page, text)] paragraf non-kosong segmen — dasar toc/paging.

    Indeks relatif (0-based) dihitung dari list ini, konsisten dengan
    --toc dan --paras. Penyaring 'inside' identik fetch_paragraphs.
    """
    _, _, _, from_page, from_para, to_page, to_para = seg
    rows = cur.execute(
        "SELECT web_page, para_idx, text FROM pages"
        " WHERE source = ? AND web_page >= ? AND web_page <= ?"
        " ORDER BY web_page, para_idx",
        (source, from_page, to_page),
    ).fetchall()
    paras = []
    for web_page, para_idx, text in rows:
        inside = (
            (from_page < web_page < to_page)
            or (web_page == from_page and web_page == to_page and from_para <= para_idx <= to_para)
            or (web_page == from_page and para_idx >= from_para)
            or (web_page == to_page and para_idx <= to_para)
        )
        if inside and text and text.strip():
            paras.append((web_page, text))
    return paras


def fetch_paragraphs(cur, source, seg):
    return [text for _, text in fetch_paragraphs_raw(cur, source, seg)]


def get_page_meta(cur, source, web_page):
    row = cur.execute(
        "SELECT printed_juz, printed_page, url FROM pages WHERE source = ? AND web_page = ?"
        " ORDER BY para_idx LIMIT 1",
        (source, web_page),
    ).fetchone()
    return row  # (juz, page, url) atau None


def truncate(paras, budget):
    """Potong di batas paragraf. Return (kept, total, truncated)."""
    if budget <= 0 or sum(len(p) for p in paras) <= budget:
        return paras, len(paras), False
    kept, used = [], 0
    for p in paras:
        if used + len(p) > budget and kept:
            break
        kept.append(p)
        used += len(p)
    return kept, len(paras), True


def range_note(label, ayah):
    """Penjelasan bila label berupa rentang blok ayat."""
    if "-" in label:
        return f"Segmen ini mencakup ayat {label} (tafsir ayat diminta berada di dalamnya)."
    if ayah is not None and label != str(ayah):
        return f"Segmen berlabel ayat {label} (mencakup ayat yang diminta)."
    return None


def build_result(cur, source, seg, ayah, budget):
    seg_id, label, section, from_page, _, _, _ = seg
    paras = fetch_paragraphs(cur, source, seg)
    kept, total, truncated = truncate(paras, budget)
    meta = get_page_meta(cur, source, from_page)
    juz, page, url = meta if meta else (None, None, None)
    return {
        "source": source,
        "book": BOOKS[source],
        "seg_id": seg_id,
        "label": label,
        "section": section,
        "note": range_note(label, ayah),
        "paragraphs": kept,
        "para_count_total": total,
        "truncated": truncated,
        "printed_juz": juz,
        "printed_page": page,
        "url": url,
    }


def citation_line(r):
    if r["url"] is None:
        return "— (halaman sumber tidak tercatat di DB)"
    if r["source"] == "dorar_en":
        return r["url"]
    return f"juz {r['printed_juz']} hal {r['printed_page']} · {r['url']}"


def render_markdown(query_desc, results, missing, budget):
    lines = [f"# {query_desc}", ""]
    for r in results:
        lines.append(f"## {r['book']}")
        lines.append(f"- Label segmen: `{r['label']}` (seg_id {r['seg_id']})")
        if r["note"]:
            lines.append(f"- {r['note']}")
        lines.append("")
        for p in r["paragraphs"]:
            lines.append(p)
        if r["truncated"]:
            lines.append("")
            lines.append(f"…dipotong, {r['para_count_total']} paragraf total, pakai --max-chars 0")
        lines.append("")
        lines.append(f"— Sumber: {citation_line(r)}")
        lines.append("")
    for source in missing:
        lines.append(f"## {BOOKS[source]}")
        lines.append("tidak tersedia di sumber ini (keterbatasan edisi/situs).")
        lines.append("")
    if budget > 0:
        lines.append(f"(Batas potong per sumber: {budget} karakter — gunakan --max-chars 0 untuk teks penuh.)")
    return "\n".join(lines).rstrip() + "\n"


def render_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


# --- Mode TOC & paging (--toc / --seg / --paras), lihat TAFSIR-PAGING-SPEC ---

TASYKIL_RE = re.compile(r"[\u064B-\u0652\u0670]")  # harakat + superscript alef
SUBHEAD_MAX_CHARS = 70  # panjang maksimum SETELAH strip tasykil
SUBHEAD_STRIP_PREFIX = "*-–—•· "  # ornamen awal baris (mis. '* ذكر ...')
SUBHEAD_AR_KEYWORDS = ("القول", "ذكر", "باب", "فصل", "مسألة", "تفسير", "المعنى", "قوله",
                       # gaya Shafwat at-Tafasir (shabuni): البلاغة/الفائدة/اللغة/تنبيه/المناسبة/سبب النزول
                       "البلاغة", "البلاغه", "الفائدة", "الفائده", "اللغة", "اللغه", "تنبيه", "المناسبة", "المناسبه",
                       "سبب النزول", "الإعراب", "الاعراب", "فائدة", "فائده", "لطيفة", "لطيفه")
SUBHEAD_EN_KEYWORDS = ("tafsir", "ayat")  # dorar_en


def strip_tasykil(text):
    return TASYKIL_RE.sub("", text)


def is_subheading(text):
    """Deteksi sub-heading segmen: <= 70 karakter setelah strip tasykil dan
    diapit tanda kurung (biasa/siku — maraghi memakai [تفسير المفردات]),
    atau diawali kata kunci (Arab/EN) setelah ornamen awal dibuang."""
    s = strip_tasykil(text).strip()
    if not s or len(s) > SUBHEAD_MAX_CHARS:
        return False
    bare = s.lstrip(SUBHEAD_STRIP_PREFIX).strip()
    if not bare:
        return False
    if (bare.startswith("(") and bare.endswith(")")) or (
        bare.startswith("[") and bare.endswith("]")
    ):
        return True
    if bare.lower().startswith(SUBHEAD_EN_KEYWORDS):
        return True
    return bare.startswith(SUBHEAD_AR_KEYWORDS)


def parse_paras(spec):
    """Parse '--paras A-B' -> (a, b); raise InputError bila cacat."""
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", spec.strip())
    if not m:
        raise InputError(f"--paras '{spec}' tidak valid — format: A-B (mis. 0-30)")
    a, b = int(m.group(1)), int(m.group(2))
    if a > b:
        raise InputError(f"--paras {a}-{b}: indeks awal tidak boleh melebihi akhir")
    return a, b


def build_toc_entry(cur, source, seg):
    """Metadata satu segmen + sub-heading (indeks paragraf relatif segmen)."""
    seg_id, label, section, from_page, _, to_page, _ = seg
    raw = fetch_paragraphs_raw(cur, source, seg)
    subs = [{"para_idx": i, "title": text} for i, (_, text) in enumerate(raw) if is_subheading(text)]
    return {
        "source": source,
        "book": BOOKS[source],
        "seg_id": seg_id,
        "label": label,
        "section": section,
        "web_page_from": from_page,
        "web_page_to": to_page,
        "para_count": len(raw),
        "subheadings": subs,
    }


def cmd_toc(cur, surah, ayah, sources, fmt):
    """--toc: daftar segmen per sumber untuk QS S:A (atau intro SURAH --intro)."""
    results, missing = [], []
    for source in sources:
        segs = (
            get_segments_for_ayah(cur, source, surah, ayah)
            if ayah is not None
            else get_intro_segments(cur, source, surah)
        )
        if not segs:
            missing.append(source)
            continue
        results.extend(build_toc_entry(cur, source, seg) for seg in segs)
    if ayah is not None:
        desc, query = f"Daftar segmen — Tafsir QS {surah}:{ayah}", {"surah": surah, "ayah": ayah}
    else:
        desc, query = f"Daftar segmen — intro/pembuka Surah {surah}", {"surah": surah, "section": "intro"}
    if fmt == "json":
        print(render_json({"query": query, "results": results, "missing_sources": missing}), end="")
        return
    lines = [f"# {desc}", ""]
    for source in sources:
        segs_here = [r for r in results if r["source"] == source]
        if not segs_here:
            continue
        lines.append(f"## {BOOKS[source]}")
        for r in segs_here:
            lines.append(
                f"- seg_id {r['seg_id']} · label `{r['label']}` · hal.web "
                f"{r['web_page_from']}–{r['web_page_to']} · {r['para_count']} paragraf"
            )
            if r["subheadings"]:
                lines.extend(f"  - {sh['para_idx']} {sh['title']}" for sh in r["subheadings"])
            else:
                lines.append("  - (tanpa sub-heading terdeteksi)")
        lines.append("")
    for source in missing:
        lines.append(f"## {BOOKS[source]}")
        lines.append("tidak tersedia di sumber ini (keterbatasan edisi/situs).")
        lines.append("")
    lines.append(
        "(Sub-heading ditulis 'indeks judul' — indeks paragraf relatif dari awal segmen;"
        " baca rentang: lookup.py <ref> --seg <seg_id> --paras A-B)"
    )
    print("\n".join(lines).rstrip() + "\n", end="")


def page_marker(source, meta):
    """Baris penanda halaman cetak; dorar tanpa juz/hal (URL saja)."""
    juz, page, url = meta if meta else (None, None, None)
    if url is None:
        return "— halaman: (halaman sumber tidak tercatat di DB)"
    if source == "dorar_en":
        return f"— halaman: {url}"
    return f"— halaman: juz {juz} hal {page} ({url})"


def cmd_segment(cur, surah, ayah, intro_mode, sources, seg_id, fmt, paras):
    """--seg [--paras]: satu segmen, teks penuh + penanda tiap ganti halaman."""
    seg = seg_source = None
    for source in sources:
        segs = (
            get_intro_segments(cur, source, surah)
            if intro_mode
            else get_segments_for_ayah(cur, source, surah, ayah)
        )
        for s in segs:
            if s[0] == seg_id:
                seg, seg_source = s, source
                break
        if seg:
            break
    if seg is None:
        ref_desc = f"intro Surah {surah}" if intro_mode else f"QS {surah}:{ayah}"
        fail(
            f"seg_id {seg_id} tidak ditemukan untuk {ref_desc} pada sumber terpilih "
            "— pakai --toc untuk melihat seg_id yang tersedia"
        )
    label = seg[1]
    raw = fetch_paragraphs_raw(cur, seg_source, seg)
    total = len(raw)
    note = "Segmen intro/pembuka surah." if intro_mode else range_note(label, ayah)
    sel = raw if paras is None else raw[paras[0]:paras[1] + 1]
    pages, last_wp, para_rows = [], None, []
    for offset, (web_page, text) in enumerate(sel):
        idx = offset if paras is None else paras[0] + offset
        para_rows.append({"para": idx, "web_page": web_page, "text": text})
        if web_page != last_wp:
            last_wp = web_page
            meta = get_page_meta(cur, seg_source, web_page)
            juz, page, url = meta if meta else (None, None, None)
            pages.append({"web_page": web_page, "printed_juz": juz, "printed_page": page, "url": url})
    ref_desc = f"intro Surah {surah}" if intro_mode else f"QS {surah}:{ayah}"
    if paras is not None:
        desc = f"Tafsir {ref_desc} — segmen {seg_id} (paragraf {paras[0]}–{paras[1]} dari {total})"
    else:
        desc = f"Tafsir {ref_desc} — segmen {seg_id} ({total} paragraf, penuh)"
    if fmt == "json":
        query = {"surah": surah, "section": "intro"} if intro_mode else {"surah": surah, "ayah": ayah}
        query["seg_id"] = seg_id
        if paras is not None:
            query["paras_requested"] = list(paras)
        payload = {
            "query": query,
            "results": [{
                "source": seg_source,
                "book": BOOKS[seg_source],
                "seg_id": seg_id,
                "label": label,
                "note": note,
                "para_count_total": total,
                "paragraphs": para_rows,
                "pages": pages,
            }],
        }
        print(render_json(payload), end="")
        return
    lines = [f"# {desc}", "", f"## {BOOKS[seg_source]}", f"- Label segmen: `{label}` (seg_id {seg_id})"]
    if note:
        lines.append(f"- {note}")
    lines.append("")
    if not sel:
        lines.append(
            f"(paragraf {paras[0]}–{paras[1]} di luar segmen — total {total} paragraf, "
            f"indeks valid 0–{total - 1})"
        )
    else:
        page_by_wp = {p["web_page"]: p for p in pages}
        meta_by_wp = {
            wp: get_page_meta(cur, seg_source, wp) for wp in page_by_wp
        }
        last_wp = None
        for row in para_rows:
            if row["web_page"] != last_wp:
                last_wp = row["web_page"]
                if lines[-1]:
                    lines.append("")
                lines.append(page_marker(seg_source, meta_by_wp[row["web_page"]]))
                lines.append("")
            lines.append(row["text"])
            lines.append("")
    print("\n".join(lines).rstrip() + "\n", end="")


def cmd_ayah(cur, surah, ayah, sources, fmt, budget):
    results, missing = [], []
    remaining = budget
    for source in sources:
        segs = get_segments_for_ayah(cur, source, surah, ayah)
        if not segs:
            missing.append(source)
            continue
        for seg in segs:
            r = build_result(cur, source, seg, ayah, remaining)
            results.append(r)
            if budget > 0:
                remaining = max(0, remaining - sum(len(p) for p in r["paragraphs"]))
    if fmt == "json":
        payload = {
            "query": {"surah": surah, "ayah": ayah},
            "results": results,
            "missing_sources": missing,
        }
        print(render_json(payload), end="")
    else:
        desc = f"Tafsir QS {surah}:{ayah}"
        print(render_markdown(desc, results, missing, budget), end="")


def cmd_intro(cur, surah, sources, fmt, budget):
    results, missing = [], []
    remaining = budget
    for source in sources:
        segs = get_intro_segments(cur, source, surah)
        if not segs:
            missing.append(source)
            continue
        for seg in segs:
            r = build_result(cur, source, seg, None, remaining)
            r["note"] = "Segmen intro/pembuka surah."
            results.append(r)
            if budget > 0:
                remaining = max(0, remaining - sum(len(p) for p in r["paragraphs"]))
    if fmt == "json":
        payload = {
            "query": {"surah": surah, "section": "intro"},
            "results": results,
            "missing_sources": missing,
        }
        print(render_json(payload), end="")
    else:
        print(render_markdown(f"Intro/pembuka Surah {surah}", results, missing, budget), end="")


def cmd_coverage(cur, surah, sources, fmt):
    total_ayat = AYAT_COUNT[surah]
    rows = []
    for source in sources:
        mapped = {
            a for (a,) in cur.execute(
                "SELECT DISTINCT ayah FROM ayah_map WHERE source = ? AND surah = ?",
                (source, surah),
            )
        }
        missing = [a for a in range(1, total_ayat + 1) if a not in mapped]
        pct = (len(mapped) / total_ayat) * 100
        rows.append({
            "source": source,
            "book": BOOKS[source],
            "covered": len(mapped),
            "total": total_ayat,
            "percent": round(pct, 2),
            "missing_ayahs": missing,
        })
    if fmt == "json":
        print(render_json({"query": {"surah": surah, "total_ayat": total_ayat}, "sources": rows}), end="")
        return
    lines = [f"# Cakupan tafsir Surah {surah} ({total_ayat} ayat, Hafs)", "",
             "| Sumber | Kitab | Cakupan | Ayat absen |", "|---|---|---|---|"]
    for r in rows:
        if r["missing_ayahs"]:
            shown = ", ".join(str(a) for a in r["missing_ayahs"][:20])
            if len(r["missing_ayahs"]) > 20:
                shown += f", … ({len(r['missing_ayahs'])} total)"
            miss = shown
        else:
            miss = "—"
        lines.append(
            f"| {r['source']} | {r['book']} | {r['covered']}/{r['total']} ({r['percent']:.2f}%) | {miss} |"
        )
    print("\n".join(lines) + "\n", end="")


def main():
    ap = argparse.ArgumentParser(
        prog="lookup.py",
        description="Query tafsir verbatim dari tafsir_full.db (5 sumber).",
    )
    ap.add_argument("ref", help="referensi: SURAH:AYAT (mis. 2:255) atau SURAH (mis. 1, untuk --intro/--coverage)")
    ap.add_argument("-s", "--sources", help="filter sumber, dipisah koma (default: semua)")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown",
                    help="format output (default: markdown)")
    ap.add_argument("--max-chars", type=int, default=6000, metavar="N",
                    help="batas karakter per sumber, potong di batas paragraf (default 6000; 0 = teks penuh)")
    ap.add_argument("--intro", action="store_true", help="ambil segmen intro/pembuka surah")
    ap.add_argument("--coverage", action="store_true", help="ringkasan cakupan surah per sumber")
    ap.add_argument("--toc", action="store_true",
                    help="daftar segmen per sumber (seg_id, label, hal.web, jumlah paragraf, sub-heading)")
    ap.add_argument("--seg", metavar="SEG_ID",
                    help="batasi ke satu segmen (id dari --toc); teks penuh + penanda ganti halaman")
    ap.add_argument("--paras", metavar="A-B",
                    help="cetak paragraf indeks A..B relatif awal segmen (wajib bersama --seg; tanpa batas karakter)")
    ap.add_argument("--db", help="path DB SQLite, .zip, atau .xz (default: dicari otomatis, lihat env TAFSIR_DB)")
    args = ap.parse_args()

    paras_range = None
    try:
        surah, ayah = parse_ref(args.ref)
        sources = parse_sources(args.sources)
        if args.max_chars < 0:
            raise InputError("--max-chars tidak boleh negatif (0 = tanpa batas)")
        if ayah is not None and (args.intro or args.coverage):
            raise InputError("--intro/--coverage memakai format SURAH saja (tanpa :AYAT)")
        if ayah is None and not (args.intro or args.coverage):
            raise InputError(
                f"referensi '{args.ref}' tanpa ayat — pakai SURAH:AYAT (mis. {surah}:1), "
                f"atau tambahkan --intro / --coverage"
            )
        if args.intro and args.coverage:
            raise InputError("--intro dan --coverage tidak bisa dipakai bersamaan")
        if args.paras is not None and args.seg is None:
            raise InputError("--paras hanya bisa dipakai bersama --seg")
        if args.seg is not None:
            if not re.fullmatch(r"\d+", args.seg):
                raise InputError(f"seg_id '{args.seg}' tidak valid — harus angka (lihat --toc)")
            if args.toc:
                raise InputError("--toc dan --seg tidak bisa dipakai bersamaan")
            if args.coverage:
                raise InputError("--coverage dan --seg tidak bisa dipakai bersamaan")
        if args.toc and args.coverage:
            raise InputError("--toc dan --coverage tidak bisa dipakai bersamaan")
        if args.paras is not None:
            paras_range = parse_paras(args.paras)
    except InputError as e:
        fail(str(e))

    db_path = args.db or find_db()
    if db_path is None:
        fail_db_missing(autodl_failed=True)  # find_db() sudah mencoba auto-download
    if str(db_path).lower().endswith(".zip"):
        db_path = extract_zip_db(db_path)
    elif str(db_path).lower().endswith(".xz"):
        db_path = extract_xz_db(db_path)
    con = open_db(db_path)
    cur = con.cursor()

    if args.coverage:
        cmd_coverage(cur, surah, sources, args.format)
    elif args.toc:
        cmd_toc(cur, surah, ayah, sources, args.format)
    elif args.seg is not None:
        cmd_segment(cur, surah, ayah, args.intro, sources, int(args.seg), args.format, paras_range)
    elif args.intro:
        cmd_intro(cur, surah, sources, args.format, args.max_chars)
    else:
        cmd_ayah(cur, surah, ayah, sources, args.format, args.max_chars)
    con.close()


if __name__ == "__main__":
    main()
