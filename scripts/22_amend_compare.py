"""改正の追跡: (1) 404 行 (2) 無い行の再照合 (3) 2025-11-01 版と 2026-11-18 版の文言比較 (4) 施行予定の改正 (5) 府省庁別 (6) 例。
本文はキャッシュから読むだけ(offline)。"""
import sys, re, json, random, difflib, collections, pandas as pd
sys.path.insert(0, 'scripts'); import egov
from clause import parse_ext, article_index, check, kids, text, walk
OLD, NEW = '2025-11-01', '2026-11-18'
FROM, TO, AFTER = '2025-11-02', '2026-11-18', '2026-11-19'
d = pd.read_csv('out/full_check.csv', dtype=str, keep_default_na=False)
R = pd.read_csv('out/law_revisions.csv', dtype=str, keep_default_na=False)
T = pd.read_csv('out/20_targets.csv', dtype=str)
P = d['根拠条項号'].map(lambda s: parse_ext(s)[0])

def body(lid, asof):
    b = egov.get(f'/law_data/{lid}', {'asof': asof, 'response_format': 'json', 'json_format': 'full'}, offline=True)
    if b.get('_status') != 200: return None, b.get('_status'), ''
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    return article_index(lb), 200, b['revision_info']['law_revision_id']
WS = re.compile(r'\s+')   # 空白・改行(全角空白を含む)
def has_rt(n): return bool(walk(n, 'Rt', []))
def elem(idx, p, depth):
    """照合した深さの要素。無ければ (None, 理由)。"""
    a = idx.get((p['附則'], p['条']))
    if a is None: return None, '条が無い'
    if depth == '条まで': return a, ''
    paras = kids(a, 'Paragraph')
    if p['項'] is not None:
        pp = [x for x in paras if x['attr'].get('Num') == p['項']]
        if not pp: return None, '項が無い'
        para = pp[0]
    else:
        if len(paras) != 1: return None, '項の指定なしで項が複数'
        para = paras[0]
    if depth == '項まで': return para, ''
    it = [x for x in kids(para, 'Item') if x['attr'].get('Num') == p['号']]
    return (it[0], '') if it else (None, '号が無い')

# ---------- (1) 404 の行
print('# 1. 本文が 404 だった行')
r404 = d[d.結果_追加.str.startswith('本文が取れない')]
print(r404[['手続ID', '所管府省庁', '手続名', '法令名', '根拠条項号', 'law_id', '段', '結果_追加']].to_string(index=False))
for i in r404.index:
    idx, st, rev = body(d.law_id[i], NEW)
    print(f'  {NEW} 版: 取得 {st} {rev} → 照合(追加の分け方): {check(idx, P[i])[:2] if idx is not None else "-"}')

# ---------- (2) 無い行の再照合
st = pd.read_csv('out/21_fetch_status.csv', dtype=str)
for l in st[st.status != '200'].law_id:
    print(f'  {NEW} 版が {st.set_index("law_id").status[l]} の法令: {l} {d[d.law_id == l].法令名.iloc[0]}  行 {int((d.law_id == l).sum())}  履歴上の最新の施行版 {R[(R.law_id == l) & (R.current_revision_status == "CurrentEnforced")].law_revision_id.tolist()}')
print(f'\n# 2. 条・項・号が無い行を {NEW} 時点の版で照合し直す')
def kubun(r):
    if r.結果_追加 == '法令はあるが条が無い': return '条が無い'
    if r.補足_追加 == '項が見つからない': return '項が無い'
    if r.補足_追加 == '号が見つからない': return '号が無い'
    return ''
d['無い区分'] = d.apply(kubun, axis=1)
M = d[d.無い区分 != ''].copy()
res = []
cache = {}
def newidx(lid):
    if lid not in cache: cache.clear(); cache[lid] = body(lid, NEW)
    return cache[lid]
for i in M.sort_values('law_id').index:
    idx, st, rev = newidx(d.law_id[i])
    if idx is None: res.append((i, f'本文が取れない({st})', '', rev)); continue
    r, note, _ = check(idx, P[i]); res.append((i, r, note, rev))
for i, r, note, rev in res: M.loc[i, '新_結果'] = r; M.loc[i, '新_補足'] = note; M.loc[i, '新_版'] = rev
def found(r):
    k, nr = r.無い区分, r.新_結果
    if k == '条が無い': return nr in ('条まで', '項まで', '号まで一致')
    if k == '項が無い': return nr in ('項まで', '号まで一致')
    if k == '号が無い': return nr == '号まで一致'
M['見つかるようになった'] = M.apply(found, axis=1)
M['版が変わった'] = M.新_版 != M.law_revision_id
for k in ['条が無い', '項が無い', '号が無い']:
    g = M[M.無い区分 == k]
    print(f'  {k}: {len(g)} 行 → 見つかるようになった {int(g.見つかるようになった.sum())} 行 (法令 {g[g.見つかるようになった].law_id.nunique()}) / 見つからないまま {int((~g.見つかるようになった).sum())} 行'
          f'  [{NEW} 版が 2025-11-01 版と違う法令の行 {int(g.版が変わった.sum())}]')
g = M; print(f'  計: {len(g)} 行 → 見つかるようになった {int(g.見つかるようになった.sum())} 行')
print('\n  区分 × 新しい版での照合結果')
print(M.groupby(['無い区分', '新_結果', '新_補足']).size().to_string())
print('\n  見つかるようになった行の多い法令(上位10)'); print(M[M.見つかるようになった].groupby('法令名').size().sort_values(ascending=False).head(10).to_string())
print('\n  見つからないままの行の多い法令(上位10)'); print(M[~M.見つかるようになった].groupby('法令名').size().sort_values(ascending=False).head(10).to_string())
M[['手続ID', '所管府省庁', '手続名', '法令名', '根拠条項号', 'law_id', '無い区分', 'law_revision_id', '新_版', '新_結果', '新_補足', '見つかるようになった']].to_csv('out/recheck_missing.csv', index=False)

# ---------- (3) 文言の比較
print(f'\n# 3. 条以上で一致した行の、照合した深さの文言を {OLD} 版と {NEW} 版で比べる')
OK = ['号まで一致', '項まで', '条まで']
e = R.amendment_enforcement_date
W = set(R[(e >= FROM) & (e <= TO)].law_id)
C = d[d.結果_追加.isin(OK)].copy()
print(f'  条以上で一致した行 {len(C)} / うち {FROM}〜{TO} に施行された改正がある法令の行 {int(C.law_id.isin(W).sum())} (法令 {C[C.law_id.isin(W)].law_id.nunique()})')
C = C[C.law_id.isin(W)]
rows = []
for lid, g in C.groupby('law_id'):
    oi, ost, orev = body(lid, OLD); ni, nst, nrev = body(lid, NEW)
    for i in g.index:
        p, depth = P[i], d.結果_追加[i]
        out = {'i': i, '旧版': orev, '新版': nrev, '旧文言': '', '新文言': '', '理由': '', 'ルビ': False}
        if oi is None or ni is None:
            out['区分'] = '比べられない'; out['理由'] = f'本文が取れない(旧 {ost} / 新 {nst})'; rows.append(out); continue
        oe, why = elem(oi, p, depth)
        if oe is None: out['区分'] = '比べられない'; out['理由'] = f'旧版で要素が取れない({why})'; rows.append(out); continue
        ne, why = elem(ni, p, depth)
        out['旧文言'] = WS.sub('', text(oe)); out['ルビ'] = has_rt(oe)
        if ne is None:
            if why == '項の指定なしで項が複数': out['区分'] = '比べられない'; out['理由'] = '新版で項が複数になり、項の指定なしの号を決められない'
            else: out['区分'] = 'その条・項・号が無くなった'; out['理由'] = f'新版で{why}'
            rows.append(out); continue
        out['新文言'] = WS.sub('', text(ne)); out['ルビ'] = out['ルビ'] or has_rt(ne)
        out['区分'] = '文言が同じ' if out['旧文言'] == out['新文言'] else '文言が変わった'
        rows.append(out)
X = pd.DataFrame(rows).set_index('i')
C = C.join(X)
C['深さ'] = C.結果_追加.map({'条まで': '条', '項まで': '項', '号まで一致': '号'})
DEL = r'(第.+?[条項号]|[0-9０-９〇一二三四五六七八九十百千]+)?削除'
C['新版で削除'] = C.新文言.str.fullmatch(DEL) & (C.区分 == '文言が変わった')
C['旧版で削除'] = C.旧文言.str.fullmatch(DEL) & (C.区分 == '文言が変わった')
order = ['文言が同じ', '文言が変わった', 'その条・項・号が無くなった', '比べられない']
vc = C.区分.value_counts()
for k in order: print(f'  {k}: {vc.get(k,0)} ({vc.get(k,0)/len(C)*100:.2f}%)')
print(f'  計 {len(C)}')
print('\n  深さ × 区分'); print(pd.crosstab(C.深さ, C.区分).reindex(columns=[k for k in order if k in vc.index]).to_string())
print('\n  比べられない・無くなったの理由'); print(C[C.理由 != ''].groupby(['区分', '理由']).size().to_string())
print(f'\n  「文言が変わった」のうち、新版が「削除」だけになったもの: {int(C.新版で削除.sum())} 行')
print(f'  「文言が変わった」のうち、旧版が「削除」だけだったもの(条などが新しく置かれた): {int(C.旧版で削除.sum())} 行')
print(f'  旧版・新版の law_revision_id が同じなのに比べた行: {int((C.旧版 == C.新版).sum())}')
print(f'  ルビ(Rt)を含む要素の行: {int(C.ルビ.sum())}  (ルビの読みは text() で除いている)')
ch = C[C.区分 == '文言が変わった']
print(f'  文言が変わった: 異なる要素 {ch.groupby(["law_id", "条キー", "根拠条項号"]).ngroups} / 法令 {ch.law_id.nunique()}')

# ---------- (4) 施行予定の改正
print(f'\n# 4. {AFTER} 以降に施行予定の改正がある法令を根拠にする行(文言は比べない)')
fut = R[(e >= AFTER)]
print(f'  該当する履歴 {len(fut)} 件 / 法令 {fut.law_id.nunique()}  状態 {fut.current_revision_status.value_counts().to_dict()}')
print(f'  施行期日が空で未施行の履歴: {int(((e == "") & (R.current_revision_status == "UnEnforced")).sum())}')
F = set(fut.law_id)
hasid = d[d.law_id != '']
print(f'  根拠にする行(法令IDが決まった 75,579 行のうち): {int(hasid.law_id.isin(F).sum())}')
print(f'  うち条以上で一致した 74,544 行に入る行: {int(d[d.結果_追加.isin(OK)].law_id.isin(F).sum())}')
print(f'  うち 3 で比べた行(施行済みの改正もある法令): {int(C.law_id.isin(F).sum())} / 3 で比べていない行: {int(d[d.結果_追加.isin(OK)].law_id.isin(F - W).sum())}')
F2 = set(R[(e >= AFTER) & (e < '2117')].law_id)
print(f'  参考: 施行期日 2117-12-30/31 の履歴を除くと 法令 {len(F2)} / 根拠にする行 {int(hasid.law_id.isin(F2).sum())} / 2117 年の履歴だけがある法令 {len(F - F2)} (行 {int(hasid.law_id.isin(F - F2).sum())})')
pd.DataFrame({'law_id': sorted(F)}).assign(最も早い施行予定日=lambda x: x.law_id.map(fut.groupby('law_id').amendment_enforcement_date.min()), 根拠にする行=lambda x: x.law_id.map(hasid.groupby('law_id').size())).to_csv('out/future_amend_laws.csv', index=False)
fy = fut.groupby('law_id').amendment_enforcement_date.min()
print('  最も早い施行予定日の年別(法令数):', fy.str[:4].value_counts().sort_index().to_dict())

# ---------- (5) 府省庁別
print('\n# 5. 所管府省庁ごとの「文言が変わった」行')
base = d[d.結果_追加.isin(OK)].groupby('所管府省庁').size().rename('条以上で一致')
g = C.groupby('所管府省庁').区分.value_counts().unstack(fill_value=0)
t = pd.DataFrame({'条以上で一致': base}).join(pd.DataFrame({'比べた行': C.groupby('所管府省庁').size()})).fillna(0).astype(int)
t['文言が変わった'] = g.get('文言が変わった', pd.Series(dtype=int)).reindex(t.index).fillna(0).astype(int)
t['割合(比べた行に対し)'] = (t.文言が変わった / t.比べた行.where(t.比べた行 > 0) * 100).round(2)
t['割合(条以上で一致に対し)'] = (t.文言が変わった / t.条以上で一致 * 100).round(2)
t = t.sort_values(['文言が変わった', '比べた行'], ascending=False)
print('| 所管府省庁 | 条以上で一致 | 比べた行 | 文言が変わった | 割合(比べた行) | 割合(条以上で一致) |\n|---|---:|---:|---:|---:|---:|')
for k, r in t.iterrows():
    a = '' if pd.isna(r['割合(比べた行に対し)']) else f"{r['割合(比べた行に対し)']:.2f}%"
    print(f"| {k} | {int(r.条以上で一致):,} | {int(r.比べた行):,} | {int(r.文言が変わった):,} | {a} | {r['割合(条以上で一致に対し)']:.2f}% |")
s = t.sum(numeric_only=True)
print(f"| 計 | {int(s.条以上で一致):,} | {int(s.比べた行):,} | {int(s.文言が変わった):,} | {s.文言が変わった/s.比べた行*100:.2f}% | {s.文言が変わった/s.条以上で一致*100:.2f}% |")
t.to_csv('out/amend_by_ministry.csv')

# ---------- (6) 例 10 件(法令が重ならないように、固定の種で選ぶ)
print('\n# 6. 文言が変わった例 10 件(種 20261118、法令ごとに 1 件)')
random.seed(20261118)
laws = sorted(ch.law_id.unique()); pick = random.sample(laws, min(10, len(laws)))
def ctx(a, b, w=40):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    i1, i2, j1, j2 = ops[0][1], ops[-1][2], ops[0][3], ops[-1][4]
    pre = lambda s, x, y: ('…' if x - w > 0 else '') + s[max(0, x - w):min(len(s), y + w)] + ('…' if y + w < len(s) else '')
    return pre(a, i1, i2), pre(b, j1, j2), len(ops)
ex = []
for n, lid in enumerate(pick, 1):
    r = ch[ch.law_id == lid].sort_values('手続ID').iloc[0]
    a, b, k = ctx(r.旧文言, r.新文言)
    ex.append({'番号': n, '手続ID': r.手続ID, '所管府省庁': r.所管府省庁, '手続名': r.手続名, '法令名': r.法令名, '根拠条項号': r.根拠条項号, '深さ': r.深さ,
               'law_id': lid, '旧版': r.旧版, '新版': r.新版, '違う箇所の数': k, '旧(抜粋)': a, '新(抜粋)': b, '旧文言': r.旧文言, '新文言': r.新文言})
    print(f'\n## 例{n} 手続ID {r.手続ID} / {r.所管府省庁} / {r.手続名}\n  {r.法令名} {r.根拠条項号}(比べた深さ: {r.深さ}) https://laws.e-gov.go.jp/law/{lid}')
    print(f'  版: {r.旧版} → {r.新版}  違う箇所 {k}\n  旧: {a}\n  新: {b}')
pd.DataFrame(ex).to_csv('out/amend_examples.csv', index=False)
C.drop(columns=[c for c in ['分解_基本', '補足_基本', '注記_基本', '結果_基本'] if c in C]).to_csv('out/amend_compare.csv', index=False)
