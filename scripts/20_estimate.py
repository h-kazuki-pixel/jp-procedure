"""改正の追跡: 取得する法令の数と所要時間の見込み。取得はしない。"""
import sys, os, pandas as pd; sys.path.insert(0, 'scripts'); import egov
FROM, TO, NEW = '2025-11-02', '2026-11-18', '2026-11-18'   # NEW = 取得する版の asof
d = pd.read_csv('out/full_check.csv', dtype=str, keep_default_na=False)
R = pd.read_csv('out/law_revisions.csv', dtype=str, keep_default_na=False)
OK = ['号まで一致', '項まで', '条まで']
miss = d[(d.結果_追加 == '法令はあるが条が無い') | ((d.結果_追加 == '条まで') & d.補足_追加.isin(['項が見つからない'])) | d.補足_追加.eq('号が見つからない')]
M = set(miss.law_id)
print(f'(2) 条・項・号が無い行 {len(miss)} / 法令 {len(M)}')
e = R.amendment_enforcement_date
win = R[(e >= FROM) & (e <= TO)]
print(f'改正履歴で施行期日が {FROM}〜{TO} の履歴 {len(win)} 件 / 法令 {win.law_id.nunique()}  状態 {win.current_revision_status.value_counts().to_dict()}')
matched = d[d.結果_追加.isin(OK)]
W = set(win.law_id) & set(matched.law_id)
print(f'(3) 条以上で一致した行 {len(matched)} / うち対象法令の行 {int(matched.law_id.isin(W).sum())} / 対象法令 {len(W)}')
X = {'507M60000002095'}
need = sorted(M | W | X)
p = lambda lid: {'asof': NEW, 'response_format': 'json', 'json_format': 'full'}
cached = [l for l in need if egov.get(f'/law_data/{l}', p(l), offline=True).get('_status') != '未取得']
print(f'取得する法令(2・3・404 の法令の和) {len(need)} (2 だけ {len(M - W)}, 3 だけ {len(W - M)}, 両方 {len(M & W)}, 404 の法令 1)  取得済み {len(cached)}')
n = len(need) - len(cached)
print(f'見込み: 下限(1.05 秒間隔) {n*1.05/60:.1f} 分 / 前回の本文取得の実測 (3472 秒 / 2627 件 = {3472/2627:.2f} 秒) で {n*3472/2627/60:.1f} 分')
pd.DataFrame({'law_id': need, '2の対象': [l in M for l in need], '3の対象': [l in W for l in need]}).to_csv('out/20_targets.csv', index=False)
