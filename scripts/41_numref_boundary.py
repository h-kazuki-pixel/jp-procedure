"""A1: 「番号の参照だけ」を、変わった漢数字の直後が 条・項・号 のものに限って数え直す。A2: 近さ 0.5〜0.7 の抜き取り。"""
import re, difflib, pandas as pd
SEED = 20261118
KAN = '〇一二三四五六七八九十百千'; WORDS = ['並びに', 'から', 'まで', '及び', '又は']
TOK = re.compile('|'.join(WORDS) + f'|[{KAN}]+|.', re.S); NUM = re.compile(f'^[{KAN}]+$')
c = pd.read_csv('out/fix_compare.csv', dtype=str, keep_default_na=False)
rest = pd.read_csv('out/fix_rest.csv', dtype=str, keep_default_na=False)
sw = pd.read_csv('out/fix_swapped.csv', dtype=str, keep_default_na=False)
def check(a, b):
    """戻り値: (漢数字の変わった箇所の数, そのうち直後が条・項・号でない数)"""
    ta, tb = TOK.findall(a), TOK.findall(b); n = bad = 0
    for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        if o[0] == 'equal': continue
        for toks, lo, hi in ((ta, o[1], o[2]), (tb, o[3], o[4])):
            for k in range(lo, hi):
                if NUM.match(toks[k]):
                    n += 1
                    if (toks[k + 1] if k + 1 < len(toks) else '') not in ('条', '項', '号'): bad += 1
    return n, bad
nr = rest[rest.番号の参照だけ == 'True'].copy()
r = [check(a, b) for a, b in zip(nr.旧文言, nr.新文言)]
nr['漢数字の差'] = [x[0] for x in r]; nr['直後が条項号でない'] = [x[1] for x in r]
keep = nr.直後が条項号でない == 0
print('# A1. 「番号の参照だけ」の数え直し(変わった漢数字は、旧・新の両側とも、すべて直後が「条」「項」「号」であること)')
print(f'  前: 番号の参照だけ {len(nr)} / それ以外 {int((rest.番号の参照だけ != "True").sum())}')
print(f'  後: 番号の参照だけ {int(keep.sum())} / それ以外 {int((rest.番号の参照だけ != "True").sum()) + int((~keep).sum())}  (移した行 {int((~keep).sum())}, 異なる要素 {nr[~keep].groupby(["law_id", "条キー", "根拠条項号"]).ngroups})')
print(f'  後の「番号の参照だけ」のうち、漢数字の差が無い行(「及び→から」「、」の出入りなどだけ): {int((keep & (nr.漢数字の差 == 0)).sum())}  ← この規則では漢数字の条件に当たらないので残した')
print(f'  前に「数の変更の疑い」とした {int((nr.数の変更の疑い == "True").sum())} 行のうち、後も番号の参照だけに残った行: {int((keep & (nr.数の変更の疑い == "True")).sum())}')
def ex(a, b, w=12):
    ta, tb = TOK.findall(a), TOK.findall(b)
    o = [o for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes() if o[0] != 'equal'][0]
    return f'…{"".join(ta[max(0, o[1]-w):o[1]])}[{"".join(ta[o[1]:o[2]])}→{"".join(tb[o[3]:o[4]])}]{"".join(ta[o[2]:o[2]+w])}…'
print('  移した例(先頭 8 要素):')
for _, x in nr[~keep].drop_duplicates(['law_id', '条キー', '根拠条項号']).head(8).iterrows(): print(f'    {x.法令名} {x.根拠条項号}: {ex(x.旧文言, x.新文言)}')
nr['A1後'] = keep.map({True: '文言が変わった: 番号の参照だけ', False: '文言が変わった: それ以外'})
c['A1後'] = c.直した後
c.loc[c.手続ID.isin(nr[~keep].手続ID), 'A1後'] = '文言が変わった: それ以外'
assert int((c.A1後 != c.直した後).sum()) == int((~keep).sum())
N = len(c); vc = c.A1後.value_counts()
order = ['文言が同じ', '文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '入れ替わった→移った', '入れ替わった→消えた', '入れ替わった→判定できない',
         '無くなった→移った', '無くなった→消えた', '無くなった→判定できない', '比べられない']
print(f'\n  A1 の後の改正の追跡の表(47,352 に対する比)\n| 区分 | 行 | 比 |\n|---|---:|---:|')
for k in order: print(f'| {k} | {vc.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
print(f'| 計 | {int(vc.sum()):,} | {vc.sum()/N*100:.2f}% |')
c.to_csv('out/fix2_compare.csv', index=False); nr.to_csv('out/fix2_numref.csv', index=False)

# ---- A2
both = pd.concat([sw.assign(元='入れ替わった'), rest.assign(元='残り')], ignore_index=True)
both['近さ_f'] = both.同じ番号の近さ.astype(float)
B = both[(both.近さ_f >= 0.5) & (both.近さ_f < 0.7)]
lab = c.set_index('手続ID').A1後
s = B.sample(n=min(30, len(B)), random_state=SEED)
print(f'\n# A2. 入れ替わりの判定に使った近さ(同じ番号の旧・新)が 0.5 以上 0.7 未満: 母数 {len(B)} 行 (うち 0.6 未満=入れ替わった {int((B.近さ_f < 0.6).sum())}, 0.6 以上 {int((B.近さ_f >= 0.6).sum())}) → {len(s)} 行 (種 {SEED})')
out = pd.DataFrame({'区分': s.手続ID.map(lab), '手続ID': s.手続ID, '手続名': s.手続名, '法令ID': s.law_id, '法令名': s.法令名, '条項号': s.根拠条項号,
    'e-Gov URL': 'https://laws.e-gov.go.jp/law/' + s.law_id, '2025-11-01 の文言': s.旧文言, '2026-11-18 の文言': s.新文言, '比べた深さ': s.深さ,
    '移った先': s.get('移った先', '').fillna(''), '近さ': s.近さ_f.map(lambda v: f'{v:.3f}'),
    '備考': ['文言は照合した深さの要素の全文(番号を含み、空白・改行を除く)。近さは同じ番号の旧・新の近さ(入れ替わりの判定に使った値)'
           + (f'。移った先の近さ {m}' if isinstance(m, str) and m else '') for m in s.get('近さ', pd.Series([''] * len(s), index=s.index)).where(s.元 == '入れ替わった', '')]})
out.to_csv('review-boundary-06.csv', index=False, encoding='utf-8-sig')
print('  区分の内訳:', out.区分.value_counts().to_dict(), ' 法令の数', out.法令ID.nunique())
