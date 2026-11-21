"""初めの期間(2025-11-02〜2026-11-18)の補い: 根拠の法令の廃止・失効を、別のファイルで足す。標準ライブラリだけ。初めのファイル(data/rdf/*.ttl.gz)は変えない。
初めの比べ(61_build_changes.py)は条文の文言だけを見ていて、法令の廃止・失効を見ていなかった。
使い方(公開用のリポジトリの一番上で): python3 scripts/60_law_status_supplement.py --found 2026-11-21 [--offline]
  - e-Gov 法令API v2 の法令一覧(廃止等の状態で絞ったもの。law_status.py)を使う。--offline なら手元に残した答えだけを使う(取らない)。
  - 期間の中で廃止・失効した法令: 区分「根拠の法令が廃止・失効した」の記録(jpp:LawStatusChange)。見つけた日は --found、
    あとで比べた理由は「初めの比べは法令の廃止を見ていなかった」(code/recheck-reason/law-status-not-checked)。
  - 期間の始め以前に廃止・失効していた法令: 法令の状態(jpp:LawStatus)だけ。
  - 分類しない法令(今の版の状態が Repeal でない、または日付が無い): e-Gov が返した値だけ(jpp:LawStatusUnclear)。
  - 書くファイル: data/rdf/weekly/supplement_law-status_2025-11-01_2026-11-18.ttl.gz(同じ中身なら同じバイト)。
    手続ごとの一覧(手続ID・手続名・法令名・状態・日付)を --csv に書く。"""
import sys, os, re, io, csv, gzip, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import egov, law_status
from rdf_config import BASE, PREFIXES
ap = argparse.ArgumentParser(); ap.add_argument('--found', required=True); ap.add_argument('--offline', action='store_true')
ap.add_argument('--data', default='data/rdf'); ap.add_argument('--csv')
A = ap.parse_args()
START, END = '2025-11-01', '2026-11-18'; PER = f'{START}_{END}'
def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(p): return f'<{BASE}{p}>'
law_procs = collections.defaultdict(set); cur = None
for line in gzip.open(f'{A.data}/procedures.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'record/r7/([^/>]+)/citation>', line)
    if m: cur = m.group(1); continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:citedLaw <' + re.escape(BASE) + r'law/([^>]+)>', line)
    if m and cur: law_procs[m.group(1)].add(cur)
LS, urls, err = law_status.fetch(egov, offline=A.offline, refresh=False)
if LS is None: raise SystemExit(f'廃止・失効の一覧を取れなかった: {err}')
chg, st, unclear = [], [], []
for lid in sorted(law_procs):
    info = LS.get(lid)
    if not info: continue
    j = law_status.judge(info, START, END)
    if j == 'in-period': chg.append((lid, info)); st.append((lid, info))
    elif j == 'before': st.append((lid, info))
    elif j == 'unclear' or j == 'after': unclear.append((lid, info))
os.makedirs(f'{A.data}/weekly', exist_ok=True)
fn = f'{A.data}/weekly/supplement_law-status_{PER}.ttl.gz'
buf = io.StringIO()
for k, v in PREFIXES.items(): buf.write(f'@prefix {k}: <{v}> .\n')
buf.write('\n')
def s(subj, pos): pos = [(p, o) for p, o in pos if o is not None]; buf.write(subj + ' ' + ' ;\n    '.join(f'{p} {o}' for p, o in pos) + ' .\n')
ACT = iri(f'activity/law-status-supplement/{A.found}')
s(ACT, [('a', 'prov:Activity'), ('rdfs:label', lit(f'初めの期間の補い: 根拠の法令の廃止・失効({A.found}、scripts/60_law_status_supplement.py)', 'ja')), ('prov:used', iri('source/egov-law-api-v2')),
        ('rdfs:comment', lit('初めの比べ(scripts/61_build_changes.py)は条文の文言だけを見ていて、法令の廃止・失効を見ていなかった。その分を別のファイルで足した。初めのファイルは変えていない。', 'ja'))])
for lid, info in chg: law_status.change_node(s, iri, lit, lid, info, PER, A.found, urls[0], ACT, law_procs[lid], recheck='law-status-not-checked')
for lid, info in st: law_status.status_node(s, iri, lit, lid, info, A.found, urls[0])
for lid, info in unclear: law_status.unclear_node(s, iri, lit, lid, info, A.found, urls[0])
with open(fn, 'wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as g: g.write(buf.getvalue().encode('utf-8'))
procs = set().union(*[law_procs[l] for l, _ in chg]) if chg else set()
print(f'書いたファイル: {fn}')
print(f'期間の中で廃止・失効した法令 {len(chg)}・手続 {len(procs)} / 法令の状態 {len(st)}(期間の始め以前 {len(st) - len(chg)}) / 分類しない {len(unclear)}: {[l for l, _ in unclear]}')
if A.csv:
    title = {}; cur = None
    for line in gzip.open(f'{A.data}/procedures.ttl.gz', 'rt', encoding='utf-8'):
        m = re.match(r'^<' + re.escape(BASE) + r'procedure/([^/>]+)> a cpsv:PublicService', line)
        if m: cur = m.group(1); continue
        if line.startswith('<'): cur = None; continue
        m = re.match(r'\s+dct:title "((?:[^"\\]|\\.)*)"', line)
        if m and cur: title[cur] = m.group(1)
    with open(A.csv, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['手続ID', '手続名', '法令ID', '法令名', '状態(e-Gov の repeal_status)', '日付(repeal_date)', '見つけた日', '出典'])
        for lid, info in chg:
            for p in sorted(law_procs[lid]): w.writerow([p, title.get(p, ''), lid, info.get('law_title', ''), info['repeal_status'], info['repeal_date'], A.found, urls[0]])
    print(f'手続ごとの一覧: {A.csv}')
