#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gabungkan hasil LLM (data/link_results/*.json) -> data/person_links_llm.jsonl
(format sama dengan person_links.jsonl; dipakai build_full_db.py sebagai prioritas).
Validasi: ishabah_id harus termasuk kandidat blok batch; pasangan usud disalin.
"""
import glob, json, pathlib, re, collections

BASE = pathlib.Path(__file__).resolve().parent
BATCH = BASE / "data" / "link_batches"
RES = BASE / "data" / "link_results"
OUT = BASE / "data" / "person_links_llm.jsonl"

# kandidat per Q dari batch
cands = {}
for f in BATCH.glob("*.txt"):
    cur = None
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### Q (\w+)#(\d+)", line)
        if m:
            cur = (m.group(1), int(m.group(2))); cands[cur] = set(); continue
        m = re.match(r"^\s*\*?\s*\[(\d+)\]", line)
        if m and cur: cands[cur].add(int(m.group(1)))

# pasangan usud dari person_links (usud_pair)
links = [json.loads(l) for l in (BASE / "data" / "person_links.jsonl").open(encoding="utf-8")]
by_key = {(l["source"], l["entry_num"]): l for l in links}

rows, stats = [], collections.Counter()
for f in sorted(RES.glob("*.json")):
    try:
        d = json.load(f.open(encoding="utf-8"))
    except Exception as e:
        stats["file_error"] += 1; print("ERR", f.name, e); continue
    for x in d:
        try:
            key = (str(x.get("source")).strip(), int(str(x.get("entry_num")).strip()))
        except (TypeError, ValueError):
            stats["bad_key"] += 1; continue
        if key not in cands:
            stats["unknown_q"] += 1; continue
        iid = x.get("ishabah_id")
        if iid is not None and int(iid) not in cands[key]:
            stats["id_not_in_candidates"] += 1; iid = None
        conf = x.get("confidence") or "low"
        if iid is None:
            rows.append({"source": key[0], "entry_num": key[1], "name": by_key.get(key, {}).get("name"),
                         "ishabah_id": None, "ishabah_name": None, "method": "llm", "confidence": conf,
                         "status": "unresolved", "candidates": sorted(cands[key]), "reason": x.get("reason")})
            stats["llm_null"] += 1
        else:
            rows.append({"source": key[0], "entry_num": key[1], "name": by_key.get(key, {}).get("name"),
                         "ishabah_id": int(iid), "ishabah_name": None, "method": "llm", "confidence": conf,
                         "status": "resolved", "candidates": sorted(cands[key]), "reason": x.get("reason")})
            stats["llm_resolved"] += 1
            stats[f"conf_{conf}"] += 1

# salin ke pasangan usud: usud_rifai -> usud_ilmiyah dengan nama ter-norm sama yang belum resolved
T = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
def nn(s):
    s = T.sub("", s or "")
    for a, b in (("أ","ا"),("إ","ا"),("آ","ا"),("ة","ه"),("ى","ي")): s = s.replace(a, b)
    return re.sub(r"[\s\[\]\(\)«»:،.\-]+", " ", s).strip()
ilm_open = collections.defaultdict(list)
for l in links:
    if l["source"] == "usud_ilmiyah" and l["status"] != "resolved":
        ilm_open[nn(l["name"])].append(l["entry_num"])
extra = []
for r in rows:
    if r["source"] == "usud_rifai" and r["ishabah_id"] is not None:
        for n2 in ilm_open.get(nn(r["name"]), []):
            extra.append({**r, "source": "usud_ilmiyah", "entry_num": n2, "name": by_key.get(("usud_ilmiyah", n2), {}).get("name"), "method": "llm_pair"})
rows += extra
stats["pair_copied"] = len(extra)

with OUT.open("w", encoding="utf-8") as w:
    for r in rows:
        w.write(json.dumps(r, ensure_ascii=False) + "\n")
print(dict(stats), "->", OUT, len(rows), "baris;", "batch Q total", len(cands), "; hasil file", len(list(RES.glob('*.json'))))
