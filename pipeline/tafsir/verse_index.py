#!/usr/bin/env python3
"""VERSE-INDEX: teks ayat per (surah, ayat) dari display blocks maraghi.

Display block = baris antara header [سورة X (N) : الآيات A-B] dan baris
berikutnya yang diawali '['. Regex pasangan `teks (N)` diekstrak berurutan.

Output: data/verse_index.json {surah: {ayat: "teks ternormalisasi"}}
Semua path relatif ke folder script ini (pc_local/); semua open() eksplisit
encoding utf-8 (wajib di Windows; default cp1252 merusak file Arab).
"""
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent          # pc_local/
DATA = ROOT / 'data'
TOC = json.load(open(ROOT / 'toc_full.json', encoding='utf-8'))['maraghi']['surahs']
P = {}
with open(DATA / 'pages_full.jsonl', encoding='utf-8') as r:
    for line in r:
        rec = json.loads(line)
        if rec['source'] == 'maraghi':
            P[rec['web_page']] = rec['paras']

HARAKAT = re.compile(r'[\u064B-\u0652\u0670\u0640]')
def norm(t):
    return re.sub(r'\s+', ' ', HARAKAT.sub('', t)).strip()

AR = '٠١٢٣٤٥٦٧٨٩'
def ar2int(s):
    return int(''.join(str(AR.index(c)) for c in s))

RE_H = re.compile(r'^\[+\s*سورة\s+[^\]]+?\s*\(\s*[٠-٩]+\s*\)\s*:\s*(?:الآيات|آيات)\s+[٠-٩]+\s+الى\s+[٠-٩]+\s*\]+')
RE_HS = re.compile(r'^\[+\s*سورة\s+[^\]]+?\s*\(\s*[٠-٩]+\s*\)\s*:\s*آية\s+[٠-٩]+\s*\]+')
# pasangan: teks Arab lalu (N)
RE_VN = re.compile(r'([\u0621-\u064A][\u0621-\u064A\s]{1,}?)\s*\(([٠-٩]+)\)')

def build():
    idx = {}
    for sn, meta in TOC.items():
        flat = []
        for w in range(meta['start'], meta['end_excl']):
            for p, t in enumerate(P.get(w, [])):
                flat.append(t)
        verses = {}
        in_block = False
        for t in flat:
            tn = norm(t)
            if RE_H.match(tn) or RE_HS.match(tn):
                in_block = True
                # header: ABAIKAN pasangan (N) di header — itu nomor surah/rentang,
                # bukan penomoran ayat display
                continue
            if in_block:
                if t.startswith('['):
                    in_block = False
                    continue
                for ph, n in RE_VN.findall(tn):
                    ph = ph.strip()
                    # Ronde-2 fix (C): filter 'ph.startswith(سورة)' DIHAPUS —
                    # satu-satunya baris yang pernah kena filter itu justru
                    # ayat asli 24:1 ("سُورَةٌ أَنْزَلْناها..."); artefak nama
                    # surah tidak pernah muncul di display block (scan korpus
                    # penuh: 0 hit lain).
                    verses[ar2int(n)] = ph
        # basmalah Fatihah: baris بِسْمِ tanpa nomor, konvensi pipeline = ayat 1
        if not verses.get(1) and sn == '1':
            for t in flat:
                if norm(t).startswith('بسم الله'):
                    verses[1] = norm(t)
                    break
        idx[int(sn)] = verses
    return idx

if __name__ == '__main__':
    idx = build()
    # ---- audit terhadap jumlah ayat Hafs ----
    AY = {1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,11:123,12:111,
    13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,21:112,22:78,23:118,24:64,25:77,
    26:227,27:93,28:88,29:69,30:60,31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,39:75,
    40:85,41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,49:18,50:45,51:60,52:49,53:62,
    54:55,55:78,56:96,57:29,58:22,59:24,60:13,61:14,62:11,63:11,64:18,65:12,66:12,67:30,
    68:52,69:52,70:44,71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,79:46,80:42,81:29,
    82:19,83:36,84:25,85:22,86:17,87:19,88:26,89:30,90:20,91:15,92:21,93:11,94:8,95:8,
    96:19,97:5,98:8,99:8,100:11,101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,
    110:3,111:5,112:4,113:5,114:6}
    bad = []
    for sn, v in idx.items():
        need = set(range(1, AY[sn] + 1))
        have = set(v.keys())
        extra = have - need
        if extra:
            for e in extra:
                del v[e]
        if have != need and (need - have):
            bad.append((sn, sorted(need - have)[:6]))
    print(f'surah: {len(idx)} | ayat total: {sum(len(v) for v in idx.values())}')
    print('surah dgn ayat hilang (post-clean):', bad[:12])
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / 'ayat_count.json', 'w', encoding='utf-8') as f:
        json.dump(AY, f)
    with open(DATA / 'verse_index.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(idx, ensure_ascii=False, indent=0))
    print('-> data/verse_index.json + data/ayat_count.json')