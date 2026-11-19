"""R7 の各行に法令IDを決める。(a) 法令番号 → (b) 法令名の完全一致 → (c) 表記のゆれを直して一致。
照合先は e-Gov 法令一覧 asof=2025-11-01。(c) の最後に、現時点の一覧の題名(改題後)との一致を別の小段 c2 として数える。"""
import sys, re, unicodedata, collections, pandas as pd
sys.path.insert(0, 'scripts'); from common_load import load
r7 = load('r7')
r6 = load('r6')[['手続ID', '法令名', '法令番号']].rename(columns={'法令名': 'r6_法令名', '法令番号': 'r6_法令番号'})
L = pd.read_csv('data/api/laws_asof_2025-11-01.csv', dtype=str, keep_default_na=False)
Lc = pd.read_csv('data/api/laws_asof_current.csv', dtype=str, keep_default_na=False)
d = r7.merge(r6, on='手続ID', how='left').fillna({'r6_法令名': '', 'r6_法令番号': ''})

def pick(cands):
    """候補 law_id 群から1つに決める。1件ならそれ。複数なら廃止等でないものが1件ならそれ。"""
    cands = list(dict.fromkeys(cands))
    if len(cands) == 1: return cands[0], ''
    alive = [c for c in cands if status[c] == 'None']
    if len(alive) == 1: return alive[0], ''
    return None, f'候補{len(cands)}件で決まらない'
status = dict(zip(L.law_id, L.repeal_status)); status.update({k: v for k, v in zip(Lc.law_id, Lc.repeal_status) if k not in status})
by_num = collections.defaultdict(list); [by_num[n].append(i) for n, i in zip(L.law_num, L.law_id)]
by_title = collections.defaultdict(list); [by_title[t].append(i) for t, i in zip(L.law_title, L.law_id)]

DASH = '‐-‑‒–—―ー－−'
def nz(s):
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s)
    s = re.sub(f'(?<=[〇一二三四五六七八九十0-9])[{DASH}](?=[〇一二三四五六七八九十0-9])', '-', s)  # 人事院規則一〇―一一 など
    s = s.replace('ヶ', 'ケ').replace('「', '').replace('」', '')
    s = re.sub(r'^[○〇◯]', '', s)
    s = re.sub(r'\(抄\)$|抄$', '', s)
    s = re.sub(r'\(附則\)$|附則$', '', s)
    return s
by_nz = collections.defaultdict(list)
for t, i in zip(L.law_title, L.law_id):
    by_nz[nz(t)].append(i)
    m = re.fullmatch(r'.+?号[（(](.+)[）)]', t)  # 「昭和二十二年法律第五十四号（私的独占の…法律）」形式
    if m: by_nz[nz(m.group(1))].append(i)
by_nz_cur = collections.defaultdict(list)
for t, i in zip(Lc.law_title, Lc.law_id):
    by_nz_cur[nz(t)].append(i)
    m = re.fullmatch(r'.+?号[（(](.+)[）)]', t)
    if m: by_nz_cur[nz(m.group(1))].append(i)

res = []
for _, r in d.iterrows():
    name = r['法令名'].strip(); stage, lid, note = '', None, ''
    if name == '':
        res.append(('空欄', None, '')); continue
    num = r['r6_法令番号'].strip()
    r6n = r['r6_法令名'].strip()
    # R7 は72文字で切れている名前がある。ただし R7 の名前がそのまま一覧の題名にあるなら切れていないとみなす
    same_law = (r6n == name) or (len(name) == 72 and name not in by_title and r6n.startswith(name))
    if num and same_law and num in by_num:
        lid, note = pick(by_num[num])
        if lid: res.append(('a 法令番号', lid, '')); continue
    if name in by_title:
        lid, note = pick(by_title[name])
        if lid: res.append(('b 法令名完全一致', lid, '')); continue
    k = nz(name)
    if k in by_nz:
        lid, note = pick(by_nz[k])
        if lid: res.append(('c1 表記ゆれ補正', lid, '')); continue
    if k in by_nz_cur:
        lid, note = pick(by_nz_cur[k])
        if lid: res.append(('c2 現時点の題名(改題後)と一致', lid, '')); continue
    res.append(('決まらない', None, note))
d['段'] = [x[0] for x in res]; d['law_id'] = [x[1] or '' for x in res]; d['決まらない理由'] = [x[2] for x in res]
title = dict(zip(Lc.law_id, Lc.law_title)); title.update(dict(zip(L.law_id, L.law_title)))
d['egov_law_title'] = d['law_id'].map(lambda x: title.get(x, ''))
d['egov_repeal_status'] = d['law_id'].map(lambda x: status.get(x, ''))
order = ['a 法令番号', 'b 法令名完全一致', 'c1 表記ゆれ補正', 'c2 現時点の題名(改題後)と一致', '決まらない', '空欄']
print('照合先: asof=2025-11-01 一覧', len(L), '件 / 現時点一覧', len(Lc), '件')
print('\n段ごとの件数 (行数 / 異なる法令名の数)')
for s in order:
    x = d[d['段'] == s]; print(f'  {s}: {len(x)} 行 ({len(x)/len(d)*100:.2f}%) / {x["法令名"].nunique()} 法令名')
ok = d['law_id'] != ''
print(f'  計 決まった: {ok.sum()} 行 ({ok.mean()*100:.2f}%) / 異なる法令ID {d.loc[ok,"law_id"].nunique()}')
print('\n決まった法令IDの廃止等の状態(行数):', d.loc[ok, 'egov_repeal_status'].value_counts().to_dict())
un = d[d['段'] == '決まらない']
print('\n決まらない理由:', un['決まらない理由'].replace('', '一覧に該当なし').value_counts().to_dict())
print('\n決まらなかった法令名 上位50 (行数)')
for i, (n, c) in enumerate(un['法令名'].value_counts().head(50).items(), 1): print(f'  {i:2d}. {c:4d}  {n}')
# 補足: R7 法令名は72文字で切れているものがある。前方一致で1件に決まる数 (段には入れない)
L72 = un[un['法令名'].str.len() == 72]
pref = 0
for n in L72['法令名'].unique():
    c = [i for t, i in zip(L.law_title, L.law_id) if t.startswith(n)]
    if len(set(c)) == 1: pref += (L72['法令名'] == n).sum()
print(f'\n補足: 決まらない行のうち法令名がちょうど72文字の行 {len(L72)} 行、そのうち一覧の題名と前方一致で1件に決まる行 {pref} (段には含めていない)')
d.to_csv('out/r7_law_id.csv', index=False, columns=['手続ID', '所管府省庁', '手続名', '法令名', '根拠条項号', '手続類型', 'r6_法令番号', '段', 'law_id', 'egov_law_title', 'egov_repeal_status', '決まらない理由'])
un['法令名'].value_counts().to_csv('out/unmatched_law_names.csv', header=['行数'])
# 点検: (a) で決めた行のうち、R7 法令名が一覧の別の法令の題名と完全一致する行 (= R6 法令番号と名前が食い違う)
a = d[d['段'] == 'a 法令番号']
conf = a[a['法令名'].map(lambda n: n in by_title) & a.apply(lambda r: r['law_id'] not in by_title.get(r['法令名'], []), axis=1)]
print(f'\n点検: a段の行のうち、法令名が一覧の別の法令の題名と完全一致する行 {len(conf)}')
for (n, t), c in conf.groupby(['法令名', 'egov_law_title']).size().items(): print(f'  {c} 行  R7法令名={n} / R6番号の法令={t}')
d['a段と名前の食い違い'] = d.index.isin(conf.index)
d.to_csv('out/r7_law_id.csv', index=False, columns=['手続ID', '所管府省庁', '手続名', '法令名', '根拠条項号', '手続類型', 'r6_法令番号', '段', 'law_id', 'egov_law_title', 'egov_repeal_status', '決まらない理由', 'a段と名前の食い違い'])
