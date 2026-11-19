"""2025-11-02 以降に改正・更新された法令と、それを根拠にする手続の数。履歴はキャッシュから読むだけ。"""
import sys, collections, pandas as pd; sys.path.insert(0, 'scripts'); import egov
FROM = '2025-11-02'
d = pd.read_csv('out/r7_law_id.csv', dtype=str, keep_default_na=False)
ids = sorted(set(d.law_id) - {''})
rows, miss = [], []
for lid in ids:
    b = egov.get(f'/law_revisions/{lid}', {'response_format': 'json'}, offline=True)
    if b.get('_status') != 200: miss.append((lid, b.get('_status'))); continue
    for r in b.get('revisions', []):
        rows.append({'law_id': lid, **{k: r.get(k) for k in ['law_revision_id', 'law_title', 'updated', 'amendment_promulgate_date',
                     'amendment_enforcement_date', 'amendment_scheduled_enforcement_date', 'amendment_law_num', 'amendment_type',
                     'repeal_status', 'repeal_date', 'current_revision_status', 'mission']}})
R = pd.DataFrame(rows).fillna('')
R.to_csv('out/law_revisions.csv', index=False)
print('対象法令', len(ids), ' 履歴を取れた法令', len(ids) - len(miss), ' 取れない', len(miss), miss[:10])
print('履歴の総数', len(R), ' current_revision_status', R['current_revision_status'].value_counts().to_dict())
# R7 の行(法令ID が決まった行)
cnt = d[d.law_id != ''].groupby('law_id').size()
def report(label, mask):
    laws = set(R.loc[mask, 'law_id'])
    print(f'  {label}: 法令 {len(laws)} / 根拠にする手続(R7 の行) {int(cnt.reindex(list(laws)).fillna(0).sum())}')
    return laws
print(f'\n# {FROM} 以降(その日を含む)')
upd = R['updated'].str[:10] >= FROM
enf = R['amendment_enforcement_date'] >= FROM
prm = R['amendment_promulgate_date'] >= FROM
uen = R['current_revision_status'] == 'UnEnforced'
rep = R['repeal_date'] >= FROM
A = report('(1) 施行期日がこの日以降の改正履歴がある', enf & (R['amendment_enforcement_date'] != ''))
A1 = report('    うち 施行済み(UnEnforced でない)の履歴がある', enf & ~uen & (R['amendment_enforcement_date'] != ''))
A2 = report('    うち 未施行(UnEnforced)の履歴がある', enf & uen)
report('(1b) 施行期日が空で未施行の履歴がある(施行日未定など)', uen & (R['amendment_enforcement_date'] == ''))
B = report('(2) 改正法令の公布日がこの日以降の履歴がある', prm & (R['amendment_promulgate_date'] != ''))
C = report('(3) updated(正誤等による更新日時)がこの日以降の履歴がある', upd & (R['updated'] != ''))
D = report('(4) 廃止日がこの日以降', rep & (R['repeal_date'] != ''))
allset = A | B | C | D
print(f'  (1)〜(4) のいずれか: 法令 {len(allset)} / 手続 {int(cnt.reindex(list(allset)).fillna(0).sum())}')
pd.DataFrame({'law_id': sorted(allset)}).assign(
    施行日以降改正=lambda x: x.law_id.isin(A), 公布日以降=lambda x: x.law_id.isin(B), updated以降=lambda x: x.law_id.isin(C), 廃止=lambda x: x.law_id.isin(D),
    手続数=lambda x: x.law_id.map(cnt)).to_csv('out/updated_laws.csv', index=False)
# 参考: 追加の呼び出し無しでできる照合 (asof=2025-11-01 一覧と現時点一覧の law_revision_id の違い)
L1 = pd.read_csv('data/api/laws_asof_2025-11-01.csv', dtype=str, keep_default_na=False).set_index('law_id')['law_revision_id']
L2 = pd.read_csv('data/api/laws_asof_current.csv', dtype=str, keep_default_na=False).set_index('law_id')['law_revision_id']
ch = {l for l in ids if l in L1.index and l in L2.index and L1[l] != L2[l]}
print(f'\n参考: 一覧(asof=2025-11-01)と一覧(現時点, 2026-11-18 取得)で law_revision_id が違う法令 {len(ch)} / 手続 {int(cnt.reindex(list(ch)).fillna(0).sum())}')
print(f'      (1) の施行済みとの一致: 両方 {len(ch & A1)} / 一覧比較だけ {len(ch - A1)} / 履歴だけ {len(A1 - ch)}')
