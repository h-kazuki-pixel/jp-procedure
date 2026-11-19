"""毎週の追跡の結果を status.json に書き、README の「最後に確かめた日」の行を、そのファイルから書き直す。標準ライブラリだけ。

使い方(リポジトリの一番上で):
  python3 scripts/74_write_status.py --checks success   … 追跡のあと。確かめ(SHACL・全体の数)が通ったとき
  python3 scripts/74_write_status.py --checks skipped   … 足した記録が 0 件で、確かめを回さなかったとき
  python3 scripts/74_write_status.py --readme-only      … status.json はそのままで、README の行だけ書き直す

status.json の中身:
  last_checked … 最後に確かめた日(data/tracking/state.json の checked_through。e-Gov の更新をこの日まで見た)
  base         … 初めに比べた期間
  weeks        … 週ごとの結果。期間、確かめた日時(UTC)、足した改正の記録の件数(0 件を含む)、手続の行、期間内の改正の数、取得の失敗、確かめの結果
確かめが通らなかった週は、ワークフローが main に入れないので、ここには残らない(Issue が立つ)。
"""
import argparse, datetime, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument('--checks', choices=['success', 'skipped'])
ap.add_argument('--tracking', default='data/tracking')
ap.add_argument('--out', default='status.json')
ap.add_argument('--readme', default='README.md')
ap.add_argument('--readme-only', action='store_true')
A = ap.parse_args()

st = json.load(open(A.out, encoding='utf-8')) if os.path.exists(A.out) else {
    'last_checked': json.load(open(f'{A.tracking}/state.json', encoding='utf-8'))['checked_through'],
    'base': {'period': ['2025-11-01', '2026-11-18'], 'note': '初めに比べた期間(scripts/61_build_changes.py)。毎週の追跡はこの次の日から'},
    'weeks': []}
if A.readme_only and not os.path.exists(A.out):   # 初めの 1 回: 週の結果はまだ無い
    with open(A.out, 'w', encoding='utf-8') as f: json.dump(st, f, ensure_ascii=False, indent=1); f.write('\n')
if not A.readme_only:
    if not A.checks: ap.error('--checks が要る')
    state = json.load(open(f'{A.tracking}/state.json', encoding='utf-8'))
    run = json.load(open(f'{A.tracking}/last_run.json', encoding='utf-8'))
    wk = {'period': run['period'], 'checked_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
          'records': run['records'], 'rows': run['rows'], 'revisions': run.get('revisions', 0), 'failures': len(run.get('failures') or []), 'checks': A.checks}
    st['weeks'] = [w for w in st['weeks'] if w['period'] != wk['period']] + [wk]
    st['last_checked'] = state['checked_through']
    with open(A.out, 'w', encoding='utf-8') as f: json.dump(st, f, ensure_ascii=False, indent=1); f.write('\n')

# README の行(<!-- status --> と <!-- /status --> のあいだ)を、status.json から書き直す
w = st['weeks'][-1] if st['weeks'] else None
line = (f"最後に確かめた日: **{st['last_checked']}**。"
        + (f"直近の週({w['period'][0]}〜{w['period'][1]})に足した改正の記録: {w['records']:,} 件。" if w else 'まだ毎週の追跡は動いていない。')
        + '(`status.json` から書いた行)')
src = open(A.readme, encoding='utf-8').read()
new, n = re.subn(r'(<!-- status -->).*?(<!-- /status -->)', lambda m: m.group(1) + line + m.group(2), src, flags=re.S)
if n != 1: raise SystemExit(f'README に <!-- status --> の行が {n} 個ある(1 個のはず)')
if new != src: open(A.readme, 'w', encoding='utf-8').write(new)
print(line)
