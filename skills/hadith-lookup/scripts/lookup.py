#!/usr/bin/env python3
"""lookup.py — CLI query hadits verbatim dari hadith_full.db (12 kitab).

Usage:
    python lookup.py bukhari:1                         # satu hadits (nomor cetak edisi)
    python lookup.py muslim:8 bukhari:2-4              # banyak rujukan sekaligus
    python lookup.py bukhari:1,2,5-7                   # daftar/rentang nomor
    python lookup.py "abu dawud:4" ahmad:3978          # alias Latin/Indonesia/Arab
    python lookup.py --search "انما الاعمال بالنيات" [-b bukhari,muslim] [--limit 10]
    python lookup.py --bab bukhari "الجنب يتوضأ"        # cari judul bab/kitab
    python lookup.py --list-books                      # kitab & cakupan di DB
    python lookup.py bukhari:1 --format json --no-notes --max-chars 0 --offset 0

Exit codes: 0 sukses (termasuk 'tidak ditemukan' — dinyatakan jujur di keluaran),
2 input salah, 3 DB tidak ditemukan/error DB.
Stdlib only (Python 3.8+): sqlite3, argparse, json, os, re, sys, glob, tempfile,
lzma, zipfile, urllib.request.

DB dicari otomatis (lihat find_db()): env HADITH_DB -> assets skill -> cwd ->
upload Cowork/claude.ai -> folder lokal pemilik -> unduh otomatis (.xz) -> exit 3.
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

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # pragma: no cover
        pass

# --- Resolusi DB -----------------------------------------------------------
SKILL_DIR = Path(__file__).resolve().parent.parent
DB_NAME = "hadith_full.db"
# Folder lokal pemilik (laptop). Override: env HADITH_LOCAL_DB. Dilewati bila
# HADITH_LOOKUP_SKIP_LOCAL di-set.
LOCAL_DB = os.environ.get("HADITH_LOCAL_DB", "")  # opsional: path DB lokal pemilik
COWORK_DIRS = ("/mnt/user-data/uploads", "/mnt/user-data", str(Path.home() / "uploads"))
# Sumber 1 GitHub release repo skill, sumber 2 cadangan; URL tidak dicetak ke log.
AUTO_DL_URLS = (
    "https://github.com/B-ngoen/sirah-tafsir-skills/releases/download/hadith-v1/hadith_full.db.xz",
    "https://github.com/B-ngoen/refdb/releases/download/v1/hadith_full.db.xz",
)
AUTO_DL_TIMEOUT = 15
try:
    CACHE_MIN_BYTES = int(os.environ.get("HADITH_CACHE_MIN_BYTES", 20 * 1024 * 1024))
except ValueError:
    CACHE_MIN_BYTES = 20 * 1024 * 1024


def _cache_dir():
    """Cache PERMANEN (bukan Temp yang diberesi OS). HADITH_CACHE_DIR = override eksplisit."""
    cands = []
    if os.environ.get("HADITH_CACHE_DIR"):
        cands.append(Path(os.environ["HADITH_CACHE_DIR"]))
    if os.environ.get("LOCALAPPDATA"):
        cands.append(Path(os.environ["LOCALAPPDATA"]) / "hadith-lookup")
    xdg = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    cands.append(Path(xdg) / "hadith-lookup")
    fallback = Path(tempfile.gettempdir()) / "hadith-lookup"
    cands.append(fallback)
    for c in cands:
        try:
            c.mkdir(parents=True, exist_ok=True)
            return c
        except OSError:
            continue
    return fallback


CACHE_DIR = _cache_dir()
DB_VERSION = "v1"  # naikkan bila skema/isi DB berubah -> cache lama tidak dipakai ulang
CACHE_DB = CACHE_DIR / f"hadith_full_{DB_VERSION}.db"
AUTO_DL_XZ = CACHE_DIR / f"hadith_full_{DB_VERSION}.db.xz"

# --- Kitab -----------------------------------------------------------------
# Urutan = urutan tampilan. (judul, edisi) hanya cadangan bila tabel books kosong.
BOOKS = {
    "bukhari": ("صحيح البخاري", "ط السلطانية (طوق النجاة)، ترقيم عبد الباقي"),
    "muslim": ("صحيح مسلم", "ت محمد فؤاد عبد الباقي"),
    "abudawud": ("سنن أبي داود", "ت محيي الدين عبد الحميد"),
    "nasai": ("سنن النسائي (المجتبى)", "ط الرسالة العالمية، ترقيم أبو غدة"),
    "ibnmajah": ("سنن ابن ماجه", "ت محمد فؤاد عبد الباقي"),
    "tirmidhi": ("سنن الترمذي", "ت أحمد شاكر وآخرون"),
    "muwatta": ("موطأ مالك رواية يحيى", "ت محمد فؤاد عبد الباقي"),
    "ahmad": ("مسند أحمد", "ط الرسالة، ت الأرنؤوط وآخرون"),
    "darimi": ("مسند الدارمي (سنن الدارمي)", "ت حسين سليم أسد"),
    "bulugh": ("بلوغ المرام", "ت سمير الزهيري، دار الفلق ط7"),
    "riyadh_arnaut": ("رياض الصالحين", "ت الأرنؤوط، الرسالة ط3"),
    "riyadh_albani": ("تحقيق رياض الصالحين للألباني", "المكتب الإسلامي (selektif)"),
}
# Kitab yang hadits-haditsnya dinilai sahih secara umum oleh ulama (keterangan umum, BUKAN kutipan edisi).
GENERAL_SAHIH = {"bukhari", "muslim"}

_ALIASES = {
    "bukhari": ["bukhari", "al-bukhari", "bukhori", "shahih bukhari", "sahih bukhari", "sahih al-bukhari",
                "البخاري", "بخاري", "صحيح البخاري"],
    "muslim": ["muslim", "shahih muslim", "sahih muslim", "مسلم", "صحيح مسلم"],
    "abudawud": ["abu dawud", "abudawud", "abu daud", "abu dawood", "abu dawud", "sunan abu dawud",
                 "sunan abi dawud", "abi dawud", "سنن أبي داود", "أبو داود", "ابو داود", "أبي داود"],
    "nasai": ["nasai", "an-nasa'i", "nasa'i", "al-nasai", "nasaai", "sunan nasai", "sunan an-nasa'i",
              "النسائي", "سنن النسائي", "نسائي"],
    "ibnmajah": ["ibnu majah", "ibn majah", "ibnmajah", "ibnumajah", "ibnu majjah", "majah",
                 "sunan ibn majah", "sunan ibnu majah", "ابن ماجه", "سنن ابن ماجه", "ماجه"],
    "tirmidhi": ["tirmidzi", "tirmidhi", "tirmizi", "at-tirmidzi", "at-tirmidhi", "termidzi",
                 "sunan tirmidzi", "sunan tirmidhi", "jami tirmidhi", "jami' at-tirmidzi",
                 "الترمذي", "ترمذي", "سنن الترمذي"],
    "muwatta": ["muwattha", "muwatta", "muwatha", "malik", "muwatta malik", "muwattha malik", "al-muwatta",
                "موطأ", "الموطأ", "موطأ مالك", "مالك"],
    "ahmad": ["ahmad", "musnad ahmad", "ahmad bin hanbal", "ahmad ibn hanbal", "imam ahmad",
              "مسند أحمد", "أحمد", "احمد"],
    "darimi": ["darimi", "ad-darimi", "addarimi", "sunan darimi", "musnad darimi",
               "الدارمي", "سنن الدارمي", "مسند الدارمي"],
    "bulugh": ["bulughul maram", "bulugh al-maram", "bulugh", "bulughulmaram", "bulugh maram",
               "بلوغ المرام", "بلوغ"],
    "riyadh_arnaut": ["riyadhus shalihin", "riyadhus salihin", "riyadush shalihin", "riyadhussholihin",
                      "riyadh", "riyadh as-salihin", "riyadh al-salihin", "riyad", "riyadh_arnaut",
                      "رياض الصالحين"],
    "riyadh_albani": ["riyadh albani", "riyadh_albani", "riyadhus shalihin albani",
                      "تحقيق رياض الصالحين للألباني", "رياض الصالحين للألباني"],
}

# --- Normalisasi (HARUS identik dengan yang dipakai builder DB untuk hadith_fts) --
_DROP = set(range(0x064B, 0x0653)) | {0x0670, 0x0640} | set(range(0x06D6, 0x06EE))
_CMAP = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}


def _nchar(ch):
    """Satu karakter -> versi ternormalisasi ('' bila dibuang). Pemetaan 1:0/1:1."""
    if ord(ch) in _DROP:
        return ""
    return _CMAP.get(ch, ch)


def normalize(s):
    """Buang harakat/superscript-alef/tatweel/tanda Quran; satukan alif (أإآٱ->ا), ى->ي, ة->ه."""
    return re.sub(r"\s+", " ", "".join(_nchar(c) for c in s)).strip()


def norm_with_map(s):
    """(teks_ternormalisasi_tanpa_collapse, peta indeks -> indeks asli) untuk cuplikan verbatim."""
    out, idx = [], []
    for i, ch in enumerate(s):
        n = _nchar(ch)
        if n:
            out.append(n)
            idx.append(i)
    return "".join(out), idx


_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def akey(s):
    s = normalize(s.translate(_AR_DIGITS)).lower()
    return re.sub(r"[\W_]+", "", s)


ALIAS_MAP = {}
for _k, _al in _ALIASES.items():
    for _a in _al + [_k, BOOKS[_k][0]]:
        ALIAS_MAP.setdefault(akey(_a), _k)
_STRIP_PREFIX = ("shahih", "sahih", "sunan", "imam", "kitab", "hr", "musnad")


class InputError(Exception):
    """Kesalahan input pengguna -> exit code 2."""


def fail(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_book(name):
    k = akey(name)
    if not k:
        raise InputError("nama kitab kosong")
    if k in ALIAS_MAP:
        return ALIAS_MAP[k]
    for p in _STRIP_PREFIX:
        if k.startswith(p) and k[len(p):] in ALIAS_MAP:
            return ALIAS_MAP[k[len(p):]]
    if len(k) >= 4:  # awalan unik
        hits = {v for a, v in ALIAS_MAP.items() if a.startswith(k)}
        if len(hits) == 1:
            return hits.pop()
    raise InputError(f"kitab '{name}' tidak dikenal — valid: {', '.join(BOOKS)} (alias Latin/Indonesia/Arab diterima; lihat --list-books)")


def parse_books(spec):
    if not spec:
        return list(BOOKS)
    out = []
    for part in re.split(r"[,;]", spec):
        if part.strip():
            b = resolve_book(part.strip())
            if b not in out:
                out.append(b)
    if not out:
        raise InputError("daftar kitab kosong")
    return out


MAX_RANGE = 2000


def parse_ref(tok):
    """'bukhari:1' / 'bukhari:1,2' / 'bukhari:1-3' / 'abu dawud:4,9-11' -> (book, [(a,b,kitab_no|None),...]).
    Muwatta (tanpa nomor global): 'muwatta:K/N', 'malik:K/N', 'muwatta:K/N1-N2'; 'muwatta:N' polos -> kitab_no None
    (kandidatnya didaftar, bukan dipilih diam-diam)."""
    if ":" not in tok:
        raise InputError(f"rujukan '{tok}' tidak valid — format: KITAB:NOMOR (mis. bukhari:1, muslim:8, bukhari:1-3, bukhari:1,2, muwatta:K/N)")
    name, nums = tok.rsplit(":", 1)
    book = resolve_book(name)
    spans = []
    for part in nums.translate(_AR_DIGITS).split(","):
        part = part.strip()
        m = re.fullmatch(r"(?:(\d+)\s*/\s*)?(\d+)\s*(?:-\s*(\d+))?", part)
        if not m:
            raise InputError(f"nomor '{part}' pada '{tok}' tidak valid — pakai angka, daftar 1,2, rentang 1-3 (Muwatta: K/N)")
        k = int(m.group(1)) if m.group(1) else None
        if k is not None and book != "muwatta":
            raise InputError(f"format K/N hanya untuk Muwatta (edisi tanpa nomor global); '{tok}' tidak valid")
        a = int(m.group(2))
        b = int(m.group(3)) if m.group(3) else a
        if a > b:
            raise InputError(f"rentang {a}-{b} terbalik pada '{tok}'")
        if b - a + 1 > MAX_RANGE:
            raise InputError(f"rentang {a}-{b} terlalu lebar (maks {MAX_RANGE} nomor per rentang)")
        spans.append((a, b, k))
    return book, spans


# --- DB ---------------------------------------------------------------------
def fail_db_missing(path=None, autodl_failed=False):
    msg = "DB hadits tidak ditemukan"
    msg += ("\n!!! UNTUK ASISTEN AI: skill ini gagal karena basis data tidak ada. JANGAN mencari jawaban di web, "
            "situs hadits, kitab lain, atau ingatan Anda sebagai pengganti. Sampaikan pesan ini apa adanya ke "
            "pengguna, tawarkan langkah perbaikan di bawah, lalu BERHENTI.")
    if path:
        msg += f": {path}"
    if autodl_failed:
        msg += "\n(auto-download gagal — server mati, aset belum dirilis, atau tidak ada internet)"
    msg += (
        "\n- Di Cowork/claude.ai: unggah file hadith_full.db.xz (atau .zip/.db) ke sesi ini, lalu jalankan ulang."
        "\n- Di komputer sendiri: letakkan hadith_full.db(.xz) di folder skill/assets atau cwd,"
        " atau set env HADITH_DB / HADITH_LOCAL_DB."
    )
    fail(msg, code=3)


def find_db():
    """Urutan: env HADITH_DB (autoritatif) -> [HADITH_LOOKUP_SKIP_LOCAL=1 langsung ke unduh] ->
    assets skill -> cwd -> folder upload Cowork -> folder lokal pemilik -> unduh otomatis -> None."""
    env = os.environ.get("HADITH_DB", "").strip()
    if env:
        return Path(env)
    if os.environ.get("HADITH_LOOKUP_SKIP_LOCAL", "").strip():
        return download_db()
    cands = []
    for ext in ("", ".zip", ".xz"):
        cands.append(SKILL_DIR / "assets" / (DB_NAME + ext))
    for ext in ("", ".zip", ".xz"):
        cands.append(Path(DB_NAME + ext))
    for d in COWORK_DIRS:
        cands += [Path(x) for x in sorted(glob.glob(os.path.join(d, DB_NAME + "*")))]
    if LOCAL_DB:
        cands += [Path(LOCAL_DB), Path(LOCAL_DB + ".zip"), Path(LOCAL_DB + ".xz")]
    for c in cands:
        if c.is_file():
            return c
    return download_db()


def _dl_urls():
    env = os.environ.get("HADITH_DB_URL", "").strip()
    return tuple(u.strip() for u in env.split(",") if u.strip()) if env else AUTO_DL_URLS


def download_db():
    if CACHE_DB.is_file() and CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return CACHE_DB
    urls = _dl_urls()
    for idx, url in enumerate(urls, 1):
        db = _download_from_url(url, idx, len(urls))
        if db is not None:
            return db
    return None


def _download_from_url(url, idx, n):
    """Unduh satu sumber; URL tidak pernah dicetak (hanya 'sumber unduhan i/n')."""
    print(f"[auto-download] mengunduh DB hadits dari sumber unduhan {idx}/{n}…", file=sys.stderr)
    part = Path(str(AUTO_DL_XZ) + ".part")
    try:
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "hadith-lookup/1"})
        with urllib.request.urlopen(req, timeout=AUTO_DL_TIMEOUT) as resp:
            try:
                total = int(resp.headers.get("Content-Length") or 0)
            except ValueError:
                total = 0
            done, mark = 0, 25
            with open(part, "wb") as dst:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
                    done += len(chunk)
                    if total and done * 100 // total >= mark:
                        print(f"[auto-download] {min(100, done * 100 // total)}% "
                              f"({done // 1048576} MB / {total // 1048576} MB)", file=sys.stderr)
                        mark += 25
        os.replace(part, AUTO_DL_XZ)
    except (urllib.error.URLError, OSError, ValueError) as e:
        try:
            part.unlink()
        except OSError:
            pass
        tail = "coba sumber berikutnya…" if idx < n else "semua sumber gagal."
        print(f"[auto-download] sumber unduhan {idx}/{n} gagal ({type(e).__name__}) — {tail}", file=sys.stderr)
        return None
    db = extract_xz_db(AUTO_DL_XZ)
    try:
        AUTO_DL_XZ.unlink()
    except OSError:
        pass
    return db


def extract_zip_db(zip_path):
    if CACHE_DB.is_file() and CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return CACHE_DB
    try:
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.endswith(".db")]
            if not names:
                fail(f"zip {zip_path} tidak memuat file .db", code=3)
            with zf.open(min(names, key=len)) as src, open(CACHE_DB, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
    except (zipfile.BadZipFile, OSError) as e:
        fail(f"gagal mengekstrak zip {zip_path}: {e}", code=3)
    return CACHE_DB


def extract_xz_db(xz_path):
    if CACHE_DB.is_file() and CACHE_DB.stat().st_size > CACHE_MIN_BYTES:
        return CACHE_DB
    try:
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        with lzma.open(xz_path, "rb") as src, open(CACHE_DB, "wb") as dst:
            while True:
                chunk = src.read(4 * 1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    except (lzma.LZMAError, EOFError, OSError) as e:
        fail(f"gagal mengekstrak xz {xz_path}: {e}", code=3)
    return CACHE_DB


def open_db(db_path):
    if not os.path.isfile(db_path):
        fail_db_missing(db_path)
    try:
        con = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        con.execute("SELECT COUNT(*) FROM hadith")  # smoke test
        return con
    except sqlite3.Error as e:
        fail(f"gagal membuka DB {db_path}: {e}", code=3)


WANT_COLS = ["hid", "book", "num", "num_label", "sub_num", "kitab", "bab", "text", "notes", "grade",
             "grade_by", "juz", "page_from", "page_to", "web_from", "web_to", "url", "num_to", "kitab_no"]


class DB:
    """Pembungkus tipis: tahan terhadap kolom/tabel opsional yang tidak ada (grade_by, xref, books)."""

    def __init__(self, con):
        self.con = con
        have = {r[1] for r in con.execute("PRAGMA table_info(hadith)")}
        self.has_grade_by = "grade_by" in have
        self.has_num_to = "num_to" in have
        self.has_kitab_no = "kitab_no" in have
        self.sel = ", ".join(("h." + c) if c in have else ("NULL AS " + c) for c in WANT_COLS)
        tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        self.has_xref = "xref" in tabs
        self.has_num_fixes = "num_fixes" in tabs
        self.has_books = "books" in tabs
        self.has_fts = any(t.startswith("hadith_fts") for t in tabs)
        self._books = None

    def rows(self, sql, params=()):
        cur = self.con.execute(sql, params)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def books_info(self):
        if self._books is None:
            self._books = {}
            if self.has_books:
                for r in self.rows("SELECT book, book_id, title, edition, n_hadith, num_min, num_max FROM books"):
                    self._books[r["book"]] = r
        return self._books

    def title_edition(self, book):
        info = self.books_info().get(book) or {}
        t = info.get("title") or BOOKS.get(book, (book, ""))[0]
        e = info.get("edition") or BOOKS.get(book, ("", ""))[1]
        return t, e

    def book_range(self, book):
        info = self.books_info().get(book)
        if info and info.get("num_min") is not None:
            return info["num_min"], info["num_max"], info.get("n_hadith")
        r = self.con.execute("SELECT MIN(num), MAX(num), COUNT(*) FROM hadith WHERE book=?", (book,)).fetchone()
        return (r[0], r[1], r[2]) if r and r[2] else (None, None, 0)

    def hadith_by_nums(self, book, spans):
        """Baris yang nomornya (num..num_to) memuat salah satu nomor span; muwatta K/N -> kitab_no=K. Urut hid."""
        conds, params = [], [book]
        for a, b, k in spans:
            if self.has_num_to:
                c = "(h.num BETWEEN ? AND ? OR (h.num_to IS NOT NULL AND h.num < ? AND h.num_to >= ?))"
                p = [a, b, a, a]
            else:
                c, p = "(h.num BETWEEN ? AND ?)", [a, b]
            if k is not None:
                if not self.has_kitab_no:
                    raise InputError("DB ini tidak punya kolom kitab_no — rujukan K/N tidak bisa dipakai")
                c = f"(h.kitab_no = ? AND {c})"
                p = [k] + p
            conds.append(c)
            params += p
        return self.rows(f"SELECT {self.sel} FROM hadith h WHERE h.book=? AND ({' OR '.join(conds)}) ORDER BY h.hid", params)

    def muwatta_candidates(self, n):
        """Semua kitab yang memiliki hadits bernomor n (Muwatta edisi ini tanpa nomor global)."""
        if not self.has_kitab_no:
            return self.rows("SELECT NULL AS kitab_no, kitab, COUNT(*) AS n_rows, MIN(hid) AS hid FROM hadith "
                             "WHERE book='muwatta' AND num=? GROUP BY kitab ORDER BY MIN(hid)", (n,))
        return self.rows("SELECT kitab_no, kitab, COUNT(*) AS n_rows, MIN(hid) AS hid FROM hadith "
                         "WHERE book='muwatta' AND num=? GROUP BY kitab_no, kitab ORDER BY MIN(hid)", (n,))

    def num_fix(self, hid):
        if not self.has_num_fixes:
            return None
        if getattr(self, "_fixes", None) is None:  # tabel kecil, tanpa indeks -> muat sekali
            self._fixes = {r["hid"]: r for r in self.rows(
                "SELECT hid, printed_label, printed_num, assigned_num, reason FROM num_fixes")}
        return self._fixes.get(hid)

    def hadith_by_label(self, book, n):
        """Cadangan: nomor tidak ada di kolom num -> cocokkan token angka utuh pada sub_num/num_label."""
        ar = str(n).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
        rows = self.rows(
            f"SELECT {self.sel} FROM hadith h WHERE h.book=? AND (h.num_label LIKE ? OR h.num_label LIKE ? "
            f"OR h.sub_num LIKE ? OR h.sub_num LIKE ?) ORDER BY h.hid",
            (book, f"%{n}%", f"%{ar}%", f"%{n}%", f"%{ar}%"))
        pat = re.compile(r"(?<!\d)%d(?!\d)" % n)
        out = []
        for r in rows:
            hay = ((r["num_label"] or "") + " " + (r["sub_num"] or "")).translate(_AR_DIGITS)
            if pat.search(hay):
                out.append(r)
        return out

    def xref_hadith(self, book, num):
        """Hadits terkait via tabel xref (dua arah). Return [(method, row)]."""
        if not self.has_xref:
            return []
        pairs = self.con.execute(
            "SELECT ref_book, ref_num, method FROM xref WHERE book=? AND num=? "
            "UNION SELECT book, num, method FROM xref WHERE ref_book=? AND ref_num=?",
            (book, num, book, num)).fetchall()
        out = []
        for rb, rn, method in pairs:
            for r in self.hadith_by_nums(rb, [(rn, rn, None)]):
                out.append((method, r))
        return out


# --- Format keluaran --------------------------------------------------------
def citation(h):
    parts = []
    if h.get("juz") is not None:
        parts.append(f"juz {h['juz']}")
    pf, pt = h.get("page_from"), h.get("page_to")
    if pf is not None:
        parts.append(f"hal {pf}" if pt in (None, pf) else f"hal {pf}–{pt}")
    else:
        parts.append("(halaman cetak tidak tercatat)")
    cite = " ".join(parts)
    return f"{cite} · {h['url']}" if h.get("url") else cite


def grade_lines(h):
    """Derajat HANYA sebagaimana tersimpan; tidak pernah dari ingatan."""
    g = (h.get("grade") or "").strip()
    if g:
        by = (h.get("grade_by") or "").strip()
        who = (f" — otoritas yang tertulis: {by}" if by else
               " — otoritas penilai tidak tercatat di DB (lihat catatan edisi di atas)")
        lines = [f"- Derajat (sebagaimana tertulis di edisi): {g}{who}"]
    elif (h.get("notes") or "").strip():
        lines = ["- Derajat: tidak ada derajat terstruktur yang tersimpan di DB untuk hadits ini. Penilaian (bila ada) "
                 "hanya boleh dibaca dari catatan muhaqqiq verbatim (bukan disimpulkan/diingat); jika catatan tidak "
                 "menyebut derajat, katakan tidak ada."]
    else:
        lines = ["- Derajat: edisi ini tidak mencantumkan derajat untuk hadits ini (tidak ada teks derajat maupun "
                 "catatan muhaqqiq yang tersimpan; jangan diisi dari ingatan)."]
    if h["book"] in GENERAL_SAHIH:
        lines.append("- Keterangan umum (BUKAN kutipan dari edisi ini): hadits dalam kitab ini secara umum "
                     "dinilai sahih oleh jumhur ulama; edisi di DB tidak memuat penilaian per hadits.")
    return lines


def truncate_lines(text, budget):
    """Potong catatan di batas baris (min 1 baris). Return (teks, terpotong?)."""
    if budget <= 0 or len(text) <= budget:
        return text, False
    kept, used = [], 0
    for ln in text.split("\n"):
        if used + len(ln) > budget and kept:
            break
        kept.append(ln)
        used += len(ln) + 1
    return "\n".join(kept), True


def render_hadith(db, h, show_notes, notes_budget, heading="###"):
    """Return (markdown, jumlah_karakter_utama, notes_terpotong)."""
    title, ed = db.title_edition(h["book"])
    lines = [f"{heading} {title} — {ed}  [`{h['book']}`]", f"- Nomor (sebagaimana tercetak): {h['num_label'] or h['num']}"]
    if h.get("num") is not None and str(h["num"]) != (h["num_label"] or ""):
        lines[-1] += f"  (nomor kueri: {h['num']})"
    if h.get("num_to") is not None and h.get("num_to") != h.get("num"):
        lines[-1] += f"  [baris rentang: mencakup nomor {h['num']}–{h['num_to']}]"
    if h.get("sub_num"):
        lines.append(f"- Sub-nomor/penanda varian (sebagaimana tersimpan): {h['sub_num']}")
    fx = db.num_fix(h["hid"]) if h.get("hid") is not None else None
    if fx:
        lines.append(f"- Nomor tercetak di edisi: {fx['printed_label']}; nomor baku {fx['assigned_num']} ditetapkan dari urutan "
                     f"(alasan: {fx['reason']})")
    if h["book"] == "muwatta" and h.get("kitab_no") is not None:
        lines.append(f"- Rujukan Muwatta (edisi tanpa nomor global): kitab ke-{h['kitab_no']}, hadits no. {h['num']} "
                     f"→ `muwatta:{h['kitab_no']}/{h['num']}`")
    if h.get("kitab"):
        lines.append(f"- Kitab: {h['kitab']}")
    if h.get("bab"):
        lines.append(f"- Bab: {h['bab']}")
    lines += ["", "**Teks hadits (verbatim, sanad+matan):**", "", h["text"] or ""]
    cut = False
    if show_notes and h.get("notes"):
        n, cut = truncate_lines(h["notes"], notes_budget)
        lines += ["", "**Catatan muhaqqiq/edisi (verbatim — BUKAN bagian teks hadits):**", "", n]
        if cut:
            lines.append(f"…catatan dipotong (total {len(h['notes'])} karakter), pakai --max-chars 0")
    lines.append("")
    lines += grade_lines(h)
    lines.append(f"— Sumber: {title}، {ed} · {citation(h)}")
    return "\n".join(lines) + "\n", len(h["text"] or ""), cut


def compress_nums(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ",".join(out)


def hadith_dict(db, h, xref=None):
    title, ed = db.title_edition(h["book"])
    d = {k: h.get(k) for k in ("book", "num", "num_label", "sub_num", "kitab", "bab", "text", "notes", "grade", "grade_by")}
    d["book_title"], d["edition"] = title, ed
    d["num_to"], d["kitab_no"] = h.get("num_to"), h.get("kitab_no")
    d["num_fix"] = db.num_fix(h["hid"]) if h.get("hid") is not None else None
    d["grade_stored"] = bool((h.get("grade") or "").strip())
    d["citation"] = {"juz": h.get("juz"), "page_from": h.get("page_from"), "page_to": h.get("page_to"),
                     "web_from": h.get("web_from"), "web_to": h.get("web_to"), "url": h.get("url"),
                     "text": citation(h)}
    if xref is not None:
        d["xref"] = xref
    return d


# --- Perintah ---------------------------------------------------------------
def cmd_refs(db, refs, args):
    """refs = [(book, spans)]. Kumpulkan -> tampilkan dengan anggaran karakter + offset."""
    items, missing, notes, ambiguous = [], [], [], []
    for book, spans in refs:
        lo, hi, n_book = db.book_range(book)
        if book == "muwatta":
            plain = [(a, b) for a, b, k in spans if k is None]
            spans = [(a, b, k) for a, b, k in spans if k is not None]
            for a, b in plain:
                for n in range(a, b + 1):
                    cands = db.muwatta_candidates(n)
                    if len(cands) == 1:
                        spans.append((n, n, cands[0]["kitab_no"]))
                    elif cands:
                        ambiguous.append({"book": book, "num": n, "candidates": cands})
                    else:
                        missing.append({"book": book, "numbers": [n],
                                        "reason": "tidak ada kitab Muwatta yang memuat nomor ini"})
        rows = db.hadith_by_nums(book, spans) if spans else []
        covered = set()
        for r in rows:
            for n in range(r["num"], (r.get("num_to") or r["num"]) + 1):
                covered.add((r.get("kitab_no") if book == "muwatta" else None, n))
        absent = []
        for a, b, k in spans:
            for n in range(a, b + 1):
                if ((k if book == "muwatta" else None), n) not in covered:
                    absent.append((k, n))
        if book != "muwatta":
            for k, n in list(absent):  # cadangan: label verbatim
                alt = db.hadith_by_label(book, n)
                if alt:
                    rows += [r for r in alt if r["hid"] not in {x["hid"] for x in rows}]
                    notes.append(f"{book}:{n} dicocokkan lewat num_label/sub_num verbatim, bukan kolom num.")
                    absent.remove((k, n))
        rows.sort(key=lambda r: r["hid"])
        for r in rows:
            xr = []
            if book.startswith("riyadh"):
                xr = db.xref_hadith(book, r["num"]) if r["num"] is not None else []
            items.append({"row": r, "xref": xr})
        if absent:
            if not n_book:
                reason = "kitab ini belum ada di DB yang terpasang"
            elif book == "muwatta":
                reason = "kombinasi kitab/nomor tidak ada (Muwatta dirujuk sebagai K/N: nomor kitab/nomor hadits)"
            else:
                reason = f"nomor tersimpan untuk kitab ini: {lo}–{hi} ({n_book} baris hadits)"
            label = [f"{k}/{n}" if k is not None else n for k, n in absent]
            missing.append({"book": book, "numbers": label, "reason": reason})

    total = len(items)
    start = min(args.offset, total)
    budget = args.max_chars
    shown, used, blocks, jitems = 0, 0, [], []
    next_offset = None
    for pos in range(start, total):
        it = items[pos]
        r = it["row"]
        if budget > 0 and shown > 0 and used + len(r["text"] or "") > budget:
            next_offset = pos
            break
        remaining = max(budget - used - len(r["text"] or ""), 0) if budget > 0 else 0
        md, ulen, _ = render_hadith(db, r, args.notes, remaining if budget > 0 else 0)
        used += len(md)
        xr_md, xr_json = [], []
        for method, xrow in it["xref"]:
            rem2 = max(budget - used - len(xrow["text"] or ""), 0) if budget > 0 else 0
            m2, _, _ = render_hadith(db, xrow, args.notes, rem2 if budget > 0 else 0, heading="####")
            used += len(m2)
            xr_md.append(f"**Entri terkait (xref: nomor {xrow['num']} di `{xrow['book']}`; metode: {method}) — "
                         f"ditampilkan dengan nomornya sendiri:**\n\n{m2}")
            xr_json.append(dict(hadith_dict(db, xrow), xref_method=method))
        blocks.append(md + ("\n" + "\n".join(xr_md) if xr_md else ""))
        jitems.append(hadith_dict(db, r, xr_json))
        shown += 1
    if next_offset is None and start + shown < total:
        next_offset = start + shown

    query = " ".join(args.refs)
    if args.format == "json":
        print(json.dumps({"query": {"refs": args.refs}, "total_matches": total, "offset": start,
                          "results": jitems, "missing": missing, "ambiguous": ambiguous, "notes": notes,
                          "truncated": next_offset is not None, "next_offset": next_offset},
                         ensure_ascii=False, indent=2))
        return
    out = [f"# Hadits: {query}", ""]
    out += blocks
    if start == 0 or not blocks:
        for m in missing:
            nums = m["numbers"]
            shown = compress_nums([int(x) for x in nums]) if all(str(x).isdigit() for x in nums) else ",".join(map(str, nums))
            out.append(f"**TIDAK ADA di DB:** `{m['book']}:{shown}` — {m['reason']}. "
                       "Jangan mengisi dari ingatan; sampaikan ke pengguna bahwa nomor ini tidak tersedia.\n")
    for amb in ambiguous:
        out.append(f"**AMBIGU:** `muwatta:{amb['num']}` — Muwatta edisi ini TIDAK punya nomor global; hadits no. {amb['num']} "
                   f"ada di {len(amb['candidates'])} kitab. Tentukan dengan `muwatta:K/N` (K = nomor kitab):")
        for c in amb["candidates"]:
            out.append(f"- `muwatta:{c['kitab_no']}/{amb['num']}` — {c['kitab'] or '—'}"
                       + (f" ({c['n_rows']} baris)" if c["n_rows"] > 1 else ""))
        out.append("")
    for n in notes:
        out.append(f"(Catatan: {n})")
    if total == 0 and not missing and not ambiguous:
        out.append("Tidak ada hasil.")
    if next_offset is not None:
        out.append(f"\n…{total - next_offset} hadits lagi belum ditampilkan (batas --max-chars {budget}). "
                   f"Ketik **lanjut** → jalankan ulang perintah yang sama dengan `--offset {next_offset}` "
                   "(atau naikkan --max-chars / pakai 0 untuk penuh).")
    print("\n".join(out).rstrip() + "\n")


def fts_queries(q, mode):
    toks = re.findall(r"\w+", normalize(q))
    if not toks:
        raise InputError("kueri pencarian kosong setelah normalisasi")
    quoted = ['"%s"' % t.replace('"', '') for t in toks]
    if mode == "any":
        return [("salah satu kata", " OR ".join(quoted))], toks
    if len(toks) == 1:
        return [("kata", quoted[0])], toks
    return [("frasa persis", '"%s"' % " ".join(toks)), ("semua kata (tak harus berurutan)", " AND ".join(quoted))], toks


def snippet(text, toks, before=100, after=240):
    norm, idx = norm_with_map(text)
    pos = -1
    phrase = " ".join(toks)
    p = norm.find(phrase)
    if p >= 0:
        pos = p
    else:
        for t in toks:
            p = norm.find(t)
            if p >= 0:
                pos = p
                break
    if pos < 0 or not idx:
        s, e = 0, min(len(text), before + after)
    else:
        s = max(idx[pos] - before, 0)
        e = min(idx[min(pos + len(phrase), len(idx) - 1)] + after, len(text))
    if s > 0:  # mundur ke batas kata agar tidak memotong di tengah huruf+harakat
        k = text.find(" ", s, s + 40)
        s = k + 1 if k != -1 else s
    if e < len(text):
        k = text.rfind(" ", max(e - 40, s), e)
        e = k if k != -1 else e
    pre = "…" if s > 0 else ""
    post = "…" if e < len(text) else ""
    return pre + text[s:e].strip() + post


def cmd_search(db, args):
    if not db.has_fts:
        fail("DB tidak memiliki tabel hadith_fts — tidak bisa mencari", code=3)
    books = parse_books(args.books)
    limit = args.limit or 10
    attempts, toks = fts_queries(args.search, "any" if args.any else "auto")
    rows, mode = [], None
    ph = ",".join("?" * len(books))
    for label, match in attempts:
        try:
            rows = db.rows(
                f"SELECT {db.sel} FROM hadith_fts JOIN hadith h ON h.hid = hadith_fts.rowid "
                f"WHERE hadith_fts MATCH ? AND h.book IN ({ph}) ORDER BY hadith_fts.rank LIMIT ?",
                [match] + books + [limit])
        except sqlite3.Error as e:
            fail(f"kueri FTS gagal: {e}", code=3)
        if rows:
            mode = label
            break
    if args.format == "json":
        res = []
        for r in rows:
            d = hadith_dict(db, r)
            d["snippet"] = snippet(r["text"] or "", toks)
            d.pop("text"), d.pop("notes")
            res.append(d)
        print(json.dumps({"query": {"search": args.search, "normalized": " ".join(toks), "books": books, "limit": limit},
                          "match_mode": mode, "count": len(res), "results": res}, ensure_ascii=False, indent=2))
        return
    out = [f"# Pencarian: {args.search}", "",
           f"(kueri ternormalisasi: `{' '.join(toks)}` · kitab: {', '.join(books)} · limit {limit})", ""]
    if not rows:
        out.append("**TIDAK ADA hasil** di DB untuk kueri ini (setelah normalisasi harakat/alif/ya/ta marbutah). "
                   "Jangan mengisi dari ingatan; coba kata kunci yang lebih pendek atau --any.")
    else:
        out.append(f"{len(rows)} hasil — cocok: {mode}" + (" — mungkin ada lebih banyak, naikkan --limit" if len(rows) == limit else ""))
        out.append("")
        for i, r in enumerate(rows, 1):
            title, ed = db.title_edition(r["book"])
            out.append(f"{i}. **{title}** [`{r['book']}`] — nomor {r['num_label'] or r['num']}")
            if r.get("kitab") or r.get("bab"):
                out.append(f"   Kitab/Bab: {r.get('kitab') or '—'} › {r.get('bab') or '—'}")
            out.append(f"   Cuplikan (verbatim, bukan teks penuh): {snippet(r['text'] or '', toks)}")
            if (r.get("grade") or "").strip():
                by = (r.get("grade_by") or "").strip()
                out.append(f"   Derajat tersimpan: {r['grade']}" + (f" — {by}" if by else " — otoritas tidak tercatat"))
            out.append(f"   — Sumber: {citation(r)}")
            out.append(f"   Teks penuh: `python lookup.py {r['book']}:{r['num']}`")
            out.append("")
    print("\n".join(out).rstrip() + "\n")


def cmd_bab(db, args):
    book = resolve_book(args.bab[0])
    q = args.bab[1]
    toks = re.findall(r"\w+", normalize(q))
    if not toks:
        raise InputError("teks bab kosong")
    limit = args.limit or 20
    # Hanya kolom judul (tanpa teks) agar ringan di DB besar; detail baris diambil untuk bab yang ditampilkan saja.
    heads = db.rows("SELECT kitab, bab, MIN(hid) AS hid, COUNT(*) AS n FROM hadith WHERE book=? "
                    "GROUP BY kitab, bab ORDER BY MIN(hid)", (book,))
    groups = {}
    for hd in heads:
        hay = normalize((hd["kitab"] or "") + " " + (hd["bab"] or ""))
        if all(t in hay for t in toks):
            groups[(hd["kitab"], hd["bab"])] = hd
    items = list(groups.items())
    total_items = len(items)
    items = items[:limit]
    for key, hd in items:
        rws = db.rows("SELECT h.hid, h.num, h.juz, h.page_from, h.page_to, h.url FROM hadith h "
                      "WHERE h.book=? AND h.kitab IS ? AND h.bab IS ? ORDER BY h.hid", (book, key[0], key[1]))
        hd["nums"] = [r["num"] for r in rws if r["num"] is not None]
        hd["first"] = rws[0]
    items = [(k, {"nums": hd["nums"] or [0], "first": hd["first"], "n": hd["n"]}) for k, hd in items]
    title, ed = db.title_edition(book)
    if args.format == "json":
        print(json.dumps({"query": {"bab": q, "book": book}, "count": total_items, "results": [
            {"kitab": k, "bab": b, "n_hadith": g["n"], "num_min": min(g["nums"]), "num_max": max(g["nums"]),
             "numbers": sorted(set(g["nums"])), "citation": citation(g["first"])}
            for (k, b), g in items[:limit]]}, ensure_ascii=False, indent=2))
        return
    out = [f"# Cari bab: {q} — {title}", ""]
    if not items:
        out.append(f"**TIDAK ADA** judul bab/kitab yang memuat semua kata itu di `{book}` pada DB ini. "
                   "Jangan menebak nomor; coba kata kunci lebih pendek.")
    else:
        out.append(f"{total_items} bab cocok" + (f" (ditampilkan {limit} pertama)" if total_items > limit else ""))
        out.append("")
        for (k, b), g in items[:limit]:
            nums = sorted(set(g["nums"]))
            shown = compress_nums(nums) if len(nums) <= 12 else f"{nums[0]}–{nums[-1]}"
            out.append(f"- Kitab: {k or '—'} › Bab: {b or '—'}")
            out.append(f"  hadits tersimpan di bab ini: {g['n']} · nomor {shown}")
            out.append(f"  — Sumber: {citation(g['first'])}")
            out.append(f"  baca: `python lookup.py {book}:{shown if len(nums) <= 12 else str(nums[0]) + '-' + str(nums[-1])}`")
        out.append("")
    print("\n".join(out).rstrip() + "\n")


def cmd_list_books(db, args):
    info = db.books_info()
    rows = []
    for key in BOOKS:
        lo, hi, n = db.book_range(key)
        t, e = db.title_edition(key)
        rows.append({"book": key, "title": t, "edition": e, "n_hadith": n or 0, "num_min": lo, "num_max": hi,
                     "in_db": bool(n), "has_grade_by_column": db.has_grade_by})
    if args.format == "json":
        print(json.dumps({"books": rows}, ensure_ascii=False, indent=2))
        return
    out = ["# Kitab di DB hadits", "", "| key | kitab | edisi | hadits | rentang nomor |", "|---|---|---|---|---|"]
    for r in rows:
        rng = f"{r['num_min']}–{r['num_max']}" if r["in_db"] else "belum ada di DB"
        out.append(f"| {r['book']} | {r['title']} | {r['edition']} | {r['n_hadith']} | {rng} |")
    out += ["", "Alias diterima (Latin/Indonesia/Arab), mis.: bukhari, `abu dawud`, `ibnu majah`, tirmidzi, "
            "muwattha, `musnad ahmad`, `bulughul maram`, `riyadhus shalihin` (= riyadh_arnaut; entri al-Albani via xref)."]
    print("\n".join(out) + "\n")


def build_parser():
    ap = argparse.ArgumentParser(prog="lookup.py", description="Query hadits verbatim dari hadith_full.db (12 kitab).")
    ap.add_argument("refs", nargs="*", help="rujukan KITAB:NOMOR (bukhari:1, muslim:8, bukhari:1-3, bukhari:1,2)")
    ap.add_argument("--search", metavar="TEKS", help="cari teks Arab/frasa (FTS ternormalisasi)")
    ap.add_argument("-b", "--books", help="filter kitab untuk --search, dipisah koma")
    ap.add_argument("--limit", type=int, default=None, metavar="N", help="maks hasil search (10) / bab (20)")
    ap.add_argument("--any", action="store_true", help="--search: cocokkan SALAH SATU kata (default: frasa lalu semua kata)")
    ap.add_argument("--bab", nargs=2, metavar=("KITAB", "TEKS"), help="cari judul bab/kitab di satu kitab")
    ap.add_argument("--list-books", action="store_true", help="daftar kitab & cakupan di DB")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--max-chars", type=int, default=8000, metavar="N",
                    help="anggaran karakter keluaran, dipotong di batas hadits/baris catatan (default 8000; 0 = penuh)")
    ap.add_argument("--offset", type=int, default=0, metavar="K", help="lewati K hadits pertama (untuk 'lanjut')")
    ap.add_argument("--notes", dest="notes", action="store_true", default=True, help="tampilkan catatan muhaqqiq (default)")
    ap.add_argument("--no-notes", dest="notes", action="store_false", help="sembunyikan catatan muhaqqiq")
    ap.add_argument("--db", help="path DB (.db/.zip/.xz); default dicari otomatis (env HADITH_DB)")
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    refs = []
    try:
        modes = [bool(args.refs), bool(args.search), bool(args.bab), args.list_books]
        if sum(modes) != 1:
            raise InputError("pakai tepat satu mode: KITAB:NOMOR | --search | --bab | --list-books")
        if args.max_chars < 0 or args.offset < 0 or (args.limit is not None and args.limit < 1):
            raise InputError("--max-chars/--offset tidak boleh negatif dan --limit minimal 1")
        if args.refs:
            refs = [parse_ref(t) for t in args.refs]
        if args.search:
            parse_books(args.books)
            fts_queries(args.search, "auto")
        if args.bab:
            resolve_book(args.bab[0])
    except InputError as e:
        fail(str(e))

    db_path = args.db or find_db()
    if db_path is None:
        fail_db_missing(autodl_failed=True)
    if str(db_path).lower().endswith(".zip"):
        db_path = extract_zip_db(db_path)
    elif str(db_path).lower().endswith(".xz"):
        db_path = extract_xz_db(db_path)
    con = open_db(db_path)
    db = DB(con)
    try:
        if args.list_books:
            cmd_list_books(db, args)
        elif args.search:
            cmd_search(db, args)
        elif args.bab:
            cmd_bab(db, args)
        else:
            cmd_refs(db, refs, args)
    except InputError as e:
        fail(str(e))
    finally:
        con.close()


if __name__ == "__main__":
    main()
