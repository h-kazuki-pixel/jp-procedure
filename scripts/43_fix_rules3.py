"""「入れ替わった」の決まりの直し(fix-report-3)。本文は読み直さず、42 の結果(out/fix3_*.csv)だけを使う。
r0 = 同じ番号の旧・新の近さ(40_fix の値: 照合した深さの要素の全文、番号を含み空白・改行を除く)
r1 = 別の番号で最も近いものの近さ(42 の (a) の探索の最良候補。moves_lib.judge(exclude_own=True)、番号を除いた文言)"""
import re, difflib, pandas as pd
N = 47352
c = pd.read_csv('out/fix3_compare.csv', dtype=str, keep_default_na=False)
ch = pd.read_csv('out/fix3_changed.csv', dtype=str, keep_default_na=False).set_index('手続ID')
assert len(c) == N and len(ch) == 2737
ch['r0'] = ch.同じ番号の近さ.astype(float)
ch['r1'] = pd.to_numeric(ch.a_近さ.replace('', None))
def cap(s): return re.sub(r'^（(.*)）$', r'\1', re.sub(r'\s+', '', s))   # 外側の全角かっこを外して比べる
def capsim(a, b):
    a, b = cap(a), cap(b)
    if not a and not b: return None   # どちらにも見出しが無い
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
art = ch.深さ == '条'
ch['見出しの近さ'] = [capsim(o, n) if a else None for o, n, a in zip(ch.旧見出し, ch.新見出し, art)]
capchg = art & (ch.旧見出し != ch.新見出し)
def rule(r, cc):
    if r.r0 >= 0.90: return '文言が変わった', '(1) r0 ≥ 0.90'
    if pd.notna(r.r1) and r.r1 >= 0.90 and r.r1 - r.r0 >= 0.05: return '入れ替わった→移った', '(2)'
    if cc and r.見出しの近さ < 0.5: return '入れ替わった→移った先なし', '(3)'
    return ('大きく書き換わった', '(4) r0 < 0.6') if r.r0 < 0.6 else ('文言が変わった', '(4) r0 ≥ 0.6')
lab = [rule(r, cc) for (_, r), cc in zip(ch.iterrows(), capchg)]
ch['新区分3'] = [x[0] for x in lab]; ch['当てた決まり'] = [x[1] for x in lab]
m = ch.新区分3 == '文言が変わった'
ch.loc[m, '新区分3'] = c.set_index('手続ID').loc[ch.index[m], 'A1後'].where(lambda s: s.str.startswith('文言が変わった'), '文言が変わった: それ以外')
# A1後 が「入れ替わった…」だった行は A1 の細分(番号の参照だけ/それ以外)が無い。r0 ≥ 0.6 なのに A1後が入れ替わった、の行は無いはずだが確かめる
bad = m & ~c.set_index('手続ID').loc[ch.index, 'A1後'].str.startswith('文言が変わった').values
print(f'# 対象: 文言が変わった 2,737 行(42 の時点)。A1 の細分が無い「文言が変わった」行: {int(bad.sum())}')
print(f'  r1 が無い行(元の文言が短く探していない): {int(ch.r1.isna().sum())}')
print(f'  条を比べた行 {int(art.sum())}、見出しが変わった行 {int(capchg.sum())}、そのうち見出しの近さ < 0.5: {int((capchg & (ch.見出しの近さ < 0.5)).sum())}')
one = capchg & ((ch.旧見出し == '') != (ch.新見出し == ''))
print(f'  見出しが変わった行のうち、片方にだけ見出しがある行: {int(one.sum())}(近さ 0 として扱った)。(3) に当たった行のうち片方だけ: {int((one & (ch.当てた決まり == "(3)")).sum())}')
print('\n# 当てた決まり(行)'); print(ch.当てた決まり.value_counts().to_string())
mv2 = ch.新区分3 == '入れ替わった→移った'
print(f'\n  (2) で移った {int(mv2.sum())} 行のうち、42 の探索の判定: {ch[mv2].a_判定.value_counts().to_dict()}')
print('   (42 の探索で「判定できない」だった理由:', ch[mv2 & (ch.a_判定 != "移った")].a_理由.value_counts().to_dict(), ')')
nm = (ch.a_判定 == '移った') & ~mv2
print(f'  42 で (a) に当たったが (2) に当たらない行: {int(nm.sum())}  内訳 {ch[nm].当てた決まり.value_counts().to_dict()}')
ch['移った先3'] = ch.a_移った先.where(mv2, ''); ch['移った先の近さ3'] = ch.a_近さ.where(mv2, '')
# 全体の表
c = c.set_index('手続ID')
c['新区分_前'] = c.新区分; c.loc[ch.index, '新区分'] = ch.新区分3
c.loc[ch.index, '移った先'] = ch.移った先3; c.loc[ch.index, '移った先の近さ'] = ch.移った先の近さ3
c.loc[ch.index, 'r0'] = ch.r0; c.loc[ch.index, 'r1'] = ch.r1; c.loc[ch.index, '見出しの近さ'] = ch.見出しの近さ; c.loc[ch.index, '当てた決まり'] = ch.当てた決まり
v = c.移った先の近さ.replace('', '0').astype(float)
keep_manual = c.人の確認日 != ''
c['確かさ低'] = c.新区分.str.endswith('→移った') & (v >= 0.90) & (v < 0.95) & ~keep_manual
order = ['文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '大きく書き換わった', '入れ替わった→移った', '入れ替わった→移った先なし',
         '無くなった→移った', '無くなった→移った先なし', '無くなった→判定できない']
vc = c.新区分.value_counts(); assert set(vc.index) <= set(order) | {'文言が同じ', '比べられない'}, set(vc.index)
print(f'\n# 直した後の表(47,352 に対する比)\n| 区分 | 行 | うち確かさ低 | 前(fix-report-2) | 比 |\n|---|---:|---:|---:|---:|')
pv = c.新区分_前.value_counts()
for k in order: print(f'| {k} | {vc.get(k, 0):,} | {int((c.確かさ低 & (c.新区分 == k)).sum()):,} | {pv.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
notify = sum(vc.get(k, 0) for k in order)
print(f'| 知らせる行の計 | {notify:,} | {int(c.確かさ低.sum()):,} | {sum(pv.get(k, 0) for k in order):,} | {notify/N*100:.2f}% |')
for k in ['文言が同じ', '比べられない']: print(f'| {k} | {vc.get(k, 0):,} | | {pv.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
print(f'| 計 | {int(vc.sum()):,} | | {int(pv.sum()):,} | {vc.sum()/N*100:.2f}% |')
ok = (notify == 3090, vc.get('文言が同じ', 0) == 44196, vc.get('比べられない', 0) == 66, int(vc.sum()) == N)
print(f'  確かめ: 知らせる行 {notify} = 3090 → {ok[0]} / 同じ {vc.get("文言が同じ", 0)} = 44196 → {ok[1]} / 比べられない {vc.get("比べられない", 0)} = 66 → {ok[2]} / 計 {int(vc.sum())} = 47352 → {ok[3]}')
assert all(ok)
print(f'  「入れ替わった→判定できない」は 0 行(決まりの上で入る道が無い)。表から外した。fix-report-2 でも 0 行。')
print('\n# 前(fix-report-2)→ 後(行。変わらない行も含む)')
x = pd.crosstab(c.新区分_前, c.新区分); print(x.to_string())
# 一覧: 前回の 31 行(r0 ≥ 0.9 で入れ替わり: (b) だけ 21、(a) 10)と review-boundary-06.csv の 30 行
hi = ch[(ch.r0 >= 0.9) & ch.新区分.str.startswith('入れ替わった')]
print(f'\n  前回の 31 行: r0 ≥ 0.9 で fix-report-2 では入れ替わった = {len(hi)} 行 ({hi.新区分.value_counts().to_dict()})')
rb = pd.read_csv('review-boundary-06.csv', dtype=str, keep_default_na=False)
rows = []
for i, r in hi.iterrows(): rows.append(('前回の31行: ' + ('別の番号に当たった' if r.新区分 == '入れ替わった→移った' else '見出しだけ'), i))
for _, r in rb.iterrows(): rows.append(('review-boundary-06', r.手続ID))
L = []
for src, pid in rows:
    r = c.loc[pid]; inch = pid in ch.index
    L.append({'出どころ': src, '手続ID': pid, '法令名': r.法令名, '根拠条項号': r.根拠条項号, '深さ': r.深さ,
              'rdf-report の区分(A1後)': r.A1後, 'fix-report-2 の区分': r.新区分_前, 'fix-report-3 の区分': r.新区分, '当てた決まり': r.get('当てた決まり', ''),
              'r0': f'{float(r.r0):.3f}' if inch else '', 'r1': (f'{float(r.r1):.3f}' if inch and pd.notna(r.r1) else ''),
              '旧見出し': ch.旧見出し[pid] if inch else '', '新見出し': ch.新見出し[pid] if inch else '',
              '見出しの近さ': (f'{ch.見出しの近さ[pid]:.3f}' if inch and pd.notna(ch.見出しの近さ[pid]) else ''), '移った先': r.移った先})
L = pd.DataFrame(L); L.to_csv('review-rule3.csv', index=False, encoding='utf-8-sig')
print(f'  一覧 review-rule3.csv: {len(L)} 行')
print(pd.crosstab([L.出どころ, L['fix-report-2 の区分']], L['fix-report-3 の区分']).to_string())
print('\n  一覧(全行):')
for _, r in L.iterrows(): print(f"    {r.出どころ} | {r.手続ID} | {r.法令名} {r.根拠条項号}({r.深さ}) | {r['fix-report-2 の区分']} → {r['fix-report-3 の区分']} | {r.当てた決まり} | r0 {r.r0} r1 {r.r1} | 見出し {r.旧見出し}→{r.新見出し} {r.見出しの近さ} | {r.移った先}")
# 例
for k in ['(2)', '(3)']:
    e = ch[ch.当てた決まり == k].drop_duplicates(['law_id', '根拠条項号']).head(6)
    print(f'\n  {k} の例:')
    for i, r in e.iterrows(): print(f'    {r.法令名} {r.根拠条項号} r0 {r.r0:.3f} r1 {r.r1 if pd.isna(r.r1) else round(r.r1,3)} → {r.a_移った先 if k == "(2)" else "(移った先は付けない)"} | 見出し {r.旧見出し}→{r.新見出し} {r.見出しの近さ}')
c.reset_index().to_csv('out/fix4_compare.csv', index=False)
