#!/usr/bin/env python3
"""BATCH grouping 114 surah x 5 buku Arab — versi multiprocessing PC (KANONIK).

Satu-satunya file grouping yang dipakai di laptop ini.
grouping_batch.py = DEPRECATED (referensi saja, jangan dijalankan).

Metode anchor per buku:
  maraghi : header "[سورة N (S) : الآيات A الى B]" -> label rentang; header
            dengan nomor surah LAIN -> guard (out_of_scope).
  tabari  : prefix "القول في تأويل" + quote -> ayat via verse-index, monotonik.
  shabuni : siklus seksi بين يدي/فضلها/التسمية/المناسبة/اللغة/التفسير/
            البلاغة/الفوائد/خاتمة; quote {X} -> rentang ayat via verse-index.
            Label WAJIB rentang ("A-B") bila membahas >1 ayat (QC-RB.md).
  awlad   : blok quote utuh berdiri sendiri "﴿X (N)﴾" -> nomor ayat, monotonik.
  jawzi   : sama seperti awlad (basmalah = ayat 1 HANYA Fatihah, riwayat Hafs).
            SPECIAL: surah 113/114 flat hanya h.4698 -> seluruh segmen 'intro'
            (pembuka gabungan Muawwidzatain: hadits fadhilah Al-Falaq dan
            An-Nas bersama; buku terpotong di situ — bukan tafsir per-ayat).

GUARD (wajib, QC-RB.md): heading "تفسير سورة X" / "سورة X" berdiri sendiri /
basmalah setelah ayat terakhir -> segmen terakhir dipotong di situ,
sisa = segmen 'out_of_scope' (spill surah berikutnya).

RONDE-2 (QC perbaikan grouping):
  A. tabari & awlad: blok kutipan multi-ayat ber-nomor cetak (N) di
     dalam kutipan -> label = rentang min-max nomor LANGSUNG; awlad juga
     menerima blok tanpa ﴾ penutup dan blok ayat mentah tanpa bracket
     (diverifikasi prefix teks-ayat via verse_index). Frasa tabari tanpa
     nomor di-strip markernya sebelum match verse-index.
  B. shabuni: seksi anotasi (التسمية/المناسبة/اللغة/البلاغة/الفوائد) =
     kind 'section', label = rentang pasase yang diulas (label tafsir
     terdekat sebelumnya); dikecualikan dari cek monotonik & intro-after-
     tafsir. Intro hanya di awal surah.
  C. verse_index: filter anti-artefak 'startswith(سورة)' dihapus —
     menjatuhkan ayat asli 24:1 (satu-satunya hit di korpus).

RONDE-3 (label rentang implisit, ROUND3-SPEC.md):
  1. Buku ber-anchor monotonik (tabari/awlad/jawzi/maraghi): segmen tafsir
     label 'N' yang anchor tafsir BERIKUTNYA mulai M > N+1 memuat tafsir
     N..M-1 -> label diperluas 'N-(M-1)'; label rentang 'A-B' dengan
     B < M-1 -> 'A-(M-1)'; anchor terakhir surah -> sampai AYAT_COUNT.
     (Teks tidak hilang: segmen antar-anchor memuat tafsir rentang
     penuh — spec ronde-3.)
  2. Validator: cek cakupan AYAT penuh (union label tafsir = 1..N);
     celah SETELAH anchor pertama = FAIL (harus tak mungkin pasca-
     ekspansi); celah SEBELUM anchor pertama = warning 'leading-gap'
     (tafsirnya berada di zona intro/spill — tidak dipetakan, jujur).
     Diketahui: awlad 2:1 (tafsir الم bercampur intro fadl), jawzi 1:1
     (tafsir basmalah tertanam intro). Shabuni dikecualikan (sudah
     rentang via jendela pasase).
  3. TOC tabari 46 dipatch start 12729->12725 (heading + tafsir 46:1-4
     tadinya jatuh ke trailing out_of_scope surah 45; bukti fisik
     [12725,0..6], penutup 45 di [12724,last]).

RONDE-4 (alignment dua deret tabari + validator kepadatan/probe,
          ROUND4-SPEC.md):
  1. tabari: matching serakah per-anchor diganti ALIGNMENT DUA DERET
     (DP monotonik global). Deret heading H = semua 'القول في تأويل'
     (posisi + frasa quote ternormalisasi); deret ayat A[1..N] dari
     verse_index. Skor match = prefix kuat SAJA: frasa = awal ayat
     (dua arah, guard panjang) = +60; >= 3 kata pertama sama = +40;
     nomor cetak (N) di dalam quote = +100. Tier substring bebas
     DILARANG (match palsu 'ولكم في الارض' -> 179, 'الذين يظنون' ->
     249, 'واتقوا يوما' -> 281, klan 'يا ايها الذين امنوا' -> 282
     adalah akar runtuhnya surah 2 pada ronde sebelumnya).
     Heading tanpa match (frasa potongan tengah ayat) TIDAK diberi
     nomor sendiri: di-interpolasi — heading tak-match antara anchor
     match L dan anchor match R berikutnya digabung jadi SATU segmen
     rentang 'L+1-(R-1)' bila R > L+1, atau melebur ke segmen L bila
     R == L+1 (kasus umum: satu ayat dipecah banyak heading frasa).
     Heading tak-match sebelum match pertama -> teks jatuh ke zona
     intro (tidak dipetakan, jujur).
  2. RONDE-4 revisi: DASAR deret ayat = quran-no-tashkeel.json kanonik
     (github.com/amrayn/quran-text, 6.236 ayat Hafs, basmalah = 1:1)
     untuk SEMUA matching/alignment/probe/kepadatan, ternormalisasi norm()
     yang sama (norm() diperluas: strip tanda waqaf Quranik U+06D6-U+06ED).
     verse_index.json Maraghi diturunkan jadi cross-check sekunder —
     bila beda, percayai kanonik (laporan diff di main()).
  3. Sentinel alignment: match pertama wajib ayat <= 3; match
     terakhir wajib >= N - max(3, N//50). Gagal -> FAIL surah
     (deteksi alignment gila).
  3. VALIDATOR baru SEMUA BUKU (basis ayat kanonik): (a) kepadatan — segmen tafsir
     berlabel k ayat yang membentang > (halaman_surah/ayat_surah) * k
     * DENSITY_TOL halaman = FAIL surah; (b) probe konten — tabel
     PROBES (ayat terkenal) wajib menemukan frasanya di teks segmen
     yang melabeli ayat tsb; gagal = FAIL surah.

Validator per surah SEBELUM tulis output:
  (a) cakupan posisi penuh tanpa celah (flat[0]..flat[-1]),
  (b) label angka monotonik: buku linear = strict (lo >= prev_hi);
      shabuni = non-strict (hi tidak turun; اللغة/البلاغة boleh lintas-ayat),
  (c) guard hanya boleh hidup di dalam segmen out_of_scope (by construction).
Gagal validasi -> tulis {book}_{sn:03d}.FAIL.json berisi alasan,
JANGAN tulis .rb.json.

Windows note (eval #5, #6): semua open() pakai encoding='utf-8'; PAGES/TOC/VI
di-load via Pool(initializer=...) sekali per worker, HANYA buku yang diproses.
Semua path relatif ke folder script ini (= pc_local/), lihat eval #3, #4.

Usage:
    python grouping_mp.py [book] [n_workers]
    book: maraghi | tabari | shabuni | awlad | jawzi
    n_workers: default = cpu_count() - 1
"""
import json, pathlib, re, sys, time
from multiprocessing import Pool, cpu_count

ROOT = pathlib.Path(__file__).resolve().parent          # pc_local/
DATA = ROOT / 'data'
TOC_FILE = ROOT / 'toc_full.json'
PAGES_FILE = DATA / 'pages_full.jsonl'
VI_FILE = DATA / 'verse_index.json'      # RONDE-4: cross-check sekunder saja
CANON_FILE = ROOT / 'quran-no-tashkeel.json'   # RONDE-4: dasar deret ayat
OUT = DATA / 'grouping_full'

BOOKS = ['tabari', 'maraghi', 'shabuni', 'ibnkathir_awlad', 'ibnkathir_jawzi']
ALIAS = {'maraghi': 'maraghi', 'tabari': 'tabari', 'shabuni': 'shabuni',
         'awlad': 'ibnkathir_awlad', 'jawzi': 'ibnkathir_jawzi'}

# ---------- normalization helpers ----------
# RONDE-4: \u06D6-\u06ED = tanda waqaf/annotasi Quranik (ۖ ۚ ۛ ۝ ۞ ۩)
# — ada di quran-no-tashkeel.json; WAJIB distrip agar prefix-match
# dengan teks buku (tanpa tanda itu) tidak gagal.
HARAKAT = re.compile(r'[\u064B-\u0652\u0670\u0640\u06D6-\u06ED]')

def norm(t):
    """Strip harakat/tatweel + unify orthography (ta marbuta, alif maqsura,
    hamza-alef) + collapse whitespace."""
    t = HARAKAT.sub('', t)
    t = t.replace('ة', 'ت').replace('ى', 'ي')
    t = re.sub(r'[أإآ]', 'ا', t)
    return re.sub(r'\s+', ' ', t).strip()

AR = '٠١٢٣٤٥٦٧٨٩'

def ar2int(s):
    return int(''.join(str(AR.index(c)) for c in s))

# ---------- ayat count per surah (Hafs) ----------
AYAT_COUNT = {1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,11:123,12:111,
13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,21:112,22:78,23:118,24:64,25:77,
26:227,27:93,28:88,29:69,30:60,31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,39:75,
40:85,41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,49:18,50:45,51:60,52:49,53:62,
54:55,55:78,56:96,57:29,58:22,59:24,60:13,61:14,62:11,63:11,64:18,65:12,66:12,67:30,
68:52,69:52,70:44,71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,79:46,80:42,81:29,
82:19,83:36,84:25,85:22,86:17,87:19,88:26,89:30,90:20,91:15,92:21,93:11,94:8,95:8,
96:19,97:5,98:8,99:8,100:11,101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,
110:3,111:5,112:4,113:5,114:6}

# ---------- regexes ----------
# NOTE: semua pola Arab di bawah ditulis dalam BENTUK PASCA-norm() karena
# dicocokkan ke tn = norm(t): أإآ->ا, ى->ي, ة->ت.
# maraghi headers; group 1 = surah number (for guard), eval #14: \[+ /\]+
RE_MRANGE = re.compile(r'^\[+\s*سورت\s+[^\]]+?\s*\(\s*([٠-٩]+)\s*\)\s*:\s*(?:الايات|ايات)\s+([٠-٩]+)\s+الي\s+([٠-٩]+)\s*\]+')
RE_MSINGLE = re.compile(r'^\[+\s*سورت\s+[^\]]+?\s*\(\s*([٠-٩]+)\s*\)\s*:\s*ايت\s+([٠-٩]+)\s*\]+')
# tabari anchors; eval #1: \s in raw string (was \\s = literal backslash + s)
RE_TOPEN = re.compile(r'^\(?\s*القول في تاويل')
RE_TQUOTE = re.compile(r'[﴿«]([^﴾»]{2,}?)[﴾»]')
# shabuni inline quotes {X} or ﴿X﴾
RE_QT = re.compile(r'[﴿{]([^﴾}]{2,}?)[﴾}]')
# awlad/jawzi standalone numbered quote block: "﴿X (N)﴾." (eval #10)
RE_BLOCK = re.compile(r'^\s*[﴿{](.+?)\s*\(([٠-٩]+)\)\s*[﴾}]\s*[.،]?\s*$')
# Ronde-2 (A): blok multi-ayat — pembuka kutipan boleh tanpa penutup ﴾
RE_BLOCK_OPEN = re.compile(r'^\s*[﴿{]')
RE_NUM_PAREN = re.compile(r'\(([٠-٩]+)\)')
RE_LABEL = re.compile(r'^(\d+)-(\d+)$')
# RONDE-4: attribution rujukan-silang Shamela tepat setelah kutipan pertama
# "[NamaSurah: N]" — paragraf kutipan LINTAS-SURAH, bukan blok ayat surah
# ini. Kasus jawzi 2 p513: "﴿وارسلناه الي مائت الف او يزيدون (١٤٧)﴾
# [الصافات: ١٤٧]" diterima sebagai anchor 2:147 palsu, meracuni last_n
# sehingga 45 anchor asli 75-146 ditolak non-monotonik (density 209 hal).
RE_XREF_AFTER = re.compile(r'^\s*\[[^\]\n]{2,40}:\s*[٠-٩]+\s*\]')

def nums_in_quote(t):
    """Nomor cetak (N) yang berada DI DALAM span kutipan ﴿...﴾ — bukan
    footnote setelah kutipan. Tanpa penutup -> span = sisa paragraf."""
    closes = [i for i in (t.find('﴾'), t.find('}')) if i != -1]
    span = t[:min(closes)] if closes else t
    return [ar2int(x) for x in RE_NUM_PAREN.findall(span)]

def _is_verse_block(t, lo, vi_surah):
    """Blok ayat mentah tanpa bracket (awlad 104/105): paragraf dengan
    marker (N) dibuang harus diawali teks ayat lo (verifikasi via VI,
    dua arah, 24 karakter pertama)."""
    vt = vi_surah.get(lo)
    if not vt:
        return False
    body = norm(RE_NUM_PAREN.sub('', t)).strip(' .،:؛-﴿﴾')
    v = norm(vt)
    return body[:24].startswith(v[:24]) or v[:24].startswith(body[:24])

def parse_label(label):
    """'3' -> (3,3); '2-5' -> (2,5); special labels -> None."""
    if label.isdigit():
        return (int(label), int(label))
    m = RE_LABEL.match(label)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None

# RONDE-3: buku ber-anchor monotonik yang label tafsirnya di-perluas
# menjadi rentang implisit (shabuni sudah rentang via jendela pasase).
EXPAND_BOOKS = {'tabari', 'ibnkathir_awlad', 'ibnkathir_jawzi', 'maraghi'}

# RONDE-4: konstanta validator kepadatan + tabel probe konten
DENSITY_TOL = 8         # x rata-rata halaman/ayat surah (ROUND4-SPEC.md #5)
DENSITY_MARGINAL = 1.5  # violasi <= 1.5x limit = warning, bukan FAIL
                        # (kepadatan riwayat buku; mode-bug nyata >= 3x)
# RONDE-4: kasus density ekstrem TERVERIFIKASI FISIK (kutipan di rentang
# didominasi label sendiri; konten = narasi riwayat/tamsil panjang, bukan
# anchor hilang) -> FAIL diturunkan jadi warning '[verified]'.
VERIFIED_DENSITY = {
    ('ibnkathir_awlad', 14, 27, 27): 'tamsil 14:27 diuraikan ulang 15x',
    ('ibnkathir_jawzi', 14, 27, 27): 'tamsil 14:27 diuraikan ulang 13x',
    ('ibnkathir_awlad', 17, 1, 1): 'hadits-hadits Isra wal-Miraj (62 hal)',
    ('ibnkathir_jawzi', 17, 1, 1): 'hadits-hadits Isra wal-Miraj (39 hal)',
    ('ibnkathir_awlad', 33, 56, 56): 'riwayat shalawat Nabi SAW (31 hal)',
    ('ibnkathir_jawzi', 33, 56, 56): 'riwayat shalawat Nabi SAW (21 hal)',
}
PROBES = [           # (surah, ayat, frasa wajib — sudah ternormalisasi)
    (2, 255, 'الله لا اله الا هو الحي القيوم'),
    (2, 282, 'اذا تداينتم'),
    (12, 4, 'احد عشر كوكبا'),
    (18, 9, 'اصحاب الكهف'),
    (55, 13, 'فباي الاء ربكما'),
    (112, 1, 'قل هو الله احد'),
]

def expand_labels(segs, n_ayat):
    """RONDE-3: perluas label tafsir jadi rentang implisit.
    Segmen label 'N' (atau rentang 'A-B' dengan B < M-1) yang anchor
    tafsir berikutnya mulai di M -> 'N-(M-1)' / 'A-(M-1)'; anchor tafsir
    terakhir -> sampai n_ayat. Overlap (M <= hi+1) tidak disentuh.
    Return (segs, n_changed)."""
    idx = [k for k, s in enumerate(segs) if s['kind'] == 'tafsir']
    changed = 0
    for j, k in enumerate(idx):
        rng = parse_label(segs[k]['label'])
        if not rng:
            continue
        lo, hi = rng
        if j + 1 < len(idx):
            nxt = parse_label(segs[idx[j + 1]]['label'])
            m = nxt[0] if nxt else n_ayat + 1
        else:
            m = n_ayat + 1
        new_hi = min(m - 1, n_ayat)
        if new_hi > hi:
            segs[k]['label'] = str(lo) if lo == new_hi else f'{lo}-{new_hi}'
            changed += 1
    return segs, changed

# ---------- worker globals (loaded once per worker, filtered per book) ----------
_W = {}

def _init_worker(book):
    """Pool initializer: load TOC + PAGES (only `book`) + kanonik Quran.
    RONDE-4 revisi: _W['q'] = quran-no-tashkeel.json (norm() diterapkan)
    = DASAR deret ayat untuk SEMUA matching/alignment/probe/kepadatan.
    verse_index.json TIDAK lagi dipakai di worker (cross-check di main)."""
    _W['toc'] = json.load(open(TOC_FILE, encoding='utf-8'))
    pages = {}
    with open(PAGES_FILE, encoding='utf-8') as r:
        for line in r:
            rec = json.loads(line)
            if rec['source'] == book:
                pages[rec['web_page']] = rec['paras']
    _W['pages'] = pages
    # RONDE-4 revisi: deret ayat kanonik (norm: harakat + tanda waqaf +
    # unify ortografi — sama dengan yang diterapkan ke teks buku).
    canon = json.load(open(CANON_FILE, encoding='utf-8'))
    _W['q'] = {int(s['id']): {int(v['id']): norm(v['text'])
                              for v in s['verses']}
               for s in canon}

def surah_flat(book, sn):
    s = _W['toc'][book]['surahs'][str(sn)]
    flat = []
    pages = _W['pages']
    for w in range(s['start'], s['end_excl']):
        for p, t in enumerate(pages.get(w, [])):
            flat.append([w, p, t])
    return flat

# ---------- phrase -> ayat matching (verse-index) ----------
def match_phrase(phrase, vi_surah, n_ayat):
    """Frasa quote -> nomor ayat. Tier (Ronde-2 B):
      1. prefix eksak (2 arah; arah balik wajib len(VI)>=8 — ayat pendek
         seperti 'الم' (2:1) tidak boleh menelan frasa panjang);
      2. prefix tanpa-spasi 2 arah (variasi 'ياأيها' vs 'يا أيها'),
         guard len yang sama;
      3. prefix 2 kata pertama;
      4. substring 2 arah, hanya bila len(VI)>=12 (anti 'الم' false-hit)."""
    ph = phrase.strip()
    if not ph:
        return None
    ph2 = ph.replace(' ', '')
    for a in range(1, n_ayat + 1):
        t = vi_surah.get(a)
        if not t:
            continue
        if t.startswith(ph) or (len(t) >= 8 and ph.startswith(t)):
            return a
    for a in range(1, n_ayat + 1):
        t = vi_surah.get(a)
        if not t:
            continue
        t2 = t.replace(' ', '')
        if t2.startswith(ph2) or (len(t2) >= 8 and ph2.startswith(t2)):
            return a
    words = ph.split()
    if len(words) >= 2:
        k2 = ' '.join(words[:2])
        for a in range(1, n_ayat + 1):
            t = vi_surah.get(a)
            if t and t.startswith(k2):
                return a
    for a in range(1, n_ayat + 1):
        t = vi_surah.get(a)
        if t and len(t) >= 12 and (ph in t or t in ph):
            return a
    return None

# ---------- maraghi ----------
def maraghi_segments(flat, sn):
    """anchors: headers milik surah sn; guards: header dengan nomor surah lain."""
    anchors, guards = [], []
    for i, (w, p, t) in enumerate(flat):
        tn = norm(t)
        m = RE_MRANGE.match(tn)
        if m:
            snum, a, b = ar2int(m.group(1)), ar2int(m.group(2)), ar2int(m.group(3))
            if snum != sn:
                guards.append(i)
                continue
            lb = str(a) if a == b else f'{a}-{b}'
            anchors.append((i, lb, 'tafsir'))
            continue
        m = RE_MSINGLE.match(tn)
        if m:
            snum, a = ar2int(m.group(1)), ar2int(m.group(2))
            if snum != sn:
                guards.append(i)
                continue
            anchors.append((i, str(a), 'tafsir'))
    return anchors, guards

# ---------- tabari (RONDE-4: alignment dua deret, DP monotonik) ----------
def _collect_tabari_heads(flat, n_ayat):
    """Deret H: semua heading 'القول في تأويل' berurutan dalam surah.
    Tiap heading = {i: posisi flat, ph: frasa ternormalisasi (nomor
    cetak di-strip), nums_lo/nums_hi: rentang nomor cetak di dalam
    quote (nomor ayat eksplisit — sinyal terkuat)."""
    heads = []
    for i, (w, p, t) in enumerate(flat):
        tn = norm(t).lstrip('()[]«»،. ـ')
        if not RE_TOPEN.match(tn):
            continue
        qm = RE_TQUOTE.search(t)
        if not qm:
            continue
        raw_q = qm.group(1)
        qnums = sorted({ar2int(x) for x in RE_NUM_PAREN.findall(raw_q)
                        if 1 <= ar2int(x) <= n_ayat})
        ph = norm(RE_NUM_PAREN.sub('', raw_q)).strip(' .،:؛')
        heads.append({'i': i, 'ph': ph, 'ph_words': ph.split(),
                      'nums_lo': qnums[0] if qnums else None,
                      'nums_hi': qnums[-1] if qnums else None})
    return heads

def _tab_score(h, a, vt, vt_words):
    """Skor match heading h vs ayat a (ROUND4-SPEC.md #3).
    Prefix kuat SAJA: frasa = awal ayat (dua arah, guard panjang) = 60;
    >= 3 kata pertama sama = 40; nomor cetak == a = 100. Frasa 1-2 kata
    yang persis awal ayat = 30 (lemah — anti false-hit 'الم'-klan).
    Tier substring bebas DILARANG."""
    sc = 0
    if h['nums_lo'] == a:
        sc += 100
    ph, pw = h['ph'], h['ph_words']
    if ph and vt:
        if vt.startswith(ph):
            sc += 60 if len(pw) >= 3 else 30
        elif len(vt.replace(' ', '')) >= 8 and ph.startswith(vt):
            sc += 60
        else:
            c = 0
            for x, y in zip(pw, vt_words):
                if x != y:
                    break
                c += 1
            if c >= 3:
                sc += 40
    return sc

def _align_dp(heads, vi_surah, n_ayat):
    """DP alignment monotonik global H vs A[1..N]: assign tiap heading
    ke satu ayat (atau None) non-decreasing, maksimalkan total skor.
    Kesalahan lokal tidak menular (beda dgn greedy per-anchor yang
    mengunci last_hi). Return list assignment per heading (None =
    tak match -> interpolasi)."""
    NEG = float('-inf')
    vt = {a: vi_surah.get(a) for a in range(1, n_ayat + 1)}
    vtw = {a: (vt[a].split() if vt[a] else None) for a in vt}
    dp = [NEG] * (n_ayat + 1)      # dp[a]: skor terbaik, ayat match terakhir = a
    dp[0] = 0.0                     # state 0 = belum ada match
    bt = []                         # per heading: (prev, matched)
    for h in heads:
        scored = []
        for a in range(1, n_ayat + 1):
            s = _tab_score(h, a, vt[a], vtw[a])
            if s > 0:
                scored.append((a, s))
        ndp = dp[:]                 # default: no-match, mewarisi state
        prev = list(range(n_ayat + 1))
        mat = [False] * (n_ayat + 1)
        # prefix-max: best_a[b] = argmax dp[0..b] (monotonic b >= a)
        best, best_a = dp[0], 0
        pref = [0] * (n_ayat + 1)
        for a in range(n_ayat + 1):
            if dp[a] > best:
                best, best_a = dp[a], a
            pref[a] = best_a
        for a, s in scored:
            cand = dp[pref[a]] + s
            if cand > ndp[a]:
                ndp[a] = cand
                prev[a] = pref[a]
                mat[a] = True
        dp = ndp
        bt.append((prev, mat))
    a = max(range(n_ayat + 1), key=lambda x: dp[x])
    assigns = [None] * len(heads)
    for i in range(len(heads) - 1, -1, -1):
        prev, mat = bt[i]
        if mat[a]:
            assigns[i] = a
        a = prev[a]
    return assigns

def tabari_segments(flat, n_ayat, vi_surah):
    """RONDE-4: alignment dua deret. Return (anchors, err).
    err != None -> FAIL surah (sentinel alignment gila)."""
    heads = _collect_tabari_heads(flat, n_ayat)
    if not heads:
        return [], 'no headings القول في تأويل'
    assigns = _align_dp(heads, vi_surah, n_ayat)
    matches = [(h, a) for h, a in zip(heads, assigns) if a is not None]
    if not matches:
        return [], 'alignment: no heading matched any ayat'
    first_a, last_a = matches[0][1], matches[-1][1]
    if first_a > 3:
        return [], f'alignment: first heading match = ayat {first_a} (wajib 1..3)'
    # RONDE-4 sentinel akhir: heading penutup tabari kerap = kutipan blok
    # multi-ayat yang mengalir sampai akhir surah (terverifikasi fisik:
    # S37 heading terakhir kutipan 178-182, S80 31-42, S82 9-19) — gap
    # besar di surah pendek itu NORMAL. 'Gila' = gap melewati separuh
    # surah atau absolut ekstrem.
    tol = max(12, n_ayat // 2)
    if n_ayat - last_a > tol:
        return [], (f'alignment: last heading match = ayat {last_a} '
                    f'(gap {n_ayat - last_a} > {tol} dari N={n_ayat})')
    anchors = []
    prev_hi = None
    pend = []                      # heading tak-match sejak match terakhir
    for h, a in matches:
        if pend and prev_hi is not None:
            gap_lo, gap_hi = prev_hi + 1, a - 1
            if gap_lo <= gap_hi:   # R == L+1 -> melebur ke segmen L
                lb = str(gap_lo) if gap_lo == gap_hi else f'{gap_lo}-{gap_hi}'
                anchors.append((pend[0], lb, 'tafsir'))
        pend = []                  # heading tak-match sebelum match pertama:
        lo = hi = a                # teks jatuh ke zona intro (tak dipetakan)
        if h['nums_lo'] == a and h['nums_hi'] is not None:
            lo, hi = h['nums_lo'], h['nums_hi']
        anchors.append((h['i'], str(lo) if lo == hi else f'{lo}-{hi}', 'tafsir'))
        prev_hi = hi
    # RONDE-4 union-merge: anchor berurutan yang labelnya OVERLAP
    # (heading kutipan-blok besar '30-32' disusul heading detail frasa
    # ayat dalam blok itu — S39 '30-31'+'30-32', S56 '32-38'+'34')
    # digabung jadi satu segmen rentang union; tanpa ini cek monotonik
    # strict gagal padahal teksnya memang satu blok tafsir.
    merged = []
    for pos, lb, kind in anchors:
        rng = parse_label(lb)
        prev = parse_label(merged[-1][1]) if merged else None
        if rng and prev and rng[0] <= prev[1]:
            new_hi = max(prev[1], rng[1])
            lb2 = str(prev[0]) if prev[0] == new_hi else f'{prev[0]}-{new_hi}'
            merged[-1] = (merged[-1][0], lb2, kind)
        else:
            merged.append((pos, lb, kind))
    return merged, None

# ---------- shabuni ----------
# Ronde-2 (B): seksi anotasi (التسمية/المناسبة/اللغة/البلاغة/الفوائد) =
# 'section' — mereka mengulas ULANG rentang pasase yang baru selesai,
# mundur terhadap urutan ayat. Intro (بين يدي/فضلها) hanya di awal surah;
# bila muncul setelah tafsir -> diperlakukan sebagai section.
SH_HEADS = [
    ('intro', 'بين يدي السورت'), ('intro', 'بينا يدي'),
    ('intro', 'فضله'), ('intro', 'فضلها'),
    ('section', 'التسميت'), ('section', 'المناسبت'),
    ('section', 'اللغت'),
    ('tafsir', 'التفسير'),
    ('section', 'البلاغت'), ('section', 'الفوائد'),
    ('closing', 'خاتمت'),
]

def _sh_head(tn):
    for kind, h in SH_HEADS:
        if tn.startswith(h):
            return kind
    return None

def shabuni_segments(flat, n_ayat, vi_surah):
    """Ronde-2 (B): التفسير = tafsir; seksi anotasi = kind 'section'
    dengan label = label tafsir terdekat sebelumnya (dikecualikan dari
    cek monotonik & intro-after-tafsir). المناسبة di tengah kitab =
    section, bukan intro.
    Label tafsir per unit: lo = quote PEMBUKA pasase; hi = quote
    terbesar dalam jendela [lo unit ini, pembuka unit tafsir BERIKUTNYA)
    — quote komparatif maju/mundur di luar jendela dibuang (surah 2, 27,
    dsb.: tafsir pasase A kerap mengutip ayat pasase B)."""
    units = []            # list of dicts {kind, start, quotes:[ordered]}
    cur = None
    for i, (w, p, t) in enumerate(flat):
        tn = norm(t)
        kind = _sh_head(tn)
        if kind:
            if cur:
                cur['end'] = i - 1
                units.append(cur)
            cur = {'kind': kind, 'start': i, 'quotes': []}
            # heading may carry content in the same paragraph -> keep scanning quotes
        if cur is None:
            cur = {'kind': 'intro', 'start': i, 'quotes': []}
        for qm in RE_QT.finditer(t):
            ph = norm(qm.group(1)).strip(' .،:')
            if len(ph) < 2:
                continue
            a = match_phrase(ph, vi_surah, n_ayat)
            if a:
                cur['quotes'].append(a)
    if cur:
        cur['end'] = len(flat) - 1
        units.append(cur)

    # label rentang per unit tafsir (pendekatan jendela antar-pembuka)
    t_idx = [k for k, u in enumerate(units)
             if u['kind'] == 'tafsir' and u['quotes']]
    labels = {}
    for j, k in enumerate(t_idx):
        q = units[k]['quotes']
        lo = q[0]
        hi_bound = n_ayat + 1
        if j + 1 < len(t_idx):
            hi_bound = units[t_idx[j + 1]]['quotes'][0]
            if hi_bound <= lo:
                hi_bound = lo       # pembuka berikutnya sama/mundur -> jendela kosong
        in_win = [a for a in q if lo <= a < hi_bound]
        hi = max(in_win) if in_win else lo
        labels[k] = str(lo) if lo == hi else f'{lo}-{hi}'

    anchors = []
    prev_tafsir = None   # rentang label tafsir terdekat sebelumnya
    for k, u in enumerate(units):
        kind = u['kind']
        if kind == 'closing':
            anchors.append((u['start'], 'closing', 'closing'))
        elif kind == 'tafsir':
            if k in labels:
                lb = labels[k]
                anchors.append((u['start'], lb, 'tafsir'))
                prev_tafsir = lb
            elif prev_tafsir:
                # no quote in this unit -> keep previous label (merge later)
                anchors.append((u['start'], prev_tafsir, 'tafsir'))
            else:
                anchors.append((u['start'], 'intro', 'intro'))
        else:  # section anotasi / intro yang muncul setelah tafsir
            if prev_tafsir:
                anchors.append((u['start'], prev_tafsir, 'section'))
            elif kind == 'intro':
                anchors.append((u['start'], 'intro', 'intro'))
            else:   # section sebelum tafsir pertama (mis. اللغة pembuka)
                anchors.append((u['start'], 'intro', 'section'))
    return anchors

# ---------- awlad / jawzi ----------
def _monotonic_pick(cands):
    """RONDE-4: pilih subsequence anchor monotonik terbaik dari kandidat
    (posisi, lo, hi) — DP gaya-LCS. Skor PRIMER = rentang ayat kontigu
    yang di-span rantai (min_lo..max_hi), SEKUNDER = jumlah anchor.
    Rationale (4 kasus uji fisik):
      - greedy first-come: forward-quote meracuni last_n (jawzi 2 p513
        '147'; jawzi 17 p2693 kutipan 109 di tengah tafsir 85 menolak 10
        anchor asli 86-109) -> harus kalah dari rantai fragmentasi;
      - skor jumlah-ayat-tercakup murni: blok REKAP besar (jawzi 5 p1624
        kutipan ulang 7-53 SETELAH tafsir per-ayat 7-34) menang padahal
        posisinya salah -> kalah via tie-break jumlah anchor (rentang
        sama, fragmentasi lebih banyak); gap sisanya ditutup expand_labels;
      - skor span-kontigu menyelamatkan blok pembuka besar (S51/79/84:
        '1-14' menang atas fragmentasi '9','12' yang mulai dari 9).
    Constraint sama dengan greedy lama: lo_berikut > hi_sebelum."""
    n = len(cands)
    if n == 0:
        return []
    span = [c[2] - c[1] + 1 for c in cands]   # span berakhir di j (sendirian)
    cnt = [1] * n
    lo_first = [c[1] for c in cands]
    prev = [-1] * n
    best = [(span[j], cnt[j]) for j in range(n)]
    for j in range(n):
        for i in range(j):
            if cands[j][1] > cands[i][2]:       # monotonik strict
                cand = (cands[i][2] - lo_first[i] + 1 + 0, 0)
                # span rantai i + j: lo_first_i .. hi_j
                cand = (cands[j][2] - lo_first[i] + 1, cnt[i] + 1)
                if cand > best[j]:
                    best[j] = cand
                    cnt[j] = cand[1]
                    lo_first[j] = lo_first[i]
                    prev[j] = i
    j = max(range(n), key=lambda x: best[x])
    chain = []
    while j != -1:
        chain.append(j)
        j = prev[j]
    return [cands[j] for j in reversed(chain)]

def quote_block_segments(flat, n_ayat, vi_surah=None):
    """Anchor = paragraf blok quote utuh berdiri sendiri berpenomoran.
    Ronde-2 (A): blok multi-ayat berisi nomor cetak (N) DI DALAM kutipan
    -> label = rentang min-max nomor LANGSUNG (abaikan verse-index untuk
    label). Tiga varian diterima:
      (1) blok lama '﴿X (N)﴾.' utuh berdiri sendiri;
      (2) blok multi-ayat berawalan ﴿ — penutup ﴾ boleh hilang/terpotong
          halaman; hanya nomor DI DALAM span kutipan yang dihitung;
      (3) blok ayat mentah TANPA bracket (awlad 104/105) — wajib
          terverifikasi teks-ayat via verse_index (prefix 24 karakter).
    Nomor surah lain dalam kutipan disaring oleh cek monotonik.
    RONDE-4: kandidat dikumpulkan semua lalu dipilih subsequence
    monotonik MAKSIMAL (_monotonic_pick) — lihat docstring fungsi itu."""
    cands = []
    for i, (w, p, t) in enumerate(flat):
        nums = {ar2int(x) for x in RE_NUM_PAREN.findall(t)}
        nums = {n for n in nums if 1 <= n <= n_ayat}
        if not nums:
            continue
        lo, hi = min(nums), max(nums)
        if RE_BLOCK.match(t):
            pass                       # (1) pola lama, utuh berdiri sendiri
        elif RE_BLOCK_OPEN.match(t):
            close = t.find('﴾')
            if close != -1 and RE_XREF_AFTER.match(t[close + 1:close + 80]):
                continue              # RONDE-4: kutipan rujukan-silang, skip
            qnums = {n for n in nums_in_quote(t) if 1 <= n <= n_ayat}
            if not qnums:              # nomor hanya di luar kutipan -> cek (3)
                if vi_surah is None or not _is_verse_block(t, lo, vi_surah):
                    continue
                qnums = nums
            lo, hi = min(qnums), max(qnums)
        elif vi_surah is not None and _is_verse_block(t, lo, vi_surah):
            pass                       # (3) blok ayat mentah tanpa bracket
        else:
            continue
        cands.append((i, lo, hi))
    anchors = []
    for i, lo, hi in _monotonic_pick(cands):
        lb = str(lo) if lo == hi else f'{lo}-{hi}'
        anchors.append((i, lb, 'tafsir'))
    return anchors

# ---------- guard detection (QC-RB.md wajib) ----------
RE_ISTIADHAH = re.compile(r'^اعوذ بالله')
RE_CLOSING = re.compile(r'^(خاتمت|اللهم امين|امين|رب يسر|رب اعن|رب يسرك واعن)')

def guard_positions(flat, self_name, next_name):
    """Kandidat guard: heading nama surah (self -> leading cut, next ->
    trailing cut) + basmalah/﷽ (trailing only, handled by caller)."""
    hits = {'self': [], 'next': [], 'basmalah': []}
    sname = norm(self_name)
    nname = norm(next_name) if next_name else ''
    for i, (w, p, t) in enumerate(flat):
        tn0 = norm(t)
        if tn0 == '﷽' or tn0 == 'بسم الله الرحمن الرحيم':
            hits['basmalah'].append(i)
            continue
        tn = tn0.lstrip('*[]()﴾﴿.،:; ٠١٢٣٤٥٦٧٨٩')
        for tag, name in (('self', sname), ('next', nname)):
            if not name:
                continue
            key = f'سورت {name}'
            if tn == key or tn.startswith(f'تفسير {key}'):
                hits[tag].append(i)
                break
            # complex heading e.g. "[تفسير] [١] سورة البقرة [مدنية ...]"
            if 'سورت' in tn[:30] and key in tn and len(tn) < 140:
                hits[tag].append(i)
                break
    return hits

# ---------- assembly: anchors -> contiguous segments ----------
def assemble(flat, anchors, gself, gnext, gbasmalah):
    """Bangun segmen kontigu flat[0]..flat[-1]:
    [out_of_scope leading][intro/istiadhah][tafsir...][closing][out_of_scope].
    Return (segs, cut_info) atau (None, reason)."""
    n = len(flat)
    first_i, last_i = anchors[0][0], anchors[-1][0]

    # leading cut: heading surah SELF paling akhir sebelum anchor pertama
    leading = [g for g in gself if g < first_i]
    zone_start = (max(leading) + 1) if leading else 0

    # trailing cut: guard pertama SETELAH anchor terakhir.
    # RONDE-4: basmalah yang LANGSUNG mengikuti anchor terakhir
    # (b == last_i+1) adalah basmalah PEMBUKA PASASE (maraghi 95-114:
    # header -> basmalah -> kutipan ayat -> tafsir; terverifikasi delta=1
    # di 19 surah), BUKAN spill surah berikutnya. Spill basmalah asli
    # (awlad/jawzi) selalu berjarak > 1 paragraf dari anchor terakhir
    # (terverifikasi: 0 kasus b <= last_i+3 di 4 buku lain) — tetap cut.
    trailing = ([g for g in gnext if g > last_i]
                + [b for b in gbasmalah if b > last_i + 1])
    trail_cut = min(trailing) if trailing else n

    # closing heading di zona post-anchor (sebelum guard)
    closing_at = None
    for i in range(last_i + 1, trail_cut):
        if RE_CLOSING.match(norm(flat[i][2]).lstrip('*[]() ')):
            closing_at = i
            break

    segs = []

    def seg(a, b, label, kind):
        if b < a:
            return
        segs.append({'from': [flat[a][0], flat[a][1]],
                     'to': [flat[b][0], flat[b][1]],
                     'label': label, 'kind': kind,
                     '_a': a, '_b': b})

    if leading:
        seg(0, max(leading), 'out_of_scope', 'out_of_scope')

    # intro zone: [zone_start .. first_i-1], split istiadhah jika ada
    if first_i > zone_start:
        ist = None
        for i in range(zone_start, first_i):
            if RE_ISTIADHAH.match(norm(flat[i][2])):
                ist = i
                break
        if ist is None or ist == zone_start:
            seg(zone_start, first_i - 1, 'intro', 'intro')
        else:
            seg(zone_start, ist - 1, 'intro', 'intro')
            seg(ist, first_i - 1, 'istiadhah', 'istiadhah')

    # tafsir segments; merge anchors berurutan dengan label+kind identik
    merged = []
    for a in anchors:
        if merged and merged[-1][1] == a[1] and merged[-1][2] == a[2]:
            continue
        merged.append(a)
    for k, (idx, lb, kind) in enumerate(merged):
        if k + 1 < len(merged):
            end = merged[k + 1][0] - 1
        else:
            end = trail_cut - 1
            if closing_at is not None and closing_at > idx:
                end = min(end, closing_at - 1)
        seg(idx, end, lb, kind)

    if closing_at is not None and closing_at <= trail_cut - 1:
        seg(closing_at, trail_cut - 1, 'closing', 'closing')
    if trail_cut < n:
        seg(trail_cut, n - 1, 'out_of_scope', 'out_of_scope')
    return segs, None

# ---------- validator (eval #11; RONDE-3 + cek cakupan ayat) ----------
def validate(segs, flat, strict=True, cover_n=0, sn=0, book=''):
    """Return (errs, warns). cover_n > 0 -> aktifkan cek cakupan AYAT
    (RONDE-3): union label tafsir harus 1..cover_n; celah setelah anchor
    pertama = error, celah sebelum anchor pertama = warning leading-gap
    (tafsir ayat itu berada di zona intro/spill, tidak dipetakan).
    sn > 0 -> aktifkan validator RONDE-4: kepadatan segmen + probe
    konten ayat terkenal (PROBES)."""
    errs = []
    # (a) coverage: contiguous, full span
    if segs[0]['_a'] != 0:
        errs.append('coverage: first segment starts at flat[%d]' % segs[0]['_a'])
    for k in range(1, len(segs)):
        if segs[k]['_a'] != segs[k - 1]['_b'] + 1:
            errs.append('coverage: gap/overlap at segment %d' % k)
    if segs[-1]['_b'] != len(flat) - 1:
        errs.append('coverage: last segment ends at flat[%d] of %d'
                    % (segs[-1]['_b'], len(flat) - 1))
    # (b) label monotonicity + special-label placement
    # Ronde-2 (B): segmen kind 'section' (anotasi shabuni yang mengulas
    # ulang pasase) dikecualikan dari cek monotonik — cek hanya untuk
    # segmen tafsir inti.
    EXEMPT = ('intro', 'istiadhah', 'closing', 'out_of_scope', 'section')
    prev_hi = 0
    for k, s in enumerate(segs):
        lb, kind = s['label'], s['kind']
        if kind in EXEMPT:
            continue
        rng = parse_label(lb)
        if not rng:
            errs.append('label: cannot parse %r (seg %d)' % (lb, k))
            continue
        lo, hi = rng
        if strict and lo < prev_hi:
            errs.append('monotonic: seg %d label %s goes back before %d'
                        % (k, lb, prev_hi))
        if not strict and hi < prev_hi:
            errs.append('monotonic(non-strict): seg %d hi %d < prev %d'
                        % (k, hi, prev_hi))
        prev_hi = max(prev_hi, hi)
    # placement: out_of_scope hanya prefix/suffix; intro sebelum tafsir;
    # closing setelah tafsir dan di ekor core
    kinds = [s['kind'] for s in segs]
    CORE = ('tafsir', 'balagha', 'fawaid', 'section')
    i0, i1 = 0, len(segs) - 1
    while i0 <= i1 and kinds[i0] == 'out_of_scope':
        i0 += 1
    while i1 >= i0 and kinds[i1] == 'out_of_scope':
        i1 -= 1
    for k in range(i0, i1 + 1):
        if kinds[k] == 'out_of_scope':
            errs.append('order: out_of_scope in middle (seg %d)' % k)
    first_t = next((k for k in range(i0, i1 + 1) if kinds[k] in CORE), None)
    for k in range(i0, i1 + 1):
        kd = kinds[k]
        if kd in ('intro', 'istiadhah') and first_t is not None and k > first_t:
            errs.append('order: %s after tafsir (seg %d)' % (kd, k))
        if kd == 'closing' and first_t is not None and k < first_t:
            errs.append('order: closing before tafsir (seg %d)' % k)
        if kd == 'closing' and any(kinds[j] in CORE + ('intro', 'istiadhah')
                                    for j in range(k + 1, i1 + 1)):
            errs.append('order: closing not at tail (seg %d)' % k)
    # RONDE-3: cakupan ayat penuh
    warns = []
    if cover_n:
        first_lo = None
        cov = set()
        for s in segs:
            if s['kind'] != 'tafsir':
                continue
            rng = parse_label(s['label'])
            if not rng:
                continue
            lo, hi = rng
            if first_lo is None:
                first_lo = lo
            cov.update(range(lo, hi + 1))
        if cov:
            missing = sorted(set(range(1, cover_n + 1)) - cov)
            interior = [m for m in missing if m > first_lo]
            leading = [m for m in missing if m < first_lo]
            if interior:
                errs.append('cover: ayat tak tercakup setelah anchor pertama: %s'
                            % interior[:8])
            if leading:
                warns.append('leading-gap: ayat %s sebelum anchor tafsir pertama '
                             '(tafsirnya di zona intro/spill; tidak dipetakan)'
                             % leading[:8])
    # RONDE-4 (a): kepadatan segmen — sembunyi > limit = FAIL surah.
    # Formula ROUND4-SPEC #5: (halaman_surah / ayat_surah) * k * DENSITY_TOL.
    # Implementasi limit = max(varian-ayat murni, varian-bobot-karakter):
    #   - varian-ayat = formula spec literal;
    #   - varian-karakter = bobot k efektif (total karakter ayat label /
    #     rata-rata karakter ayat surah) — mengoreksi false-positive
    #     sistemik pada ayat super-panjang yang tafsirnya ratusan halaman
    #     (2:196 = 108 hal, 10 heading frasa potongan, semuanya fisik
    #     ayat 196) DAN pada muqatta'ah pendek ('الم' 3 char, tafsir 16
    #     hal) — keduanya terverifikasi label-benar.
    # Violasi <= DENSITY_MARGINAL x limit = warning (kepadatan riwayat
    # buku; kasus nyata 1.2-1.4x) — jauh dari mode-bug yang mau ditangkap
    # ('281' = 5.5x, '282' = 3.1x ronde-3).
    if sn:
        n_ay = AYAT_COUNT.get(sn, 0)
        if n_ay:
            vi_sn = _W.get('q', {}).get(sn, {})
            chlen = {a: len(t) for a, t in vi_sn.items()}
            c_all = sum(chlen.values())
            c_avg = c_all / n_ay if c_all else 0
            pages_surah = flat[-1][0] - flat[0][0] + 1
            base = pages_surah / n_ay
            for k, s in enumerate(segs):
                if s['kind'] != 'tafsir':
                    continue
                rng = parse_label(s['label'])
                if not rng:
                    continue
                span = s['to'][0] - s['from'][0] + 1
                limit_ayat = base * (rng[1] - rng[0] + 1) * DENSITY_TOL
                if c_avg:
                    c_lab = sum(chlen.get(a, c_avg)
                                for a in range(rng[0], rng[1] + 1))
                    limit_chars = DENSITY_TOL * pages_surah * (c_lab / c_all)
                else:
                    limit_chars = 0
                limit = max(limit_ayat, limit_chars)
                if span > limit:
                    msg = ('density: seg %d label %s span %d halaman > limit '
                           '%.0f (ayat %.0f / chars %.0f)'
                           % (k, s['label'], span, limit, limit_ayat, limit_chars))
                    vkey = (book, sn, rng[0], rng[1])
                    if vkey in VERIFIED_DENSITY:
                        warns.append(msg + ' [verified: '
                                     + VERIFIED_DENSITY[vkey] + ']')
                    elif span > DENSITY_MARGINAL * limit:
                        errs.append(msg)
                    else:
                        warns.append(msg + ' [marginal]')
    # RONDE-4: guard anti-truncation senyap — out_of_scope dominan =
    # kecurigaan konten tafsir terbuang ke zona guard (kasus basmalah
    # maraghi 95-114 tertangkap probe 112; ini jaring pengaman umum).
    n_oos = sum(s['_b'] - s['_a'] + 1 for s in segs
                if s['kind'] == 'out_of_scope')
    if n_oos > 0.4 * len(flat):
        warns.append('out_of_scope %d/%d paragraf (%.0f%%) — cek potongan konten'
                     % (n_oos, len(flat), 100.0 * n_oos / len(flat)))
    # RONDE-4 (b): probe konten ayat terkenal
    if sn:
        for ps, pa, phr in PROBES:
            if ps != sn:
                continue
            phr = norm(phr)
            cov = []
            for s in segs:
                if s['kind'] != 'tafsir':
                    continue
                rng = parse_label(s['label'])
                if rng and rng[0] <= pa <= rng[1]:
                    cov.append(s)
            if not cov:
                errs.append('probe: tak ada segmen tafsir melabeli %d:%d'
                            % (ps, pa))
                continue
            found = False
            for s in cov:
                txt = ' '.join(norm(flat[j][2])
                               for j in range(s['_a'], s['_b'] + 1))
                if phr in txt:
                    found = True
                    break
            if not found:
                errs.append('probe: frasa tak ditemukan di segmen %d:%d '
                            '(%d segmen dicek)' % (ps, pa, len(cov)))
    return errs, warns

# ---------- per-surah worker ----------
def process_surah(args):
    book, sn = args
    toc = _W['toc']
    meta = toc[book]['surahs'][str(sn)]
    n_ayat = AYAT_COUNT[sn]
    flat = surah_flat(book, sn)
    if meta['end_excl'] <= meta['start'] or not flat:
        # Ronde-2: rentang kosong = konten memang tidak ada di buku (mis.
        # shabuni terpotong: halaman terakhir 1627 = Al-Falaq, An-Nas
        # absen) -> skip yang jujur, bukan fail TOC.
        return {'surah': sn, 'status': 'skip',
                'reason': 'kosong (konten tidak ada di buku/TOC)'}

    self_name = meta['surah']

    # SPECIAL RULE (human-verified 2026-08): jawzi p.4698 is the combined
    # opener of surat al-Muawwidzatain — hadith on the fadhilah of Al-Falaq
    # AND An-Nas together, then the book ends. Not per-verse tafsir, so the
    # whole flat (shared by surah 113 and 114) becomes a single 'intro' segment.
    if book == 'ibnkathir_jawzi' and sn in (113, 114) \
            and {w for w, _p, _t in flat} == {4698}:
        segs = [{'from': [flat[0][0], flat[0][1]],
                 'to': [flat[-1][0], flat[-1][1]],
                 'label': 'intro', 'kind': 'intro',
                 '_a': 0, '_b': len(flat) - 1}]
        errs, _warns = validate(segs, flat, strict=True)
        if errs:  # safety net; a single intro segment cannot violate
            return {'surah': sn, 'status': 'fail',
                    'reason': 'muawwidzatain-rule: ' + '; '.join(errs[:3])}
        segs[0].pop('_a', None); segs[0].pop('_b', None)
        name = f'{book}_{sn:03d}.rb.json'
        with open(OUT / name, 'w', encoding='utf-8') as f:
            json.dump(segs, f, ensure_ascii=False, indent=1)
        return {'surah': sn, 'status': 'ok', 'segments': 1,
                'note': 'p.4698 shared Muawwidzatain opener -> intro'}

    next_name = toc[book]['surahs'].get(str(sn + 1), {}).get('surah', '')
    g = guard_positions(flat, self_name, next_name)

    try:
        if book == 'maraghi':
            anchors, extra_guards = maraghi_segments(flat, sn)
            g['next'].extend(extra_guards)
        elif book == 'tabari':
            # RONDE-4: alignment dua deret (basis kanonik); sentinel gila = FAIL
            anchors, align_err = tabari_segments(flat, n_ayat, _W['q'][sn])
            if align_err:
                name = f'{book}_{sn:03d}.FAIL.json'
                with open(OUT / name, 'w', encoding='utf-8') as f:
                    json.dump({'surah': sn, 'book': book, 'reason': [align_err]},
                              f, ensure_ascii=False, indent=1)
                return {'surah': sn, 'status': 'fail', 'reason': align_err}
        elif book == 'shabuni':
            anchors = shabuni_segments(flat, n_ayat, _W['q'][sn])
        else:  # awlad / jawzi
            # Ronde-2 (A): awlad pakai VI utk verifikasi blok ayat tanpa
            # bracket; jawzi tetap jalur legacy (tanpa VI).
            vi_sn = _W['q'][sn] if book == 'ibnkathir_awlad' else None
            anchors = quote_block_segments(flat, n_ayat, vi_sn)

        # drop anchors that fall inside guard zones (safety, eval #11c)
        if not anchors:
            return {'surah': sn, 'status': 'fail', 'reason': 'no anchors'}

        segs, reason = assemble(flat, anchors, g['self'], g['next'], g['basmalah'])
        if not segs:
            return {'surah': sn, 'status': 'fail', 'reason': reason or 'assemble empty'}

        # RONDE-3: perluas label tafsir jadi rentang implisit (sebelum
        # validasi agar cek monotonik & cakupan melihat label final)
        if book in EXPAND_BOOKS:
            segs, _n_exp = expand_labels(segs, n_ayat)

        strict = (book != 'shabuni')
        errs, warns = validate(segs, flat, strict=strict,
                               cover_n=(n_ayat if book in EXPAND_BOOKS else 0),
                               sn=sn, book=book)
        if errs:
            name = f'{book}_{sn:03d}.FAIL.json'
            with open(OUT / name, 'w', encoding='utf-8') as f:
                json.dump({'surah': sn, 'book': book, 'reason': errs[:20]},
                          f, ensure_ascii=False, indent=1)
            return {'surah': sn, 'status': 'fail',
                    'reason': '; '.join(errs[:3])}

        for s in segs:  # strip internal flat-index markers
            s.pop('_a', None); s.pop('_b', None)
        name = f'{book}_{sn:03d}.rb.json'
        stale = OUT / f'{book}_{sn:03d}.FAIL.json'
        if stale.exists():   # RONDE-3: bersihkan FAIL lawas saat sukses
            stale.unlink()
        with open(OUT / name, 'w', encoding='utf-8') as f:
            json.dump(segs, f, ensure_ascii=False, indent=1)
        res = {'surah': sn, 'status': 'ok', 'segments': len(segs)}
        if warns:
            res['warnings'] = warns
        return res

    except Exception as e:
        return {'surah': sn, 'status': 'fail',
                'reason': f'{type(e).__name__}: {e}'}

# ---------- main ----------
def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ALIAS:
        print(__doc__)
        print('books:', ' | '.join(ALIAS))
        sys.exit(1)
    book_arg = sys.argv[1]
    book = ALIAS[book_arg]
    n_workers = int(sys.argv[2]) if len(sys.argv) > 2 else max(1, cpu_count() - 1)

    OUT.mkdir(parents=True, exist_ok=True)
    if not PAGES_FILE.exists():
        print(f'ERROR: {PAGES_FILE} tidak ada — jalankan parse_mp.py dulu.')
        sys.exit(1)
    if not CANON_FILE.exists():
        print(f'ERROR: {CANON_FILE} tidak ada — dasar deret ayat RONDE-4.')
        sys.exit(1)

    # RONDE-4 revisi: cross-check sekunder — verse_index.json Maraghi vs
    # kanonik (informasional; bila beda, kanonik yang dipercaya).
    if VI_FILE.exists():
        canon = json.load(open(CANON_FILE, encoding='utf-8'))
        qq = {int(s['id']): {int(v['id']): norm(v['text']) for v in s['verses']}
              for s in canon}
        vi = json.load(open(VI_FILE, encoding='utf-8'))
        n_eq = n_diff = n_vi_only = 0
        for s, v in vi.items():
            sn = int(s)
            for a, t in v.items():
                an = int(a)
                tn = norm(t)
                qc = qq.get(sn, {}).get(an)
                if qc is None:
                    n_vi_only += 1
                elif qc == tn:
                    n_eq += 1
                else:
                    n_diff += 1
        print(f'cross-check verse_index vs kanonik: sama={n_eq} beda={n_diff} '
              f'hanya-di-VI={n_vi_only} (beda -> percayai kanonik)')

    print(f'Grouping: {book} (114 surah) with {n_workers} workers')
    t0 = time.time()
    stats = {'ok': 0, 'fail': 0, 'skip': 0, 'issues': [], 'warnings': {}}
    with Pool(n_workers, initializer=_init_worker, initargs=(book,)) as pool:
        for result in pool.imap(process_surah, [(book, sn) for sn in range(1, 115)]):
            sn = result['surah']
            if result['status'] == 'ok':
                stats['ok'] += 1
                if result.get('warnings'):   # RONDE-3: leading-gap dsb.
                    stats['warnings'][str(sn)] = result['warnings']
            else:
                stats[result['status']] += 1
                stats['issues'].append(f"{sn}: {result['reason']}")
            if sn % 10 == 0:
                el = time.time() - t0
                print(f'  progress {sn}/114 ({sn / el if el else 0:.1f} surah/s)')

    el = time.time() - t0
    print(f'Done in {el:.1f}s  ok={stats["ok"]} fail={stats["fail"]} skip={stats["skip"]}')
    for it in stats['issues'][:20]:
        print('  !', it)

    report = OUT / '_report.json'
    rep = json.load(open(report, encoding='utf-8')) if report.exists() else {}
    rep[book] = stats
    with open(report, 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
