"""判定の決まりの直し(fix-report-2)。本文はキャッシュから読むだけ。"""
import sys, json, re, time, pandas as pd
sys.path.insert(0, 'scripts')
from moves_lib import load, judge
from clause import kids, text
OLD, NEW = '2025-11-01', '2026-11-18'
t0 = time.time()
c = pd.read_csv('out/fix2_compare.csv', dtype=str, keep_default_na=False)
sw = pd.read_csv('out/fix_swapped.csv', dtype=str, keep_default_na=False)
rest = pd.read_csv('out/fix_rest.csv', dtype=str, keep_default_na=False)
mv = pd.read_csv('out/moves.csv', dtype=str, keep_default_na=False)
N = len(c); assert N == 47352
ratio = pd.concat([sw, rest]).set_index('手続ID').同じ番号の近さ.astype(float)
ch = c[c.区分 == '文言が変わった'].copy(); ch['同じ番号の近さ'] = ch.手続ID.map(ratio); assert ch.同じ番号の近さ.notna().all()
print(f'# 対象: 文言が変わった {len(ch)} 行 / 無くなった {int((c.区分 == "その条・項・号が無くなった").sum())} 行')

# (a) 同じ法令の別の番号の同じ深さの要素に 0.90 以上で見つかる(探し方は moves_lib.judge。元と同じ番号は候補から外す)
# (b) 条を比べた行で、条の見出し(ArticleCaption)が旧・新で違う
res, cap = {}, {}
def caption(idx, p):
    a = idx.get((p['附則'], p['条']))
    if a is None: return None
    cs = kids(a, 'ArticleCaption'); return re.sub(r'\s+', '', text(cs[0])) if cs else ''
for lid, g in ch.groupby('law_id'):
    oi, ni = load(lid, OLD), load(lid, NEW); cache = {}
    for i in g.index:
        p = json.loads(c.分解_追加[i]); key = (lid, c.深さ[i], c.根拠条項号[i], c.分解_追加[i])
        if key not in res: res[key] = judge(oi, ni, p, c.深さ[i], cache, exclude_own=True)
        res[i] = res[key]
        if c.深さ[i] == '条': cap[i] = (caption(oi, p), caption(ni, p))
ch['a_判定'] = [res[i]['判定'] for i in ch.index]; ch['a_移った先'] = [res[i]['移った先'] for i in ch.index]; ch['a_近さ'] = [res[i]['近さ'] for i in ch.index]
ch['a_理由'] = [res[i]['理由'] for i in ch.index]
ch['旧見出し'] = [cap.get(i, (None, None))[0] for i in ch.index]; ch['新見出し'] = [cap.get(i, (None, None))[1] for i in ch.index]
A = ch.a_判定 == '移った'
B = (ch.深さ == '条') & (ch.旧見出し.fillna('') != ch.新見出し.fillna(''))
print(f'  探索と見出しの比べ: {time.time()-t0:.0f} 秒')
print(f'\n# (a)(b) の当たり(文言が変わった {len(ch)} 行)')
print(f'  (a) に当たる: {int(A.sum())} 行 / (b) に当たる: {int(B.sum())} 行 / 両方: {int((A & B).sum())} / (b) だけ: {int((B & ~A).sum())}')
print(f'  条を比べた行 {int((ch.深さ == "条").sum())} のうち 見出しが旧・新の片方だけにある行: {int(((ch.深さ == "条") & ((ch.旧見出し == "") != (ch.新見出し == ""))).sum())}')
lo = ch.同じ番号の近さ < 0.6
print(f'  近さ < 0.6 の {int(lo.sum())} 行: (a) {int((lo & A).sum())} / (b) だけ {int((lo & B & ~A).sum())} / どちらでもない {int((lo & ~A & ~B).sum())}')
print(f'  近さ ≥ 0.6 の {int((~lo).sum())} 行: (a) {int((~lo & A).sum())} / (b) だけ {int((~lo & B & ~A).sum())} / どちらでもない {int((~lo & ~A & ~B).sum())}')
print(f'  → 3. 近さ ≥ 0.6 で (b) に当たり「入れ替わった」に移る行: {int((~lo & B).sum())}(うち (a) にも当たる {int((~lo & B & A).sum())})。(a) で移る行も含めた、近さ ≥ 0.6 から「入れ替わった」へ移る行: {int((~lo & (A | B)).sum())}')
hi = ch.同じ番号の近さ >= 0.9
print(f'  参考: 同じ番号の近さ ≥ 0.9 なのに (a) に当たる行 {int((hi & A).sum())} / (b) だけに当たる行 {int((hi & B & ~A).sum())}(見出しの小さな書き換えなど。分類は決まりのまま)')
print('  (a) で探した結果の内訳(全 2,737 行。移った以外は (a) に当たらない):', ch.a_判定.value_counts().to_dict())

def new_label(r, a, b):
    if a: return '入れ替わった→移った'
    if b: return '入れ替わった→移った先なし'
    if r.同じ番号の近さ < 0.6: return '大きく書き換わった'
    return c.A1後[r.name]   # 番号の参照だけ / それ以外(rdf-report の A1 の決まり)
ch['新区分'] = [new_label(r, a, b) for (_, r), a, b in zip(ch.iterrows(), A, B)]
ch['移った先'] = ch.a_移った先.where(A, ''); ch['近さ'] = ch.a_近さ.where(A, '')
c['新区分'] = c.A1後; c['移った先'] = ''; c['移った先の近さ'] = ''
c.loc[ch.index, '新区分'] = ch.新区分; c.loc[ch.index, '移った先'] = ch.移った先; c.loc[ch.index, '移った先の近さ'] = ch.近さ
# 無くなった: 前回の判定のまま。「消えた」は使わないので「移った先なし」と呼ぶ
mm = mv.set_index('手続ID')
gone = c.区分 == 'その条・項・号が無くなった'
c.loc[gone, '新区分'] = '無くなった→' + c.loc[gone, '手続ID'].map(mm.判定).replace({'消えた': '移った先なし'})
c.loc[gone, '移った先'] = c.loc[gone, '手続ID'].map(mm.移った先).where(c.loc[gone, '手続ID'].map(mm.判定) == '移った', '')
c.loc[gone, '移った先の近さ'] = c.loc[gone, '手続ID'].map(mm.近さ).where(c.loc[gone, '手続ID'].map(mm.判定) == '移った', '')
# 4. 確かさ低
mvd = c.新区分.str.endswith('→移った')
lowc = mvd & (c.移った先の近さ.replace('', '0').astype(float) >= 0.90) & (c.移った先の近さ.replace('', '0').astype(float) < 0.95)
c['確かさ低'] = lowc
# 5. 区分を確かめて決めた行(列の名前は「人の確認」だが、読んだのは作った Claude Code とは別の AI(別の会話の Claude)。作った人はまだ行を読んでいない)
MAN = [('租税特別措置法施行令', '第26条の4第19項'), ('租税特別措置法施行令', '第26条の4第9項'), ('沖縄の復帰に伴う国税関係法令の適用の特別措置等に関する政令', '第74条の2第27項')]
c['人の確認日'] = ''; c['人の確認の理由'] = ''
for law, art in MAN:
    hit = c[(c.法令名 == law) & (c.根拠条項号 == art)]
    keys = set(zip(hit.law_id, hit.深さ, hit.分解_追加))
    same = c[[k in keys for k in zip(c.law_id, c.深さ, c.分解_追加)]]
    print(f'\n  人の確認: {law} {art} → 同じ要素の行 {len(same)} (手続ID {sorted(same.手続ID)})  前の区分 {same.新区分.value_counts().to_dict()}')
    for i in same.index:
        c.loc[i, '新区分'] = c.新区分[i].split('→')[0] + '→判定できない'; c.loc[i, '人の確認日'] = '2026-11-18'
        c.loc[i, '人の確認の理由'] = '移った先は、無くなった制度と似た別の制度の規定と見られる'; c.loc[i, '確かさ低'] = False
print(f'\n# 4. 「確かさ低」の印(移った のうち 0.90 ≤ 近さ < 0.95、人の確認で判定できないにした行を除く): {int(c.確かさ低.sum())} 行  内訳 {c[c.確かさ低].新区分.value_counts().to_dict()}')

order = ['文言が変わった: 番号の参照だけ', '文言が変わった: それ以外', '大きく書き換わった', '入れ替わった→移った', '入れ替わった→移った先なし', '入れ替わった→判定できない',
         '無くなった→移った', '無くなった→移った先なし', '無くなった→判定できない']
vc = c.新区分.value_counts()
assert set(vc.index) <= set(order) | {'文言が同じ', '比べられない'}, set(vc.index) - set(order)
print(f'\n# 6. 直した後の表(47,352 に対する比)\n| 区分 | 行 | うち確かさ低 | 比 |\n|---|---:|---:|---:|')
for k in order: print(f'| {k} | {vc.get(k, 0):,} | {int((c.確かさ低 & (c.新区分 == k)).sum()):,} | {vc.get(k, 0)/N*100:.2f}% |')
notify = sum(vc.get(k, 0) for k in order)
print(f'| 知らせる行の計 | {notify:,} | {int(c.確かさ低.sum()):,} | {notify/N*100:.2f}% |')
print(f'| 文言が同じ | {vc.get("文言が同じ", 0):,} | | {vc.get("文言が同じ", 0)/N*100:.2f}% |')
print(f'| 比べられない | {vc.get("比べられない", 0):,} | | {vc.get("比べられない", 0)/N*100:.2f}% |')
print(f'| 計 | {int(vc.sum()):,} | | {vc.sum()/N*100:.2f}% |')
ok = (notify == 3090, vc.get('文言が同じ', 0) == 44196, vc.get('比べられない', 0) == 66, int(vc.sum()) == 47352)
print(f'  確かめ: 知らせる行 {notify} = 3090 → {ok[0]} / 同じ {vc.get("文言が同じ", 0)} = 44196 → {ok[1]} / 比べられない {vc.get("比べられない", 0)} = 66 → {ok[2]} / 計 = 47352 → {ok[3]}')
assert all(ok)
prev = c.A1後.value_counts()
print('\n  前(rdf-report の A1 の後)からの移り変わり(行):'); print(pd.crosstab(c.A1後, c.新区分).to_string())
ex = ch[B & ~A].drop_duplicates(['law_id', '根拠条項号']).head(8)
print('\n  (b) だけに当たる例(見出し 旧 → 新):')
for _, r in ex.iterrows(): print(f'    {r.法令名} {r.根拠条項号}: {r.旧見出し or "(見出し無し)"} → {r.新見出し or "(見出し無し)"}  同じ番号の近さ {r.同じ番号の近さ:.3f}')
ex = ch[A & ~lo].drop_duplicates(['law_id', '根拠条項号']).head(8)
print('\n  近さ ≥ 0.6 で (a) に当たる例:')
for _, r in ex.iterrows(): print(f'    {r.法令名} {r.根拠条項号} → {r.a_移った先}  移った先の近さ {r.a_近さ} / 同じ番号の近さ {r.同じ番号の近さ:.3f}')
c.to_csv('out/fix3_compare.csv', index=False); ch.to_csv('out/fix3_changed.csv', index=False)
print(f'\n所要 {time.time()-t0:.0f} 秒')
