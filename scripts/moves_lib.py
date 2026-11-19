"""移った先の探し方(30_moves.py と 40_fix.py で共通)。"""
import sys, re, difflib
sys.path.insert(0, 'scripts'); import egov
from clause import article_index, kids, text
HI, LO = 0.90, 0.60          # 近さ ≥ HI なら「移った」、最良でも < LO なら「消えた」、その間は「判定できない」
MINLEN = 10                  # 番号を除いた元の文言がこの字数未満なら「判定できない」
TIE = 0.01                   # 最良と 2 番目の差がこれ未満(どちらも ≥ HI)なら「判定できない」
WS = re.compile(r'\s+')
TITLE = {'Article': 'ArticleTitle', 'Paragraph': 'ParagraphNum', 'Item': 'ItemTitle'}
TAG = {'条': 'Article', '項': 'Paragraph', '号': 'Item'}
def body_txt(n):  # 番号(条名・項番号・号名)を除いた文言。空白・改行は除く。ルビの読みは text() が除く
    return WS.sub('', ''.join(text(c) for c in n.get('children', []) if not (isinstance(c, dict) and c['tag'] == TITLE[n['tag']])))
def load(lid, asof):
    b = egov.get(f'/law_data/{lid}', {'asof': asof, 'response_format': 'json', 'json_format': 'full'}, offline=True)
    if b.get('_status') != 200: return None
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    return article_index(lb)
def art_label(k):
    sup, num = k; s = num.split('_')
    return ('附則' if sup else '') + f'第{s[0]}条' + ''.join(f'の{x}' for x in s[1:])
def sub_label(n): s = (n or '?').split('_'); return s[0] + ''.join(f'の{x}' for x in s[1:])
def elements(idx, tag):
    """(番号ラベル, 位置キー, 要素) を列挙。位置キーは (附則, 条, 項, 号)。"""
    for k, a in idx.items():
        if tag == 'Article': yield art_label(k), (k[0], k[1], None, None), a; continue
        for p in kids(a, 'Paragraph'):
            pn = p['attr'].get('Num')
            if tag == 'Paragraph': yield f'{art_label(k)}第{sub_label(pn)}項', (k[0], k[1], pn, None), p; continue
            for it in kids(p, 'Item'):
                yield f'{art_label(k)}第{sub_label(pn)}項第{sub_label(it["attr"].get("Num"))}号', (k[0], k[1], pn, it['attr'].get('Num')), it
def old_elem(idx, p, depth):
    a = idx.get((p['附則'], p['条']))
    if a is None: return None, None
    if depth == '条': return a, (p['附則'], p['条'], None, None)
    paras = kids(a, 'Paragraph')
    para = [x for x in paras if x['attr'].get('Num') == p['項']] if p['項'] else (paras if len(paras) == 1 else [])
    if not para: return None, None
    pn = para[0]['attr'].get('Num')
    if depth == '項': return para[0], (p['附則'], p['条'], pn, None)
    it = [x for x in kids(para[0], 'Item') if x['attr'].get('Num') == p['号']]
    return (it[0], (p['附則'], p['条'], pn, p['号'])) if it else (None, None)
def sim(a, b):
    if not a or not b: return 0.0
    if 2 * min(len(a), len(b)) / (len(a) + len(b)) < LO: return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.real_quick_ratio() < LO or sm.quick_ratio() < LO: return 0.0
    return sm.ratio()
def judge(oi, ni, p, depth, cache, exclude_own=False):
    """旧版 oi の要素(p, depth)の移った先を、新版 ni の同じ深さの要素から探す。cache は法令ごとの dict。
    exclude_own=True なら、元と同じ番号(位置)の要素を候補から外す(既定は外さない=これまでと同じ)。"""
    r = {'判定': '', '移った先': '', '近さ': '', '2番目の近さ': '', '理由': '', '元の文言(番号除く)': '', '移った先の文言(番号除く)': ''}
    if oi is None or ni is None: r.update(判定='判定できない', 理由='本文が取れない'); return r
    oe, opos = old_elem(oi, p, depth)
    if oe is None: r.update(判定='判定できない', 理由='旧版で要素が取れない'); return r
    a = body_txt(oe); r['元の文言(番号除く)'] = a
    if len(a) < MINLEN: r.update(判定='判定できない', 理由=f'元の文言が短い({len(a)}字)'); return r
    tag = TAG[depth]
    if tag not in cache: cache[tag] = [(lab, pos, body_txt(e)) for lab, pos, e in elements(ni, tag)]
    if 'old_' + tag not in cache: cache['old_' + tag] = {pos: body_txt(e) for _, pos, e in elements(oi, tag)}
    oldtxt = cache['old_' + tag]
    sc = sorted(((1.0 if a == t else sim(a, t), lab, pos, t) for lab, pos, t in cache[tag] if not (exclude_own and pos == opos)), key=lambda x: -x[0])
    best = sc[0] if sc else (0.0, '', None, '')
    second = sc[1][0] if len(sc) > 1 else 0.0
    r['近さ'] = f'{best[0]:.3f}'; r['2番目の近さ'] = f'{second:.3f}'; r['移った先の位置'] = best[2]
    if best[0] >= HI:
        r['移った先'] = best[1]; r['移った先の文言(番号除く)'] = best[3]
        prev = oldtxt.get(best[2], '')
        if prev and (prev == best[3] or sim(prev, best[3]) >= HI):
            r.update(判定='判定できない', 理由='近い文言の要素が旧版でも同じ番号にあった(移動ではなく、もともと似た文言)')
        elif second >= HI and best[0] - second < TIE:
            r.update(判定='判定できない', 理由=f'近い候補が複数(最良 {best[0]:.3f} / 2番目 {second:.3f})')
        else:
            r.update(判定='移った', 理由='文言が同じ' if best[0] == 1.0 else '文言が近い')
    elif best[0] < LO: r.update(判定='消えた', 理由=('同じ深さの候補が無い' if not sc else '近さの上限の見積もり(字数比・quick_ratio)が全候補で 0.6 未満' if best[0] == 0.0 else '最も近い候補が 0.6 未満'))
    else: r.update(判定='判定できない', 理由=f'最も近い候補が {LO}〜{HI} の間'); r['移った先'] = best[1]; r['移った先の文言(番号除く)'] = best[3]
    return r
