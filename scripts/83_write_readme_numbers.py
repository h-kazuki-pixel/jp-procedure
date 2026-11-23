"""README の数を、データから書き直す。.venv の python(pyoxigraph)。
使い方: python3 scripts/83_write_readme_numbers.py <店の場所> <公開用のリポジトリ>
README の中の <!-- n:キー -->数<!-- /n --> の「数」を、店への問いとファイルの大きさから出した値に置き換える(3 桁ごとにコンマ)。
冒頭の例の文(<!-- e:手続ID -->文<!-- /e -->)も、改正の記録の旧い文言・新しい文言と、法令の状態から書く(手で書かない)。
隣に view.html があれば、その JavaScript なしの要約(同じ印)と、meta description・og:description の「例: 」の後ろにも同じ文を書く。
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
# 主な数: 初めの期間・毎週の追跡・補い(根拠の法令の廃止・失効)に分ける
N['changes_base'] = one('SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a jpp:ProvisionChange ; dct:temporal ?per . ?per dcat:startDate "2025-11-01"^^xsd:date ; dcat:endDate "2026-11-18"^^xsd:date . }')
N['change_rows_base'] = one('SELECT (COUNT(*) AS ?n) WHERE { ?c a jpp:ProvisionChange ; dct:temporal ?per ; jpp:affects ?p . ?per dcat:startDate "2025-11-01"^^xsd:date ; dcat:endDate "2026-11-18"^^xsd:date . }')
N['changes_weekly'] = N['changes'] - N['changes_base']; N['change_rows_weekly'] = N['change_rows'] - N['change_rows_base']
# 調査で、名と所管府省庁が同じ手続(手続 ID が別)の組の数と、その手続の数(README・閲覧ページの数の断り)
_g = st.query(P + 'SELECT ?t ?o (COUNT(DISTINCT ?ps) AS ?k) WHERE { ?ps a cpsv:PublicService ; dct:title ?t ; cv:hasCompetentAuthority ?o } GROUP BY ?t ?o HAVING (COUNT(DISTINCT ?ps) > 1)')
_g = [int(r['k'].value) for r in _g]; N['same_name_groups'] = len(_g); N['same_name_rows'] = sum(_g)
N['law_status_laws'] = one('SELECT (COUNT(DISTINCT ?l) AS ?n) WHERE { ?c a jpp:LawStatusChange ; jpp:law ?l }')
N['law_status_rows'] = one('SELECT (COUNT(*) AS ?n) WHERE { ?c a jpp:LawStatusChange ; jpp:affects ?p }')
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
# ---- 例の文 ----
import html
VIEW = 'https://h-kazuki-pixel.github.io/jp-procedure/view.html'
PS = 'https://w3id.org/jp-procedure/procedure/'
BASEPER = '?per dcat:startDate "2025-11-01"^^xsd:date ; dcat:endDate "2026-11-18"^^xsd:date .'
AMT = re.compile(r'[〇一二三四五六七八九十百千万億]+円')
def rows(q): return [{k: (r[k].value if r[k] is not None else None) for k in [v.value for v in res.variables]} for res in [st.query(P + q)] for r in res]
def title_org(i):
    r = rows(f'SELECT ?t ?o WHERE {{ <{PS}{i}> dct:title ?t ; cv:hasCompetentAuthority ?a . ?a skos:prefLabel ?o }}')
    if len(r) != 1: raise SystemExit(f'例の手続 {i} の名・府省庁が 1 つに決まらない({len(r)})')
    return r[0]['t'], r[0]['o']
def amounts(old, new):
    # 旧い文言と新しい文言の額(漢数字+円)を前から並べ、違う所を出す。1 か所でなければ止める
    a, b = AMT.findall(old), AMT.findall(new)
    d = [(x, y) for x, y in zip(a, b) if x != y]
    if len(a) != len(b) or len(d) != 1: raise SystemExit(f'例の額が 1 か所に決まらない(旧 {a} / 新 {b})')
    return d[0]
def ex_law_status(i):
    # 根拠に挙げる法令の状態(jpp:LawStatusChange。初めの期間)の法令の名・日付・状態
    t, o = title_org(i)
    r = rows(f'SELECT ?law ?d ?stl WHERE {{ ?c a jpp:LawStatusChange ; jpp:affects <{PS}{i}> ; jpp:law ?l ; jpp:repealDate ?d ; jpp:repealStatus ?s ; dct:temporal ?per . {BASEPER} '
             '?l rdfs:label ?law . ?s skos:prefLabel ?stl }')
    if len(r) != 1: raise SystemExit(f'例の手続 {i} の法令の状態が 1 つに決まらない({len(r)})')
    r = r[0]; kind = '規則' if r['law'].endswith('規則') else '法令'
    return f'[手続 {i}「{t}」]({VIEW}#/procedure/{i})', f'手続「{t}」({o})が根拠に挙げる{kind}({r["law"]})は、e-Gov で {r["d"]} に{r["stl"]}と記録されています。'
def ex_amount(i):
    # 同じ条・項・号の改正の記録 2 つ(初めの期間と毎週の追跡)の、旧い文言・新しい文言から変わった額を出す。毎週の追跡の日付は、見つけた改正の施行期日
    t, o = title_org(i)
    r = rows(f'SELECT ?s ?law ?pl ?ot ?nt ?fd WHERE {{ ?c a jpp:ProvisionChange ; jpp:affects <{PS}{i}> ; jpp:provision ?p ; jpp:oldVersion ?ov ; jpp:newVersion ?nv ; dct:temporal ?per . '
             '?per dcat:startDate ?s . ?p rdfs:label ?pl ; eli:is_part_of+ ?l . ?l a eli:LegalResource ; rdfs:label ?law . ?ov jpp:text ?ot . ?nv jpp:text ?nt . '
             'OPTIONAL { ?c jpp:foundRevision ?fr . ?fr jpp:enforcementDate ?fd } } ORDER BY ?s')
    if len(r) != 2 or r[0]['s'] != '2025-11-01' or r[1]['fd'] is None or len({(x['law'], x['pl']) for x in r}) != 1:
        raise SystemExit(f'例の手続 {i} の改正の記録が、同じ条・項・号の初めの期間と毎週の追跡の 2 つでない({[(x["s"], x["pl"]) for x in r]})')
    (a, b), (c, d) = amounts(r[0]['ot'], r[0]['nt']), amounts(r[1]['ot'], r[1]['nt'])
    return f'[手続 {i}「{t}」]({VIEW}#/procedure/{i})', (f'{r[0]["law"]} {r[0]["pl"]}の額が「{a}」から「{b}」に変わりました(初めの期間)。'
                                                     f'{r[1]["fd"]} 施行の改正で、「{c}」から「{d}」に変わりました(毎週の追跡)。')
EX = {'18109': ex_law_status('18109'), '107294': ex_amount('107294')}
for i, (lk, tx) in EX.items(): print(f'  例 {i}: {tx}')
def fill_ex(src, name, md):
    def rep(m):
        k = m.group(1)
        if k not in EX: raise SystemExit(f'{name} の例の印のキー {k} を知らない')
        return f'<!-- e:{k} -->' + (f'{EX[k][0]}: {EX[k][1]}' if md else html.escape(EX[k][1], quote=False)) + '<!-- /e -->'
    return re.sub(r'<!-- e:([0-9]+) -->[^<]*<!-- /e -->', rep, src), len(re.findall(r'<!-- e:', src))
vp = os.path.join(R, 'view.html')
if os.path.exists(vp):
    vs = open(vp, encoding='utf-8').read()
    vn, ne = fill_ex(vs, 'view.html', False)
    # 閲覧ページの <!-- n:キー --> も README と同じ数で書く(数の断りの組の数)
    def vrep(m):
        if m.group(1) not in N: raise SystemExit(f'view.html の印のキー {m.group(1)} を知らない')
        return f'<!-- n:{m.group(1)} -->{N[m.group(1)]:,}<!-- /n -->'
    vn = re.sub(r'<!-- n:([^ ]+) -->[^<]*<!-- /n -->', vrep, vn)
    # meta description・og:description の「例: 」の後ろ(属性の中なので印を置けない)は、はじめの画面の大きな例(CONFIG.featured)の文にする
    fid = re.search(r"featured: '([0-9]+)'", vn).group(1)
    vn, nm = re.subn(r'(<meta (?:name="description"|property="og:description") content="[^"]*?例: )[^"]*(">)', lambda m: m.group(1) + html.escape(EX[fid][1]) + m.group(2), vn)
    if nm != 2: raise SystemExit(f'view.html の meta・og:description の「例: 」が 2 か所でない({nm})')
    if vn != vs: open(vp, 'w', encoding='utf-8').write(vn)
    print(f'  view.html の例の印 {ne} か所と meta {nm} か所を書いた')
p = os.path.join(R, 'README.md'); src0 = open(p, encoding='utf-8').read()
src, ne = fill_ex(src0, 'README.md', True); print(f'  README の例の印 {ne} か所を書いた')
used = set()
def rep(m):
    k = m.group(1)
    if k not in N: raise SystemExit(f'README の印のキー {k} を知らない')
    used.add(k); return f'<!-- n:{k} -->{N[k]:,}<!-- /n -->'
new = re.sub(r'<!-- n:([^ ]+) -->[^<]*<!-- /n -->', rep, src)
if new != src0: open(p, 'w', encoding='utf-8').write(new)
print(f'README の印 {len(re.findall(r"<!-- n:", new))} か所(キー {len(used)})を書き直した。使わなかったキー: {sorted(set(N) - used)}')
