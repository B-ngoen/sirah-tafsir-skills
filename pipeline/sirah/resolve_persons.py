#!/usr/bin/env python3
"""resolve_persons.py — resolusi entitas lintas kamus biografi → kunci kanonik Al-Ishabah.

Input : data/person_segments.jsonl, data/pages_full.jsonl
Output: data/person_links.jsonl, data/person_links_unresolved.txt, data/person_links_report.json

Ronde 2 (B2-ROUND2.md):
1. Judul dipotong klausa pada `،`/`؛`/` - `; gelar dibuang; klausa berawalan ابن/بن/ب menyambung nasab.
2. Pencocokan token nasab toleran jarak edit <=1 (SymSpell delete-1 dua sisi), token >=4 huruf, posisi >=1.
3. Duplikat persis antar-qism Ishabah → resolved (id terkecil, exact_dup, medium).
4. alias_map: entri kuna/lakab Ishabah → entri utama (inti judul ⊂ head_norm utama, fallback "اسمه nasab").
5. Kunya saja dgn >1 kandidat → wajib penguat (lakab/nisbah), selain itu ambiguous.
6. Rantai nasab badan dipakai untuk indeks Ishabah (judul pendek → badan melengkapi).
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path("data")
OUT_LINKS = DATA / "person_links.jsonl"
OUT_UNRESOLVED = DATA / "person_links_unresolved.txt"
OUT_REPORT = DATA / "person_links_report.json"

MAX_CHAIN_TOKENS = 6
HEAD_PARAS = 6
KUNYA_PREFIXES = {"ابو", "ابي", "ابا", "ام"}
TITLE_CONNECTORS = {"بن", "ابن", "بنت", "ابنه", "مولي", "ب"}  # ب tunggal = OCR dari بن (hanya di judul); ابنه = ابنة ternormalisasi
BODY_CONNECTORS = {"بن", "ابن", "بنت", "ابنه", "مولي"}
SKIP_CLAUSE_HEADS = {"امه", "امها", "امهما", "زوجه", "زوجها", "اخته", "اختهما", "اخوه", "ابوه", "ابنته", "بنته", "امهاتهم", "امهاتهن", "امهاتهم"}

STOP_TOKENS = {"و", "ف", "ثم", "يكني", "ويكني", "كني", "الملقب", "لقب", "الشهير", "المشهور", "هو", "هي", "وهو", "وهي", "المعروف", "بقية"}

HONORIFICS = [
    "صلي الله عليه وسلم", "صلي الله عليه واله وسلم", "صلي الله عليه",
    "عليه السلام", "عليها السلام", "عليهما السلام",
    "رضي الله عنه", "رضي الله عنها", "رضي الله عنهما", "رضي الله عنهم", "رضي الله عنهن",
    "رضي الله", "رضوان الله عليه", "رحمة الله عليه", "رحمه الله", "غفر الله له",
    "اسلام رضي الله عنه", "امراه", "امراه ا", "زوجه", "زوجه النبي",
]
# Gelar (bentuk pasca-normalisasi) — dibuang dari judul, TIDAK dianggap nasab
GELAR = [
    "امير المومنين", "ام المومنين", "خليفه رسول الله", "خاتم النبيين",
    "سيدنا", "حبيب الله", "صفوه الله", "نقيب بني", "حليف بني", "حليف",
]

# --------------------------------------------------------------------------
# Normalisasi
# --------------------------------------------------------------------------

def norm_name(s: str) -> str:
    s = re.sub(r"[\uFB50-\uFDFF\uFE70-\uFEFF\u200B-\u200F\u061C]", " ", s)
    s = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]", "", s)
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
          .replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي"))
    s = re.sub(r"[^\u0621-\u064A\s]", " ", s)
    s = re.sub(r"\bعبدال", "عبد ال", s)
    for h in HONORIFICS:
        s = s.replace(h, " ")
    return re.sub(r"\s+", " ", s).strip()


def strip_gelar(norm: str) -> str:
    for g in GELAR:
        norm = re.sub(r"\b" + g.replace(" ", r"\s+") + r"\b", " ", norm)
    return re.sub(r"\s+", " ", norm).strip()


def del1(t: str) -> set[str]:
    """Varian delete-1 + bentuk asli (SymSpell dua sisi → jarak edit <=1)."""
    return {t} | {t[:i] + t[i + 1:] for i in range(len(t))}


def edist_le1(s: str, t: str) -> bool:
    """Jarak edit Levenshtein benar-benar <= 1."""
    if s == t:
        return True
    if abs(len(s) - len(t)) > 1:
        return False
    if len(s) == len(t):
        return sum(1 for x, y in zip(s, t) if x != y) <= 1
    if len(s) > len(t):
        s, t = t, s
    i = j = 0
    skipped = False
    while i < len(s) and j < len(t):
        if s[i] == t[j]:
            i += 1
            j += 1
        elif not skipped:
            skipped = True
            j += 1
        else:
            return False
    return True


# --------------------------------------------------------------------------
# Parsing nama
# --------------------------------------------------------------------------

def _strip_al(tok: str) -> str:
    return tok[2:] if len(tok) > 3 and tok.startswith("ال") else tok


def _is_nisbah_tok(tok: str) -> bool:
    return len(tok) > 3 and tok.startswith("ال") and _strip_al(tok).endswith("ي")


class NameInfo:
    __slots__ = ("chain", "kunyas", "father_kunya", "nisbah", "kunya_titled", "kunya_head", "norm", "tokens")

    def __init__(self):
        self.chain: list[str] = []
        self.kunyas: set[str] = set()
        self.father_kunya: str | None = None
        self.nisbah: set[str] = set()
        self.kunya_titled: bool = False
        self.kunya_head: str | None = None
        self.norm: str = ""
        self.tokens: list[str] = []


def _kunya_phrase(seg_tokens: list[str]) -> str | None:
    p = seg_tokens[0]
    if p in ("ابو", "ابي", "ابا"):
        rest = []
        for t in seg_tokens[1:]:
            if len(t) > 3 and t.startswith("ال"):
                break
            rest.append(t)
            if len(rest) >= 3:
                break
        return "ابو " + " ".join(rest) if rest else "ابو"
    if p == "ام":
        rest = []
        for t in seg_tokens[1:]:
            if len(t) > 3 and t.startswith("ال"):
                break
            rest.append(t)
            if len(rest) >= 2:
                break
        return "ام " + " ".join(rest) if rest else "ام"
    return None


def _canon_tokens(seg: list[str], is_last: bool, nisbah_out: set[str]) -> list[str]:
    if seg and seg[0].startswith("عبد"):
        return list(seg)
    out: list[str] = []
    for i, t in enumerate(seg):
        stripped = _strip_al(t)
        if len(t) > 3 and t.startswith("ال"):
            if _is_nisbah_tok(t):
                nisbah_out.add(t)
                continue
            if is_last and i > 0:
                nisbah_out.add(t)   # lakab di segmen akhir (الصديق)
                continue
        out.append(stripped)
    return out


def _split_segments(toks: list[str], connectors: set[str]) -> list[list[str]]:
    segs: list[list[str]] = [[]]
    for t in toks:
        if t in connectors:
            segs.append([])
        else:
            segs[-1].append(t)
    return [s for s in segs if s]


def _absorb_segments(segs: list[list[str]], info: NameInfo) -> None:
    """Serap daftar segmen (sudah dipisah konektor) ke info.chain/kunya/nisbah."""
    for idx, seg in enumerate(segs):
        is_last = idx == len(segs) - 1
        kpos = next((i for i, t in enumerate(seg) if t in KUNYA_PREFIXES), None)
        if kpos is not None:
            name_part = seg[:kpos]
            kun_seg = seg[kpos:]
            if name_part:
                canon = _canon_tokens(name_part, is_last=False, nisbah_out=info.nisbah)
                if canon:
                    info.chain.append(" ".join(canon))
            # lakab di belakang frasa kunya (ابو بكر الصديق)
            for t in kun_seg[1:]:
                if len(t) > 3 and t.startswith("ال") and _strip_al(t).endswith("ي"):
                    info.nisbah.add(t)
                elif len(t) > 3 and t.startswith("ال"):
                    info.nisbah.add(t)
            phrase = _kunya_phrase(kun_seg)
            if not phrase:
                continue
            if idx == 0 and kpos == 0:
                info.kunya_titled = True
                info.kunya_head = phrase
            elif kpos == 0:
                info.kunyas.add(phrase)
                if idx == 1 and info.father_kunya is None:
                    info.father_kunya = phrase   # بن أبي X → kunya ayah
            else:
                info.kunyas.add(phrase)          # name + ابو Y → kunya sendiri
        else:
            canon = _canon_tokens(seg, is_last=is_last, nisbah_out=info.nisbah)
            if canon:
                info.chain.append(" ".join(canon))


def split_clauses(raw: str) -> list[str]:
    parts = re.split(r"[،؛]|\s[-–—]+\s", raw)
    return [p.strip() for p in parts if p.strip()]


def parse_name(raw: str) -> NameInfo:
    """Parse judul penuh: klausa-klausa, kunya, nisbah, rantai nasab."""
    info = NameInfo()
    clauses = split_clauses(raw or "")
    full_parts: list[str] = []
    for ci, cl in enumerate(clauses):
        cn = strip_gelar(norm_name(cl))
        toks = [t for t in cn.split() if t not in STOP_TOKENS]
        if not toks:
            continue
        if ci > 0:
            # klausa lanjutan: nasab? gelar keluarga? appositive kunya/lakab?
            if toks[0] in SKIP_CLAUSE_HEADS:
                continue
            if toks[0] in ("بن", "ابن", "ب") and len(toks) > 1:
                rest = toks[1:]
            elif toks[0] in ("ابن",):
                continue
            else:
                # appositive: ekstrak kunya/lakab saja, jangan sentuh chain
                app = NameInfo()
                _absorb_segments(_split_segments(toks, TITLE_CONNECTORS), app)
                info.kunyas |= app.kunyas
                info.nisbah |= app.nisbah
                full_parts.append(cn)
                continue
            segs = _split_segments(rest, TITLE_CONNECTORS)
            _absorb_segments(segs, info)
            full_parts.append(cn)
            continue
        # klausa pertama
        segs = _split_segments(toks, TITLE_CONNECTORS)
        _absorb_segments(segs, info)
        full_parts.append(cn)
    info.norm = re.sub(r"\s+", " ", " ".join(full_parts)).strip()
    info.tokens = info.norm.split()
    return info


def chain_key(chain: list[str], n: int) -> tuple[str, ...] | None:
    return tuple(chain[:n]) if len(chain) >= n else None


# --------------------------------------------------------------------------
# Ekstraksi rantai nasab dari badan
# --------------------------------------------------------------------------

def extract_chains(text_norm: str, max_tokens: int = MAX_CHAIN_TOKENS) -> list[list[str]]:
    toks = [t for t in text_norm.split() if t not in STOP_TOKENS]
    chains: list[list[str]] = []
    i = 0
    n = len(toks)
    while i < n:
        if toks[i] in BODY_CONNECTORS:
            i += 1
            continue
        seg = [toks[i]]
        j = i + 1
        while j < n and toks[j] not in BODY_CONNECTORS:
            seg.append(toks[j])
            j += 1
        segs = [seg]
        while j < n and toks[j] in BODY_CONNECTORS:
            k = j + 1
            if k >= n or toks[k] in BODY_CONNECTORS:
                break
            nxt = [toks[k]]
            k += 1
            while k < n and toks[k] not in BODY_CONNECTORS:
                nxt.append(toks[k])
                k += 1
            segs.append(nxt)
            j = k
        if len(segs) >= 2:
            flat: list[str] = []
            for s in segs:
                if s[0].startswith("عبد"):
                    flat.append(" ".join(s))
                    continue
                keep = [_strip_al(t) if not _is_nisbah_tok(t) else None for t in s]
                joined = " ".join(t for t in keep if t)
                if joined:
                    flat.append(joined)
                if len(flat) >= max_tokens:
                    break
            if len(flat) >= 2:
                chains.append(flat[:max_tokens])
        i = j if j > i else i + 1
    chains.sort(key=len, reverse=True)
    return chains


HEADING_RE = re.compile(r"^\s*[\u0660-\u0669\u06F0-\u06F90-9]{1,7}\s*[-–—.:،)ـ]")


def is_heading_like(para: str) -> bool:
    p = para.strip()
    return bool(HEADING_RE.match(p)) or p.startswith("[")


# --------------------------------------------------------------------------
# Muat data
# --------------------------------------------------------------------------

def load_pages() -> dict[str, dict[int, list[str]]]:
    pages: dict[str, dict[int, list[str]]] = {}
    with open(DATA / "pages_full.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            pages.setdefault(r["source"], {})[r["web_page"]] = r["paras"]
    return pages


def load_segments() -> list[dict]:
    with open(DATA / "person_segments.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def head_paras(pages: dict, source: str, seg: dict, want: int = HEAD_PARAS) -> list[str]:
    out: list[str] = []
    sp, lp = seg["start_page"], seg.get("last_page") or seg["start_page"]
    ps = seg.get("para_start") if seg.get("para_start") is not None else 0
    book = pages.get(source, {})
    page = book.get(sp)
    while page is not None and sp <= lp + 1 and len(out) < want:
        for i in range(ps, len(page)):
            if len(out) >= want:
                break
            if out and is_heading_like(page[i]):
                return out
            out.append(page[i])
        sp += 1
        ps = 0
        page = book.get(sp)
    return out


def first_body_para(pages: dict, source: str, seg: dict) -> str:
    sp, lp = seg["start_page"], seg.get("last_page") or seg["start_page"]
    ps = seg.get("para_start") if seg.get("para_start") is not None else 0
    book = pages.get(source, {})
    first: str | None = None
    page = book.get(sp)
    idx = ps + 1
    while page is not None and sp <= lp + 1:
        for i in range(idx, len(page)):
            p = page[i].strip()
            if is_heading_like(p):
                return first if first else p
            if len(p) > 8 and first is None:
                first = p
        sp += 1
        idx = 0
        page = book.get(sp)
    return first or ""


# --------------------------------------------------------------------------
# Indeks Ishabah
# --------------------------------------------------------------------------

class IshIndex:
    def __init__(self):
        self.exact: dict[str, list[int]] = defaultdict(list)
        self.exact_no_nisbah: dict[str, list[int]] = defaultdict(list)
        self.c3: dict[tuple, set[int]] = defaultdict(set)
        self.c2: dict[tuple, set[int]] = defaultdict(set)
        self.c0: dict[str, set[int]] = defaultdict(set)
        self.kunya_titles: dict[str, set[int]] = defaultdict(set)
        self.profiles: dict[int, dict] = {}
        self.kunya_ids: set[int] = set()
        self.alias: dict[int, int] = {}          # entri kuna -> entri utama

    # ---- build ----
    def build(self, segs: list[dict], pages: dict) -> None:
        for seg in segs:
            if seg["source"] != "ishabah" or seg.get("entry_num") is None:
                continue
            name = (seg.get("name") or "").strip()
            if not name:
                continue
            eid = seg["entry_num"]
            info = parse_name(name)
            paras = head_paras(pages, "ishabah", seg)
            head_norm = norm_name(" ".join(paras))
            body_chains = extract_chains(head_norm)
            # rantai badan hanya boleh MELANJUTKAN rantai judul (prefiks sama), bukan menimpa identitas
            full_chain = list(info.chain)
            for ch in body_chains:
                if info.chain:
                    if ch[:len(info.chain)] == info.chain and len(ch) > len(full_chain):
                        full_chain = ch
                elif len(ch) > len(full_chain):
                    full_chain = ch
            prof = {
                "seg": seg, "info": info, "chain": full_chain,
                "kunyas": set(info.kunyas), "father_kunya": info.father_kunya,
                "nisbah": set(info.nisbah), "head_norm": head_norm,
                "kunya_titled": info.kunya_titled,
                "terms": set(head_norm.split()),
            }
            # kunya dari badan (maks 4 frasa)
            htoks = head_norm.split()
            for tok_i, tok in enumerate(htoks):
                if tok in KUNYA_PREFIXES and tok_i + 1 < len(htoks):
                    rest = []
                    for t in htoks[tok_i + 1: tok_i + 4]:
                        if len(t) > 3 and t.startswith("ال"):
                            break
                        rest.append(t)
                        if len(rest) >= 2:
                            break
                    if rest:
                        prof["kunyas"].add(("ابو " if tok != "ام" else "ام ") + " ".join(rest))
                if len(prof["kunyas"]) >= 6:
                    break
            self.exact[info.norm].append(eid)
            self.profiles[eid] = prof
            if info.kunya_titled:
                self.kunya_ids.add(eid)
                if info.kunya_head:
                    self.kunya_titles[info.kunya_head].add(eid)
            else:
                no_nis = info.norm
                for n in info.nisbah:
                    no_nis = no_nis.replace(" " + n, "").replace(n, "")
                no_nis = re.sub(r"\s+", " ", no_nis).strip()
                if no_nis:
                    self.exact_no_nisbah[no_nis].append(eid)
                self._index_chain(full_chain, eid)
        self._build_alias()

    def _index_chain(self, chain: list[str], eid: int) -> None:
        k1, k2, k3 = chain_key(chain, 1), chain_key(chain, 2), chain_key(chain, 3)
        if k1:
            self.c0[k1[0]].add(eid)
        if k2:
            self.c2[k2].add(eid)
            a, b = k2
            if len(b) >= 4:  # varian fuzzy pos-1
                for v in del1(b):
                    if v != b:
                        self.c2[(a, v)].add(eid)
        if k3:
            self.c3[k3].add(eid)
            a, b, c = k3
            if len(b) >= 4:
                for v in del1(b):
                    if v != b:
                        self.c3[(a, v, c)].add(eid)
            if len(c) >= 4:
                for v in del1(c):
                    if v != c:
                        self.c3[(a, b, v)].add(eid)

    def _lookup2(self, a: str, b: str, fuzzy: bool = True) -> set[int]:
        """Kandidat dua sisi (del1 x del1) lalu difilter edist<=1 — substitusi jarak-1
        (نقيل/نفيل) tetap tertangkap, pasangan jarak-2 (عثمان/النعمان) tertolak."""
        if not fuzzy:
            return set(self.c2.get((a, b), ()))
        out = set(self.c2.get((a, b), ()))
        if len(b) >= 4:
            for v in del1(b):
                if v != b:
                    out |= self.c2.get((a, v), set())
        if out:
            out = {h for h in out
                   if len(self.profiles[h]["chain"]) > 1
                   and (self.profiles[h]["chain"][1] == b or edist_le1(b, self.profiles[h]["chain"][1]))}
        return out

    def _lookup3(self, a: str, b: str, c: str, fuzzy: bool = True) -> set[int]:
        if not fuzzy:
            return set(self.c3.get((a, b, c), ()))
        out = set(self.c3.get((a, b, c), ()))
        if len(b) >= 4:
            for v in del1(b):
                if v != b:
                    out |= self.c3.get((a, v, c), set())
        if len(c) >= 4:
            for v in del1(c):
                if v != c:
                    out |= self.c3.get((a, b, v), set())
        if out:
            out = {h for h in out
                   if len(self.profiles[h]["chain"]) > 2
                   and (self.profiles[h]["chain"][1] == b or edist_le1(b, self.profiles[h]["chain"][1]))
                   and (self.profiles[h]["chain"][2] == c or edist_le1(c, self.profiles[h]["chain"][2]))}
        return out

    # ---- alias: entri kuna -> entri utama ----
    def _build_alias(self) -> None:
        mains = [eid for eid, p in self.profiles.items() if not p["kunya_titled"]]
        for eid in sorted(self.kunya_ids):
            prof = self.profiles[eid]
            core = prof["info"].norm
            if not core:
                continue
            # 1) inti judul kuna muncul utuh di head_norm entri utama
            hits = {m for m in mains if core in self.profiles[m]["head_norm"]}
            if len(hits) == 1:
                self.alias[eid] = next(iter(hits))
                continue
            if len(hits) > 1:
                continue
            # 2) "اسمه X بن Y …" → resolusi nasab ke entri utama (kemunculan pertama; nama boleh majemuk)
            m = None
            d2 = None
            for mm in re.finditer(r"(?:واسمه|اسمه)\s+(\S+(?:\s\S+)?(?:\s(?:بن|ابن)\s+\S+(?:\s\S+)?){1,3})", prof["head_norm"]):
                dd = parse_name(mm.group(1))
                if dd.chain and not dd.kunya_titled:
                    m, d2 = mm, dd
                    break
            if not m:
                continue
            cand = self._resolve_chain(d2, prof["head_norm"])
            if len(cand) == 1:
                self.alias[eid] = next(iter(cand))

    def _resolve_chain(self, d: NameInfo, head_norm: str) -> set[int]:
        """Resolusi rantai ke entri utama (untuk keperluan alias)."""
        k3 = chain_key(d.chain, 3)
        if k3:
            hits = {h for h in self._lookup3(*k3) if h in self.profiles and not self.profiles[h]["kunya_titled"]}
            if len(hits) == 1:
                return hits
        k2 = chain_key(d.chain, 2)
        if k2:
            hits = {h for h in self._lookup2(*k2) if h in self.profiles and not self.profiles[h]["kunya_titled"]}
            if hits:
                dis = self._disambiguate(sorted(hits), d)
                if len(dis) == 1:
                    return dis
        return set()

    def _score(self, cid: int, d: NameInfo) -> int:
        p = self.profiles[cid]
        pref = 0
        for i, seg in enumerate(d.chain[1:6]):
            if i + 1 < len(p["chain"]) and p["chain"][i + 1] == seg:
                pref += 1
            else:
                break
        nis = 1 if (d.nisbah and (d.nisbah & p["nisbah"] or d.nisbah & p["terms"])) else 0
        kun = 0
        if d.kunyas:
            kun = 1 if (d.kunyas & p["kunyas"] or any(k in p["head_norm"] for k in d.kunyas)) else 0
        fk = 1 if (d.father_kunya and (d.father_kunya == p["father_kunya"] or d.father_kunya.split()[-1] in p["terms"])) else 0
        return pref * 4 + nis * 3 + kun * 2 + fk

    def _disambiguate(self, cand_ids: list[int], d: NameInfo) -> list[int]:
        scored = [(self._score(cid, d), cid) for cid in cand_ids]
        top = max(s for s, _ in scored)
        return sorted(cid for s, cid in scored if s == top)


# --------------------------------------------------------------------------
# Resolusi
# --------------------------------------------------------------------------

def _cand_list(idx: IshIndex, ids, cap: int = 6) -> list[dict]:
    out = []
    for i in list(ids)[:cap]:
        nm = idx.profiles.get(i, {}).get("seg", {}).get("name", "")
        out.append({"ishabah_id": i, "ishabah_name": nm})
    return out


def _ok(eid: int, idx: IshIndex, method: str, conf: str, cands=None) -> dict:
    return {"status": "resolved", "ishabah_id": eid,
            "ishabah_name": idx.profiles[eid]["seg"]["name"],
            "method": method, "confidence": conf, "candidates": cands or []}


def _amb(idx: IshIndex, ids, method: str, conf: str) -> dict:
    return {"status": "ambiguous", "candidates": _cand_list(idx, sorted(ids)), "method": method,
            "confidence": conf, "ishabah_id": None, "ishabah_name": None}


def _unres() -> dict:
    return {"status": "unresolved", "candidates": [], "method": None,
            "confidence": None, "ishabah_id": None, "ishabah_name": None}


def _pick_dup(idx: IshIndex, hits: list[int], method: str) -> dict:
    """Temuan 3: duplikat antar-qism → id terkecil, exact_dup, medium."""
    cands = _cand_list(idx, sorted(set(hits)))
    return _ok(min(hits), idx, method, "medium", cands)


def _dup_or_amb(idx: IshIndex, hits: list[int], method: str, conf: str) -> dict:
    """Dup-antara-qism: bila SEMUA kandidat ber-norm identik → resolved id terkecil
    (dup_norm, medium); bila saling ber-relasi prefiks (norm pendek = prefiks norm panjang)
    → pilih norm terpendek; selain itu → ambiguous."""
    def norm_of(h):
        p = idx.profiles[h]
        return p["info"].norm or " ".join(p["chain"])
    norms = {norm_of(h) for h in hits}
    if len(norms) == 1:
        return _pick_dup(idx, sorted(hits), "dup_norm")
    ordered = sorted(norms, key=lambda n: len(n.split()))
    pref_ok = all(ordered[i + 1].split()[:len(ordered[i].split())] == ordered[i].split()
                  for i in range(len(ordered) - 1))
    if pref_ok:
        short = ordered[0]
        short_hits = sorted(h for h in hits if norm_of(h) == short)
        if short_hits:
            return _ok(min(short_hits), idx, "dup_norm", "medium", _cand_list(idx, sorted(hits)))
    return _amb(idx, hits, method, conf)


def resolve_one(idx: IshIndex, d: NameInfo) -> dict:
    # 1) exact (judul vs judul)
    hits = idx.exact.get(d.norm)
    if hits:
        hits = sorted(set(hits))
        if len(hits) == 1:
            return _ok(hits[0], idx, "exact", "high")
        return _pick_dup(idx, hits, "exact_dup")
    if not d.kunya_titled:
        no_nis = d.norm
        for n in d.nisbah:
            no_nis = no_nis.replace(" " + n, "").replace(n, "")
        no_nis = re.sub(r"\s+", " ", no_nis).strip()
        if no_nis and no_nis != d.norm:
            for table in (idx.exact, idx.exact_no_nisbah):
                hits = sorted(set(table.get(no_nis, [])))
                if len(hits) == 1:
                    return _ok(hits[0], idx, "exact", "high")
                if len(hits) > 1:
                    return _pick_dup(idx, hits, "exact_dup")
    # 2) nasab3 — dua tahap: exact dulu, fuzzy hanya bila exact kosong
    k3 = chain_key(d.chain, 3)
    if k3 is not None and not d.kunya_titled:
        a, b, c = k3
        for fuzzy in (False, True):
            hits = sorted({h for h in idx._lookup3(a, b, c, fuzzy=fuzzy)
                           if h in idx.profiles and not idx.profiles[h]["kunya_titled"]})
            if len(hits) == 1:
                return _ok(hits[0], idx, "nasab3", "high")
            if len(hits) > 1:
                best, _rest = _disambig_split(idx, hits, d)
                if len(best) == 1:
                    return _ok(best[0], idx, "nasab3", "high")
                if len(best) > 1:
                    return _dup_or_amb(idx, best, "nasab3", "high")
                # tahap exact tanpa pemenang → coba tahap fuzzy juga
                if not fuzzy:
                    continue
                return _dup_or_amb(idx, hits, "nasab3", "high")
    # 3) nasab2 + penguat — dua tahap exact/fuzzy
    k2 = chain_key(d.chain, 2)
    if k2 is not None and not d.kunya_titled:
        a, b = k2
        for fuzzy in (False, True):
            hits = sorted({h for h in idx._lookup2(a, b, fuzzy=fuzzy)
                           if h in idx.profiles and not idx.profiles[h]["kunya_titled"]})
            if len(hits) == 1:
                return _ok(hits[0], idx, "nasab2", "medium")
            if len(hits) > 1:
                best, _rest = _disambig_split(idx, hits, d)
                if len(best) == 1:
                    return _ok(best[0], idx, "nasab2", "medium")
                if not fuzzy:
                    continue
                return _dup_or_amb(idx, best if best else hits, "nasab2", "medium")
    # 4) nama tunggal + kunya ayah (بنت أبي بكر / بن أبي قحافة)
    if not d.kunya_titled and d.father_kunya and d.chain:
        fk_tok = d.father_kunya.split()[-1]
        cands = []
        for cid in idx.c0.get(d.chain[0], ()):  # nama pertama sama
            p = idx.profiles.get(cid)
            if not p or p["kunya_titled"]:
                continue
            if fk_tok in p["terms"] or (p["father_kunya"] and p["father_kunya"] == d.father_kunya):
                fk_exact = 1 if (p["father_kunya"] and p["father_kunya"] == d.father_kunya) else 0
                strong = (d.nisbah and (d.nisbah & p["nisbah"] or d.nisbah & p["terms"])) or \
                         (d.kunyas and (d.kunyas & p["kunyas"] or any(k in p["head_norm"] for k in d.kunyas)))
                cands.append((4 + fk_exact * 2 + (1 if strong else 0), cid))
        if cands:
            top = max(s for s, _ in cands)
            best = sorted({cid for s, cid in cands if s == top})
            if len(best) == 1 and top >= 5:   # penguat wajib: kunya-ayah persis atau nisbah/kunya
                return _ok(best[0], idx, "nasab_kunya", "medium")
            return _dup_or_amb(idx, sorted({cid for s, cid in cands}), "nasab_kunya", "medium")
    # 5) nama tunggal + kunya sendiri (الحارث أبو عبد الله)
    if not d.kunya_titled and len(d.chain) == 1 and d.kunyas:
        cands = sorted({cid for cid in idx.c0.get(d.chain[0], ())
                        if not idx.profiles.get(cid, {}).get("kunya_titled")
                        and (d.kunyas & idx.profiles[cid]["kunyas"]
                             or any(k in idx.profiles[cid]["head_norm"] for k in d.kunyas))})
        if len(cands) == 1:
            return _ok(cands[0], idx, "name_kunya", "medium")
        if len(cands) > 1:
            return _dup_or_amb(idx, cands, "name_kunya", "medium")
    # 6) nama tunggal + nisbah (سكن الضمري، ناسح الحضرمي)
    if not d.kunya_titled and len(d.chain) == 1 and d.nisbah:
        cands = sorted({cid for cid in idx.c0.get(d.chain[0], ())
                        if not idx.profiles.get(cid, {}).get("kunya_titled")
                        and (d.nisbah & idx.profiles[cid]["nisbah"]
                             or d.nisbah & idx.profiles[cid]["terms"])})
        if len(cands) == 1:
            return _ok(cands[0], idx, "name_nisbah", "medium")
        if len(cands) > 1:
            return _dup_or_amb(idx, cands, "name_nisbah", "medium")
    return _unres()


def _disambig_split(idx: IshIndex, hits: list[int], d: NameInfo) -> tuple[list[int], list[int]]:
    """Bagi kandidat: (kelompok skor teratas, sisa). Skor: prefix-nasab > nisbah/lakab > kunya > kunya-ayah."""
    scored = [(idx._score(cid, d), cid) for cid in hits]
    top = max(s for s, _ in scored)
    best = sorted(cid for s, cid in scored if s == top)
    rest = sorted(cid for s, cid in scored if s < top)
    return best, rest


def resolve_kunya_titled(idx: IshIndex, pages: dict, source: str, seg: dict, d: NameInfo) -> dict:
    """Aturan d: judul kunya - pakai "ismuhu"-nasab bila ada, lalu alias kuna."""
    # d1: "اسمه X بن Y" dari paragraf pertama
    paras = head_paras(pages, source, seg, want=4)
    head_norm = norm_name(" ".join(paras))
    # d1: "اسمه X بن Y" dari paragraf pertama — kemunculan PERTAMA menang (nama si entri,
    # bukan nama ayah di kalimat berikutnya); nama boleh majemuk (عبد الله بن أبي قحافة)
    pat = re.compile(r"(?:واسمه|واسمها|اسمه|اسمها)\s+(\S+(?:\s\S+)?(?:\s(?:بن|ابن|بنت)\s+\S+(?:\s\S+)?){1,3})")
    m = None
    for mm in pat.finditer(head_norm):
        dd = parse_name(mm.group(1))
        if dd.chain and not dd.kunya_titled:
            m, d2 = mm, dd
            break
    if m:
        res = resolve_one(idx, d2)
        if res["status"] == "resolved":
            res["method"] = "kunya_nasab"
            return res
    # d2: frasa nasab dalam judul sendiri (ام عبيد بنت صخر; ابو عتيق محمد بن عبد الرحمن)
    if len(d.chain) >= 2:
        d2b = NameInfo()
        d2b.chain, d2b.kunyas, d2b.nisbah = list(d.chain), set(d.kunyas), set(d.nisbah)
        d2b.father_kunya, d2b.kunya_head = d.father_kunya, None
        d2b.norm, d2b.tokens = d.norm, list(d.tokens)
        # judul memuat nama eksplisit → izinkan jalur nasab (override flag kuna)
        res = resolve_one(idx, d2b)
        if res["status"] == "resolved" and res["method"] in ("nasab3", "nasab2"):
            return res
    # d3: cocokkan kunya (+lakab penguat) ke bagian kuna lalu alias ke entri utama
    if d.kunya_head:
        cands = idx.kunya_titles.get(d.kunya_head, set())
        if d.nisbah:
            filtered = {c for c in cands if any(n in idx.profiles[c]["head_norm"] for n in d.nisbah)}
        else:
            filtered = set()
        pool = filtered if filtered else cands
        if len(pool) == 1:
            c = next(iter(pool))
            target = idx.alias.get(c, c)
            return _ok(target, idx, "kunya", "medium")
        if len(pool) > 1:
            targets = {idx.alias.get(c, c) for c in pool}
            if len(targets) == 1:
                return _ok(next(iter(targets)), idx, "kunya", "medium")
            # self-exact: kandidat kuna ber-norm PERSIS = judul → dup-antar-qism (temuan 3)
            self_hits = sorted(c for c in pool if idx.profiles[c]["info"].norm == d.norm)
            if len(self_hits) == 1:
                c = self_hits[0]
                return _ok(idx.alias.get(c, c), idx, "kunya", "medium",
                           _cand_list(idx, sorted(targets)))
            if len(self_hits) > 1:
                c = min(self_hits)
                return _ok(idx.alias.get(c, c), idx, "kunya_dup", "medium",
                           _cand_list(idx, sorted(targets)))
            return _amb(idx, targets, "kunya", "medium")     # temuan 5: wajib penguat
        if len(cands) > 1:
            # self-exact juga berlaku di kumpulan kuna luas
            self_hits = sorted(c for c in cands if idx.profiles[c]["info"].norm == d.norm)
            if len(self_hits) >= 1:
                c = min(self_hits)
                return _ok(idx.alias.get(c, c), idx, "kunya" if len(self_hits) == 1 else "kunya_dup",
                           "medium", _cand_list(idx, sorted({idx.alias.get(x, x) for x in cands})))
            return _amb(idx, {idx.alias.get(c, c) for c in cands}, "kunya", "medium")
        if len(cands) == 1:
            c = next(iter(cands))
            return _ok(idx.alias.get(c, c), idx, "kunya", "medium")
    # d4: coba apa adanya (exact title kunya vs kunya-section)
    hits = idx.exact.get(d.norm)
    if hits and len(hits) == 1:
        c = hits[0]
        if c in idx.kunya_ids and c in idx.alias:
            return _ok(idx.alias[c], idx, "kunya", "medium")
    return _unres()


def resolve_entry(idx: IshIndex, pages: dict, source: str, seg: dict) -> dict:
    name = (seg.get("name") or "").strip()
    d = parse_name(name)
    if d.kunya_titled:
        return resolve_kunya_titled(idx, pages, source, seg, d)
    return resolve_one(idx, d)


# --------------------------------------------------------------------------
# Pasangan Usud
# --------------------------------------------------------------------------

def pair_usud(segs: list[dict]) -> dict[tuple[str, int], tuple[str, int]]:
    by_src: dict[str, dict[int, str]] = {"usud_ilmiyah": {}, "usud_rifai": {}}
    for s in segs:
        if s["source"] in by_src and s.get("entry_num") is not None:
            nm = (s.get("name") or "").strip()
            if nm:
                by_src[s["source"]][s["entry_num"]] = norm_name(nm)
    pairs: dict[tuple[str, int], tuple[str, int]] = {}
    used: set[int] = set()
    for num, nm in sorted(by_src["usud_ilmiyah"].items()):
        for delta in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5):
            cand = num + delta
            if cand in by_src["usud_rifai"] and cand not in used and by_src["usud_rifai"][cand] == nm:
                used.add(cand)
                pairs[("usud_ilmiyah", num)] = ("usud_rifai", cand)
                pairs[("usud_rifai", cand)] = ("usud_ilmiyah", num)
                break
    return pairs


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    pages = load_pages()
    segs = load_segments()
    by_source: dict[str, list[dict]] = defaultdict(list)
    for s in segs:
        by_source[s["source"]].append(s)
    for src in by_source:
        by_source[src].sort(key=lambda r: (r.get("entry_num") is None, r.get("entry_num") or 0))

    idx = IshIndex()
    idx.build(by_source.get("ishabah", []), pages)
    pairs = pair_usud(segs)

    rows: list[dict] = []
    skipped_structural = 0
    resolved_cache: dict[tuple[str, int], dict] = {}
    seg_map = {(r["source"], r.get("entry_num")): r for r in segs if r.get("entry_num") is not None}

    order = ["istiab", "usud_ilmiyah", "usud_rifai", "tabaqat"]
    for source in order:
        for seg in by_source.get(source, []):
            name = (seg.get("name") or "").strip()
            if not name or seg.get("entry_num") is None:
                continue
            if source == "tabaqat" and name.startswith("الطبقة"):
                skipped_structural += 1
                continue
            num = seg["entry_num"]
            key = (source, num)
            if key in resolved_cache:
                rows.append({"source": source, "entry_num": num, "name": name, **resolved_cache[key]})
                continue
            res = resolve_entry(idx, pages, source, seg)
            if source in ("usud_ilmiyah", "usud_rifai"):
                partner = pairs.get(key)
                if partner and partner not in resolved_cache:
                    pres = dict(res)
                    if res["status"] == "resolved":
                        pres["method"] = "usud_pair"
                    resolved_cache[partner] = pres
            rows.append({"source": source, "entry_num": num, "name": name, **res})

    with open(OUT_LINKS, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(OUT_UNRESOLVED, "w", encoding="utf-8") as f:
        for r in rows:
            if r["status"] == "resolved":
                continue
            seg = seg_map.get((r["source"], r["entry_num"]))
            body = first_body_para(pages, r["source"], seg) if seg else ""
            body = re.sub(r"\s+", " ", body).replace("\t", " ")[:150]
            f.write(f"{r['source']}\t{r['entry_num']}\t{r['name']}\t{body}\n")

    # ---------- laporan ----------
    report: dict = {"counts": {}, "sources": {}, "probes": [], "targets": {}}
    for source in order:
        rs = [r for r in rows if r["source"] == source]
        n = len(rs)
        st = Counter(r["status"] for r in rs)
        methods = Counter(r["method"] for r in rs if r["status"] == "resolved")
        report["sources"][source] = {
            "n": n, "resolved": st["resolved"], "ambiguous": st["ambiguous"], "unresolved": st["unresolved"],
            "resolved_pct": round(100.0 * st["resolved"] / n, 1) if n else 0,
            "ambiguous_pct": round(100.0 * st["ambiguous"] / n, 1) if n else 0,
            "unresolved_pct": round(100.0 * st["unresolved"] / n, 1) if n else 0,
            "methods": dict(sorted(methods.items(), key=lambda kv: -kv[1])),
        }
    report["counts"] = {
        "ishabah_entries_indexed": len(idx.profiles),
        "ishabah_kunya_section": len(idx.kunya_ids),
        "kunya_alias_resolved": len(idx.alias),
        "usud_pairs": len(pairs) // 2,
        "rows_out": len(rows),
        "skipped_structural_tabaqat": skipped_structural,
    }

    def find_row(source, num):
        return next((r for r in rows if r["source"] == source and r["entry_num"] == num), None)

    probes = []
    for label, source, num, expect in [
        ("istiab#1633→4835", "istiab", 1633, 4835),
        ("usud_rifai#3064→4835", "usud_rifai", 3064, 4835),
        ("usud_ilmiyah#3066→4835", "usud_ilmiyah", 3066, 4835),
        ("tabaqat#46→4835", "tabaqat", 46, 4835),
        ("istiab#1878→5752 (عمر)", "istiab", 1878, 5752),
        ("istiab#1612→4852 (عبد الله بن عمر)", "istiab", 1612, 4852),
    ]:
        row = find_row(source, num)
        got = row.get("ishabah_id") if row else None
        probes.append({"probe": label, "expect": expect, "got": got, "pass": got == expect})

    row = next((r for r in rows if r["source"] == "istiab" and r["name"].startswith("عمر بن الخطاب")), None)
    ih = idx.profiles.get(row.get("ishabah_id"), {}) if row and row.get("ishabah_id") else {}
    ok = bool(row and row["status"] == "resolved" and ih and ih["seg"]["name"].startswith("عمر بن الخطاب"))
    probes.append({"probe": "istiab عمر بن الخطاب → ishabah عمر بن الخطاب", "expect": "resolved+name",
                   "got": f"{row['status'] if row else 'missing'}:{ih.get('seg', {}).get('name', '')[:30] if ih else None}", "pass": ok})
    row = next((r for r in rows if r["source"].startswith("usud") and r["name"].startswith("عائشة بنت أبي بكر")), None)
    ih = idx.profiles.get(row.get("ishabah_id"), {}) if row and row.get("ishabah_id") else {}
    ok = bool(row and row["status"] == "resolved" and ih and ih["seg"]["name"].startswith("عائشة بنت أبي بكر"))
    probes.append({"probe": "usud عائشة بنت أبي بكر → ishabah عائشة بنت أبي بكر", "expect": "resolved+name",
                   "got": f"{row['status'] if row else 'missing'}:{ih.get('seg', {}).get('name', '')[:30] if ih else None}", "pass": ok})
    report["probes"] = probes

    for src, target in [("istiab", 70.0), ("usud_ilmiyah", 70.0), ("usud_rifai", 70.0)]:
        pct = report["sources"][src]["resolved_pct"]
        report["targets"][src] = {"resolved_pct": pct, "target": target, "pass": pct >= target}

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # ---------- ringkasan ----------
    print("=" * 78)
    print("RESOLVE_PERSONS — ringkasan resolusi entitas → Al-Ishabah")
    print("=" * 78)
    print(f"{'sumber':<14}{'n':>6}{'resolved':>10}{'ambig':>8}{'unres':>8}{'res%':>8}")
    print("-" * 78)
    for src in order:
        s = report["sources"][src]
        print(f"{src:<14}{s['n']:>6}{s['resolved']:>10}{s['ambiguous']:>8}{s['unresolved']:>8}{s['resolved_pct']:>8}")
    print("-" * 78)
    print("metode per sumber:")
    for src in order:
        m = report["sources"][src]["methods"]
        if m:
            print(f"  {src:<12}" + "  ".join(f"{k}={v}" for k, v in m.items()))
    print("-" * 78)
    print("probe wajib:")
    for p in probes:
        print(f"  [{'PASS' if p['pass'] else 'FAIL'}] {p['probe']:<44} expect={p['expect']} got={p['got']}")
    print("-" * 78)
    print("target resolved ≥70% (istiab/usud):")
    for src, t in report["targets"].items():
        print(f"  [{'PASS' if t['pass'] else 'FAIL'}] {src:<14} {t['resolved_pct']}%")
    print("-" * 78)
    c = report["counts"]
    print(f"index ishabah: {c['ishabah_entries_indexed']} (kuna: {c['ishabah_kunya_section']}, alias->utama: {c['kunya_alias_resolved']}); "
          f"pasangan usud: {c['usud_pairs']}; baris: {c['rows_out']}; struktural tabaqat: {skipped_structural}")
    print(f"selesai {time.time() - t0:.1f}s → {OUT_LINKS.name}, {OUT_UNRESOLVED.name}, {OUT_REPORT.name}")
    all_pass = all(p["pass"] for p in probes) and all(t["pass"] for t in report["targets"].values())
    print("VALIDATOR:", "LOLOS" if all_pass else "BELUM LOLOS")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
