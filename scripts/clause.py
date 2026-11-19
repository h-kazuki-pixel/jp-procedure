"""根拠条項号の分解と、法令本文(JSON full)での照合。"""
import re, unicodedata
KN = {c: i for i, c in enumerate('〇一二三四五六七八九')}
def k2i(t):
    if t.isdigit(): return int(t)
    if all(c in KN for c in t): return int(''.join(str(KN[c]) for c in t))
    n, cur = 0, 0
    for c in t:
        if c in KN: cur = KN[c]
        elif c in '十百千': n += (cur or 1) * {'十': 10, '百': 100, '千': 1000}[c]; cur = 0
        else: raise ValueError(t)
    return n + cur
D = '[0-9〇一二三四五六七八九十百千]+'
NUM = f'({D})'
PAT = re.compile(rf'^(附則)?第{NUM}条((?:の{D})*)(?:第{NUM}項)?(?:第{NUM}号((?:の{D})*))?$')
def norm(raw): return re.sub(r'\s+', '', unicodedata.normalize('NFKC', raw or ''))
def _sub(x): return [k2i(v) for v in re.findall(f'の({D})', x or '')]
def parse_base(raw):
    """試行と同じ厳しい分解。合わなければ None。"""
    m = PAT.match(norm(raw))
    if not m: return None
    return {'附則': bool(m.group(1)),
            '条': '_'.join(str(v) for v in [k2i(m.group(2))] + _sub(m.group(3))),
            '項': str(k2i(m.group(4))) if m.group(4) else None,
            '号': '_'.join(str(v) for v in [k2i(m.group(5))] + _sub(m.group(6))) if m.group(5) else None}

# 追加する型。順に積み重ねて書き換え、最初に分けられた規則の名前を記録する。
def r_edaban(t):   # 第13の2条 -> 第13条の2 (枝番号の位置の書き違いとみなす)
    return re.sub(rf'第({D})((?:の{D})+)条', r'第\1条\2', t)
def r_dai(t):      # 第5条2項 / 第5条第2項3号 -> 「第」を補う
    return re.sub(rf'(?<=[条項])(?<!第)({D})(?=[項号])', r'第\1', t)
def r_list(t):     # 列挙: 先頭の条項だけを使う。「第7条第1,2項」→「第7条第1項」
    t = re.sub(rf'第({D})[,、・]{D}(?:[,、・]{D})*([項号])', r'第\1\2', t)
    return re.split(r'[、,，;；]|及び|並びに|又は|若しくは|から', t)[0]
def r_junyo(t):    # 準用: 「第A条で準用する第B条第1項」→ 準用される側 B を照合対象にする
    m = re.match(r'^(.+?)(?:において|で|により)準用する(.+?)(?:の規定)?$', t)
    return m.group(2) if m else t
def r_yomikae(t):  # 読み替えて準用: 「第A条第1項において読み替えて準用する第B条第2項」→ B
    m = re.match(r'^(.+?)(?:において|で|により)?読み替えて準用する(.+?)(?:の規定)?$', t)
    return m.group(2) if m else t
def r_seitei(t):   # 制定附則(=原始附則) → 附則
    return re.sub(r'^制定附則', '附則', t)
KANA = 'イロハニホヘトチリヌルヲワカヨタレソツネナラムウヰノオクヤマケフコエテアサキユメミシヱヒモセス'
def r_saibun(t):   # 号の細分(イ、ロ、(1) など)は号までで照合する
    return re.sub(rf'(第{D}号(?:の{D})*)の?[{KANA}](?:\({D}\))*$', r'\1', t)
RULES = [('枝番号の位置(第NのN条)', r_edaban), ('「第」の抜け', r_dai), ('列挙は先頭', r_list), ('準用は準用される側', r_junyo),
         ('読み替えて準用は準用される側', r_yomikae), ('制定附則は附則', r_seitei), ('号の細分は号まで', r_saibun)]
def parse_ext(raw):
    """戻り値: (分解結果 or None, 使った規則名 ('' は基本で分けられた), 準用する側の原文)"""
    t = norm(raw); p = parse_base(t)
    if p: return p, '', ''
    junyo_src = ''
    for name, f in RULES:
        if f in (r_junyo, r_yomikae):
            m = re.match(r'^(.+?)(?:において|で|により)?(?:読み替えて)?準用する', t)
            if m and not junyo_src: junyo_src = m.group(1)
        t = f(t); p = parse_base(t)
        if p: return p, name, junyo_src
    return None, '', ''

def kids(n, tag): return [c for c in n.get('children', []) if isinstance(c, dict) and c['tag'] == tag]
def walk(n, tag, acc):
    if isinstance(n, dict):
        if n['tag'] == tag: acc.append(n); return acc
        for c in n.get('children', []): walk(c, tag, acc)
    return acc
def text(n):
    if isinstance(n, str): return n
    if n.get('tag') == 'Rt': return ''
    return ''.join(text(c) for c in n.get('children', []))
def article_index(lb):
    """(附則か, 条番号) -> Article ノード。附則は原文の附則(AmendLawNum の無いもの)だけ。"""
    idx = {}
    for sp in kids(lb, 'MainProvision'):
        for a in walk(sp, 'Article', []): idx.setdefault((False, a['attr'].get('Num')), a)
    for sp in kids(lb, 'SupplProvision'):
        if 'AmendLawNum' in (sp.get('attr') or {}): continue
        for a in walk(sp, 'Article', []): idx.setdefault((True, a['attr'].get('Num')), a)
    return idx
def check(idx, p):
    """戻り値: (結果, 補足, 注記)。注記は区分を変えない参考情報。"""
    r, note = _check(idx, p)
    memo = []
    if r == '法令はあるが条が無い':
        if not idx: memo.append('条立ての無い法令')
        elif (not p['附則'], p['条']) in idx: memo.append('附則に同じ番号の条あり' if not p['附則'] else '本則に同じ番号の条あり')
    else:
        a = idx[(p['附則'], p['条'])]
        body = ''.join(text(c) for c in a.get('children', []) if isinstance(c, dict) and c['tag'] not in ('ArticleTitle', 'ArticleCaption'))
        if body.strip() == '削除': memo.append('条が「削除」')
    return r, note, '・'.join(memo)
def _check(idx, p):
    art = idx.get((p['附則'], p['条']))
    if art is None: return '法令はあるが条が無い', ''
    paras = kids(art, 'Paragraph')
    if p['項'] is None and p['号'] is None: return '条まで', '項・号の指定なし'
    if p['項'] is not None:
        pp = [x for x in paras if x['attr'].get('Num') == p['項']]
        if not pp: return '条まで', '項が見つからない'
        para = pp[0]
    else:
        if len(paras) != 1: return '条まで', '項の指定なしで号(項が複数)'
        para = paras[0]
    if p['号'] is None: return '項まで', '号の指定なし'
    if not [x for x in kids(para, 'Item') if x['attr'].get('Num') == p['号']]:
        return ('項まで' if p['項'] else '条まで'), '号が見つからない'
    return '号まで一致', ('項の指定なし(単一項)' if p['項'] is None else '')
