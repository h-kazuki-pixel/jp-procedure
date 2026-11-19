"""分け方の直し: 「文言が変わった」を、入れ替わった / 番号の参照だけ / それ以外 に分け、改正の追跡の表を作り直す。本文はキャッシュから読むだけ。"""
import sys, re, json, difflib, time, pandas as pd
sys.path.insert(0, 'scripts')
from moves_lib import HI, LO, load, judge
OLD, NEW = '2025-11-01', '2026-11-18'
SWAP = 0.60                    # 同じ番号の旧・新の近さがこれ未満なら「入れ替わった」
t0 = time.time()
c = pd.read_csv('out/amend_compare.csv', dtype=str, keep_default_na=False)
mv = pd.read_csv('out/moves.csv', dtype=str, keep_default_na=False)
N = len(c); assert N == 47352
ch = c[c.区分 == '文言が変わった'].copy()
print(f'# 対象: 「文言が変わった」{len(ch)} 行 / 異なる要素 {ch.groupby(["law_id", "条キー", "根拠条項号"]).ngroups} / 法令 {ch.law_id.nunique()}')

# ---- 1. 同じ番号の旧・新の近さ
pair = {}
def ratio(a, b):
    k = (a, b)
    if k not in pair: pair[k] = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    return pair[k]
ch['同じ番号の近さ'] = [ratio(a, b) for a, b in zip(ch.旧文言, ch.新文言)]
print(f'  近さの計算: {len(pair)} 組, {time.time()-t0:.0f} 秒')
print(f'\n# 1. 同じ番号の旧い文言と新しい文言の近さ(difflib ratio, autojunk=False。比べた文言は前回と同じ: 照合した深さの要素の全文、番号を含み空白・改行を除く)')
print('  近さの分布(行):'); print(pd.cut(ch.同じ番号の近さ, [0, .2, .4, .6, .8, .9, .95, .99, 1.0], include_lowest=True, right=False).value_counts().sort_index().to_string())
sw = ch[ch.同じ番号の近さ < SWAP].copy()
print(f'  近さ < {SWAP} の行(入れ替わった): {len(sw)} 行 / 異なる要素 {sw.groupby(["law_id", "条キー", "根拠条項号"]).ngroups} / 法令 {sw.law_id.nunique()}')
res = {}
for lid, g in sw.groupby('law_id'):
    oi, ni = load(lid, OLD), load(lid, NEW); cache = {}
    for i in g.index:
        key = (lid, c.深さ[i], c.根拠条項号[i], c.分解_追加[i])
        if key not in res: res[key] = judge(oi, ni, json.loads(c.分解_追加[i]), c.深さ[i], cache)
        res[i] = res[key]
for col in ['判定', '移った先', '近さ', '2番目の近さ', '理由', '元の文言(番号除く)', '移った先の文言(番号除く)']:
    sw[col] = [res[i][col] for i in sw.index]
from moves_lib import old_elem
own = {}
for lid, g in sw.groupby('law_id'):
    oi = load(lid, OLD)
    for i in g.index: own[i] = old_elem(oi, json.loads(c.分解_追加[i]), c.深さ[i])[1] if oi is not None else None
sw['移った先が同じ番号'] = [res[i]['判定'] == '移った' and res[i].get('移った先の位置') is not None and tuple(res[i]['移った先の位置']) == own[i] for i in sw.index]
vc = sw.判定.value_counts()
print(f'  前回と同じ方法(scripts/moves_lib.py: 移った ≥ {HI} / 消えた < {LO} / その間などは判定できない)で移った先を探した結果:')
for k in ['移った', '消えた', '判定できない']: print(f'    {k}: {vc.get(k, 0)} 行')
print('  判定 × 理由'); print(sw.assign(理由=sw.理由.str.replace(r'\(最良.*\)', '', regex=True)).groupby(['判定', '理由']).size().to_string())
print('  深さ × 判定'); print(pd.crosstab(sw.深さ, sw.判定).to_string())
print(f'  「移った」のうち、移った先が元と同じ番号(同じ位置)になった行: {int(sw.移った先が同じ番号.sum())}')
print('  入れ替わった行の多い法令:'); print(sw.groupby('法令名').size().sort_values(ascending=False).head(10).to_string())

# ---- 2. 残りを「番号の参照だけ」と「それ以外」に
KAN = '〇一二三四五六七八九十百千'
WORDS = ['並びに', 'から', 'まで', '及び', '又は']
TOK = re.compile('|'.join(WORDS) + f'|[{KAN}]+|.', re.S)
OKTOK = re.compile(f'^(?:[{KAN}]+|第|条|項|号|の|、|' + '|'.join(WORDS) + ')$')
def toks(s): return TOK.findall(s)
def num_only(a, b):
    ta, tb = toks(a), toks(b)
    ops = [o for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes() if o[0] != 'equal']
    seg = [t for o in ops for t in ta[o[1]:o[2]] + tb[o[3]:o[4]]]
    return bool(ops) and all(OKTOK.match(t) for t in seg), len(ops)
REF = {'第', '条', '項', '号', 'の'}
def amount_like(a, b):
    """番号の参照だけ のうち、差が漢数字だけで、直前が 第・の でなく、直後が 条・項・号・の でない箇所がある → 数(金額・日数など)の変更の疑い"""
    ta, tb = toks(a), toks(b)
    for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        if o[0] == 'equal': continue
        seg = ta[o[1]:o[2]] + tb[o[3]:o[4]]
        if seg and all(re.fullmatch(f'[{KAN}]+', t) for t in seg):
            na = ta[o[2]] if o[2] < len(ta) else ''; nb = tb[o[4]] if o[4] < len(tb) else ''
            pa = ta[o[1] - 1] if o[1] > 0 else ''; pb = tb[o[3] - 1] if o[3] > 0 else ''
            if na not in REF and nb not in REF and pa not in ('第', 'の') and pb not in ('第', 'の'): return True
    return False
rest = ch[ch.同じ番号の近さ >= SWAP].copy()
r2 = [num_only(a, b) for a, b in zip(rest.旧文言, rest.新文言)]
rest['番号の参照だけ'] = [x[0] for x in r2]; rest['違う箇所の数'] = [x[1] for x in r2]
print(f'\n# 2. 残りの「文言が変わった」{len(rest)} 行を分ける')
print(f'  差の部分(語の単位で比べ、旧・新の両側)が 漢数字 / 第 / 条 / 項 / 号 / の / 、 / {" / ".join(WORDS)} だけでできている = 番号の参照だけ')
print(f'  語の単位: 「{"」「".join(WORDS)}」と漢数字の連なりを 1 語、ほかは 1 字を 1 語とした')
print(f'  番号の参照だけ: {int(rest.番号の参照だけ.sum())} 行 / 異なる要素 {rest[rest.番号の参照だけ].groupby(["law_id", "条キー", "根拠条項号"]).ngroups}')
print(f'  それ以外: {int((~rest.番号の参照だけ).sum())} 行 / 異なる要素 {rest[~rest.番号の参照だけ].groupby(["law_id", "条キー", "根拠条項号"]).ngroups}')
def ex(a, b, w=15):
    ta, tb = toks(a), toks(b)
    o = [o for o in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes() if o[0] != 'equal'][0]
    pre = ''.join(ta[max(0, o[1]-w):o[1]]); post = ''.join(ta[o[2]:o[2]+w])
    return f'…{pre}[{"".join(ta[o[1]:o[2]])}→{"".join(tb[o[3]:o[4]])}]{post}…'
rest['数の変更の疑い'] = [r.番号の参照だけ and amount_like(r.旧文言, r.新文言) for r in rest.itertuples()]
print(f'  番号の参照だけ のうち 数(金額・日数など)の変更の疑い: {int(rest.数の変更の疑い.sum())} 行 / 異なる要素 {rest[rest.数の変更の疑い].groupby(["law_id", "条キー", "根拠条項号"]).ngroups}'
      f'  (差が漢数字だけで、その直前が旧・新とも 第・の でなく、直後が旧・新とも 第・条・項・号・の でない箇所がある行。分類は変えていない)')
print('  深さ × 分類'); print(pd.crosstab(rest.深さ, rest.番号の参照だけ.map({True: '番号の参照だけ', False: 'それ以外'}).rename('分類')).to_string())
print('  数の変更の疑い の例(先頭 10 要素、最初の違う箇所):')
for _, r in rest[rest.数の変更の疑い].drop_duplicates(['law_id', '条キー', '根拠条項号']).head(10).iterrows(): print(f'    {r.法令名} {r.根拠条項号}: {ex(r.旧文言, r.新文言)}')
print('  番号の参照だけ の例(先頭 5 要素、最初の違う箇所):')
for _, r in rest[rest.番号の参照だけ].drop_duplicates(['law_id', '条キー', '根拠条項号']).head(5).iterrows(): print(f'    {r.法令名} {r.根拠条項号}: {ex(r.旧文言, r.新文言)}')
print('  それ以外 の例(先頭 5 要素、最初の違う箇所):')
for _, r in rest[~rest.番号の参照だけ].drop_duplicates(['law_id', '条キー', '根拠条項号']).head(5).iterrows(): print(f'    {r.法令名} {r.根拠条項号}: {ex(r.旧文言, r.新文言)}')

# ---- 3. 移った のうち 0.90 ≤ 近さ < 0.95
L = []
for src, df in (('無くなった', mv[mv.判定 == '移った']), ('入れ替わった', sw[sw.判定 == '移った'])):
    x = df[(df.近さ.astype(float) >= 0.90) & (df.近さ.astype(float) < 0.95)]
    L.append(pd.DataFrame({'出どころ': src, '手続ID': x.手続ID, '手続名': x.手続名, '法令ID': x.law_id, '法令名': x.法令名, '条項号': x.根拠条項号, '比べた深さ': x.深さ,
                           '移った先': x.移った先, '近さ': x.近さ, '2番目の近さ': x['2番目の近さ'], 'e-Gov URL': 'https://laws.e-gov.go.jp/law/' + x.law_id,
                           '2025-11-01 の文言(番号除く)': x['元の文言(番号除く)'], '2026-11-18 の移った先の文言(番号除く)': x['移った先の文言(番号除く)']}))
L = pd.concat(L, ignore_index=True).sort_values(['出どころ', '法令ID', '条項号', '手続ID'])
L.to_csv('review-moves-090-095.csv', index=False, encoding='utf-8-sig')
print(f'\n# 3. 「移った」のうち 0.90 ≤ 近さ < 0.95: {len(L)} 行 / 異なる要素 {L.groupby(["法令ID", "条項号"]).ngroups}  内訳 {L.出どころ.value_counts().to_dict()} → review-moves-090-095.csv')
for _, r in L.drop_duplicates(['法令ID', '条項号']).iterrows(): print(f'    [{r.出どころ}] {r.法令名} {r.条項号} → {r.移った先}  {r.近さ}')

# ---- 4. 直した後の区分
c['直した後'] = c.区分
c.loc[rest.index, '直した後'] = rest.番号の参照だけ.map({True: '文言が変わった: 番号の参照だけ', False: '文言が変わった: それ以外'})
c.loc[sw.index, '直した後'] = '入れ替わった→' + sw.判定
c.loc[mv.index if False else c.区分 == 'その条・項・号が無くなった', '直した後'] = None
m2 = mv.set_index(['手続ID'])['判定']
c.loc[c.区分 == 'その条・項・号が無くなった', '直した後'] = '無くなった→' + c.loc[c.区分 == 'その条・項・号が無くなった', '手続ID'].map(m2)
assert c.直した後.notna().all()
order = ['文言が同じ', '文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '入れ替わった→移った', '入れ替わった→消えた', '入れ替わった→判定できない',
         '無くなった→移った', '無くなった→消えた', '無くなった→判定できない', '比べられない']
vc = c.直した後.value_counts()
assert set(vc.index) <= set(order), set(vc.index) - set(order)
print(f'\n# 4. 直した後の区分(法令の単位で知らせが行く行 {N:,} に対する比)')
print('| 区分 | 行 | 比 |\n|---|---:|---:|')
for k in order: print(f'| {k} | {vc.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
print(f'| 計 | {int(vc.sum()):,} | {vc.sum()/N*100:.2f}% |')
diff = N - vc.get('文言が同じ', 0) - vc.get('比べられない', 0)
print(f'  参考: 条・項・号の単位で文言に違いがあった行(同じ・比べられない を除く) {diff:,} ({diff/N*100:.2f}%)')
mvsame = int((mv[mv.判定 == '移った'].近さ == '1.000').sum()); swsame = int((sw[sw.判定 == '移った'].近さ == '1.000').sum())
print(f'  移った のうち 移った先の文言が同じ(近さ 1.000): 無くなった→移った {mvsame} / 入れ替わった→移った {swsame}')
print('\n  深さ × 直した後の区分'); print(pd.crosstab(c.直した後, c.深さ).reindex([k for k in order if k in vc.index]).to_string())
# 府省庁別
g = pd.crosstab(c.所管府省庁, c.直した後).reindex(columns=[k for k in order if k in vc.index], fill_value=0)
g.insert(0, '比べた行', g.sum(axis=1))
g = g.sort_values('文言が変わった: それ以外', ascending=False)
print('\n  所管府省庁ごと(行。割合は その府省庁の比べた行 に対する「文言が変わった: それ以外」の比)')
cols = ['比べた行', '文言が同じ', '文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '入れ替わった→移った', '入れ替わった→消えた', '入れ替わった→判定できない', '無くなった→移った', '無くなった→消えた', '無くなった→判定できない', '比べられない']
cols = [k for k in cols if k in g.columns]
print('| 所管府省庁 | ' + ' | '.join(cols) + ' | それ以外の割合 |\n|---|' + '---:|' * (len(cols) + 1))
for k, r in g.iterrows(): print(f'| {k} | ' + ' | '.join(f'{int(r[x]):,}' for x in cols) + f' | {r["文言が変わった: それ以外"]/r.比べた行*100:.2f}% |')
s = g.sum(); print('| 計 | ' + ' | '.join(f'{int(s[x]):,}' for x in cols) + f' | {s["文言が変わった: それ以外"]/s.比べた行*100:.2f}% |')
c.to_csv('out/fix_compare.csv', index=False); sw.to_csv('out/fix_swapped.csv', index=False); rest.to_csv('out/fix_rest.csv', index=False)
print(f'\n所要 {time.time()-t0:.0f} 秒')
