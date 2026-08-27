#!/usr/bin/env python3
"""link_candidates.py — Tugas B3: siapkan batch resolusi entitas untuk LLM.

Input : data/person_links.jsonl, data/person_segments.jsonl, data/pages_full.jsonl
Output: data/link_batches/<source>_<NNN>.txt  (maks 120 entri/file)
        data/link_batches/INDEX.json
        data/LINK-LLM-SPEC.md

Normalisasi & tokenisasi nasab diimpor dari resolve_persons.py (satu sumber).

Kandidat entri Ishabah (spesifikasi B3):
  +3 token nama diri sama (token pertama), +2 tiap token nasab (ayah, kakek)
  sama pada posisi segmen sama, +1 tiap token nasab/nisbah/kunya sama di posisi
  manapun, +2 lakab unik sama (df <= UNIQUE_LAKAB_MAX_DF), toleransi edit <=1
  untuk token >=4 huruf. Kandidat ronde sebelumnya (kolom `candidates`)
  WAJIB disertakan.

Penyempurnaan pasca-merge (B3-FIX + verifikasi file):
1. Token pertama أبي/ابو/ابا yang DIIKUTI بن/ابن/ب = nama diri (Ubayy), bukan kunya.
2. Gerbang token pertama untuk kandidat non-kuna/lakab — kecuali bila kueri
   sendiri berjudul kuna/lakab (nama dirinya tak diketahui dari judul).
3. Kueri berjudul kuna: entri Ishabah yang berbagi frasa kuna yang sama
   (mis. "أبو بكر الصديق" → entri utama berkuna أبو بكر) di-force masuk
   di awal daftar (maks 4), sebelum sisa slot diisi skor tertinggi.
4. Entri kuna Ishabah dipetakan ke entri utama via alias_map resolve_persons.
5. Validasi diri membaca FILE batch tertulis (bukan hasil dipanggil ulang).
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from resolve_persons import (
    BODY_CONNECTORS,
    KUNYA_PREFIXES,
    STOP_TOKENS,
    TITLE_CONNECTORS,
    IshIndex,
    first_body_para,
    load_pages,
    load_segments,
    pair_usud,
    parse_name,
)

DATA = Path("data")
OUT_DIR = DATA / "link_batches"
SPEC_OUT = DATA / "LINK-LLM-SPEC.md"
LINKS = DATA / "person_links.jsonl"

MAX_PER_FILE = 120
MAX_CAND = 8
UNIQUE_LAKAB_MAX_DF = 10          # lakab dengan df <= ini dianggap "unik" (الصديق, الفاروق, …)
MAX_KUNYA_FORCE = 4               # maks entri berbagi frasa kuna yang di-force masuk

TASHKEEL_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640"
    r"\uFB50-\uFDFF\uFE70-\uFEFF\u200B-\u200F\u061C]"
)
# karakter non-Arab/non-Latin yang tak boleh muncul (CJK, Cyrillic, Thai, Hebrew, dll)
FORBIDDEN_RE = re.compile(r"[\u0370-\u03FF\u0400-\u04FF\u0590-\u05FF\u0E00-\u0E7F\u3000-\u9FFF\uFF00-\uFFEF]")

LLM_SPEC_TEXT = (
    "Baca file batch. Untuk tiap blok `### Q`, putuskan: `ishabah_id` dari daftar kandidat "
    "yang orangnya SAMA (nama, ayah, kakek, kabilah/nisbah, kunya harus konsisten; bukan "
    "sekadar mirip), atau null bila tidak ada yang sama/tidak yakin. Keluarkan file JSON "
    "`data/link_results/<nama_batch>.json`: array `{\"source\",\"entry_num\",\"ishabah_id\"|null,"
    "\"confidence\":\"high|medium|low\",\"reason\":\"<≤15 kata>\"}` — satu objek per blok, jangan "
    "ada yang terlewat. Jangan mengarang id di luar kandidat."
)


def strip_tashkeel(s: str) -> str:
    """Buang tasykil/tatweel/presentation forms, rapatkan spasi (huruf asli dipertahankan)."""
    return re.sub(r"\s+", " ", TASHKEEL_RE.sub("", s)).strip()


# ---------------------------------------------------------------------------
# Edit distance <= 1 (Levenshtein: sub/ins/del) untuk token
# ---------------------------------------------------------------------------

def edit_le1(a: str, b: str) -> bool:
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        return sum(x != y for x, y in zip(a, b)) <= 1
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    # b lebih panjang 1: cek hapus satu huruf dari b == a
    i = j = 0
    skipped = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif skipped:
            return False
        else:
            skipped = True
            j += 1
    return True


def del_variants(t: str) -> list[str]:
    return [t] + [t[:i] + t[i + 1:] for i in range(len(t))]


# ---------------------------------------------------------------------------
# Profil token nama (dipakai untuk entri kueri maupun entri Ishabah)
# ---------------------------------------------------------------------------

class Prof:
    __slots__ = ("eid", "name", "first_tok", "chain", "seg_toks", "anyset",
                 "nisbah", "kunya_sub", "lakabs", "kunya_or_lakab", "kunya_head")


def is_ubayy_title(info) -> bool:
    """Token pertama kunya-prefix yang diikuti konektor بن/ابن/ب = nama diri (Ubayy)."""
    nt = info.tokens
    return bool(nt) and nt[0] in KUNYA_PREFIXES and len(nt) > 1 and nt[1] in TITLE_CONNECTORS


def make_prof(name: str, info, chain: list[str], nisbah: set, kunyas: set,
              eid: int = -1, head_terms: frozenset = frozenset()) -> Prof:
    p = Prof()
    p.eid = eid
    p.name = name
    kunya_titled = info.kunya_titled
    chain = [s for s in chain if s]
    kunyas = set(kunyas)
    if is_ubayy_title(info):
        # أبي بن كعب … → chain [ابي, كعب, …]; buang artefak kunya bare-prefix
        kunya_titled = False
        chain = [info.tokens[0]] + chain
        kunyas = {k for k in kunyas if len(k.split()) > 1}
    # frasa kunya judul (kunya_head) tidak selalu masuk info.kunyas pada parse_name baru
    kunya_phrase_toks: set[str] = set()
    if kunya_titled and info.kunya_head:
        kunyas.add(info.kunya_head)
        kunya_phrase_toks = set(info.kunya_head.split())
    p.kunya_head = info.kunya_head if kunya_titled else None
    title_toks = [t for t in info.tokens
                  if t not in KUNYA_PREFIXES and t not in (TITLE_CONNECTORS | BODY_CONNECTORS)
                  and t not in STOP_TOKENS and t not in kunya_phrase_toks]
    p.kunya_sub = {t for k in kunyas for t in k.split()[1:]}
    p.chain = list(chain)
    p.seg_toks = [set(s.split()) for s in p.chain]
    p.nisbah = set(nisbah)
    # lakab identitas (+2) HANYA dari parse judul; token badan (ber-ال) hanya
    # menambah sinyal anywhere (+1) — penyebutan "روى عن أبي بكر الصديق" bukan lakab pemilik entri
    title_lakabs = {t for t in nisbah if not t.endswith("ي")}
    for t in head_terms:
        if len(t) > 3 and t.startswith("ال") and not t.endswith("ي") and t not in p.nisbah:
            p.nisbah.add(t)
    p.anyset = set(title_toks) | p.kunya_sub | p.nisbah
    for st in p.seg_toks:
        p.anyset |= st
    # token pertama = segmen 0 chain; fallback title hanya untuk entri non-kuna
    p.first_tok = (p.chain[0].split()[0] if p.chain
                   else (title_toks[0] if title_toks and not kunya_titled else None))
    p.lakabs = title_lakabs
    # entri kuna/lakab dikecualikan dari gerbang token pertama
    p.kunya_or_lakab = bool(kunya_titled) or p.first_tok is None or (p.first_tok or "").startswith("ال")
    return p


# ---------------------------------------------------------------------------
# Skoring kandidat
# ---------------------------------------------------------------------------

class Scorer:
    def __init__(self, profs: dict[int, Prof]):
        self.profs = profs
        self.any_index: dict[str, list[int]] = defaultdict(list)
        for eid, p in profs.items():
            for t in p.anyset:
                self.any_index[t].append(eid)
        # indeks neighborhood-delesi untuk pencarian token mirip (edit <=1, token >=4 huruf)
        self.del_index: dict[str, set] = defaultdict(set)
        for t in self.any_index:
            if len(t) >= 4:
                for v in del_variants(t):
                    self.del_index[v].add(t)
        self.unique_lakabs: set[str] = set()
        self._mt_cache: dict[str, frozenset] = {}

    def set_unique_lakabs(self, df: Counter) -> None:
        self.unique_lakabs = {t for t, n in df.items() if n <= UNIQUE_LAKAB_MAX_DF}

    def match_tokens(self, t: str) -> frozenset:
        """Token yang dianggap 'sama' dengan t: diri sendiri + yang berjarak edit <=1 (len>=4)."""
        hit = self._mt_cache.get(t)
        if hit is not None:
            return hit
        out = {t}
        if len(t) >= 4:
            near: set[str] = set()
            for v in del_variants(t):
                near |= self.del_index.get(v, set())
            for u in near:
                if u != t and edit_le1(t, u):
                    out.add(u)
        res = frozenset(out)
        self._mt_cache[t] = res
        return res

    def tok_match(self, a: str, b: str) -> bool:
        if a == b:
            return True
        if len(a) >= 4 and len(b) >= 4:
            return edit_le1(a, b)
        return False

    def universe(self, q: Prof) -> set[int]:
        """Eid entri Ishabah yang berbagi minimal satu token (toleransi edit) dengan kueri."""
        eids: set[int] = set()
        for t in q.anyset:
            for m in self.match_tokens(t):
                lst = self.any_index.get(m)
                if lst:
                    eids.update(lst)
        return eids

    def score(self, q: Prof, c: Prof) -> int:
        s = 0
        # +3 token nama diri (pertama) sama
        if q.first_tok and c.first_tok and self.tok_match(q.first_tok, c.first_tok):
            s += 3
        # +2 token nasab sama pada posisi segmen sama (ayah=1, kakek=2, …)
        pos_matched: set[str] = set()
        for j in range(1, min(len(q.chain), len(c.chain))):
            ctoks = c.seg_toks[j]
            for t in q.chain[j].split():
                if any(m in ctoks for m in self.match_tokens(t)):
                    s += 2
                    pos_matched.add(t)
        # +1 token nasab/nisbah/kunya sama di posisi manapun
        anywhere: set[str] = set()
        for j, seg in enumerate(q.chain):
            if j == 0:
                continue
            for t in seg.split():
                if t not in pos_matched:
                    anywhere.add(t)
        anywhere |= q.nisbah
        anywhere |= q.kunya_sub
        for t in anywhere:
            for m in self.match_tokens(t):
                if m in c.anyset:
                    s += 1
                    break
        # +2 lakab unik sama
        if q.lakabs:
            for lk in q.lakabs & c.lakabs & self.unique_lakabs:
                s += 2
        return s


# ---------------------------------------------------------------------------
# Potongan teks untuk blok
# ---------------------------------------------------------------------------

def nasab_snippet(pages: dict, source: str, seg: dict) -> str:
    """Paragraf heading + paragraf berikutnya (para_start .. para_start+1), maks 300 kar."""
    page = pages.get(source, {}).get(seg.get("start_page") or 0)
    if page is None:
        return ""
    ps = seg.get("para_start") if seg.get("para_start") is not None else 0
    parts = [page[i] for i in (ps, ps + 1) if i < len(page)]
    return strip_tashkeel(" ".join(parts))[:300]


def block_text(source: str, row: dict, snippet: str, cands: list[tuple]) -> str:
    lines = [f"### Q {source}#{row['entry_num']}",
             f"judul: {row['name']}",
             f"nasab: {snippet}"]
    if cands:
        lines.append("kandidat:")
        for mark, eid, name, body in cands:
            # format spec B3: `  [id] nama | badan` (tanpa penanda)
            lines.append(f"  [{eid}] {name} | {body}")
    else:
        lines.append("kandidat: (tidak ada)")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    pages = load_pages()
    segs = load_segments()
    seg_by_key = {(s["source"], s["entry_num"]): s for s in segs if s.get("entry_num") is not None}

    rows = []
    with open(LINKS, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    row_by_key = {(r["source"], r["entry_num"]): r for r in rows}

    # ---- index Ishabah (profil + rantai dari badan, sama seperti resolve_persons) ----
    idx = IshIndex()
    idx.build([s for s in segs if s["source"] == "ishabah"], pages)
    alias = idx.alias

    profs: dict[int, Prof] = {}
    kunya_index: dict[str, set[int]] = defaultdict(set)   # frasa kuna → eids
    for eid, prof in idx.profiles.items():
        profs[eid] = make_prof(prof["seg"].get("name") or "", prof["info"], prof["chain"],
                               prof["nisbah"], prof["kunyas"], eid,
                               head_terms=frozenset(prof["terms"]))
        for k in prof["kunyas"]:
            kunya_index[k].add(eid)
    scorer = Scorer(profs)
    lakab_df: Counter = Counter()
    for p in profs.values():
        for lk in p.lakabs:
            lakab_df[lk] += 1
    scorer.set_unique_lakabs(lakab_df)

    # cuplikan badan entri Ishabah (120 karakter, tanpa tasykil)
    body_cache: dict[int, str] = {}
    for eid, prof in idx.profiles.items():
        body_cache[eid] = strip_tashkeel(first_body_para(pages, "ishabah", prof["seg"]))[:120]

    # ---- pasangan usud: perwakilan = usud_rifai; usud_ilmiyah yang berpasangan di-skip ----
    pairs = pair_usud(segs)

    # ---- generator kandidat ----
    def gen_cands(row: dict) -> list[tuple]:
        """Return [(eid, name, body)] — prev di atas, lalu entri berbagi kuna (kueri
        kuna-titled), lalu skor tertinggi ter-gerbang, lalu sisanya."""
        info = parse_name(row["name"] or "")
        q = make_prof(row["name"] or "", info, info.chain, info.nisbah, info.kunyas)
        scored: dict[int, int] = {}
        for eid in scorer.universe(q):
            sc = scorer.score(q, profs[eid])
            if sc > 0:
                scored[eid] = sc
        # entri kuna dipetakan ke entri utama via alias_map — skor utama =
        # akumulasi bukti identitas (kuna + utama: satu orang yang sama)
        for e in list(scored):
            a = alias.get(e)
            if a is not None and a != e:
                scored[a] = scored.get(a, 0) + scored[e]
        prev_ids = [c["ishabah_id"] for c in (row.get("candidates") or [])
                    if c.get("ishabah_id") in profs][:MAX_CAND]
        prev_set = set(prev_ids)
        # kueri berjudul kuna/lakab → force entri yang berbagi frasa kuna judul
        force: list[int] = []
        if q.kunya_or_lakab and q.kunya_head:
            force = sorted((e for e in kunya_index.get(q.kunya_head, ())
                            if e not in prev_set and e in scored),
                           key=lambda e: (-scored[e], e))[:MAX_KUNYA_FORCE]
        forced_set = set(force)
        gated: list[tuple[int, int]] = []
        ungated: list[tuple[int, int]] = []
        gate_on = q.first_tok is not None and not q.kunya_or_lakab
        for e, sc in scored.items():
            if e in prev_set or e in forced_set:
                continue
            c = profs[e]
            # gerbang token pertama (kandidat non-kuna/lakab wajib cocok token pertama kueri)
            if gate_on and not c.kunya_or_lakab:
                if not (c.first_tok and scorer.tok_match(q.first_tok, c.first_tok)):
                    ungated.append((sc, e))
                    continue
            gated.append((sc, e))
        gated.sort(key=lambda t: (-t[0], t[1]))
        ungated.sort(key=lambda t: (-t[0], t[1]))
        slots = max(MAX_CAND - len(prev_ids) - len(force), 0)
        fill = force + [e for _, e in gated[:slots]] + [e for _, e in ungated][:MAX_CAND]
        chosen = prev_ids + fill[:MAX_CAND - len(prev_ids)]
        out = [("*" if e in prev_set else "", e, profs[e].name, body_cache.get(e, ""))
               for e in chosen]
        return out

    # ---- batch ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.txt"):
        old.unlink()
    (OUT_DIR / "INDEX.json").unlink(missing_ok=True)

    per_source: Counter = Counter()
    skipped_paired = 0
    dist = Counter()
    files_out: list[dict] = []
    example_blocks: dict[str, str] = {}
    cur_source = None
    buf: list[str] = []
    file_no = 0

    def flush() -> None:
        nonlocal buf, file_no
        if not buf:
            return
        file_no += 1
        fname = f"{cur_source}_{file_no:03d}.txt"
        (OUT_DIR / fname).write_text("".join(buf), encoding="utf-8")
        files_out.append({"file": fname, "source": cur_source, "entries": len(buf)})
        buf = []

    total = 0
    for row in rows:
        source = row["source"]
        if row["status"] not in ("ambiguous", "unresolved"):
            continue
        num = row["entry_num"]
        if source == "usud_ilmiyah" and (source, num) in pairs:
            skipped_paired += 1
            continue
        seg = seg_by_key.get((source, num))
        if seg is None:
            continue
        if source != cur_source:
            flush()
            cur_source = source
            file_no = 0

        cands = gen_cands(row)
        blk = block_text(source, row, nasab_snippet(pages, source, seg), cands)
        buf.append(blk)
        per_source[source] += 1
        total += 1
        n = len(cands)
        dist["0" if n == 0 else ("1-3" if n <= 3 else "4-8")] += 1
        if source not in example_blocks and cands:
            example_blocks[source] = blk
        if len(buf) >= MAX_PER_FILE:
            flush()
    flush()

    index = {
        "max_per_file": MAX_PER_FILE,
        "total_files": len(files_out),
        "total_entries": total,
        "files": files_out,
    }
    with open(OUT_DIR / "INDEX.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    with open(SPEC_OUT, "w", encoding="utf-8") as f:
        f.write("# LINK-LLM-SPEC — instruksi LLM pemroses batch\n\n" + LLM_SPEC_TEXT + "\n")

    # ---------- validasi diri: baca FILE tertulis ----------
    def find_block(source: str, num: int) -> str | None:
        for x in files_out:
            if x["source"] != source:
                continue
            text = (OUT_DIR / x["file"]).read_text(encoding="utf-8")
            m = re.search(rf"### Q {source}#{num}\n(.*?)(?=### Q |\Z)", text, re.S)
            if m:
                return m.group(1)
        return None

    def block_ids(blk: str) -> list[int]:
        return [int(mo.group(1)) for ln in blk.splitlines()
                for mo in [re.match(r"  (?:\* )?\[(\d+)\] ", ln)] if mo]

    checks = []
    # 1) istiab#6: kandidat ronde sebelumnya terjaga di blok batch tertulis
    r6 = row_by_key.get(("istiab", 6))
    if r6 and r6["status"] in ("ambiguous", "unresolved"):
        blk6 = find_block("istiab", 6)
        want6 = [c["ishabah_id"] for c in (r6.get("candidates") or [])]
        ids6 = block_ids(blk6) if blk6 else []
        checks.append(("istiab#6: kandidat ronde-1 terjaga di blok",
                       blk6 is not None and set(want6) <= set(ids6) and want6 == ids6[:len(want6)]))
    # 2) satu entri ambiguous tiap sumber: kandidat ronde-1 terjaga
    ok_prev_all = True
    n_checked = 0
    for src in ("istiab", "usud_rifai", "tabaqat"):
        prow = next((r for r in rows if r["source"] == src and r["status"] == "ambiguous"
                     and len(r.get("candidates") or []) >= 3
                     and not (src == "usud_ilmiyah" and (src, r["entry_num"]) in pairs)
                     and r["source"] != "usud_ilmiyah"), None)
        if not prow:
            continue
        blk = find_block(src, prow["entry_num"])
        want = [c["ishabah_id"] for c in prow["candidates"]]
        got = block_ids(blk) if blk else []
        n_checked += 1
        if not (blk and set(want) <= set(got) and want == got[:len(want)]):
            ok_prev_all = False
    checks.append((f"kandidat ronde-1 terjaga (probe {n_checked} entri ambiguous)", ok_prev_all))
    # 3) format baris kandidat: '  [id] nama | badan' persis spec
    bad_fmt = 0
    mx_nasab = mx_body = 0
    for x in files_out:
        for blk in (OUT_DIR / x["file"]).read_text(encoding="utf-8").split("### Q ")[1:]:
            for ln in blk.splitlines():
                if ln.startswith("  [") or ln.startswith("  * ["):
                    m = re.match(r"  (?:\* )?\[\d+\] .+ \| .*$", ln)
                    if not m:
                        bad_fmt += 1
                    body = ln.split(" | ", 1)[1] if " | " in ln else ""
                    mx_body = max(mx_body, len(body))
                elif ln.startswith("nasab: "):
                    mx_nasab = max(mx_nasab, len(ln) - len("nasab: "))
    checks.append(("format baris kandidat `[id] nama | badan` (0 pelanggaran)", bad_fmt == 0))
    checks.append((f"panjang potongan (nasab<=300, badan<=120; maks {mx_nasab}/{mx_body})",
                   mx_nasab <= 300 and mx_body <= 120))
    # 4) file <= 120 entri & INDEX konsisten
    checks.append(("semua file <= 120 entri", all(x["entries"] <= MAX_PER_FILE for x in files_out)))
    checks.append(("jumlah entri INDEX == blok Q tertulis",
                   sum(x["entries"] for x in files_out)
                   == sum(len(re.findall(r"^### Q ", (OUT_DIR / x["file"]).read_text(encoding="utf-8"), re.M))
                          for x in files_out)))
    # 5) tak ada karakter terlarang (CJK/Cyrillic/Thai/Hebrew/dll)
    forbidden_hits = 0
    for x in files_out:
        if FORBIDDEN_RE.search((OUT_DIR / x["file"]).read_text(encoding="utf-8")):
            forbidden_hits += 1
    checks.append((f"karakter terlarang (CJK/dll): {forbidden_hits} file", forbidden_hits == 0))

    # 6) blok verifikasi wajib (B3-FIX #4) — entri resolved dibangun ulang via mesin kandidat
    def gen_block(source: str, num: int) -> str:
        row = row_by_key[(source, num)]
        seg = seg_by_key[(source, num)]
        return block_text(source, row, nasab_snippet(pages, source, seg), gen_cands(row))

    ver = {}
    for tag, src, num, want in [
        ("istiab#1633→4835", "istiab", 1633, 4835),
        ("tabaqat#46→4835", "tabaqat", 46, 4835),
        ("istiab#1878→5752", "istiab", 1878, 5752),
    ]:
        try:
            blk = gen_block(src, num)
            ver[tag] = {"blk": blk, "has": bool(re.search(rf"  (?:\* )?\[{want}\] ", blk))}
        except KeyError:
            ver[tag] = None   # entri tidak ada lagi di person_links
    checks.append(("istiab#1633 memuat [4835] عبد الله بن عثمان (Abu Bakr)",
                   bool(ver.get("istiab#1633→4835") and ver["istiab#1633→4835"]["has"])))
    checks.append(("tabaqat#46 memuat [4835] عبد الله بن عثمان (Abu Bakr)",
                   bool(ver.get("tabaqat#46→4835") and ver["tabaqat#46→4835"]["has"])))
    checks.append(("istiab#1878 memuat [5752] عمر بن الخطاب (bila masih ada)",
                   True if ver.get("istiab#1878→5752") is None
                   else bool(ver["istiab#1878→5752"]["has"])))

    # ---------- ringkasan ----------
    print("=" * 78)
    print("B3 LINK_CANDIDATES — batch resolusi entitas untuk LLM")
    print("=" * 78)
    print("entri dibatch per sumber:")
    for src in ("istiab", "usud_ilmiyah", "usud_rifai", "tabaqat"):
        print(f"  {src:<14}{per_source.get(src, 0):>6}")
    print(f"  {'TOTAL':<14}{total:>6}")
    print(f"  usud_ilmiyah di-skip (paired, wakil usud_rifai): {skipped_paired}")
    print(f"file batch: {len(files_out)} di {OUT_DIR}/  (maks {MAX_PER_FILE} entri/file)")
    print(f"distribusi jumlah kandidat: 0 → {dist.get('0', 0)} | 1-3 → {dist.get('1-3', 0)} "
          f"| 4-8 → {dist.get('4-8', 0)}")
    print("-" * 78)
    print("validasi diri (dibaca dari file tertulis):")
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    print("-" * 78)
    print("contoh blok:")

    def print_block(blk: str, max_lines: int = 3) -> None:
        lines = blk.rstrip("\n").splitlines()
        cand = [ln for ln in lines if ln.startswith("  [") or ln.startswith("  * [")]
        extra = f"  … (+{len(cand) - max_lines} kandidat lain)" if len(cand) > max_lines else None
        print("\n".join(lines[:4] + cand[:max_lines] + ([extra] if extra else [])))
        print()

    for src in ("istiab", "usud_rifai", "tabaqat"):
        blk = example_blocks.get(src)
        if blk:
            print_block(blk)
    print("-" * 78)
    print("blok verifikasi (B3-FIX #4):")
    blk6v = find_block("istiab", 6)
    if blk6v:
        print("-- istiab#6 (dari file batch; * = kandidat ronde sebelumnya) --")
        print_block("### Q istiab#6\n" + blk6v, max_lines=6)
    for tag in ("istiab#1633→4835", "tabaqat#46→4835", "istiab#1878→5752"):
        v = ver.get(tag)
        if not v:
            print(f"-- {tag}: entri tidak ada di person_links (dilewati) --")
            continue
        print(f"-- {tag} (dibangun ulang; entri sudah resolved, tidak masuk batch) --")
        print_block(v["blk"], max_lines=4)
    print("-" * 78)
    print(f"selesai dalam {time.time() - t0:.1f}s → "
          f"{len(files_out)} file batch, INDEX.json, {SPEC_OUT.name}")
    all_pass = all(ok for _, ok in checks)
    print("VALIDATOR:", "LOLOS" if all_pass else "BELUM LOLOS")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
