#!/usr/bin/env python3
"""Build tafsir_full.db (114 surah, 6 sumber) dari data pc_local.

Generalisasi build_db.py (folder induk, pilot Al-Fatihah):
  - loop 114 surah, sumber = 5 buku Arab + dorar_en
  - input: data/pages_full.jsonl + data/grouping_full/*_{sn:03d}.rb.json
  - ekspansi label rentang ("2-5") per ayat -> ayah_map
  - out_of_scope dibuang total; intro/istiadhah/closing -> section saja
  - smoke test lookup acak (seed tetap) di akhir

Skema:
  pages(source, book_id, web_page, printed_juz, printed_page, url, para_idx, text)
  segments(seg_id, source, surah, label, section, from_page, from_para, to_page, to_para)
  ayah_map(source, surah, ayah, seg_id)
Aturan: teks verbatim, tanpa modifikasi apa pun.
Semua path relatif ke folder script ini (pc_local/); encoding utf-8 eksplisit.

Usage:
    python build_db_full.py
"""
import json, pathlib, random, re, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent          # pc_local/
DATA = ROOT / 'data'
PAGES_FILE = DATA / 'pages_full.jsonl'
GROUP_DIR = DATA / 'grouping_full'
DB = DATA / 'tafsir_full.db'

SPECIAL = ('intro', 'istiadhah', 'closing')


def expand_label(label):
    """'3' -> [3]; '2-5' -> [2,3,4,5]; non-angka -> []"""
    m = re.fullmatch(r'(\d+)-(\d+)', label)
    if m:
        return list(range(int(m.group(1)), int(m.group(2)) + 1))
    if label.isdigit():
        return [int(label)]
    return []


def load_pages(con):
    """Stream-insert pages; build per-source order index for lookups.
    order[src] = sorted list of (web_page, para_idx); pos maps to index."""
    order = {}
    page_paras = {}          # (source, web_page) -> [text, ...]
    n = 0
    with open(PAGES_FILE, encoding='utf-8') as r:
        for line in r:
            rec = json.loads(line)
            src = rec['source']
            paras = rec['paras']
            page_paras[(src, rec['web_page'])] = paras
            con.executemany(
                'INSERT OR REPLACE INTO pages VALUES(?,?,?,?,?,?,?,?)',
                [(src, rec.get('book_id'), rec['web_page'],
                  rec.get('printed_juz'), rec.get('printed_page'),
                  rec.get('url'), i, t) for i, t in enumerate(paras)])
            order.setdefault(src, []).extend(
                (rec['web_page'], i) for i in range(len(paras)))
            n += 1
    for src in order:
        order[src].sort()
    con.commit()
    return order, page_paras, n


def load_segments(con):
    """Insert segments + ayah_map from grouping_full/*.rb.json."""
    n_seg = n_map = 0
    skipped = {'out_of_scope': 0, 'empty': 0}
    files = sorted(GROUP_DIR.glob('*.rb.json'))
    cur = con.cursor()
    for f in files:
        m = re.fullmatch(r'(.+)_(\d{3})\.rb\.json', f.name)
        if not m:
            continue
        src, sn = m.group(1), int(m.group(2))
        for s in json.load(open(f, encoding='utf-8')):
            lab = s['label']
            kind = s.get('kind', 'tafsir')
            if lab == 'out_of_scope' or kind == 'out_of_scope':
                skipped['out_of_scope'] += 1
                continue
            section = lab if lab in SPECIAL or kind in SPECIAL else 'tafsir'
            if kind in SPECIAL and lab not in SPECIAL:
                section = kind
            cur.execute(
                'INSERT INTO segments(source,surah,label,section,'
                'from_page,from_para,to_page,to_para) VALUES(?,?,?,?,?,?,?,?)',
                (src, sn, lab, section,
                 s['from'][0], s['from'][1], s['to'][0], s['to'][1]))
            seg_id = cur.lastrowid
            n_seg += 1
            for ay in expand_label(lab):
                cur.execute('INSERT INTO ayah_map VALUES(?,?,?,?)',
                            (src, sn, ay, seg_id))
                n_map += 1
    con.commit()
    return n_seg, n_map, skipped, len(files)


def make_lookup(con, order, page_paras):
    pos = {src: {k: i for i, k in enumerate(ks)} for src, ks in order.items()}

    def lookup(surah, ayah):
        out = {}
        rows = con.execute(
            'SELECT source, seg_id FROM ayah_map WHERE surah=? AND ayah=? '
            'ORDER BY source', (surah, ayah)).fetchall()
        for src, seg_id in rows:
            fp, fpa, tp, tpa, lab = con.execute(
                'SELECT from_page,from_para,to_page,to_para,label '
                'FROM segments WHERE seg_id=?', (seg_id,)).fetchone()
            if (src, fp) not in page_paras or (src, tp) not in page_paras:
                continue   # page not in DB (skipped source)
            a, b = pos[src][(fp, fpa)], pos[src][(tp, tpa)]
            texts = []
            for (w, i) in order[src][a:b + 1]:
                texts.append(page_paras[(src, w)][i])
            if not texts:
                continue
            out.setdefault(src, []).append(
                {'label': lab, 'n_paras': len(texts),
                 'chars': sum(len(t) for t in texts),
                 'first': texts[0][:60]})
        return out
    return lookup


def main():
    if not PAGES_FILE.exists():
        print(f'ERROR: {PAGES_FILE} tidak ada - jalankan parse_mp.py dulu.')
        sys.exit(1)
    if not GROUP_DIR.exists() or not list(GROUP_DIR.glob('*.rb.json')):
        print(f'ERROR: {GROUP_DIR} kosong - jalankan grouping_mp.py / grouping_dorar.py dulu.')
        sys.exit(1)
    if DB.exists():
        DB.unlink()

    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript("""
    CREATE TABLE pages(
      source TEXT, book_id TEXT, web_page INT, printed_juz INT, printed_page INT,
      url TEXT, para_idx INT, text TEXT,
      PRIMARY KEY(source, web_page, para_idx));
    CREATE TABLE segments(
      seg_id INTEGER PRIMARY KEY, source TEXT, surah INT, label TEXT, section TEXT,
      from_page INT, from_para INT, to_page INT, to_para INT);
    CREATE TABLE ayah_map(source TEXT, surah INT, ayah INT, seg_id INT);
    CREATE INDEX idx_ayah ON ayah_map(surah, ayah);
    CREATE INDEX idx_seg ON segments(source, surah);
    """)

    order, page_paras, n_pages = load_pages(con)
    n_seg, n_map, skipped, n_files = load_segments(con)
    print(f'DB     : {DB}')
    print(f'pages  : {n_pages} page-records | {sum(len(v) for v in order.values())} paras')
    print(f'segment: {n_seg} dari {n_files} file grouping | ayah_map: {n_map}')
    print(f'buang  : {skipped}')

    lookup = make_lookup(con, order, page_paras)

    # ---- smoke test: surah 1 penuh + 10 (surah, ayat) acak seed tetap ----
    print('\n-- smoke test --')
    print('Al-Fatihah (surah 1, 7 ayat):')
    for ay in range(1, 8):
        r = lookup(1, ay)
        srcs = ', '.join(f'{s}({sum(x["n_paras"] for x in v)}p)'
                         for s, v in sorted(r.items()))
        print(f'  1:{ay} -> {len(r)} sumber | {srcs}')

    print('\nLookup acak (seed=42):')
    random.seed(42)
    pairs = [(random.randint(2, 114), 1) for _ in range(5)] + \
            [(random.randint(2, 114), random.randint(2, 20)) for _ in range(5)]
    for surah, ayah in pairs:
        r = lookup(surah, ayah)
        srcs = ', '.join(f'{s}({sum(x["n_paras"] for x in v)}p)'
                         for s, v in sorted(r.items()))
        print(f'  {surah}:{ayah} -> {len(r)} sumber | {srcs[:100]}')

    # integrity counters
    print('\ncoverage check:')
    for tbl in ('pages', 'segments', 'ayah_map'):
        print(f'  {tbl}: {c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]}')
    bad = c.execute(
        'SELECT COUNT(*) FROM ayah_map m LEFT JOIN segments s '
        'ON m.seg_id=s.seg_id WHERE s.seg_id IS NULL').fetchone()[0]
    print(f'  ayah_map yatim: {bad}')
    con.close()
    print('\nSELESAI.')


if __name__ == '__main__':
    main()
