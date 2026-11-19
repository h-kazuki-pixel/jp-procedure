"""改正の記録の判定の決まり(第 5 版、fix-report-5)を 1 か所にまとめたもの。
40〜45 の各スクリプトが順に足してきた決まりを、1 つの要素について一度に当てる。毎週の追跡(70_weekly_track.py)はこれを使う。"""
import re, difflib
from moves_lib import elements, old_elem, sim, TAG, HI, LO, MINLEN
from clause import kids, text
VERSION = '5'
TIE = 0.01
WS = re.compile(r'\s+')
TITLES = {'ArticleTitle', 'ParagraphNum', 'ItemTitle'} | {f'Subitem{i}Title' for i in range(1, 11)}
def _t2(n):
    if isinstance(n, str): return n
    if n.get('tag') in TITLES or n.get('tag') == 'Rt': return ''
    return ''.join(_t2(c) for c in n.get('children', []))
def body(n):
    """近さを測る文言: 条名・項番号・号名(どの深さでも)とルビの読みと空白・改行を除く。文の中の参照の番号と見出しは残す。"""
    return WS.sub('', _t2(n))
def full(n):
    """同じか違うかを見る文言: 番号を含む全文から空白・改行を除いたもの(ルビの読みは除く)。"""
    return WS.sub('', text(n))
# ---- 「番号の参照だけ」(40 の num_only と、41 の A1 の数え直し)
KAN = '〇一二三四五六七八九十百千'; WORDS = ['並びに', 'から', 'まで', '及び', '又は']
TOK = re.compile('|'.join(WORDS) + f'|[{KAN}]+|.', re.S); NUMT = re.compile(f'^[{KAN}]+$')
OKTOK = re.compile(f'^(?:[{KAN}]+|第|条|項|号|の|、|' + '|'.join(WORDS) + ')$')
def numref_only(a, b):
    ta, tb = TOK.findall(a), TOK.findall(b)
    ops = [o for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes() if o[0] != 'equal']
    seg = [t for o in ops for t in ta[o[1]:o[2]] + tb[o[3]:o[4]]]
    if not (ops and all(OKTOK.match(t) for t in seg)): return False
    for o in ops:
        for toks, lo, hi in ((ta, o[1], o[2]), (tb, o[3], o[4])):
            for k in range(lo, hi):
                if NUMT.match(toks[k]) and (toks[k + 1] if k + 1 < len(toks) else '') not in ('条', '項', '号'): return False
    return True
def caption(idx, p):
    a = idx.get((p['附則'], p['条']))
    if a is None: return None
    cs = kids(a, 'ArticleCaption'); return WS.sub('', text(cs[0])) if cs else ''
def capsim(a, b):
    a = re.sub(r'^（(.*)）$', r'\1', a or ''); b = re.sub(r'^（(.*)）$', r'\1', b or '')
    if not a and not b: return None
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
def search(oi, ni, a, opos, depth, cache):
    """別の番号の候補を探す。戻り値: r1, 最も近い候補の位置, 並んだ候補 [(ラベル, 位置, 近さ)], 最も近い候補が旧版でも同じ番号に近い文言か"""
    tag = TAG[depth]
    if tag not in cache:
        cache[tag] = [(lab, pos, body(e)) for lab, pos, e in elements(ni, tag)]
        cache['old_' + tag] = {pos: body(e) for _, pos, e in elements(oi, tag)}
    sc = sorted(((1.0 if a == t else sim(a, t), lab, pos) for lab, pos, t in cache[tag] if pos != opos), key=lambda x: -x[0])
    if not sc: return 0.0, None, [], False
    best = sc[0]; near = [(lab, pos, s) for s, lab, pos in sc if best[0] - s < TIE]
    prev = cache['old_' + tag].get(best[2], ''); tb = next(t for lab, pos, t in cache[tag] if pos == best[2])
    return best[0], best[2], near, bool(prev) and (prev == tb or sim(prev, tb) >= HI)
def classify(oi, ni, p, depth, cache):
    """1 つの要素を判定する。p は {附則, 条, 項, 号}、depth は 条/項/号。
    戻り値: None(文言が同じ)または dict(kind, r0, r1, moved, cands, rule)。比べられないときは kind='比べられない'。"""
    oe, opos = old_elem(oi, p, depth)
    if oe is None: return {'kind': '比べられない', 'rule': '旧版で要素が取れない'}
    ne, npos = old_elem(ni, p, depth)
    if ne is None and depth != '条' and p['項'] is None and ni.get((p['附則'], p['条'])) is not None and len(kids(ni[(p['附則'], p['条'])], 'Paragraph')) > 1:
        return {'kind': '比べられない', 'rule': '新版で項が複数になり、項の指定なしの号を決められない'}
    a = body(oe)
    r = {'r0': None, 'r1': None, 'moved': None, 'cands': [], 'rule': ''}
    if ne is None:   # 無くなった
        if len(a) < MINLEN: return {**r, 'kind': '無くなった→判定できない', 'rule': '元の文言が短い'}
        r1, bpos, near, prev = search(oi, ni, a, opos, depth, cache); r['r1'] = r1
        if r1 >= HI:
            if prev: return {**r, 'kind': '無くなった→判定できない', 'rule': '旧版でも同じ番号に近い文言'}
            if len(near) > 1: return {**r, 'kind': '無くなった→移った先が一つに決まらない', 'cands': near, 'rule': '候補が並ぶ'}
            return {**r, 'kind': '無くなった→移った', 'moved': bpos, 'rule': '移った'}
        if r1 < LO: return {**r, 'kind': '無くなった→移った先なし', 'rule': '最も近い候補が 0.6 未満'}
        return {**r, 'kind': '無くなった→判定できない', 'rule': '最も近い候補が 0.6〜0.9'}
    fa, fb = full(oe), full(ne)
    if fa == fb: return None
    b = body(ne); r0 = 1.0 if a == b else difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(); r['r0'] = r0
    wording = '文言が変わった: 番号の参照だけ' if numref_only(fa, fb) else '文言が変わった: それ以外'
    if r0 >= 0.90: return {**r, 'kind': wording, 'rule': '(1)'}
    r1 = None
    if len(a) >= MINLEN:
        r1, bpos, near, prev = search(oi, ni, a, opos, depth, cache); r['r1'] = r1
        if r1 >= 0.90 and r1 - r0 >= 0.05 and not prev:
            if len(near) > 1: return {**r, 'kind': '入れ替わった→移った先が一つに決まらない', 'cands': near, 'rule': '(2) 候補が並ぶ'}
            return {**r, 'kind': '入れ替わった→移った', 'moved': bpos, 'rule': '(2)'}
    if depth == '条':
        co, cn = caption(oi, p), caption(ni, p)
        if co != cn and (capsim(co, cn) if capsim(co, cn) is not None else 1.0) < 0.5: return {**r, 'kind': '入れ替わった→移った先なし', 'rule': '(3)'}
    if r0 < 0.6: return {**r, 'kind': '大きく書き換わった', 'rule': '(4) r0 < 0.6'}
    return {**r, 'kind': wording, 'rule': '(4) r0 ≥ 0.6'}
