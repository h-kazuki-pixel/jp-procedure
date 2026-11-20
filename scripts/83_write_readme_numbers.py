"""README の数を、データから書き直す。.venv の python(pyoxigraph)。
使い方: python3 scripts/83_write_readme_numbers.py <店の場所> <公開用のリポジトリ>
README の中の <!-- n:キー -->数<!-- /n --> の「数」を、店への問いとファイルの大きさから出した値に置き換える(3 桁ごとにコンマ)。
- 印の中だけを書き直す。印の無い数には触らない。知らないキーがあれば止める。
- 全体の数の確かめ(57_count_checks.py に README=README.md を渡す)が、SPARQL を使わずに数えた数と README の数を比べる。
- 何度流しても、同じデータなら同じ README になる。"""
import sys, os, re, csv, glob, pyoxigraph as ox
STORE, R = sys.argv[1], sys.argv[2]
st = ox.Store.read_only(STORE)
P = open(os.path.join(R, 'queries', 'PREFIXES.rq'), encoding='utf-8').read()
def one(q): r = list(st.query(P + q)); return int(r[0][0].value)
N = {}
N['triples_total'] = len(st)
N['procedures'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a cpsv:PublicService }')
N['records'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a jpp:SurveyRecord }')
N['organisations'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a cv:PublicOrganisation }')
N['laws'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a eli:LegalResource }')
sub_all = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a eli:LegalResourceSubdivision }')
# 改正の記録の移った先・候補として足した条・項・号(61・70 が「改正の記録の移った先・候補として足した」の rdfs:comment を付けたもの)
N['subdivisions_added'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a eli:LegalResourceSubdivision ; rdfs:comment ?cm FILTER(STRSTARTS(STR(?cm), "改正の記録の移った先・候補として足した")) }')
N['subdivisions_base'] = sub_all - N['subdivisions_added']
N['expressions'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a eli:LegalExpression }')
N['versions_zero'] = one('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a eli:LegalExpression ; jpp:lawRevision ?r FILTER(STRENDS(?r, "_000000000000000")) }')
N['changes'] = one('SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a jpp:ProvisionChange }')
N['change_rows'] = one('SELECT (COUNT(*) AS ?n) WHERE { ?c a jpp:ProvisionChange ; jpp:affects ?p }')
BASE = '?per dcat:startDate "2025-11-01"^^xsd:date ; dcat:endDate "2026-11-18"^^xsd:date .'
# 初めの期間の改正: 施行期日がその期間の中にある改正。毎週の追跡が初めて足した改正で、初めて見つけた日(jpp:firstFoundOn)が期間の終わりより後のものは除く(初めに比べたときには e-Gov に無かった)
LATE = ' FILTER NOT EXISTS { ?r jpp:firstFoundOn ?rf FILTER(?rf > "2026-11-18"^^xsd:date) }'
N['revisions'] = one('SELECT (COUNT(DISTINCT ?r) AS ?n) WHERE { ?r a jpp:LawRevision ; jpp:enforcementDate ?d FILTER(?d > "2025-11-01"^^xsd:date && ?d <= "2026-11-18"^^xsd:date)' + LATE + ' }')
N['revision_laws'] = one('SELECT (COUNT(DISTINCT ?l) AS ?n) WHERE { ?r a jpp:LawRevision ; jpp:revisionOf ?l ; jpp:enforcementDate ?d FILTER(?d > "2025-11-01"^^xsd:date && ?d <= "2026-11-18"^^xsd:date)' + LATE + ' }')
N['revisions_linked'] = one(f'SELECT (COUNT(DISTINCT ?r) AS ?n) WHERE {{ ?c a jpp:ProvisionChange ; dct:temporal ?per ; jpp:lawRevisionInPeriod ?r . {BASE} }}')
for r in st.query(P + f'SELECT ?k (COUNT(DISTINCT ?c) AS ?rec) (COUNT(?p) AS ?rows) WHERE {{ ?c a jpp:ProvisionChange ; dct:temporal ?per ; jpp:changeKind ?k ; jpp:affects ?p . {BASE} }} GROUP BY ?k'):
    k = r['k'].value.rsplit('/', 1)[-1]; N[f'kind_rec:{k}'] = int(r['rec'].value); N[f'kind_rows:{k}'] = int(r['rows'].value)
N['law_level'] = one(f'''SELECT (COUNT(DISTINCT ?ps) AS ?n) WHERE {{ ?r a jpp:LawRevision ; jpp:revisionOf ?law ; jpp:enforcementDate ?d .
  FILTER(?d > "2025-11-01"^^xsd:date && ?d <= "2026-11-18"^^xsd:date){LATE}
  ?c jpp:citedLaw ?law ; jpp:matchResult ?m . FILTER(?m IN (<https://w3id.org/jp-procedure/code/match-result/article>, <https://w3id.org/jp-procedure/code/match-result/paragraph>, <https://w3id.org/jp-procedure/code/match-result/item>)) ?ps jpp:hasCitation ?c }}''')
for f in sorted(glob.glob(os.path.join(R, 'data', 'rdf', '*.ttl.gz'))): N['size:data/rdf/' + os.path.basename(f)] = os.path.getsize(f)
N['size:jsonld_total'] = sum(os.path.getsize(f) for f in glob.glob(os.path.join(R, 'data', 'jsonld', '*.jsonld.gz')))
for f in sorted(glob.glob(os.path.join(R, 'data', 'csv', '*.csv'))):
    N['size:data/csv/' + os.path.basename(f)] = os.path.getsize(f)
    N['csv_rows:' + os.path.basename(f)] = sum(1 for _ in csv.reader(open(f, encoding='utf-8'))) - 1
N['size:data/redactions.csv'] = os.path.getsize(os.path.join(R, 'data', 'redactions.csv'))
p = os.path.join(R, 'README.md'); src = open(p, encoding='utf-8').read()
used = set()
def rep(m):
    k = m.group(1)
    if k not in N: raise SystemExit(f'README の印のキー {k} を知らない')
    used.add(k); return f'<!-- n:{k} -->{N[k]:,}<!-- /n -->'
new = re.sub(r'<!-- n:([^ ]+) -->[^<]*<!-- /n -->', rep, src)
if new != src: open(p, 'w', encoding='utf-8').write(new)
print(f'README の印 {len(re.findall(r"<!-- n:", new))} か所(キー {len(used)})を書き直した。使わなかったキー: {sorted(set(N) - used)}')
