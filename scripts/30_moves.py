"""「無くなった」353 行の行き先: 2026-11-18 版の同じ法令の中で、元の文言と同じか近い条・項・号を探す。本文はキャッシュから読むだけ。
(探し方は scripts/moves_lib.py。2026-11-18 に関数を移しただけで、判定は変えていない)"""
import sys, json, pandas as pd
sys.path.insert(0, 'scripts')
from moves_lib import HI, LO, MINLEN, TIE, load, judge
OLD, NEW = '2025-11-01', '2026-11-18'
c = pd.read_csv('out/amend_compare.csv', dtype=str, keep_default_na=False)
X = c[c.区分 == 'その条・項・号が無くなった'].copy()
res = {}
for lid, g in X.groupby('law_id'):
    oi, ni = load(lid, OLD), load(lid, NEW); cache = {}
    for i in g.index:
        key = (lid, c.深さ[i], c.根拠条項号[i], c.分解_追加[i])
        if key not in res: res[key] = judge(oi, ni, json.loads(c.分解_追加[i]), c.深さ[i], cache)
        res[i] = res[key]
for col in ['判定', '移った先', '近さ', '2番目の近さ', '理由', '元の文言(番号除く)', '移った先の文言(番号除く)']:
    X[col] = [res[i][col] for i in X.index]
print(f'# 「無くなった」{len(X)} 行 / 異なる要素 {X.groupby(["law_id", "深さ", "根拠条項号"]).ngroups} / 法令 {X.law_id.nunique()}')
print(f'  基準: 近さ = difflib.SequenceMatcher(autojunk=False).ratio() = 2×一致字数/(両方の字数の和)。番号(条名・項番号・号名)と空白・改行を除いた文言で比べる。')
print(f'  移った: 近さ ≥ {HI}(1.000 は文言が同じ)/ 消えた: 最良でも < {LO} / 判定できない: その間、元の文言が {MINLEN} 字未満、近い候補が複数(差 < {TIE})、候補が旧版でも同じ番号にあった')
print(f'  候補: 新版の同じ法令の、同じ深さ(条なら条、項なら項、号なら号)の全要素。本則と制定附則。')
vc = X.判定.value_counts()
for k in ['移った', '消えた', '判定できない']: print(f'  {k}: {vc.get(k, 0)} 行')
print('\n  判定 × 理由'); print(X.assign(理由=X.理由.str.replace(r'\(最良.*\)', '', regex=True)).groupby(['判定', '理由']).size().to_string())
print('\n  判定 × 深さ'); print(pd.crosstab(X.深さ, X.判定).to_string())
u = X.drop_duplicates(['law_id', '深さ', '根拠条項号'])
print('\n  異なる要素で数えた判定:', u.判定.value_counts().to_dict())
print('\n  近さの分布(異なる要素):'); print(pd.cut(u.近さ.replace('', None).dropna().astype(float), [0, .3, .6, .8, .9, .95, .999, 1.0], include_lowest=True).value_counts().sort_index().to_string())
mv = X[X.判定 == '移った']
print('\n  移った例(先頭 15、法令・元の番号・移った先・近さ):')
for _, r in mv.drop_duplicates(['law_id', '根拠条項号']).head(15).iterrows(): print(f'    {r.法令名} {r.根拠条項号}({r.深さ}) → {r.移った先}  {r.近さ}')
print('\n  消えた行の多い法令:'); print(X[X.判定 == '消えた'].groupby('法令名').size().sort_values(ascending=False).head(10).to_string())
X.to_csv('out/moves.csv', index=False)
