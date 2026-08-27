#!/usr/bin/env python3
"""lookup.py — CLI query verbatim sirah_full.db (skill sirah-lookup).

Usage:
    python lookup.py event ghazwah_badr_kubra     # satu event (markdown, semua sumber)
    python lookup.py event badar                  # >1 kandidat -> daftar kandidat, exit 2
    python lookup.py event "غزوة بدر"              # normalisasi tasykil otomatis
    python lookup.py event --list                 # semua event urut kronologis
    python lookup.py event ... -s tarikh_tabari   # filter sumber (koma)
    python lookup.py person 4835                  # entri kanonik Ishabah no. 4835
    python lookup.py person "أبو بكر"              # pencarian nama (FTS + LIKE)
    python lookup.py year 2                       # segmen "سنة 2" Thabari + registry
    python lookup.py search خندق                  # cari event & person, tampilkan id
    python lookup.py coverage [event|person]      # ringkasan cakupan per sumber
    python lookup.py info                         # meta DB, sumber, provenance
    python lookup.py ... --format json            # output JSON
    python lookup.py ... --max-chars 0            # teks penuh (default 6000/segmen)
    python lookup.py event badar --toc            # daftar isi per segmen (sub-heading)
    python lookup.py event badar --seg 21         # teks penuh satu segmen
    python lookup.py event badar --seg 21 --paras 0-40   # rentang paragraf + sitasi per halaman
    python lookup.py event badar --seg 21 --subbab 79   # satu sub-bab (idx/awalan judul, boleh diulang)
    python lookup.py event badar --seg 21 --paras 0-40 --exclude-poetry  # lewati bait syair

--toc: daftar isi per segmen (para_idx sub-heading, rentang [A–B], ~kchar,
penanda [syair]/[nasab]/[catatan], total kchar + jumlah syair/nasab per
segmen) untuk membaca segmen panjang bab demi bab. --seg membatasi ke satu
segmen (event/year: seg_id, person: entry_id). --paras A-B mencetak
paragraf A..B (0-based, relatif awal segmen) dari --seg, dengan sitasi
juz/hal/URL tiap ganti halaman. --subbab mengambil satu sub-bab dari
heading sampai heading berikutnya. --exclude-poetry melewati paragraf
bait syair dengan placeholder jujur di tempatnya.

--max-chars N berlaku PER SEGMEN (event) / PER ENTRI kamus (person), bukan
per sumber: sumber dengan beberapa segmen menampilkan tiap segmen dengan
potongan N karakter masing-masing (heading tetap terlihat di tiap segmen).

Exit codes: 0 sukses, 2 input salah / tidak ditemukan / ambigu (kandidat
ditampilkan), 3 DB tidak ditemukan / error DB.

Stdlib only: sqlite3, argparse, json, os, sys, glob, lzma, zipfile,
urllib, tempfile, pathlib.

Portabel: DB dicari otomatis (env SIRAH_DB -> assets skill -> cwd ->
upload Cowork/claude.ai -> path laptop -> unduh otomatis dua sumber:
GitHub release, lalu server privat owner); bila ketemu .zip/.xz
diekstrak sekali ke cache permanen. URL unduhan tidak pernah dicetak ke
log/error. Lihat find_db(), download_db(), extract_zip_db(), extract_xz_db().
"""

import argparse
import glob
import json
import lzma
import os
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
LOCAL_DB = os.environ.get("SIRAH_LOCAL_DB", "")  # opsional: path DB lokal pemilik
COWORK_DIRS = ("/mnt/user-data/uploads", "/mnt/user-data", str(Path.home() / "uploads"))
VAULT_DIR = Path(os.environ.get("SIRAH_CACHE_ROOT") or "/nonexistent")  # opsional: root cache khusus


def _cache_dir() -> Path:
    """Folder cache PERMANEN untuk DB hasil unduh/ekstrak.

    JANGAN pakai tempfile.gettempdir(): Temp diberesi Windows/Storage Sense
    dan sandbox membuang isinya tiap sesi -> DB ratusan MB terunduh ulang
    terus. Urutan: vault (laptop pemilik) -> LOCALAPPDATA (Windows) -> XDG
    data (sandbox/Linux) -> tempdir (upaya terakhir, tidak permanen).
    """
    cands = []
    if str(VAULT_DIR) not in ("", ".") and VAULT_DIR.is_dir():
        cands.append(VAULT_DIR / ".cache" / "sirah-lookup")
    if os.environ.get("LOCALAPPDATA"):
        cands.append(Path(os.environ["LOCALAPPDATA"]) / "sirah-lookup")
    xdg = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    cands.append(Path(xdg) / "sirah-lookup")
    fallback = Path(tempfile.gettempdir()) / "sirah-lookup"
    cands.append(fallback)
    for c in cands:
        try:
            c.mkdir(parents=True, exist_ok=True)
            return c
        except OSError:
            continue
    return fallback


CACHE_DIR = _cache_dir()
ZIP_CACHE_DB = CACHE_DIR / "sirah_full.db"

# Migrasi sekali jalan: cache lama di Temp dipindahkan, bukan diunduh ulang.
_LEGACY_DB = Path(tempfile.gettempdir()) / "sirah-lookup" / "sirah_full.db"
if _LEGACY_DB != ZIP_CACHE_DB and _LEGACY_DB.exists() and not ZIP_CACHE_DB.exists():
    try:
        os.replace(_LEGACY_DB, ZIP_CACHE_DB)
    except OSError:
        pass
CACHE_MIN_BYTES = 100 * 1024 * 1024  # cache hasil ekstrak dianggap valid bila > 100 MB
# Auto-download: dua URL dicoba berurutan — sumber 1 GitHub release
# (domain diizinkan sandbox claude.ai; urllib otomatis mengikuti redirect
# 302 ke CDN objects.githubusercontent.com), sumber 2 rilis cadangan
# (fallback). URL TIDAK boleh dicetak ke pesan error/log — cukup sebut
# "sumber unduhan 1/2".
AUTO_DL_URLS = (
    "https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/sirah-v1/sirah_full.db.xz",
    "https://github.com/B-ngoen/refdb/releases/download/v1/sirah_full.db.xz",
)
AUTO_DL_TIMEOUT = 15  # detik, timeout koneksi
AUTO_DL_XZ = CACHE_DIR / "sirah_full.db.xz"  # unduhan sementara (dihapus usai ekstrak)

# Urutan tampilan sumber (master).
SOURCE_ORDER = [
    "hisyam_saqqa", "hisyam_thaha", "ibn_ishaq", "tabaqat", "tarikh_tabari",
    "ishabah", "usud_ilmiyah", "usud_rifai", "istiab", "tabaqat_tabiin",
]
# Sumber yang memuat segmen event (sirah/tabaqat/tarikh), urut tampil.
EVENT_SOURCES = ["hisyam_saqqa", "hisyam_thaha", "ibn_ishaq", "tabaqat", "tarikh_tabari"]
# Sumber kamus/biografi dengan person_entries, urut tampil.
PERSON_SOURCES = ["tabaqat", "ishabah", "usud_ilmiyah", "usud_rifai", "istiab"]
VALID_SOURCES = set(SOURCE_ORDER)

MISSING_NOTE = "tidak tersedia di sumber ini (keterbatasan edisi/situs/cakupan registry)."


class InputError(Exception):
    """Kesalahan input pengguna -> exit code 2."""


def fail(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# --- Normalisasi Arab (sama dengan build_full_db.py; teks asli tidak diubah) ---
_MARK_RANGES = (
    (0x0610, 0x061A),  # tanda baca Arab
    (0x064B, 0x065F),  # harakat
    (0x0670, 0x0670),  # alif khanjariyah
    (0x06D6, 0x06ED),  # tanda tasykil tambahan Quran
    (0x0640, 0x0640),  # tatweel
)
_LETTER_MAP = {0x0623: 0x0627, 0x0625: 0x0627, 0x0622: 0x0627,  # أ إ آ -> ا
               0x0629: 0x0647, 0x0649: 0x064A}                  # ة -> ه, ى -> ي
_NORM_TABLE = {cp: None for lo, hi in _MARK_RANGES for cp in range(lo, hi + 1)}
_NORM_TABLE.update(_LETTER_MAP)


def norm(text):
    if not text:
        return ""
    return " ".join(text.translate(_NORM_TABLE).split())


def like_escape(s):
    """Escape %, _ dan \\ untuk LIKE ... ESCAPE '\\'."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def fts_expr(qn):
    """Bangun ekspresi FTS5 aman: tiap token dalam kutip, digabung AND."""
    toks = [t for t in qn.split() if t]
    if not toks:
        return None
    return " AND ".join('"' + t.replace('"', '""') + '"' for t in toks)


def fail_db_missing(path=None, autodl_failed=False):
    """Exit 3 dengan pesan menuntun dua skenario (Cowork vs laptop)."""
    msg = "DB sirah tidak ditemukan"
    if path:
        msg += f": {path}"
    if autodl_failed:
        msg += "\n(auto-download dari kedua sumber juga gagal — server mati atau tidak ada internet)"
    msg += (
        "\n- Di Cowork/claude.ai: unggah file sirah_full.db.xz dari flashdisk Anda"
        " ke sesi ini, lalu jalankan ulang."
        "\n- Di laptop: letakkan sirah_full.db(.xz) di folder kerja atau skills/sirah-lookup/assets/,"
        " atau set env SIRAH_DB / SIRAH_LOCAL_DB."
    )
    fail(msg, code=3)


def find_db():
    """Cari sirah_full.db / .zip / .xz berurutan; return Path kandidat pertama (atau None).

    Urutan: (a) env SIRAH_DB — autoritatif, bila di-set tapi file tidak ada
    maka open_db() exit 3; (b) assets di folder skill; (c) cwd;
    (d) folder upload Cowork/claude.ai (glob sirah_full.db*);
    (e) env SIRAH_LOCAL_DB; (f) auto-download — GitHub release lalu
    rilis cadangan (jalur terakhir sebelum fail_db_missing).
    Env SIRAH_LOOKUP_SKIP_LOCAL=1 melewati jalur b-e dan langsung ke (f) —
    untuk testing/simulasi Cowork.
    """
    env = os.environ.get("SIRAH_DB", "").strip()
    if env:
        return Path(env)  # bisa .db/.zip/.xz; keberadaan divalidasi open_db()
    if os.environ.get("SIRAH_LOOKUP_SKIP_LOCAL", "").strip():
        return download_db()  # testing: langsung auto-download
    candidates = [
        SKILL_DIR / "assets" / "sirah_full.db",
        SKILL_DIR / "assets" / "sirah_full.db.zip",
        SKILL_DIR / "assets" / "sirah_full.db.xz",
        Path("sirah_full.db"),
        Path("sirah_full.db.zip"),
        Path("sirah_full.db.xz"),
        Path("data") / "sirah_full.db",
    ]
    for d in COWORK_DIRS:
        candidates += [Path(x) for x in sorted(glob.glob(os.path.join(d, "sirah_full.db*")))]
    if LOCAL_DB:
        candidates += [Path(LOCAL_DB), Path(LOCAL_DB + ".zip"), Path(LOCAL_DB + ".xz")]
    for c in candidates:
        if c.is_file():
            return c
    return download_db()  # jalur terakhir sebelum fail_db_missing()


def download_db():
    """Unduh sirah_full.db.xz ke cache dari dua sumber berurutan, lalu ekstrak.

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
    print(f"[auto-download] mengunduh DB dari sumber unduhan {idx}/{n_sources}…", file=sys.stderr)
    part = Path(str(AUTO_DL_XZ) + ".part")
    try:
        ZIP_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "sirah-lookup/1"})
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
    """Ekstrak sirah_full.db dari zip sekali ke cache; return path hasil ekstrak.

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
    """Ekstrak sirah_full.db dari .xz sekali ke cache; return path hasil ekstrak.

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
        con.execute("SELECT COUNT(*) FROM events")  # smoke test
        return con
    except sqlite3.Error as e:
        fail(f"gagal membuka DB {db_path}: {e}", code=3)


# --- Util query/render ---
def load_sources(cur):
    """dict source -> {title_ar, title_id, role, note} dari tabel sources."""
    out = {}
    for source, title_ar, title_id, role, note in cur.execute(
        "SELECT source, title_ar, title_id, role, note FROM sources"
    ):
        out[source] = {"title_ar": title_ar, "title_id": title_id, "role": role, "note": note}
    return out


def fetch_paragraphs_indexed(cur, source, from_page, from_para, to_page, to_para):
    """Paragraf verbatim dgn indeks: list (web_page, para_idx, text) dalam rentang."""
    rows = cur.execute(
        "SELECT web_page, para_idx, text FROM pages"
        " WHERE source = ? AND web_page >= ? AND web_page <= ?"
        " ORDER BY web_page, para_idx",
        (source, from_page, to_page),
    ).fetchall()
    out = []
    for web_page, para_idx, text in rows:
        inside = (
            (from_page < web_page < to_page)
            or (web_page == from_page and web_page == to_page and from_para <= para_idx <= to_para)
            or (web_page == from_page and para_idx >= from_para)
            or (web_page == to_page and para_idx <= to_para)
        )
        if inside:
            out.append((web_page, para_idx, text))
    return [(wp, pi, t) for wp, pi, t in out if t and t.strip()]


def fetch_paragraphs(cur, source, from_page, from_para, to_page, to_para):
    """Paragraf verbatim dalam rentang halaman/paragraf (inklusif di batas)."""
    return [t for _, _, t in fetch_paragraphs_indexed(
        cur, source, from_page, from_para, to_page, to_para)]


# --- Deteksi sub-heading untuk --toc (dawapan dibandingkan pada bentuk norm) ---
HEADING_WORDS = {"غزوه", "سريه", "ذكر", "حديث", "امر", "قصه", "خبر", "باب", "فصل", "شعر", "سنه",
                 "مقتل", "اسلام", "هجره", "وفاه", "بيعه", "خطبه", "تسميه", "القول"}
_NARRATION_MARKS = ("قال:", "حدثنا", "اخبرنا")  # ciri riwayat, bukan judul
_TRAILING_BAD = ("«", "»", '"', "،", ",")


def _strip_shalawat(tn):
    """Buang frasa shalawat (ter-norm, termasuk bentuk -ﷺ-) agar tak
    dihitung dalam panjang judul."""
    tn = tn.replace("صلي الله عليه وسلم", " ").replace("ﷺ", " ").replace("--", " ")
    return " ".join(tn.split())


def is_heading(text):
    """Heading bila: (a) efektif <=70 kar (tanpa shalawat) dan berbentuk
    kurung berdiri sendiri / diawali kata rubrik (aturan lama); ATAU
    (b) <=120 kar DAN diawali kata heading (daftar diperluas) ATAU berkurung
    berdiri sendiri, DAN bukan ciri riwayat (قال:/حدثنا/أخبرنا) DAN tidak
    diakhiri tanda kutip/koma (potongan kalimat)."""
    tn = norm(text)
    if not tn:
        return False
    ts = _strip_shalawat(tn)
    if not ts:
        return False
    toks = ts.split()
    first_is_heading = bool(toks) and (toks[0] in HEADING_WORDS or ts.startswith("ما نزل"))
    bracketed = (
        (ts.startswith("(") and (ts.endswith(")") or ts.endswith(":")))
        or (ts.startswith("[") and ts.endswith("]"))
    )
    if len(ts) <= 70:
        return bracketed or first_is_heading
    # Aturan panjang (b): heading bersarang Thabaqat dkk.
    if len(ts) > 120:
        return False
    if any(m in ts for m in _NARRATION_MARKS):
        return False
    if ts.endswith(_TRAILING_BAD):
        return False
    return first_is_heading or bracketed


def is_poetry_line(text):
    """Satu paragraf mengandung pemisah shathr ` ... ` / ` … ` (bait syair)."""
    return " ... " in text or " … " in text


def flag_poetry(paras):
    """Tandai paragraf bait syair: pemisah shathr, ATAU baris pendek
    berima (<=70 kar, bukan heading) yang mengikuti bait sebelumnya
    (shathr lanjutan)."""
    flags = [is_poetry_line(t) for t in paras]
    for i, t in enumerate(paras):
        if (
            not flags[i]
            and i > 0
            and flags[i - 1]
            and len(t.strip()) <= 70
            and not is_heading(t)
        ):
            flags[i] = True
    return flags


def is_nasab_list(text):
    """Paragraf daftar orang: nama diikuti `بن` berulang di token awal."""
    toks = _tokens(norm(text))
    if len(toks) < 5:
        return False
    early = toks[:4]
    return ("بن" in early) and sum(1 for x in toks[:8] if x == "بن") >= 2


def is_footnote(text):
    """Catatan kaki: diawali (N) atau [N] setelah lstrip."""
    s = text.lstrip()
    if len(s) < 3 or s[0] not in "([":
        return False
    close = ")" if s[0] == "(" else "]"
    i = 1
    while i < len(s) and s[i].isdigit():
        i += 1
    return 1 < i < len(s) and s[i] == close


def parse_paras_range(s):
    """Parse 'A-B' -> (a, b); InputError bila format salah atau a > b."""
    parts = s.split("-")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise InputError(f"--paras '{s}' tidak valid — format A-B (mis. 0-40)")
    a, b = int(parts[0]), int(parts[1])
    if a > b:
        raise InputError(f"--paras {a}-{b}: A harus <= B")
    return a, b


def entry_to_seg(row):
    """Baris person_entries (SELECT dgn source) -> dict segmen seragam."""
    (entry_id, source, entry_num, _name_ar, _ls, _lm, _lc,
     from_page, from_para, to_page, to_para, n_pages, basis, _gen) = row
    return {
        "seg_id": entry_id, "from_page": from_page, "from_para": from_para,
        "to_page": to_page, "to_para": to_para, "n_pages": n_pages,
        "basis": basis or f"entri kamus no. {entry_num}", "truncated": 0,
    }


def get_page_meta(cur, source, web_page):
    row = cur.execute(
        "SELECT printed_juz, printed_page, url FROM pages WHERE source = ? AND web_page = ?"
        " ORDER BY para_idx LIMIT 1",
        (source, web_page),
    ).fetchone()
    return row  # (juz, hal, url) atau None


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


def citation(juz, page, url):
    if url is None:
        return "(halaman sumber tidak tercatat di DB)"
    juz_part = f"juz {juz} " if juz is not None else ""
    page_part = f"hal {page} · " if page is not None else ""
    return f"{juz_part}{page_part}{url}"


def parse_sources(spec, allowed):
    """Filter -s terhadap SOURCE_ORDER; return list urut tampil, dibatasi allowed."""
    if not spec:
        return list(allowed)
    chosen = [s.strip() for s in spec.split(",") if s.strip()]
    if not chosen:
        raise InputError("daftar sumber kosong")
    unknown = [s for s in chosen if s not in VALID_SOURCES]
    if unknown:
        raise InputError(
            f"sumber tidak dikenal: {', '.join(unknown)} — valid: {', '.join(SOURCE_ORDER)}"
        )
    chosen = set(chosen)
    return [s for s in allowed if s in chosen]


# --- Resolusi event ---
def resolve_event(cur, q):
    """Return baris events untuk query; raise InputError bila 0 / banyak kandidat.

    Prioritas: (0) event_id persis; (1) kecocokan persis name_norm / alias /
    name_id (case-insensitive); (2) substring. Bila tier-1 kosong dan tier-2
    >1, kandidat ditampilkan lalu exit 2.
    """
    q = q.strip()
    row = cur.execute(
        "SELECT event_id, name_ar, name_id, aliases_ar, era, year_h, year_note, name_norm, seq"
        " FROM events WHERE event_id = ?",
        (q,),
    ).fetchone()
    if row:
        return dict(zip(_EV_COLS, row))
    qn = norm(q)
    ql = q.lower()
    like = f"%{like_escape(qn)}%" if qn else None
    rows1 = []
    if qn:
        for r in cur.execute(
            "SELECT event_id, name_ar, name_id, aliases_ar, era, year_h, year_note, name_norm, seq"
            " FROM events WHERE name_norm = ?"
            " OR ' ' || (SELECT aliases_norm FROM event_fts WHERE event_fts.rowid = events.seq) || ' '"
            "   LIKE '% ' || ? || ' %'"
            " ORDER BY seq",
            (qn, qn),
        ):
            rows1.append(dict(zip(_EV_COLS, r)))
    for r in cur.execute(
        "SELECT event_id, name_ar, name_id, aliases_ar, era, year_h, year_note, name_norm, seq"
        " FROM events WHERE lower(name_id) = ? ORDER BY seq",
        (ql,),
    ):
        d = dict(zip(_EV_COLS, r))
        if d not in rows1:
            rows1.append(d)
    if len(rows1) == 1:
        return rows1[0]
    rows2 = []
    seen = {r["event_id"] for r in rows1}
    if qn:
        for r in cur.execute(
            "SELECT event_id, name_ar, name_id, aliases_ar, era, year_h, year_note, name_norm, seq"
            " FROM events WHERE name_norm LIKE ? ESCAPE '\\' ORDER BY seq",
            (like,),
        ):
            d = dict(zip(_EV_COLS, r))
            if d["event_id"] not in seen:
                rows2.append(d)
                seen.add(d["event_id"])
        for r in cur.execute(
            "SELECT e.event_id, e.name_ar, e.name_id, e.aliases_ar, e.era, e.year_h,"
            " e.year_note, e.name_norm, e.seq"
            " FROM event_fts f JOIN events e ON e.seq = f.rowid"
            " WHERE f.aliases_norm LIKE ? ESCAPE '\\' ORDER BY e.seq",
            (like,),
        ):
            d = dict(zip(_EV_COLS, r))
            if d["event_id"] not in seen:
                rows2.append(d)
                seen.add(d["event_id"])
    for r in cur.execute(
        "SELECT event_id, name_ar, name_id, aliases_ar, era, year_h, year_note, name_norm, seq"
        " FROM events WHERE lower(name_id) LIKE ? ESCAPE '\\' ORDER BY seq",
        (f"%{like_escape(ql)}%",),
    ):
        d = dict(zip(_EV_COLS, r))
        if d["event_id"] not in seen:
            rows2.append(d)
            seen.add(d["event_id"])
    cands = rows1 if rows1 else rows2
    if not cands:
        raise InputError(
            f"event '{q}' tidak ditemukan — coba `lookup.py search {q}` atau `event --list`"
        )
    print(f"# Kandidat event untuk \"{q}\" ({len(cands)})\n")
    for d in cands:
        year = f"{d['year_h']} H" if d["year_h"] is not None else d["era"] or "-"
        print(f"- {d['event_id']} — {d['name_ar']} — {d['name_id']} ({year})")
    print()
    raise InputError(f"lebih dari satu kandidat — pilih event_id lalu jalankan ulang")


_EV_COLS = ("event_id", "name_ar", "name_id", "aliases_ar", "era", "year_h", "year_note", "name_norm", "seq")


# --- Resolusi person ---
def person_source_count(cur, ishabah_id):
    return cur.execute(
        "SELECT COUNT(DISTINCT source) FROM person_entries WHERE ishabah_id = ?",
        (ishabah_id,),
    ).fetchone()[0]


def resolve_person(cur, q):
    """Return baris persons untuk query; InputError bila 0 / banyak kandidat.

    Angka -> ishabah_id persis. Teks -> nama dicari bertingkat: persis
    persons.name_norm, LIKE persons.name_norm, person_fts (index atas semua
    entri kamus), dan LIKE person_entries.name_norm semua kamus — hasil
    dikelompokkan ke ishabah_id. Kandidat diurutkan menurun menurut jumlah
    sumber tertaut, lalu jumlah entri yang namanya memuat frasa query, lalu
    ishabah_id. Persis tunggal langsung dipakai tanpa daftar kandidat.
    """
    q = q.strip()
    if q.isdigit():
        n = int(q)
        row = cur.execute(
            "SELECT ishabah_id, name_ar, name_norm, kunya, from_page, from_para, to_page, to_para"
            " FROM persons WHERE ishabah_id = ?",
            (n,),
        ).fetchone()
        if not row:
            raise InputError(f"ishabah_id {n} tidak ada di tabel persons (rentang 1..9710)")
        return dict(zip(_P_COLS, row))
    qn = norm(q)
    if not qn:
        raise InputError("query kosong")
    like = f"%{like_escape(qn)}%"
    expr = fts_expr(qn)
    seen = set()
    cands = []

    def add(row):
        d = dict(zip(_P_COLS, row))
        if d["ishabah_id"] not in seen:
            seen.add(d["ishabah_id"])
            cands.append(d)

    # Tier 1: persis persons.name_norm.
    for r in cur.execute(
        "SELECT ishabah_id, name_ar, name_norm, kunya, from_page, from_para, to_page, to_para"
        " FROM persons WHERE name_norm = ? ORDER BY ishabah_id",
        (qn,),
    ):
        add(r)
    # Persis tunggal -> langsung (nama lengkap Ishabah yang unik).
    exact = [d for d in cands if d["name_norm"] == qn]
    if len(exact) == 1:
        return exact[0]
    # Tier 2: LIKE persons.name_norm.
    for r in cur.execute(
        "SELECT ishabah_id, name_ar, name_norm, kunya, from_page, from_para, to_page, to_para"
        " FROM persons WHERE name_norm LIKE ? ESCAPE '\\' ORDER BY ishabah_id",
        (like,),
    ):
        add(r)
    # Tier 3: person_fts — index FTS atas name_norm SEMUA entri kamus;
    # kelompokkan entri yang tertaut ke persons.
    if expr:
        for r in cur.execute(
            "SELECT DISTINCT p.ishabah_id, p.name_ar, p.name_norm, p.kunya,"
            " p.from_page, p.from_para, p.to_page, p.to_para"
            " FROM person_fts f JOIN person_entries pe ON pe.entry_id = f.rowid"
            " JOIN persons p ON p.ishabah_id = pe.ishabah_id"
            " WHERE person_fts MATCH ? ORDER BY p.ishabah_id",
            (expr,),
        ):
            add(r)
    # Tier 4: LIKE name_norm semua entri kamus (bukan hanya persons).
    for r in cur.execute(
        "SELECT DISTINCT p.ishabah_id, p.name_ar, p.name_norm, p.kunya,"
        " p.from_page, p.from_para, p.to_page, p.to_para"
        " FROM person_entries pe JOIN persons p ON p.ishabah_id = pe.ishabah_id"
        " WHERE pe.name_norm LIKE ? ESCAPE '\\' ORDER BY p.ishabah_id",
        (like,),
    ):
        add(r)
    if not cands:
        raise InputError(
            f"person '{q}' tidak ditemukan — coba `lookup.py search {q}`"
        )
    if len(cands) == 1:
        return cands[0]
    # Skor: jumlah sumber tertaut + jumlah entri yang namanya memuat frasa.
    ids = [d["ishabah_id"] for d in cands]
    nsrc, nent = {}, {}
    for i in range(0, len(ids), 500):  # chunk IN agar aman batas variabel SQLite
        chunk = ids[i:i + 500]
        marks = ",".join("?" * len(chunk))
        for iid, n in cur.execute(
            "SELECT ishabah_id, COUNT(DISTINCT source) FROM person_entries"
            f" WHERE ishabah_id IN ({marks}) GROUP BY ishabah_id",
            chunk,
        ):
            nsrc[iid] = n
        for iid, n in cur.execute(
            "SELECT ishabah_id, COUNT(*) FROM person_entries"
            f" WHERE ishabah_id IN ({marks}) AND name_norm LIKE ? ESCAPE '\\'"
            " GROUP BY ishabah_id",
            chunk + [like],
        ):
            nent[iid] = n
    cands.sort(key=lambda d: (-nsrc.get(d["ishabah_id"], 0), -nent.get(d["ishabah_id"], 0), d["ishabah_id"]))
    print(f"# Kandidat person untuk \"{q}\" ({len(cands)})\n")
    for d in cands[:15]:
        print(f"- {d['ishabah_id']} — {d['name_ar']} ({nsrc.get(d['ishabah_id'], 0)} sumber)")
    if len(cands) > 15:
        print(f"… {len(cands) - 15} kandidat lain, persempit kata kunci")
    # Saran bila kandidat teratas dominan: >=4 sumber dan pesaing terdekat <=2.
    top_n = nsrc.get(cands[0]["ishabah_id"], 0)
    second_n = nsrc.get(cands[1]["ishabah_id"], 0) if len(cands) > 1 else 0
    if top_n >= 4 and second_n <= 2:
        print(f"\nKemungkinan besar: {cands[0]['ishabah_id']} — jalankan `person {cands[0]['ishabah_id']}`")
    print()
    raise InputError(f"lebih dari satu kandidat — pilih ishabah_id lalu jalankan ulang")


_P_COLS = ("ishabah_id", "name_ar", "name_norm", "kunya", "from_page", "from_para", "to_page", "to_para")


def year_of_event(d):
    if d["year_h"] is not None:
        return f"{d['year_h']} H"
    return d["era"] or "-"


# --- Render segmen (dipakai event & year) ---
def render_segments(cur, sources, segs_by_source, budget):
    """Kumpulkan hasil per sumber. Return (results, missing).

    segs_by_source: dict source -> list of seg rows. Budget --max-chars
    berlaku PER SEGMEN: tiap segmen dapat potongan penuh N karakter
    (potong di batas paragraf), sehingga tiap segmen minimal memuat
    paragraf heading + paragraf berikutnya.
    """
    results, missing = [], []
    for source in sources:
        segs = segs_by_source.get(source) or []
        if not segs:
            missing.append(source)
            continue
        for seg in segs:
            from_page, from_para = seg["from_page"], seg["from_para"]
            to_page, to_para = seg["to_page"], seg["to_para"]
            paras = fetch_paragraphs(cur, source, from_page, from_para, to_page, to_para)
            kept, total, was_truncated = truncate(paras, budget)
            meta = get_page_meta(cur, source, from_page)
            juz, page, url = meta if meta else (None, None, None)
            r = {
                "source": source,
                "seg_id": seg["seg_id"],
                "from_page": from_page,
                "to_page": to_page,
                "from_para": from_para,
                "to_para": to_para,
                "n_pages": seg.get("n_pages"),
                "basis": seg.get("basis"),
                "cut_by_edition": bool(seg.get("truncated")),
                "paragraphs": kept,
                "para_count_total": total,
                "output_truncated": was_truncated,
                "printed_juz": juz,
                "printed_page": page,
                "url": url,
            }
            results.append(r)
    return results, missing


def render_markdown_sections(src_meta, sources, results, missing, meta_line_fmt, budget):
    """Bagian output markdown per sumber (header + meta + paragraf + sitasi)."""
    lines = []
    for r in results:
        m = src_meta[r["source"]]
        lines.append(f"## {m['title_ar']} — {m['title_id']}")
        if m["note"]:
            lines.append(f"- Catatan edisi: {m['note']}")
        lines.append(meta_line_fmt(r))
        if r["cut_by_edition"]:
            lines.append("- Catatan: edisi elektronik terputus di sini")
        lines.append("")
        for p in r["paragraphs"]:
            lines.append(p)
        if r["output_truncated"]:
            lines.append("")
            lines.append(f"…dipotong, {r['para_count_total']} paragraf total di segmen ini, pakai --max-chars 0")
        lines.append("")
        lines.append(f"— Sumber: {citation(r['printed_juz'], r['printed_page'], r['url'])}")
        lines.append("")
    for source in missing:
        m = src_meta[source]
        lines.append(f"## {m['title_ar']} — {m['title_id']}")
        lines.append(MISSING_NOTE)
        lines.append("")
    if budget > 0:
        lines.append(
            f"(Batas potong per segmen: {budget} karakter — gunakan --max-chars 0 untuk teks penuh.)"
        )
    return "\n".join(lines).rstrip() + "\n"


# --- Mode MATERI/LENGKAP: --toc & --paras ---
def _toc_section(rows, flags, h_idx, end):
    """Meta sub-bab: (kchar, types) untuk rentang paragraf h_idx..end."""
    chars = sum(len(rows[i][2]) for i in range(h_idx, end + 1))
    body = [rows[i][2] for i in range(h_idx + 1, end + 1)]
    types = []
    if body:
        f_note = sum(is_footnote(t) for t in body) / len(body)
        f_poetry = sum(flags[i] for i in range(h_idx + 1, end + 1)) / len(body)
        f_nasab = sum(is_nasab_list(t) for t in body) / len(body)
        if f_note >= 0.6:
            types.append("catatan")
        if f_poetry >= 0.6:
            types.append("syair")
        elif f_nasab >= 0.6:
            types.append("nasab")
    return chars / 1000.0, types


def render_toc(cur, src_meta, segs_by_source, sources, desc, fmt, seg_label="seg_id"):
    """Daftar isi per segmen: seg_id, hal.web, jumlah paragraf, ~kchar total,
    jumlah syair/nasab, lalu sub-heading dgn rentang [A-B], ~kchar, penanda jenis."""
    segments = []
    for source in sources:
        for seg in segs_by_source.get(source) or []:
            rows = fetch_paragraphs_indexed(
                cur, source, seg["from_page"], seg["from_para"], seg["to_page"], seg["to_para"]
            )
            flags = flag_poetry([t for _, _, t in rows])
            head_list = [(i, t) for i, (_, _, t) in enumerate(rows) if is_heading(t)]
            headings = []
            for k, (i, t) in enumerate(head_list):
                end = (head_list[k + 1][0] - 1) if k + 1 < len(head_list) else len(rows) - 1
                kchar, types = _toc_section(rows, flags, i, end)
                headings.append({
                    "para_idx": i, "title": t, "range": [i, end],
                    "kchar": round(kchar, 1), "types": types,
                })
            segments.append({
                "seg_id": seg["seg_id"], "source": source,
                "from_page": seg["from_page"], "to_page": seg["to_page"],
                "n_paras": len(rows), "headings": headings,
                "kchar": round(sum(len(t) for _, _, t in rows) / 1000.0, 1),
                "n_poetry": sum(flags),
                "n_nasab": sum(is_nasab_list(t) for _, _, t in rows),
            })
    if fmt == "json":
        print(render_json({"query": {"desc": desc}, "segments": segments}), end="")
        return
    lines = [f"# Daftar isi: {desc}", ""]
    for s in segments:
        m = src_meta[s["source"]]
        lines.append(f"## {m['title_ar']} — {m['title_id']}")
        lines.append(
            f"- {seg_label}: {s['seg_id']}, hal.web {s['from_page']}–{s['to_page']},"
            f" {s['n_paras']} paragraf, ~{s['kchar']} kchar"
            f" (syair {s['n_poetry']}, nasab {s['n_nasab']})"
        )
        lines.append("")
        for h in s["headings"]:
            marks = " ".join(f"[{t}]" for t in h["types"])
            tail = f" [{h['range'][0]}–{h['range'][1]}] ~{h['kchar']} kchar"
            if marks:
                tail += f" {marks}"
            lines.append(f"{h['para_idx']:>5}  {h['title'].rstrip()}{tail}")
        if not s["headings"]:
            lines.append("(tanpa sub-heading terdeteksi)")
        lines.append("")
    if not segments:
        lines.append("(tidak ada segmen di sumber terpilih)")
        lines.append("")
    print("\n".join(lines).rstrip() + "\n", end="")


def render_paras(cur, src_meta, source, seg, a, b, desc, fmt, seg_label="seg_id",
                 skip_poetry=False):
    """Cetak paragraf A..B (0-based) dari satu segmen, sitasi tiap ganti halaman.

    skip_poetry=True melewati paragraf bait syair dan mencetak satu baris
    placeholder (… N bait syair dilewati, paragraf X–Y) per rentang terlewati.
    """
    rows = fetch_paragraphs_indexed(
        cur, source, seg["from_page"], seg["from_para"], seg["to_page"], seg["to_para"]
    )
    n = len(rows)
    if not rows or a >= n:
        hi = n - 1 if n else 0
        raise InputError(f"rentang --paras {a}-{b} di luar segmen (paragraf tersedia 0..{hi})")
    b = min(b, n - 1)
    flags = flag_poetry([t for _, _, t in rows])
    page_meta = {}

    def meta_for(wp):
        if wp not in page_meta:
            page_meta[wp] = get_page_meta(cur, source, wp)
        return page_meta[wp] or (None, None, None)

    sel = list(range(a, b + 1))
    if skip_poetry:
        kept_idx = [i for i in sel if not flags[i]]
        skipped_runs = []
        run_start = None
        for i in sel:
            if flags[i]:
                if run_start is None:
                    run_start = i
            elif run_start is not None:
                skipped_runs.append((run_start, i - 1))
                run_start = None
        if run_start is not None:
            skipped_runs.append((run_start, sel[-1]))
    else:
        kept_idx = sel
        skipped_runs = []

    if fmt == "json":
        paras_out = []
        for i in kept_idx:
            wp, pi, t = rows[i]
            juz, page, url = meta_for(wp)
            paras_out.append({
                "para_idx": i, "web_page": wp, "printed_juz": juz,
                "printed_page": page, "url": url, "text": t,
            })
        payload = {
            "query": {"desc": desc, "source": source, seg_label: seg["seg_id"],
                      "para_range": [a, b], "n_paras": n, "skip_poetry": skip_poetry},
            "paragraphs": paras_out,
        }
        if skip_poetry:
            payload["poetry_skipped"] = [
                {"from": x, "to": y, "n": y - x + 1} for x, y in skipped_runs
            ]
        print(render_json(payload), end="")
        return
    lines = [f"# {desc}", "",
             f"- Paragraf {a}–{b} dari {n} (indeks 0-based, relatif dari awal segmen)", ""]
    skip_set = {i for x, y in skipped_runs for i in range(x, y + 1)}
    printed_runs = list(skipped_runs)
    last_page = None
    for i in kept_idx:
        wp, pi, t = rows[i]
        # placeholder untuk rentang bait yang terlewati sebelum paragraf ini
        while printed_runs and printed_runs[0][1] < i:
            x, y = printed_runs.pop(0)
            lines.append(f"(… {y - x + 1} bait syair dilewati, paragraf {x}–{y})")
        if wp != last_page:
            juz, page, url = meta_for(wp)
            lines.append(f"— halaman: {citation(juz, page, url)}")
            lines.append("")
            last_page = wp
        lines.append(t)
    for x, y in printed_runs:
        lines.append(f"(… {y - x + 1} bait syair dilewati, paragraf {x}–{y})")
    lines.append("")
    print("\n".join(lines), end="")


def render_subbab(cur, src_meta, source, seg, subbabs, base_desc, fmt,
                  seg_label="seg_id", skip_poetry=False):
    """Cetak satu/lebih sub-bab (dari sub-heading sampai sub-heading berikutnya).

    Tiap argumen --subbab berupa para_idx heading ATAU teks awalan judul
    (dibandingkan ter-norm; ambigu -> daftar kandidat, exit 2).
    """
    rows = fetch_paragraphs_indexed(
        cur, source, seg["from_page"], seg["from_para"], seg["to_page"], seg["to_para"]
    )
    n = len(rows)
    head_list = [(i, t) for i, (_, _, t) in enumerate(rows) if is_heading(t)]
    for arg in subbabs:
        arg = arg.strip()
        if arg.isdigit():
            idx = int(arg)
            matches = [(i, t) for i, t in head_list if i == idx]
            if not matches:
                hi = head_list[-1][0] if head_list else 0
                raise InputError(
                    f"--subbab {arg}: tidak ada sub-heading di para_idx {arg}"
                    f" (heading tersedia s.d. {hi}) — lihat --toc"
                )
        else:
            qn = _strip_shalawat(norm(arg)).lstrip("([ ")
            if not qn:
                raise InputError("--subbab kosong")
            matches = [(i, t) for i, t in head_list
                       if _strip_shalawat(norm(t)).lstrip("([ ").startswith(qn)]
            if not matches:
                raise InputError(
                    f"--subbab '{arg}': tidak ada sub-heading berawalan itu — lihat --toc"
                )
            if len(matches) > 1:
                print(f"# Kandidat sub-bab untuk \"{arg}\" ({len(matches)})\n")
                for i, t in matches[:20]:
                    print(f"{i:>5}  {t}")
                print()
                raise InputError("lebih dari satu sub-bab — pakai para_idx dari --toc")
        h_idx, h_title = matches[0]
        nxt = [i for i, _ in head_list if i > h_idx]
        end = (nxt[0] - 1) if nxt else n - 1
        render_paras(cur, src_meta, source, seg, h_idx, end,
                     f"{base_desc} — sub-bab [{h_idx}–{end}]: {h_title.strip()}",
                     fmt, seg_label, skip_poetry)


# --- Sub-perintah: event ---
def cmd_event(cur, src_meta, q, sources_spec, fmt, budget, list_all, toc=False, seg=None,
              paras=None, subbab=None, exclude_poetry=False):
    sources = parse_sources(sources_spec, EVENT_SOURCES)
    if list_all:
        rows = cur.execute(
            "SELECT event_id, name_ar, name_id, era, year_h FROM events ORDER BY seq"
        ).fetchall()
        if fmt == "json":
            print(render_json({"events": [
                {"event_id": r[0], "name_ar": r[1], "name_id": r[2], "era": r[3], "year_h": r[4]}
                for r in rows
            ]}), end="")
            return
        lines = ["# Daftar event (urut kronologis registry)", "",
                 "| event_id | Arab | Indonesia | Era | Tahun H |", "|---|---|---|---|---|"]
        for event_id, name_ar, name_id, era, year_h in rows:
            y = year_h if year_h is not None else ""
            lines.append(f"| `{event_id}` | {name_ar} | {name_id} | {era or ''} | {y} |")
        print("\n".join(lines) + "\n", end="")
        return

    ev = resolve_event(cur, q)
    event_id = ev["event_id"]
    desc = f"{ev['name_ar']} — {ev['name_id']}"
    # Rollup tahunan tahun_N_h: tampilkan year_segments + rujukan silang.
    if event_id.startswith("tahun_") and event_id.endswith("_h"):
        cmd_year(cur, src_meta, ev["year_h"], fmt, budget, toc, seg, paras,
                 subbab, exclude_poetry, title=desc)
        return

    segs_by_source = {}
    for source in EVENT_SOURCES:
        segs = [
            dict(seg_id=s, from_page=fp, from_para=fq, to_page=tp, to_para=tq,
                 n_pages=np_, basis=b, truncated=tr)
            for s, fp, fq, tp, tq, np_, b, tr in cur.execute(
                "SELECT seg_id, from_page, from_para, to_page, to_para, n_pages, basis, truncated"
                " FROM event_segments WHERE event_id = ? AND source = ? ORDER BY seg_id",
                (event_id, source),
            )
        ]
        if segs:
            segs_by_source[source] = segs
    if toc:
        render_toc(cur, src_meta, segs_by_source, sources, desc, fmt)
        return
    if seg is not None:
        match = [(src, s) for src, lst in segs_by_source.items() for s in lst if s["seg_id"] == seg]
        if not match:
            raise InputError(f"seg_id {seg} bukan segmen event '{event_id}' — lihat `event {event_id} --toc`")
        msrc, mseg = match[0]
        if paras is not None:
            render_paras(cur, src_meta, msrc, mseg, paras[0], paras[1],
                         f"{desc} — segmen {seg}", fmt, skip_poetry=exclude_poetry)
            return
        if subbab:
            render_subbab(cur, src_meta, msrc, mseg, subbab, f"{desc} — segmen {seg}",
                          fmt, skip_poetry=exclude_poetry)
            return
        if exclude_poetry:
            render_paras(cur, src_meta, msrc, mseg, 0, 10**9,
                         f"{desc} — segmen {seg} (tanpa bait syair)", fmt,
                         skip_poetry=True)
            return
        segs_by_source = {msrc: [mseg]}
        sources = [msrc]
    results, missing = render_segments(cur, sources, segs_by_source, budget)

    def meta_line(r):
        return (
            f"- Segmen: {r['seg_id']}, hal.web {r['from_page']}–{r['to_page']}, {r['basis']}"
        )

    if fmt == "json":
        payload = {
            "query": {
                "event_id": event_id, "name_ar": ev["name_ar"], "name_id": ev["name_id"],
                "aliases_ar": json.loads(ev["aliases_ar"]) if ev["aliases_ar"] else [],
                "era": ev["era"], "year_h": ev["year_h"], "year_note": ev["year_note"],
            },
            "results": results,
            "missing_sources": missing,
        }
        print(render_json(payload), end="")
        return

    aliases = []
    if ev["aliases_ar"]:
        try:
            aliases = json.loads(ev["aliases_ar"])
        except ValueError:
            pass
    lines = [f"# {ev['name_ar']} — {ev['name_id']}", "",
             f"- event_id: `{event_id}` · era: {ev['era'] or '-'} · tahun: "
             f"{year_of_event(ev)}"
             + (f" ({ev['year_note']})" if ev["year_note"] else "")]
    if aliases:
        lines.append(f"- Alias: {'، '.join(aliases)}")
    lines.append("")
    out = render_markdown_sections(src_meta, sources, results, missing, meta_line, budget)
    print("\n".join(lines) + "\n" + out, end="")


# --- Sub-perintah: person ---
def person_meta_line(r):
    conf = f"/{r['link_confidence']}" if r["link_confidence"] else ""
    s = (
        f"- Entri: no. {r['entry_num']} (entry_id {r['entry_id']}), "
        f"hal.web {r['from_page']}–{r['to_page']}, tautan: {r['link_status']}{conf}"
    )
    if r["link_confidence"] in ("medium", "low"):
        s += f" — tautan entitas: {r['link_confidence']} — verifikasi nasab"
    return s


def person_entry_result(cur, row, budget):
    """Baris person_entries (SELECT dgn source di posisi 1) -> dict hasil render."""
    (entry_id, source, entry_num, name_ar, link_status, link_method, link_confidence,
     from_page, from_para, to_page, to_para, n_pages, basis, generation) = row
    paras = fetch_paragraphs(cur, source, from_page, from_para, to_page, to_para)
    # Budget PER ENTRI (segmen kamus): tiap entri dapat potongan penuh N.
    kept, total, was_truncated = truncate(paras, budget)
    meta = get_page_meta(cur, source, from_page)
    juz, page, url = meta if meta else (None, None, None)
    return {
        "source": source,
        "entry_id": entry_id,
        "entry_num": entry_num,
        "name_ar": name_ar,
        "link_status": link_status,
        "link_method": link_method,
        "link_confidence": link_confidence,
        "generation": generation,
        "from_page": from_page,
        "to_page": to_page,
        "n_pages": n_pages,
        "basis": basis,
        "cut_by_edition": False,
        "paragraphs": kept,
        "para_count_total": total,
        "output_truncated": was_truncated,
        "printed_juz": juz,
        "printed_page": page,
        "url": url,
    }


def cmd_person(cur, src_meta, q, sources_spec, fmt, budget, toc=False, seg=None,
              paras=None, subbab=None, exclude_poetry=False):
    p = resolve_person(cur, q)
    ishabah_id = p["ishabah_id"]
    desc = f"{p['name_ar']} — Ishabah no. {ishabah_id}"
    all_entries = cur.execute(
        "SELECT entry_id, source, entry_num, name_ar, link_status, link_method, link_confidence,"
        " from_page, from_para, to_page, to_para, n_pages, basis, generation"
        " FROM person_entries WHERE ishabah_id = ? ORDER BY entry_id",
        (ishabah_id,),
    ).fetchall()
    if toc:
        segs_by_source = {}
        for row in all_entries:
            segs_by_source.setdefault(row[1], []).append(entry_to_seg(row))
        render_toc(cur, src_meta, segs_by_source,
                   parse_sources(sources_spec, PERSON_SOURCES), desc, fmt,
                   seg_label="entry_id")
        return
    if seg is not None:
        rows = [r for r in all_entries if r[0] == seg]
        if not rows:
            raise InputError(f"entry_id {seg} bukan entri dari '{desc}' — lihat --toc")
        row = rows[0]
        source = row[1]
        if paras is not None:
            render_paras(cur, src_meta, source, entry_to_seg(row), paras[0], paras[1],
                         f"{desc} — entri no. {row[2]} ({source})", fmt,
                         seg_label="entry_id", skip_poetry=exclude_poetry)
            return
        if subbab:
            render_subbab(cur, src_meta, source, entry_to_seg(row), subbab,
                          f"{desc} — entri no. {row[2]} ({source})", fmt,
                          seg_label="entry_id", skip_poetry=exclude_poetry)
            return
        if exclude_poetry:
            render_paras(cur, src_meta, source, entry_to_seg(row), 0, 10**9,
                         f"{desc} — entri no. {row[2]} ({source}) (tanpa bait syair)", fmt,
                         seg_label="entry_id", skip_poetry=True)
            return
        r = person_entry_result(cur, row, budget)
        if fmt == "json":
            print(render_json({
                "query": {"ishabah_id": ishabah_id, "name_ar": p["name_ar"],
                           "kunya": p["kunya"], "entry_id": seg, "source": source,
                           "ishabah_pages": [p["from_page"], p["to_page"]]},
                "results": [r], "missing_sources": [],
            }), end="")
            return
        lines = [f"# {desc}", ""]
        if p["kunya"] and p["kunya"] != p["name_ar"]:
            lines.append(f"- Kunya: {p['kunya']}")
        lines.append(
            f"- Entri kanonik: hal.web {p['from_page']}–{p['to_page']}"
            f" ({p['to_page'] - p['from_page'] + 1} hal.), tertaut di"
            f" {person_source_count(cur, ishabah_id)} sumber"
        )
        lines.append("")
        out = render_markdown_sections(src_meta, [source], [r], [], person_meta_line, budget)
        print("\n".join(lines) + "\n" + out, end="")
        return

    sources = parse_sources(sources_spec, PERSON_SOURCES)
    results, missing = [], []
    for source in sources:
        entries = sorted([r for r in all_entries if r[1] == source], key=lambda r: r[2])
        if not entries:
            missing.append(source)
            continue
        for row in entries:
            results.append(person_entry_result(cur, row, budget))

    meta_line = person_meta_line

    if fmt == "json":
        payload = {
            "query": {
                "ishabah_id": ishabah_id, "name_ar": p["name_ar"], "kunya": p["kunya"],
                "ishabah_pages": [p["from_page"], p["to_page"]],
            },
            "results": results,
            "missing_sources": missing,
        }
        print(render_json(payload), end="")
        return

    lines = [f"# {desc}", ""]
    if p["kunya"] and p["kunya"] != p["name_ar"]:
        lines.append(f"- Kunya: {p['kunya']}")
    nsrc = person_source_count(cur, ishabah_id)
    lines.append(f"- Entri kanonik: hal.web {p['from_page']}–{p['to_page']} ({p['to_page'] - p['from_page'] + 1} hal.), tertaut di {nsrc} sumber")
    lines.append("")
    out = render_markdown_sections(src_meta, sources, results, missing, meta_line, budget)
    print("\n".join(lines) + "\n" + out, end="")


# --- Sub-perintah: year ---
def year_body(cur, n, budget):
    """Segmen 'سنة N' Thabari + daftar event registry tahun N."""
    segs = [
        dict(seg_id=s, year_title=t, from_page=fp, from_para=fq, to_page=tp, to_para=tq,
             n_pages=None, basis=f"segmen tahun: {t}", truncated=0)
        for s, t, fp, fq, tp, tq in cur.execute(
            "SELECT seg_id, year_title, from_page, from_para, to_page, to_para"
            " FROM year_segments WHERE year_h = ? ORDER BY seg_id",
            (n,),
        )
    ]
    segs_by_source = {"tarikh_tabari": segs} if segs else {}
    results, missing = render_segments(cur, ["tarikh_tabari"], segs_by_source, budget)
    # Rentang tahun yang tersedia sebagai segmen Thabari (untuk catatan bila N tak ada).
    cov = cur.execute(
        "SELECT MIN(year_h), MAX(year_h) FROM year_segments"
    ).fetchone()
    year_cov = [int(cov[0]), int(cov[1])] if cov and cov[0] is not None else None
    events = [
        {"event_id": r[0], "name_ar": r[1], "name_id": r[2], "year_h": r[3]}
        for r in cur.execute(
            "SELECT event_id, name_ar, name_id, year_h FROM events"
            " WHERE year_h = ? AND event_id NOT LIKE 'tahun\\_%' ESCAPE '\\' ORDER BY seq",
            (n,),
        )
    ]
    return {
        "results": results,
        "missing_sources": missing,
        "events": events,
        "year_segment_coverage": year_cov,
    }


def year_markdown(cur, src_meta, title, n, body, budget):
    lines = [f"# {title}", ""]
    for r in body["results"]:
        m = src_meta[r["source"]]
        lines.append(f"## {m['title_ar']} — {m['title_id']}")
        if m["note"]:
            lines.append(f"- Catatan edisi: {m['note']}")
        lines.append(
            f"- Segmen: {r['seg_id']}, hal.web {r['from_page']}–{r['to_page']}, {r['basis']}"
        )
        lines.append("")
        for p in r["paragraphs"]:
            lines.append(p)
        if r["output_truncated"]:
            lines.append("")
            lines.append(f"…dipotong, {r['para_count_total']} paragraf total di segmen ini, pakai --max-chars 0")
        lines.append("")
        lines.append(f"— Sumber: {citation(r['printed_juz'], r['printed_page'], r['url'])}")
        lines.append("")
    for source in body["missing_sources"]:
        m = src_meta[source]
        lines.append(f"## {m['title_ar']} — {m['title_id']}")
        cov = body.get("year_segment_coverage")
        if cov:
            lines.append(
                f"segmen \"سنة {n}\" tidak tersedia di sumber ini (cakupan segmen tahun Thabari"
                f" dalam DB: tahun {cov[0]}–{cov[1]} H; tahun di luar itu tidak dipisah"
                " sebagai rubrik tersendiri di edisi ini)."
            )
        else:
            lines.append(MISSING_NOTE)
        lines.append("")
    evs = body["events"]
    lines.append(f"## Peristiwa tahun {n} H dalam registry ({len(evs)})")
    lines.append("")
    if evs:
        for e in evs:
            lines.append(f"- `{e['event_id']}` — {e['name_ar']} — {e['name_id']}")
    else:
        lines.append("(tidak ada event registry bertahun ini)")
    lines.append("")
    if budget > 0:
        lines.append(
            f"(Batas potong per segmen: {budget} karakter — gunakan --max-chars 0 untuk teks penuh.)"
        )
    return "\n".join(lines).rstrip() + "\n"


def cmd_year(cur, src_meta, n, fmt, budget, toc=False, seg=None, paras=None,
             subbab=None, exclude_poetry=False, title=None):
    segs = [
        dict(seg_id=s, year_title=t, from_page=fp, from_para=fq, to_page=tp, to_para=tq,
             n_pages=None, basis=f"segmen tahun: {t}", truncated=0)
        for s, t, fp, fq, tp, tq in cur.execute(
            "SELECT seg_id, year_title, from_page, from_para, to_page, to_para"
            " FROM year_segments WHERE year_h = ? ORDER BY seg_id",
            (n,),
        )
    ]
    desc = title or f"Tahun {n} H"
    segs_by_source = {"tarikh_tabari": segs} if segs else {}
    if toc:
        render_toc(cur, src_meta, segs_by_source, ["tarikh_tabari"], desc, fmt)
        return
    if seg is not None:
        m = [x for x in segs if x["seg_id"] == seg]
        if not m:
            raise InputError(f"seg_id {seg} bukan segmen tahun {n} H — lihat `year {n} --toc`")
        srow = m[0]
        if paras is not None:
            render_paras(cur, src_meta, "tarikh_tabari", srow, paras[0], paras[1],
                         f"{desc} — segmen {seg}", fmt, skip_poetry=exclude_poetry)
            return
        if subbab:
            render_subbab(cur, src_meta, "tarikh_tabari", srow, subbab,
                          f"{desc} — segmen {seg}", fmt, skip_poetry=exclude_poetry)
            return
        if exclude_poetry:
            render_paras(cur, src_meta, "tarikh_tabari", srow, 0, 10**9,
                         f"{desc} — segmen {seg} (tanpa bait syair)", fmt, skip_poetry=True)
            return
        results, _ = render_segments(cur, ["tarikh_tabari"],
                                     {"tarikh_tabari": [srow]}, budget)

        def meta_line(r):
            return (
                f"- Segmen: {r['seg_id']}, hal.web {r['from_page']}–{r['to_page']}, {r['basis']}"
            )

        print(render_markdown_sections(src_meta, ["tarikh_tabari"], results, [],
                                       meta_line, budget), end="")
        return
    body = year_body(cur, n, budget)
    if fmt == "json":
        payload = {"query": {"year_h": n}}
        payload.update(body)
        print(render_json(payload), end="")
        return
    print(year_markdown(cur, src_meta, desc, n, body, budget), end="")


# --- Sub-perintah: search ---
# --- Sub-perintah: search ---
def _tokens(s):
    """Token kata: urutan karakter alfanumerik (Arab/Latin/angka)."""
    toks, cur_ = [], []
    for ch in s:
        if ch.isalnum():
            cur_.append(ch)
        elif cur_:
            toks.append("".join(cur_))
            cur_ = []
    if cur_:
        toks.append("".join(cur_))
    return toks


def word_tier(hay, needle):
    """Skor kecocokan: 100 persis / 60 kata-utuh (frasa berbatas) /
    40 awalan kata / 10 substring bebas / 0 tidak cocok."""
    if not hay or not needle:
        return 0
    if hay == needle:
        return 100
    toks = _tokens(hay)
    joined = " " + " ".join(toks) + " "
    ntoks = _tokens(needle)
    nq = " ".join(ntoks)
    if not nq:
        return 0
    if f" {nq} " in joined:
        return 60
    if len(ntoks) == 1 and any(t.startswith(nq) for t in toks):
        return 40
    if nq in hay:
        return 10
    return 0


def tier_label(score):
    if score >= 100:
        return "Cocok persis"
    if score >= 60:
        return "Cocok kata"
    return "Cocok sebagian"


def score_event(qn, ql, name_norm, aliases_ar, name_id):
    """Skor event = maksimum tier dari name_norm, alias utuh (parse JSON),
    dan name_id (case-insensitive, untuk query Latin/Indonesia).
    Return (score, name_tier) — name_tier dipakai tie-break agar kecocokan
    pada nama utama mengungguli kecocokan yang hanya di alias."""
    name_tier = word_tier(name_norm, qn)
    if ql and name_id:
        nid = name_id.lower()
        name_tier = max(name_tier, 100 if nid == ql else word_tier(nid, ql))
    score = name_tier
    if aliases_ar:
        try:
            aliases = json.loads(aliases_ar)
        except ValueError:
            aliases = []
        for al in aliases:
            an = norm(al)
            if an == qn:
                score = max(score, 100)
            else:
                score = max(score, word_tier(an, qn))
    return score, name_tier


def _render_scored(title, items, limit=15):
    """Bagian hasil berperingkat: kelompok 'Cocok persis/kata/sebagian',
    maks `limit` baris + baris sisa."""
    print(f"## {title} ({len(items)})")
    if not items:
        print("(tidak ada)")
        print()
        return
    last_label = None
    for score, line in items[:limit]:
        lab = tier_label(score)
        if lab != last_label:
            print(f"### {lab}")
            last_label = lab
        print(line)
    if len(items) > limit:
        print(f"… {len(items) - limit} lagi, persempit kata kunci")
    print()


def cmd_search(cur, q):
    q = q.strip()
    if not q:
        raise InputError("query kosong")
    qn = norm(q)
    ql = q.lower()
    like = f"%{like_escape(qn)}%" if qn else None
    # Rollup tahun_N_h hanya relevan bila query soal tahun.
    show_rollup = q.isdigit() or "سنه" in qn or "tahun" in ql

    # --- Event: FTS (name+alias) + LIKE name_norm/aliases_norm + name_id ---
    ev_seen = {}
    expr = fts_expr(qn)
    _EV_SEL = "event_id, name_ar, name_id, era, year_h, seq, name_norm, aliases_ar"
    if expr:
        for r in cur.execute(
            f"SELECT e.{_EV_SEL.replace(', ', ', e.')}"
            " FROM event_fts f JOIN events e ON e.seq = f.rowid"
            " WHERE event_fts MATCH ? ORDER BY e.seq",
            (expr,),
        ):
            ev_seen[r[0]] = r
    if like:
        for r in cur.execute(
            f"SELECT {_EV_SEL} FROM events"
            " WHERE name_norm LIKE ? ESCAPE '\\' ORDER BY seq",
            (like,),
        ):
            ev_seen.setdefault(r[0], r)
        for r in cur.execute(
            f"SELECT e.{_EV_SEL.replace(', ', ', e.')}"
            " FROM event_fts f JOIN events e ON e.seq = f.rowid"
            " WHERE f.aliases_norm LIKE ? ESCAPE '\\' ORDER BY e.seq",
            (like,),
        ):
            ev_seen.setdefault(r[0], r)
    for r in cur.execute(
        f"SELECT {_EV_SEL} FROM events"
        " WHERE lower(name_id) LIKE ? ESCAPE '\\' ORDER BY seq",
        (f"%{like_escape(ql)}%",),
    ):
        ev_seen.setdefault(r[0], r)

    ev_items, hidden_rollups = [], 0
    for r in sorted(ev_seen.values(), key=lambda r: r[5]):
        event_id, name_ar, name_id, era, year_h, seq, name_norm, aliases_ar = r
        is_rollup = event_id.startswith("tahun_") and event_id.endswith("_h")
        if is_rollup and not show_rollup:
            hidden_rollups += 1
            continue
        score, name_tier = score_event(qn, ql, name_norm, aliases_ar, name_id)
        y = f"{year_h} H" if year_h is not None else (era or "-")
        ev_items.append((score, name_tier, seq, f"- `{event_id}` — {name_ar} — {name_id} ({y})"))
    ev_items.sort(key=lambda t: (-t[0], -t[1], t[2]))
    ev_items = [(s, line) for s, _, _, line in ev_items]

    # --- Person: persons.name_norm (LIKE) + person_fts, kelompok ishabah_id ---
    per_seen = {}
    if like:
        for r in cur.execute(
            "SELECT ishabah_id, name_ar, name_norm FROM persons WHERE name_norm LIKE ? ESCAPE '\\'"
            " ORDER BY ishabah_id",
            (like,),
        ):
            per_seen[r[0]] = r
    if expr:
        for r in cur.execute(
            "SELECT DISTINCT p.ishabah_id, p.name_ar, p.name_norm"
            " FROM person_fts f JOIN person_entries pe ON pe.entry_id = f.rowid"
            " JOIN persons p ON p.ishabah_id = pe.ishabah_id"
            " WHERE person_fts MATCH ? ORDER BY p.ishabah_id",
            (expr,),
        ):
            per_seen.setdefault(r[0], r)
    ids = list(per_seen)
    nsrc = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        marks = ",".join("?" * len(chunk))
        for iid, n in cur.execute(
            "SELECT ishabah_id, COUNT(DISTINCT source) FROM person_entries"
            f" WHERE ishabah_id IN ({marks}) GROUP BY ishabah_id",
            chunk,
        ):
            nsrc[iid] = n
    per_items = []
    for iid in sorted(per_seen):
        _, name_ar, name_norm = per_seen[iid]
        score = word_tier(name_norm, qn)
        for (en,) in cur.execute(
            "SELECT name_norm FROM person_entries WHERE ishabah_id = ?", (iid,)
        ):
            score = max(score, word_tier(en, qn))
        per_items.append((score, -nsrc.get(iid, 0), iid,
                          f"- Ishabah no. {iid} — {name_ar} ({nsrc.get(iid, 0)} sumber)"))
    per_items.sort(key=lambda t: (-t[0], t[1], t[2]))
    per_items = [(s, line) for s, _, _, line in per_items]

    # Entri kamus yang belum tertaut (tanpa ishabah_id) — tampil apa adanya.
    unlinked = []
    if expr:
        for r in cur.execute(
            "SELECT DISTINCT pe.source, pe.entry_num, pe.name_ar"
            " FROM person_fts f JOIN person_entries pe ON pe.entry_id = f.rowid"
            " WHERE person_fts MATCH ? AND pe.ishabah_id IS NULL"
            " ORDER BY pe.source, pe.entry_num LIMIT 20",
            (expr,),
        ):
            unlinked.append(r)
    elif like:
        for r in cur.execute(
            "SELECT DISTINCT pe.source, pe.entry_num, pe.name_ar"
            " FROM person_entries pe WHERE pe.name_norm LIKE ? ESCAPE '\\' AND pe.ishabah_id IS NULL"
            " ORDER BY pe.source, pe.entry_num LIMIT 20",
            (like,),
        ):
            unlinked.append(r)

    if not ev_items and not per_items and not unlinked:
        raise InputError(f"'{q}' tidak ditemukan di event maupun person")

    print(f"# Pencarian: {q}\n")
    _render_scored("Event", ev_items)
    if hidden_rollups:
        print(f"({hidden_rollups} entri tahun disembunyikan — pakai `year N`)")
        print()
    _render_scored("Person", per_items)
    if unlinked:
        print("## Entri kamus belum tertaut ke Ishabah (maks. 20)")
        for source, entry_num, name_ar in unlinked:
            print(f"- {source} no. {entry_num} — {name_ar} (belum tertaut)")
    print()


# --- Sub-perintah: coverage ---
def cmd_coverage(cur, kind):
    if kind not in (None, "event", "person"):
        raise InputError("coverage hanya menerima 'event' atau 'person'")
    if kind in (None, "event"):
        total = cur.execute(
            "SELECT COUNT(*) FROM events WHERE event_id NOT LIKE 'tahun\\_%' ESCAPE '\\'"
        ).fetchone()[0]
        rows = []
        for source in EVENT_SOURCES:
            seg = cur.execute(
                "SELECT COUNT(DISTINCT event_id) FROM event_segments WHERE source = ?",
                (source,),
            ).fetchone()[0]
            absent = cur.execute(
                "SELECT COUNT(*) FROM event_absent WHERE source = ?", (source,)
            ).fetchone()[0]
            rows.append({
                "source": source, "covered": seg, "absent": absent, "total": total,
                "percent": round(seg / total * 100, 1) if total else 0.0,
            })
        print(f"# Cakupan event per sumber (registry: {total} event)\n")
        print("| Sumber | Event bersegmen | Absen eksplisit | Cakupan |\n|---|---|---|---|")
        for r in rows:
            print(
                f"| {r['source']} | {r['covered']} | {r['absent']} | "
                f"{r['percent']}% |"
            )
        print()
    if kind in (None, "person"):
        print("# Cakupan person per sumber\n")
        print("| Sumber | Entri | Tertaut Ishabah | Persen |\n|---|---|---|---|")
        for source in PERSON_SOURCES:
            n = cur.execute(
                "SELECT COUNT(*) FROM person_entries WHERE source = ?", (source,)
            ).fetchone()[0]
            linked = cur.execute(
                "SELECT COUNT(*) FROM person_entries WHERE source = ?"
                " AND link_status IN ('resolved','canonical')",
                (source,),
            ).fetchone()[0]
            pct = f"{linked / n * 100:.1f}%" if n else "-"
            print(f"| {source} | {n} | {linked} | {pct} |")
        meta_pct = cur.execute("SELECT value FROM meta WHERE key='link_resolved_pct'").fetchone()
        if meta_pct:
            print(f"\nKeseluruhan link_resolved_pct (meta): {meta_pct[0]}")
        print()


# --- Sub-perintah: info ---
def cmd_info(cur, db_path):
    meta = dict(cur.execute("SELECT key, value FROM meta").fetchall())
    n_paras = cur.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    n_pages = cur.execute(
        "SELECT COUNT(DISTINCT source || '/' || web_page) FROM pages"
    ).fetchone()[0]
    size = os.path.getsize(db_path)
    print("# sirah_full.db — info\n")
    print(f"- File: `{db_path}` ({size / 1024 / 1024:.1f} MB)")
    print(f"- Dibangun: {meta.get('built_at', '?')} · scrape: {meta.get('scrape_date', '?')}")
    print(f"- Registry event: {meta.get('n_events', '?')} ({meta.get('registry_version', '?')})")
    print(f"- Halaman: {meta.get('n_pages', n_pages)} · Paragraf: {meta.get('n_paras', n_paras)}")
    print(f"- Segmen event: {meta.get('n_event_segments', '?')} · Absen: {meta.get('n_absent', '?')}"
          f" · Segmen tahun Thabari: {meta.get('n_year_segments', '?')}")
    print(f"- Person Ishabah: {meta.get('n_persons', '?')} · Entri kamus: {meta.get('n_person_entries', '?')}"
          f" · link_resolved_pct: {meta.get('link_resolved_pct', '?')}")
    dup = meta.get("dup_ishabah_nums")
    if dup:
        print(f"- entry_num Ishabah duplikat (dipakai yang pertama): {dup}")
    print("\n## Sumber\n")
    print("| source | kitab (Arab) | Indonesia | peran | catatan |\n|---|---|---|---|---|")
    for source, title_ar, title_id, role, note in cur.execute(
        "SELECT source, title_ar, title_id, role, note FROM sources ORDER BY rowid"
    ):
        print(f"| {source} | {title_ar} | {title_id} | {role} | {note or ''} |")
    print()


def render_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main():
    ap = argparse.ArgumentParser(
        prog="lookup.py",
        description="Query verbatim sirah_full.db — 10 kitab sirah/tarikh/thabaqat/kamus shahabat.",
    )
    ap.add_argument("--db", help="path DB SQLite, .zip, atau .xz (default: dicari otomatis, lihat env SIRAH_DB)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p, with_text_opts=True, with_paging=False):
        p.add_argument("--db", default=argparse.SUPPRESS,
                       help=argparse.SUPPRESS)
        if with_text_opts:
            p.add_argument("-s", "--sources", help="filter sumber, dipisah koma (default: semua)")
            p.add_argument("--format", choices=["markdown", "json"], default="markdown",
                           help="format output (default: markdown)")
            p.add_argument("--max-chars", type=int, default=None, metavar="N",
                           help="batas karakter per segmen/entri, potong di batas paragraf (default 6000; 0 = penuh; dengan --seg default penuh)")
        if with_paging:
            p.add_argument("--toc", action="store_true",
                           help="daftar isi per segmen: sub-heading, rentang paragraf, ~kchar, penanda jenis (syair/nasab/catatan)")
            p.add_argument("--seg", type=int, metavar="ID",
                           help="batasi ke satu segmen (event/year: seg_id; person: entry_id)")
            p.add_argument("--paras", metavar="A-B",
                           help="cetak hanya paragraf A..B (0-based) dari --seg, sitasi tiap ganti halaman")
            p.add_argument("--subbab", action="append", metavar="IDX|JUDUL",
                           help="cetak sub-bab (para_idx heading atau awalan judul); boleh diulang; wajib --seg")
            p.add_argument("--exclude-poetry", action="store_true",
                           help="lewati paragraf bait syair (placeholder jujur di tempatnya); untuk --seg/--paras/--subbab")

    p_ev = sub.add_parser("event", help="event per event_id / nama Arab / Indonesia")
    p_ev.add_argument("query", nargs="?", help="event_id, nama (Arab/Indonesia), atau alias")
    p_ev.add_argument("--list", action="store_true", help="daftar semua event urut kronologis")
    add_common(p_ev, with_paging=True)

    p_per = sub.add_parser("person", help="entri kamus shahabat per ishabah_id / nama")
    p_per.add_argument("query", help="ishabah_id (angka) atau nama Arab")
    add_common(p_per, with_paging=True)

    p_year = sub.add_parser("year", help="segmen 'سنة N' Thabari + event registry tahun N")
    p_year.add_argument("year", help="tahun Hijriah (angka)")
    add_common(p_year, with_paging=True)

    p_se = sub.add_parser("search", help="cari event & person (FTS + LIKE), tampilkan kandidat + id")
    p_se.add_argument("query", help="kata kunci Arab/Indonesia")
    add_common(p_se, with_text_opts=False)

    p_cov = sub.add_parser("coverage", help="ringkasan cakupan per sumber")
    p_cov.add_argument("kind", nargs="?", choices=["event", "person"],
                       help="batasi ke event atau person (default: keduanya)")
    add_common(p_cov, with_text_opts=False)

    p_info = sub.add_parser("info", help="meta DB, daftar sumber, provenance")
    add_common(p_info, with_text_opts=False)

    args = ap.parse_args()

    # Validasi opsi paging (--toc/--seg/--paras/--subbab) & anggaran efektif.
    toc, seg, paras, subbab = False, None, None, None
    exclude_poetry = False
    try:
        if args.cmd in ("event", "person", "year"):
            toc = getattr(args, "toc", False)
            seg = getattr(args, "seg", None)
            paras_s = getattr(args, "paras", None)
            subbab = getattr(args, "subbab", None)
            exclude_poetry = getattr(args, "exclude_poetry", False)
            if (paras_s is not None or subbab or exclude_poetry) and seg is None:
                raise InputError("--paras/--subbab/--exclude-poetry hanya berlaku bersama --seg")
            if paras_s is not None and subbab:
                raise InputError("--paras dan --subbab tidak bisa dipakai bersamaan")
            if (paras_s is not None or subbab) and toc:
                raise InputError("--toc tidak bisa dikombinasikan dengan --paras/--subbab")
            if (args.cmd == "event" and getattr(args, "list", False)
                    and (toc or seg is not None or paras_s is not None or subbab or exclude_poetry)):
                raise InputError("--list tidak bisa dikombinasikan dengan --toc/--seg/--paras/--subbab/--exclude-poetry")
            if paras_s is not None:
                paras = parse_paras_range(paras_s)
        mc = getattr(args, "max_chars", None)
        if mc is not None and mc < 0:
            raise InputError("--max-chars tidak boleh negatif (0 = tanpa batas)")
        if args.cmd == "event" and not args.list and not args.query:
            raise InputError("berikan event_id/nama, atau pakai --list")
    except InputError as e:
        fail(str(e))
    budget = mc if mc is not None else (0 if seg is not None else 6000)

    db_path = args.db if hasattr(args, "db") else None
    if db_path is None:
        db_path = find_db()
        if db_path is None:
            fail_db_missing(autodl_failed=True)  # find_db() sudah mencoba auto-download
    db_path = Path(db_path)
    if db_path.suffix.lower() == ".zip":
        db_path = extract_zip_db(db_path)
    elif db_path.suffix.lower() == ".xz":
        db_path = extract_xz_db(db_path)
    con = open_db(db_path)
    cur = con.cursor()
    src_meta = load_sources(cur)

    try:
        if args.cmd == "event":
            cmd_event(cur, src_meta, args.query, args.sources, args.format, budget,
                      args.list, toc, seg, paras, subbab, exclude_poetry)
        elif args.cmd == "person":
            cmd_person(cur, src_meta, args.query, args.sources, args.format, budget,
                       toc, seg, paras, subbab, exclude_poetry)
        elif args.cmd == "year":
            try:
                n = int(args.year)
            except ValueError:
                raise InputError(f"tahun '{args.year}' bukan angka")
            if not 1 <= n <= 100:
                raise InputError(f"tahun {n} di luar rentang 1–100 H")
            cmd_year(cur, src_meta, n, args.format, budget, toc, seg, paras, subbab, exclude_poetry)
        elif args.cmd == "search":
            cmd_search(cur, args.query)
        elif args.cmd == "coverage":
            cmd_coverage(cur, args.kind)
        elif args.cmd == "info":
            cmd_info(cur, db_path)
    except InputError as e:
        fail(str(e))
    finally:
        con.close()


if __name__ == "__main__":
    main()
