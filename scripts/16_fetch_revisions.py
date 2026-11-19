"""各法令の改正履歴一覧(/law_revisions/{law_id})を1回ずつ取る。絞り込みの引数は付けず全履歴を取り、手元で日付を見る。"""
import sys, time, pandas as pd; sys.path.insert(0, 'scripts'); import egov
d = pd.read_csv('out/r7_law_id.csv', dtype=str, keep_default_na=False)
ids = sorted(set(d.law_id) - {''}); t0 = time.time(); st = {}
for i, lid in enumerate(ids, 1):
    b = egov.get(f'/law_revisions/{lid}', {'response_format': 'json'})
    st[lid] = b.get('_status')
    if i % 100 == 0 or i == len(ids): print(f'{i}/{len(ids)} {time.time()-t0:.0f}s', flush=True)
pd.Series(st, name='status').to_csv('out/16_fetch_status.csv', index_label='law_id')
print('status', pd.Series(st).value_counts().to_dict())
