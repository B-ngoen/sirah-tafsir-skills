#!/usr/bin/env python3
"""Dorar EN grouping — mapping deterministik dari title halaman ke surah.

Dorar (dorar.net/en/tafseer, bahasa Inggris) tidak butuh anchor scanning:
judul halaman sudah eksplisit, dua pola:
  "The overall tafseer of Quran - Al-Baqarah 1-5"   -> tafsir rentang ayat
  "The overall tafseer of Quran - Al-Baqarah 7"     -> tafsir satu ayat
  "The overall tafseer of Quran - Al-Baqarah Introduction of Sura" -> intro

Output: data/grouping_full/dorar_en_{sn:03d}.rb.json — satu segmen per halaman
(label 'A-B' / 'N' / 'intro'), urut web_page.

RONDE-3 (ROUND3-SPEC.md): validasi diturunkan jadi PERINGATAN — data
situs diterima apa adanya (anomali judul/urutan halaman situs, mis.
'Ash-Shu'araa 60-175', 'Yunus 7-89', blok terbalik Az-Zumar).
Semua .rb.json tetap ditulis; masalah dicatat di _report.json pada
key 'warnings' (per surah); ayat yang benar-benar tak ada di situs
dicatat key 'missing_on_site' — TIDAK diisi dari sumber mana pun.

Baca dari data/pages_full.jsonl (hasil parse_mp.py, source='dorar_en',
title tersimpan oleh parse_dorar). Semua path relatif ke folder script.

Usage:
    python grouping_dorar.py [--pages PATH]
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent          # pc_local/
DATA = ROOT / 'data'
OUT = DATA / 'grouping_full'

AYAT_COUNT = {1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,11:123,12:111,
13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,21:112,22:78,23:118,24:64,25:77,
26:227,27:93,28:88,29:69,30:60,31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,39:75,
40:85,41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,49:18,50:45,51:60,52:49,53:62,
54:55,55:78,56:96,57:29,58:22,59:24,60:13,61:14,62:11,63:11,64:18,65:12,66:12,67:30,
68:52,69:52,70:44,71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,79:46,80:42,81:29,
82:19,83:36,84:25,85:22,86:17,87:19,88:26,89:30,90:20,91:15,92:21,93:11,94:8,95:8,
96:19,97:5,98:8,99:8,100:11,101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,
110:3,111:5,112:4,113:5,114:6}

# Transliterasi nama surah dorar (hasil audit 1344 halaman cache lokal,
# 2026-08-18) -> nomor surah. Key = lower-case, apostrof dinormalisasi
# (' U+2018, ' U+2019, ` dan ' -> ').
EN2NO = {
    "al-fatihah": 1, "al-baqarah": 2, "al-'imran": 3, "an-nisaa'": 4,
    "al-ma'idah": 5, "al-an'am": 6, "al-a'raf": 7, "al-anfal": 8,
    "at-tawbah": 9, "yunus": 10, "hud": 11, "yusuf": 12, "ar-ra'd": 13,
    "ibraaheem": 14, "al-hijr": 15, "an-nahl": 16, "al-israa": 17,
    "al-kahf": 18, "maryam": 19, "taa haa": 20, "al-anbiyyaa": 21,
    "al-hajj": 22, "al-mu'minun": 23, "an-nur": 24, "al-furqaan": 25,
    "ash-shu'araa": 26, "an-naml": 27, "al-qassas": 28, "al-'ankabut": 29,
    "ar-rum": 30, "luqmaan": 31, "as-sajdah": 32, "al-ahzaab": 33,
    "saba'": 34, "faatir": 35, "yaa seen": 36, "as-saafaat": 37, "saad": 38,
    "az-zumar": 39, "ghaafir": 40, "fussilat": 41, "ash-shooraa": 42,
    "az-zukhruf": 43, "ad-dukhaan": 44, "al-jaathiyah": 45, "al-ahqaaf": 46,
    "muhammad": 47, "al-fat-h": 48, "al-hujuraat": 49, "qaaf": 50,
    "adh-dhaariyyaat": 51, "at-tur": 52, "an-najm": 53, "al-qamar": 54,
    "ar-rahmaan": 55, "al-waaqi'ah": 56, "al-hadeed": 57, "al-mujaadalah": 58,
    "al-hashr": 59, "al-mumtahanah": 60, "as-saff": 61, "al-jumu'ah": 62,
    "al-munaafiqoon": 63, "at-taghaabun": 64, "at-talaaq": 65,
    "at-tahreem": 66, "al-mulk": 67, "al-qalam": 68, "al-haaqqah": 69,
    "al-ma'aarij": 70, "nooh": 71, "al-jinn": 72, "al-muzzammil": 73,
    "al-muddath-thir": 74, "al-qiyyaamah": 75, "al-insaan": 76,
    "al-mursalaat": 77, "an-naba'": 78, "an-naazi'aat": 79, "abasa": 80,
    "at-takweer": 81, "at-infitaar": 82, "al-mutaffifeen": 83,
    "al-inshiqaaq": 84, "al-burooj": 85, "at-taariq": 86, "al-a'laa": 87,
    "al-ghaashiyah": 88, "al-fajr": 89, "al-balad": 90, "ash-shams": 91,
    "al-layl": 92, "adh-dhuhaa": 93, "ash-sharh": 94, "at-teen": 95,
    "al-'alaq": 96, "al-qadr": 97, "al-bayyinah": 98, "az-zalzalah": 99,
    "al-'aadiyaat": 100, "al-qaari'ah": 101, "at-takaathur": 102,
    "al-'asr": 103, "al-humazah": 104, "al-feel": 105, "quraysh": 106,
    "al-maa'oon": 107, "al-kawthar": 108, "al-kaafiroon": 109,
    "an-nasr": 110, "al-masad": 111, "al-ikhlaas": 112, "al-falaq": 113,
    "an-naas": 114,
}

TITLE_PREFIX = 'The overall tafseer of Quran - '
RE_RANGE = re.compile(r'\s+(\d+)-(\d+)$')
RE_SINGLE = re.compile(r'\s+(\d+)$')
RE_INTRO = re.compile(r'\s+Introduction of Sura$')


def canon_name(name):
    """Normalize apostrophes + collapse whitespace + lower-case."""
    name = name.replace('\u2018', "'").replace('\u2019', "'")
    name = name.replace('`', "'").replace('\u0027', "'")
    return re.sub(r'\s+', ' ', name).strip().lower()


def parse_title(title):
    """Return (surah_no, label) or (None, reason)."""
    t = title.strip()
    if not t.startswith(TITLE_PREFIX):
        return None, f'unknown title pattern: {title!r}'
    rest = t[len(TITLE_PREFIX):]
    m = RE_INTRO.search(rest)
    if m:
        name = rest[:m.start()]
        no = EN2NO.get(canon_name(name))
        if not no:
            return None, f'unknown surah name: {name!r}'
        return no, 'intro'
    m = RE_RANGE.search(rest)
    if m:
        name = rest[:m.start()]
        no = EN2NO.get(canon_name(name))
        if not no:
            return None, f'unknown surah name: {name!r}'
        a, b = int(m.group(1)), int(m.group(2))
        return no, (str(a) if a == b else f'{a}-{b}')
    m = RE_SINGLE.search(rest)
    if m:
        name = rest[:m.start()]
        no = EN2NO.get(canon_name(name))
        if not no:
            return None, f'unknown surah name: {name!r}'
        return no, str(int(m.group(1)))
    return None, f'no ayah label in title: {title!r}'


def parse_label(label):
    if label == 'intro':
        return None
    if '-' in label:
        a, b = label.split('-')
        return (int(a), int(b))
    return (int(label), int(label))


def analyze(pages_by_surah):
    """RONDE-3: validasi = peringatan (data situs diterima apa adanya).
    Return (warnings, missing_on_site[ayat])."""
    warns = []
    n_ayat = AYAT_COUNT[pages_by_surah[0]['sn']]
    covered = set()
    prev_hi = 0
    for pg in pages_by_surah:
        rng = parse_label(pg['label'])
        if rng is None:
            continue
        lo, hi = rng
        if not (1 <= lo <= hi <= n_ayat):
            warns.append(f'range {pg["label"]} di luar 1..{n_ayat} (id {pg["web_page"]})')
            continue
        if lo <= prev_hi:
            warns.append(f'tidak monotonik/overlap: {pg["label"]} setelah <= {prev_hi} (id {pg["web_page"]})')
        prev_hi = max(prev_hi, hi)
        covered.update(range(lo, hi + 1))
    missing = sorted(set(range(1, n_ayat + 1)) - covered)
    return warns, missing


def main():
    pages_file = DATA / 'pages_full.jsonl'
    if len(sys.argv) == 3 and sys.argv[1] == '--pages':
        pages_file = pathlib.Path(sys.argv[2])
    if not pages_file.exists():
        print(f'ERROR: {pages_file} tidak ada - jalankan parse_mp.py dulu.')
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    per_surah = {}
    unknown = []
    with open(pages_file, encoding='utf-8') as r:
        for line in r:
            rec = json.loads(line)
            if rec.get('source') != 'dorar_en':
                continue
            title = rec.get('title', '')
            no, lab = parse_title(title)
            if no is None:
                unknown.append(lab)
                continue
            per_surah.setdefault(no, []).append(
                {'web_page': rec['web_page'], 'label': lab,
                 'paras': rec['paras'], 'sn': no})

    stats = {'ok': 0, 'fail': 0, 'skip': 0, 'issues': [],
             'warnings': {}, 'missing_on_site': {}}
    for sn in range(1, 115):
        pgs = per_surah.get(sn)
        if not pgs:
            stats['skip'] += 1
            stats['issues'].append(f'{sn}: tidak ada halaman dorar')
            continue
        pgs.sort(key=lambda p: p['web_page'])
        warns, missing = analyze(pgs)
        if warns:
            stats['warnings'][str(sn)] = warns
        if missing:
            stats['missing_on_site'][str(sn)] = missing
        segs = [{'from': [pg['web_page'], 0],
                 'to': [pg['web_page'], len(pg['paras']) - 1],
                 'label': pg['label'], 'kind': 'intro' if pg['label'] == 'intro' else 'tafsir'}
                for pg in pgs if pg['paras']]
        with open(OUT / f'dorar_en_{sn:03d}.rb.json', 'w', encoding='utf-8') as f:
            json.dump(segs, f, ensure_ascii=False, indent=1)
        stale = OUT / f'dorar_en_{sn:03d}.FAIL.json'
        if stale.exists():    # RONDE-3: FAIL tidak dipakai lagi
            stale.unlink()
        stats['ok'] += 1

    print(json.dumps({'stats': stats, 'unknown_titles': unknown[:10],
                      'n_unknown': len(unknown)}, ensure_ascii=False, indent=1))
    rep_path = OUT / '_report.json'
    rep = json.load(open(rep_path, encoding='utf-8')) if rep_path.exists() else {}
    rep['dorar_en'] = stats
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
