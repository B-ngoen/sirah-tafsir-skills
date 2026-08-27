# toc_regen_ik.py — Regenerate surah boundaries for broken TOC books.
#
# Context (TOC-REGEN-SPEC.md): toc_full.json entries for ibnkathir_awlad
# (shamela 1509) and ibnkathir_jawzi (shamela 1503) are broken (backwards
# ranges / overlaps). Root cause visible in the HTML: muqaddimah entries that
# merely MENTION a surah name (e.g. "من لم ير بأسا أن يقول: سورة البقرة..."
# at page 161/190) were previously accepted as boundaries.
#
# Approach (rule-based, auditable):
#   1. Parse TOC anchors from each shamela_*.html index page.
#   2. Keep only entries that are genuinely surah boundaries:
#      anchored prefix (optional "تفسير") + "سورة"/"سورتي"/"السورة التي
#      يذكر فيها ...", then alias-table match with word-level prefix compare.
#   3. Select boundaries greedily: seed with first surah-1 entry, then accept
#      only strictly increasing surah number AND strictly increasing page
#      (drops duplicates such as the double البقرة entry at 1509 p.317 and
#      any stray mention).
#   4. Validate before writing anything. Fail -> report, no write.
#
# Output: toc_full.json (only the two keys replaced; others byte-identical),
# toc_full.json.bak backup, toc_regen_report.json diagnostics.

import json
import re
import shutil
import sys
from collections import OrderedDict

# ---------------------------------------------------------------------------
# Configuration

BOOKS = OrderedDict([
    ('ibnkathir_awlad', {'id': 1509, 'html': 'shamela_1509.html', 'total_pages': 6733,
                         'require_full_114': True}),
    ('ibnkathir_jawzi', {'id': 1503, 'html': 'shamela_1503.html', 'total_pages': 4698,
                         'require_full_114': False}),  # ~97% edition, gaps allowed+reported
])

TOC_JSON = 'toc_full.json'
TOC_BAK = 'toc_full.json.bak'
REPORT_JSON = 'toc_regen_report.json'

# ---------------------------------------------------------------------------
# Surah name data

# Canonical display names (as used by the healthy books in toc_full.json).
CANONICAL = {
    1: 'الفاتحة', 2: 'البقرة', 3: 'آل عمران', 4: 'النساء', 5: 'المائدة',
    6: 'الأنعام', 7: 'الأعراف', 8: 'الأنفال', 9: 'التوبة', 10: 'يونس',
    11: 'هود', 12: 'يوسف', 13: 'الرعد', 14: 'إبراهيم', 15: 'الحجر',
    16: 'النحل', 17: 'الإسراء', 18: 'الكهف', 19: 'مريم', 20: 'طه',
    21: 'الأنبياء', 22: 'الحج', 23: 'المؤمنون', 24: 'النور', 25: 'الفرقان',
    26: 'الشعراء', 27: 'النمل', 28: 'القصص', 29: 'العنكبوت', 30: 'الروم',
    31: 'لقمان', 32: 'السجدة', 33: 'الأحزاب', 34: 'سبأ', 35: 'فاطر',
    36: 'يس', 37: 'الصافات', 38: 'ص', 39: 'الزمر', 40: 'غافر',
    41: 'فصلت', 42: 'الشورى', 43: 'الزخرف', 44: 'الدخان', 45: 'الجاثية',
    46: 'الأحقاف', 47: 'محمد', 48: 'الفتح', 49: 'الحجرات', 50: 'ق',
    51: 'الذاريات', 52: 'الطور', 53: 'النجم', 54: 'القمر', 55: 'الرحمن',
    56: 'الواقعة', 57: 'الحديد', 58: 'المجادلة', 59: 'الحشر', 60: 'الممتحنة',
    61: 'الصف', 62: 'الجمعة', 63: 'المنافقون', 64: 'التغابن', 65: 'الطلاق',
    66: 'التحريم', 67: 'الملك', 68: 'القلم', 69: 'الحاقة', 70: 'المعارج',
    71: 'نوح', 72: 'الجن', 73: 'المزمل', 74: 'المدثر', 75: 'القيامة',
    76: 'الإنسان', 77: 'المرسلات', 78: 'النبأ', 79: 'النازعات', 80: 'عبس',
    81: 'التكوير', 82: 'الانفطار', 83: 'المطففين', 84: 'الانشقاق', 85: 'البروج',
    86: 'الطارق', 87: 'الأعلى', 88: 'الغاشية', 89: 'الفجر', 90: 'البلد',
    91: 'الشمس', 92: 'الليل', 93: 'الضحى', 94: 'الشرح', 95: 'التين',
    96: 'العلق', 97: 'القدر', 98: 'البينة', 99: 'الزلزلة', 100: 'العاديات',
    101: 'القارعة', 102: 'التكاثر', 103: 'العصر', 104: 'الهمزة', 105: 'الفيل',
    106: 'قريش', 107: 'الماعون', 108: 'الكوثر', 109: 'الكافرون', 110: 'النصر',
    111: 'المسد', 112: 'الإخلاص', 113: 'الفلق', 114: 'الناس',
}

# Variant names seen in classical tafsir TOCs (superset of spec's list,
# extended with the variants actually present in books 1509/1503:
# سبحان(17), اقتربت(54), ن(68), سأل سائل(70), سبح(87), والشمس وضحاها(91),
# ألم نشرح(94), والتين والزيتون(95), اقرأ(96), ليلة القدر(97), لم يكن(98),
# إذا زلزلت(99), ويل لكل همزة لمزة(104), لإيلاف قريش(106), قل يا أيها
# الكافرون(109), إذا جاء نصر الله(110), تبت(111), المعوذتين(113), ...)
ALIASES = {
    1: ['الفاتحة', 'فاتحة الكتاب'],
    2: ['البقرة'],
    3: ['آل عمران'],
    4: ['النساء'],
    5: ['المائدة'],
    6: ['الأنعام'],
    7: ['الأعراف'],
    8: ['الأنفال'],
    9: ['التوبة', 'براءة', 'سورة براءة'],
    10: ['يونس'],
    11: ['هود'],
    12: ['يوسف'],
    13: ['الرعد'],
    14: ['إبراهيم'],
    15: ['الحجر'],
    16: ['النحل'],
    17: ['الإسراء', 'بني إسرائيل', 'سبحان'],
    18: ['الكهف'],
    19: ['مريم'],
    20: ['طه'],
    21: ['الأنبياء'],
    22: ['الحج'],
    23: ['المؤمنون'],
    24: ['النور'],
    25: ['الفرقان'],
    26: ['الشعراء'],
    27: ['النمل'],
    28: ['القصص'],
    29: ['العنكبوت'],
    30: ['الروم'],
    31: ['لقمان'],
    32: ['السجدة'],
    33: ['الأحزاب'],
    34: ['سبأ'],
    35: ['فاطر'],
    36: ['يس'],
    37: ['الصافات'],
    38: ['ص', 'صاد'],
    39: ['الزمر'],
    40: ['غافر', 'المؤمن'],
    41: ['فصلت', 'حم السجدة'],
    42: ['الشورى'],
    43: ['الزخرف'],
    44: ['الدخان'],
    45: ['الجاثية'],
    46: ['الأحقاف'],
    47: ['محمد', 'القتال'],
    48: ['الفتح'],
    49: ['الحجرات'],
    50: ['ق'],
    51: ['الذاريات'],
    52: ['الطور'],
    53: ['النجم'],
    54: ['القمر', 'اقتربت', 'اقتربت الساعة'],
    55: ['الرحمن'],
    56: ['الواقعة'],
    57: ['الحديد'],
    58: ['المجادلة'],
    59: ['الحشر'],
    60: ['الممتحنة'],
    61: ['الصف'],
    62: ['الجمعة'],
    63: ['المنافقون'],
    64: ['التغابن'],
    65: ['الطلاق'],
    66: ['التحريم'],
    67: ['الملك'],
    68: ['القلم', 'ن'],
    69: ['الحاقة'],
    70: ['المعارج', 'سأل سائل'],
    71: ['نوح'],
    72: ['الجن'],
    73: ['المزمل'],
    74: ['المدثر'],
    75: ['القيامة'],
    76: ['الإنسان', 'الدهر'],
    77: ['المرسلات'],
    78: ['النبأ'],
    79: ['النازعات'],
    80: ['عبس'],
    81: ['التكوير'],
    82: ['الانفطار'],
    83: ['المطففين'],
    84: ['الانشقاق', 'إذا السماء انشقت'],
    85: ['البروج'],
    86: ['الطارق'],
    87: ['الأعلى', 'سبح', 'سبح اسم ربك الأعلى'],
    88: ['الغاشية'],
    89: ['الفجر'],
    90: ['البلد'],
    91: ['الشمس', 'والشمس وضحاها'],
    92: ['الليل', 'والليل إذا يغشى'],
    93: ['الضحى', 'والضحى'],
    94: ['الشرح', 'الانشراح', 'ألم نشرح'],
    95: ['التين', 'والتين والزيتون'],
    96: ['العلق', 'اقرأ', 'اقرأ باسم ربك'],
    97: ['القدر', 'ليلة القدر', 'إنا أنزلناه'],
    98: ['البينة', 'لم يكن', 'لم يكن الذين كفروا'],
    99: ['الزلزلة', 'إذا زلزلت', 'إذا زلزلت الأرض'],
    100: ['العاديات', 'والعاديات'],
    101: ['القارعة'],
    102: ['التكاثر'],
    103: ['العصر', 'والعصر'],
    104: ['الهمزة', 'ويل لكل همزة لمزة'],
    105: ['الفيل', 'ألم تر كيف', 'ألم تر كيف فعل ربك'],
    106: ['قريش', 'لإيلاف قريش', 'لأيلاف قريش'],
    107: ['الماعون', 'أرأيت', 'أرأيت الذي يكذب بالدين'],
    108: ['الكوثر'],
    109: ['الكافرون', 'قل يا أيها الكافرون', 'قل ياأيها الكافرون'],
    110: ['النصر', 'إذا جاء نصر الله', 'إذا جاء نصر الله والفتح', 'نصر الله'],
    111: ['المسد', 'تبت', 'تبت يدا أبي لهب', 'اللهب'],
    112: ['الإخلاص', 'قل هو الله أحد'],
    113: ['الفلق', 'قل أعوذ برب الفلق', 'المعوذتين'],
    114: ['الناس', 'قل أعوذ برب الناس'],
}

# ---------------------------------------------------------------------------
# Arabic normalization

# Harakat + dagger alif + tatweel
DIACRITICS = re.compile(r'[\u064B-\u065F\u0670\u0640]')
# Presentation forms (ornate brackets, ligature glyphs like ﵇, basmala ﷽)
PRESENTATION = re.compile(r'[\uFB50-\uFDFF\uFE70-\uFEFF]')
# Punctuation / digits / symbols removed after word-splitting context
PUNCT = re.compile(r'[^\w\s\u0621-\u064A]', re.UNICODE)

HAMZA_MAP = str.maketrans({
    'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ء': 'ا',
    'ؤ': 'و', 'ئ': 'ي', 'ى': 'ي', 'ة': 'ه',
})


def normalize_words(text):
    """Normalize Arabic text and return a list of words."""
    t = DIACRITICS.sub('', text)
    t = t.translate(HAMZA_MAP)
    t = PRESENTATION.sub(' ', t)   # strip ligatures/ornate brackets entirely
    t = PUNCT.sub(' ', t)          # brackets, quotes, commas etc.
    return [w for w in t.split() if w]


def build_alias_index():
    """Map surah number -> list of normalized word tuples."""
    idx = {}
    for no, variants in ALIASES.items():
        idx[no] = [tuple(normalize_words(v)) for v in variants]
    return idx


# ---------------------------------------------------------------------------
# Title -> surah number resolution

# Bracket groups: [..] and (..) are dropped UNLESS they contain 'سورة'
# (whole-entry brackets like "[تفسير سورة سبحان وهي مكية]" keep content).
SQUARE = re.compile(r'\[[^\[\]]*\]')
ROUND = re.compile(r'\([^()]*\)')


def clean_title(raw):
    """Remove descriptor bracket groups; keep content of heading-style brackets."""
    # Keep content when the group looks like a heading wrapper: it mentions a
    # surah (سور...) or is the bracketed "تفسير" marker itself (covers
    # "[تفسير حم السجدة وهي مكية]" which has no سورة word at all).
    def keep(g):
        return 'سور' in g or 'تفسير' in g
    t = raw
    for rx in (SQUARE, ROUND):
        out = []
        pos = 0
        for m in rx.finditer(t):
            out.append(t[pos:m.start()])
            out.append(m.group(0)[1:-1] if keep(m.group(0)) else ' ')
            pos = m.end()
        out.append(t[pos:])
        t = ''.join(out)
    return t


def resolve_surah(title):
    """Return (surah_no, variant_used) if title is a surah boundary heading, else None.

    Accepted shapes (word level, after normalization):
      [تفسير] سورة <name...>          (canonical)
      [تفسير] سورتي المعوذتين         (dual: Falaq+Nas -> treated as 113)
      [تفسير] السورة التي يذكر فيها <name>   (classical: الماعون)
    Word-level prefix compare against the alias index; longest match wins.
    """
    words = normalize_words(clean_title(title))
    i = 0
    if words and words[0] == 'تفسير':
        i = 1
    rest = words[i:]

    if not rest:
        return None

    # "تفسير حم السجدة" (1509 p.5492): no سورة word at all -> فصلت
    if len(rest) >= 2 and rest[0] == 'حم' and rest[1] == 'السجده':
        return 41, 'حم السجدة'

    # Classical periphrasis: "السورة التي يذكر فيها الماعون" -> 107
    # (note: normalized spellings — ة mapped to ه, so سورة -> سوره)
    if len(rest) >= 5 and rest[0] == 'السوره' and rest[1] == 'التي' \
            and rest[2] == 'يذكر' and rest[3] == 'فيها':
        tail = rest[4:]
    elif rest[0] in ('سوره', 'سورتي'):
        tail = rest[1:]
    else:
        return None  # not anchored on a surah heading (junk / subsection)

    if not tail:
        return None

    # Word-level prefix match against aliases, longest wins.
    best_no, best_len, best_alias = None, 0, None
    ties = set()
    for no, alias_tuples in ALIAS_INDEX.items():
        for al in alias_tuples:
            n = len(al)
            if n >= best_len and len(tail) >= n and tuple(tail[:n]) == al:
                if n > best_len:
                    best_no, best_len, best_alias = no, n, ' '.join(al)
                    ties = {no}
                else:  # n == best_len
                    ties.add(no)
    if best_no is None:
        return None
    if len(ties) > 1:
        raise SystemExit(f'FATAL: ambiguous alias match for {title!r}: surahs {sorted(ties)}')
    return best_no, best_alias


# ---------------------------------------------------------------------------
# TOC parsing

def parse_toc(html_path, book_id):
    """Return ordered list of (page:int, title:str) from the shamela index page."""
    html = open(html_path, encoding='utf-8').read()
    pat = re.compile(
        r'href="https://shamela\.ws/book/%d/(\d+)[^"]*"[^>]*>([^<]{1,150})' % book_id)
    return [(int(p), t.strip()) for p, t in pat.findall(html)]


def select_boundaries(toc):
    """Greedy monotonic selection seeded at the first surah-1 entry.

    Accept a candidate only if surah_no > last accepted AND page > last page.
    Everything before the first الفاتحة entry is ignored (kills the
    muqaddimah mention of البقرة at 1503 p.161 / 1509 p.190).
    """
    accepted = []   # (surah_no, page, title)
    variants = {}   # surah_no -> TOC variant actually used
    dropped = []    # (page, surah_no_or_None, title) audit trail
    seeded = False
    for page, title in toc:
        r = resolve_surah(title)
        if r is None:
            continue
        no, alias = r
        if not seeded:
            if no == 1:
                seeded = True
                accepted.append((no, page, title))
                variants[no] = alias
            else:
                dropped.append((page, no, title))
            continue
        last_no, last_page, _ = accepted[-1]
        if no > last_no and page > last_page:
            accepted.append((no, page, title))
            variants[no] = alias
        else:
            dropped.append((page, no, title))
    if not seeded:
        raise SystemExit('FATAL: no الفاتحة boundary found — aborting')
    return accepted, variants, dropped


# ---------------------------------------------------------------------------
# Build / validate surah ranges

def build_ranges(accepted, total_pages):
    """accepted: [(no, page, title)] -> OrderedDict no -> {surah, start, end_excl}."""
    out = OrderedDict()
    for idx, (no, page, _t) in enumerate(accepted):
        end = accepted[idx + 1][1] if idx + 1 < len(accepted) else total_pages + 1
        out[no] = {'surah': CANONICAL[no], 'start': page, 'end_excl': end}
    return out


def validate(ranges, total_pages, require_full):
    """Return list of error strings; empty list = valid."""
    errs = []
    nos = list(ranges.keys())
    if nos != sorted(nos):
        errs.append('surah numbers not sorted')
    if len(set(nos)) != len(nos):
        errs.append('duplicate surah numbers')
    if require_full and nos != list(range(1, 115)):
        errs.append(f'expected exactly surahs 1..114, got {len(nos)} '
                    f'(absent: {[n for n in range(1, 115) if n not in ranges]})')
    pages = [r['start'] for r in ranges.values()]
    if any(b <= a for a, b in zip(pages, pages[1:])):
        errs.append('pages not strictly increasing')
    for no, r in ranges.items():
        if not (1 <= r['start'] < r['end_excl'] <= total_pages + 1):
            errs.append(f'bad range surah {no}: {r["start"]}..{r["end_excl"]}')
    last = ranges[nos[-1]]
    if last['end_excl'] != total_pages + 1:
        errs.append(f'last end_excl {last["end_excl"]} != total+1 {total_pages + 1}')
    return errs


# ---------------------------------------------------------------------------
# Main

def main():
    report = OrderedDict()
    all_ok = True

    for key, cfg in BOOKS.items():
        toc = parse_toc(cfg['html'], cfg['id'])
        accepted, variants, dropped = select_boundaries(toc)
        ranges = build_ranges(accepted, cfg['total_pages'])
        errs = validate(ranges, cfg['total_pages'], cfg['require_full_114'])

        absent = [n for n in range(1, 115) if n not in ranges]
        samples = {str(no): [r['start'], r['end_excl']]
                   for no, r in list(ranges.items())[:5]}
        # non-canonical variant resolutions (audit trail)
        variant_hits = {str(no): v for no, v in sorted(variants.items())
                        if normalize_words(v) != normalize_words(CANONICAL[no])}

        report[key] = {
            'book_id': cfg['id'],
            'n_toc_entries': len(toc),
            'n_surahs': len(ranges),
            'absent_surahs': absent,
            'first_5_samples': samples,
            'variant_resolutions': variant_hits,
            'dropped_surah_candidates': [{'page': p, 'surah': n, 'title': t}
                                         for p, n, t in dropped],
            'validation_errors': errs,
        }
        print(f"[{key}] book {cfg['id']}: {len(toc)} TOC entries -> "
              f"{len(ranges)} surah boundaries; absent={absent or '[]'}")
        for no, r in list(ranges.items())[:3]:
            print(f"    surah {no} ({r['surah']}): {r['start']}..{r['end_excl']}")
        if errs:
            all_ok = False
            print(f"    VALIDATION FAILED: {errs}")

    if not all_ok:
        with open(REPORT_JSON, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print(f'\nVALIDATION FAILED — {REPORT_JSON} written, toc_full.json NOT touched.')
        sys.exit(1)

    # --- all valid: backup, patch, write report -----------------------------
    data = json.load(open(TOC_JSON, encoding='utf-8'), object_pairs_hook=OrderedDict)
    for key, cfg in BOOKS.items():
        toc = parse_toc(cfg['html'], cfg['id'])
        accepted, _variants, _dropped = select_boundaries(toc)
        ranges = build_ranges(accepted, cfg['total_pages'])
        data[key]['surahs'] = {str(no): r for no, r in ranges.items()}
        # keep book_id / n_toc_entries / toc_raw / max_page untouched

    shutil.copy2(TOC_JSON, TOC_BAK)
    with open(TOC_JSON, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1))  # no trailing newline
    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=1))

    print(f'\nOK: {TOC_JSON} updated ({TOC_BAK} backup, {REPORT_JSON} report).')


if __name__ == '__main__':
    ALIAS_INDEX = build_alias_index()
    main()
