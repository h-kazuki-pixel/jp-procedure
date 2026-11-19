"""判定の決まりの直し(fix-report-4)。本文はキャッシュから読むだけ(取得しない)。
r0 と r1 を同じ測り方で測り直す: 条名・項番号・号名(ArticleTitle, ParagraphNum, ItemTitle, Subitem1〜10Title)は要素の中のどこにあっても除く。
文の中の参照の番号(「第三条」など本文の文字)は残す。見出し(ArticleCaption)も残す。ルビの読みは除く。空白・改行は除く。"""
import sys, json, re, time, difflib, collections, pandas as pd
sys.path.insert(0, 'scripts')
from moves_lib import load, elements, old_elem, sim, TAG, HI, LO, MINLEN
OLD, NEW, N, TIE = '2025-11-01', '2026-11-18', 47352, 0.01
TITLES = {'ArticleTitle', 'ParagraphNum', 'ItemTitle'} | {f'Subitem{i}Title' for i in range(1, 11)}
WS = re.compile(r'\s+')
def t2(n):
    if isinstance(n, str): return n
    if n.get('tag') in TITLES or n.get('tag') == 'Rt': return ''
    return ''.join(t2(c) for c in n.get('children', []))
def txt(n): return WS.sub('', t2(n))
t0 = time.time()
c = pd.read_csv('out/fix4_compare.csv', dtype=str, keep_default_na=False).set_index('手続ID'); assert len(c) == N
ch = c.区分 == '文言が変わった'; gone = c.区分 == 'その条・項・号が無くなった'
print(f'# 対象: 文言が変わった {int(ch.sum()):,} 行 / 無くなった {int(gone.sum()):,} 行')
R = {}
for lid, g in c[ch | gone].groupby('law_id'):
    oi, ni = load(lid, OLD), load(lid, NEW); cache = {}
    for pid in g.index:
        p = json.loads(c.分解_追加[pid]); depth = c.深さ[pid]; key = (lid, depth, c.分解_追加[pid])
        if key in R: R[pid] = R[key]; continue
        r = dict(r0=None, r1=None, cands='', best_lab='', n_tie=0, minlen=False, prev_same=False, best_pos=None)
        if oi is None or ni is None: r['noload'] = True; R[key] = R[pid] = r; continue
        oe, opos = old_elem(oi, p, depth); a = txt(oe)
        if c.区分[pid] == '文言が変わった':
            ne, npos = old_elem(ni, p, depth); assert ne is not None and npos == opos, (pid, npos, opos)
            b = txt(ne); r['r0'] = 1.0 if a == b else difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
        if len(a) < MINLEN: r['minlen'] = True; R[key] = R[pid] = r; continue
        tag = TAG[depth]
        if tag not in cache: cache[tag] = [(lab, pos, txt(e)) for lab, pos, e in elements(ni, tag)]; cache['old_' + tag] = {pos: txt(e) for _, pos, e in elements(oi, tag)}
        sc = sorted(((1.0 if a == t else sim(a, t), lab, pos) for lab, pos, t in cache[tag] if pos != opos), key=lambda x: -x[0])
        if sc:
            best = sc[0]; r['r1'] = best[0]; r['best_lab'] = best[1]; r['best_pos'] = best[2]
            near = [x for x in sc if best[0] - x[0] < TIE]       # 最良との差が 0.01 未満(最良そのものを含む)
            r['n_tie'] = len(near) - 1; r['cands'] = ' / '.join(f'{lab}({s:.3f})' for s, lab, _ in near)
            prev = cache['old_' + tag].get(best[2], '')
            t_best = [t for lab, pos, t in cache[tag] if pos == best[2]][0]
            r['prev_same'] = bool(prev) and (prev == t_best or sim(prev, t_best) >= HI)
        else: r['r1'] = 0.0
        R[key] = R[pid] = r
print(f'  測り直し: {time.time()-t0:.0f} 秒')
for k in ['r0', 'r1', 'cands', 'best_lab', 'n_tie', 'minlen', 'prev_same']: c[k + '_4'] = [R[i][k] if i in R else None for i in c.index]
assert not any(R[i].get('noload') for i in c.index[ch | gone])
# ---- 文言が変わった の側
X = c[ch].copy()
old_r0 = X.r0.astype(float); old_r1 = pd.to_numeric(X.r1.replace('', None))
def heading_rule(i): return X.当てた決まり[i] == '(3)' or (X.深さ[i] == '条' and str(X.見出しの近さ[i]) not in ('', 'nan') and float(X.見出しの近さ[i]) < 0.5)
def rule(i):
    r0, r1 = X.r0_4[i], X.r1_4[i]
    if r0 >= 0.90: return '文言が変わった', '(1)'
    if r1 is not None and r1 >= 0.90 and r1 - r0 >= 0.05:
        return ('入れ替わった→移った先が一つに決まらない', '(2) 候補が並ぶ') if X.n_tie_4[i] > 0 else ('入れ替わった→移った', '(2)')
    if heading_rule(i): return '入れ替わった→移った先なし', '(3)'
    return ('大きく書き換わった', '(4) r0 < 0.6') if r0 < 0.6 else ('文言が変わった', '(4) r0 ≥ 0.6')
lab = {i: rule(i) for i in X.index}
X['新区分4'] = [lab[i][0] for i in X.index]; X['決まり4'] = [lab[i][1] for i in X.index]
m = X.新区分4 == '文言が変わった'
X.loc[m, '新区分4'] = X.loc[m, 'A1後'].where(X.loc[m, 'A1後'].str.startswith('文言が変わった'), '文言が変わった: それ以外')
print(f'\n# 文言が変わった の側({len(X):,} 行)')
print(f'  r0 の変わり方(前は番号を含む全文 / 今は番号を除く): 上がった {int((X.r0_4 > old_r0 + 1e-9).sum())} / 同じ {int(((X.r0_4 - old_r0).abs() <= 1e-9).sum())} / 下がった {int((X.r0_4 < old_r0 - 1e-9).sum())}')
print(f'  r0 が 1.000 になった行(番号だけが違った): {int((X.r0_4 == 1.0).sum())}')
r1n = pd.to_numeric(X.r1_4)
print(f'  r1 の変わり方: 上がった {int((r1n > old_r1 + 1e-9).sum())} / 同じ {int(((r1n - old_r1).abs() <= 1e-9).sum())} / 下がった {int((r1n < old_r1 - 1e-9).sum())} / r1 が無い(元の文言が 10 字未満) {int(r1n.isna().sum())}')
print('  当てた決まり:', X.決まり4.value_counts().to_dict())
for lo, hi in [(0.0, 0.6), (0.6, 0.9), (0.9, 1.01)]:
    mm = (X.r0_4 >= lo) & (X.r0_4 < hi); print(f'  r0 {lo}〜{hi}: {int(mm.sum())} 行')
# ---- 無くなった の側
Y = c[gone].copy()
def grule(i):
    if c.人の確認日[i]: return '無くなった→判定できない', '人の確認'
    if Y.minlen_4[i]: return '無くなった→判定できない', '元の文言が短い'
    r1 = Y.r1_4[i]
    if r1 >= HI:
        if Y.prev_same_4[i]: return '無くなった→判定できない', '旧版でも同じ番号に近い文言'
        if Y.n_tie_4[i] > 0: return '無くなった→移った先が一つに決まらない', '候補が並ぶ'
        return '無くなった→移った', '移った'
    if r1 < LO: return '無くなった→移った先なし', '最も近い候補が 0.6 未満'
    return '無くなった→判定できない', '最も近い候補が 0.6〜0.9'
gl = {i: grule(i) for i in Y.index}
Y['新区分4'] = [gl[i][0] for i in Y.index]; Y['決まり4'] = [gl[i][1] for i in Y.index]
print(f'\n# 無くなった の側({len(Y):,} 行)'); print('  理由:', Y.決まり4.value_counts().to_dict())
c['新区分_3'] = c.新区分
for D in (X, Y): c.loc[D.index, '新区分'] = D.新区分4; c.loc[D.index, '当てた決まり4'] = D.決まり4
mv = c.新区分.str.endswith('→移った'); tie = c.新区分.str.endswith('一つに決まらない')
c['移った先'] = c.best_lab_4.where(mv, ''); c['移った先の近さ'] = c.r1_4.where(mv, None)
c['移った先の候補'] = c.cands_4.where(tie, '')
v = pd.to_numeric(c.移った先の近さ).fillna(0)
c['確かさ低'] = mv & (v >= 0.90) & (v < 0.95)
order = ['文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '大きく書き換わった', '入れ替わった→移った', '入れ替わった→移った先が一つに決まらない', '入れ替わった→移った先なし',
         '無くなった→移った', '無くなった→移った先が一つに決まらない', '無くなった→移った先なし', '無くなった→判定できない']
vc = c.新区分.value_counts(); pv = c.新区分_3.value_counts(); assert set(vc.index) <= set(order) | {'文言が同じ', '比べられない'}, set(vc.index)
print(f'\n# 直した後の表(47,352 に対する比)\n| 区分 | 行 | うち確かさ低 | 前(fix-report-3) | 比 |\n|---|---:|---:|---:|---:|')
for k in order: print(f'| {k} | {vc.get(k, 0):,} | {int((c.確かさ低 & (c.新区分 == k)).sum()):,} | {pv.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
notify = sum(vc.get(k, 0) for k in order)
print(f'| 知らせる行の計 | {notify:,} | {int(c.確かさ低.sum()):,} | {sum(pv.get(k, 0) for k in order):,} | {notify/N*100:.2f}% |')
for k in ['文言が同じ', '比べられない']: print(f'| {k} | {vc.get(k, 0):,} | | {pv.get(k, 0):,} | {vc.get(k, 0)/N*100:.2f}% |')
print(f'| 計 | {int(vc.sum()):,} | | {int(pv.sum()):,} | {vc.sum()/N*100:.2f}% |')
ok = (notify == 3090, vc.get('文言が同じ', 0) == 44196, vc.get('比べられない', 0) == 66, int(vc.sum()) == N)
print(f'  確かめ: 知らせる行 {notify} = 3090 → {ok[0]} / 同じ {vc.get("文言が同じ", 0)} = 44196 → {ok[1]} / 比べられない {vc.get("比べられない", 0)} = 66 → {ok[2]} / 計 {int(vc.sum())} = 47352 → {ok[3]}')
assert all(ok)
print('\n# 前(fix-report-3)→ 後(変わった組だけ、行)')
x = c[c.新区分 != c.新区分_3].groupby(['新区分_3', '新区分']).size()
for (a, b), n in x.items(): print(f'  {a} → {b}: {n}')
print(f'  変わらない行: {int((c.新区分 == c.新区分_3).sum()):,}')
print('\n# 金融商品取引法 第27条の13第2項(review-boundary-06.csv の行)')
rb = pd.read_csv('review-boundary-06.csv', dtype=str, keep_default_na=False)
for pid in rb[(rb.法令名 == '金融商品取引法') & (rb.条項号 == '第27条の13第2項')].手続ID:
    r = c.loc[pid]
    print(f'  手続ID {pid}: fix-report-3 {r.新区分_3}(r0 {float(r.r0):.3f}, r1 {float(r.r1):.3f}) → fix-report-4 {r.新区分}({r.当てた決まり4}, r0 {r.r0_4:.3f}, r1 {r.r1_4:.3f}) 移った先 {r.移った先 or "-"} 候補 {r.移った先の候補 or "-"} 最良 {r.best_lab_4}')
print('\n# 移った先が一つに決まらない行(全部)')
T = c[tie]
for pid, r in T.iterrows(): print(f'  {r.新区分} | {pid} | {r.法令名} {r.根拠条項号}({r.深さ}) | r0 {"" if pd.isna(r.r0_4) else f"{r.r0_4:.3f}"} r1 {r.r1_4:.3f} | 候補 {r.移った先の候補}')
T.reset_index()[['手続ID', '新区分', '法令名', 'law_id', '根拠条項号', '深さ', 'r0_4', 'r1_4', '移った先の候補']].to_csv('review-tie.csv', index=False, encoding='utf-8-sig')
print(f'  → review-tie.csv {len(T)} 行')
c.reset_index().to_csv('out/fix5_compare.csv', index=False)
print(f'\n所要 {time.time()-t0:.0f} 秒')
