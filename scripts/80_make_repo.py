"""公開用のリポジトリの形(既定は作業フォルダと同じ階層の jp-procedure。環境変数 REPO で変えられる)に、データ・スクリプト・問い・形・報告を写し、JSON-LD・CSV・stats.json を作る。.venv の python。
- 人やプロジェクトで変わる値(プロジェクト ID・番号・組織・メールアドレス・手元のパス・名前)は、写すときにこのスクリプトの中で置き換え文字にする(REPL)。
- 何度流しても同じ公開用フォルダになる(gzip の日時は 0、空白ノードの名前は出てきた順に付け直す、日時を書かない)。
- 公開用のリポジトリで直接書いたもの(README.md・deploy.md・view.html・status.json・CLAUDE.md・LICENSE・w3id/・deploy/・.github/・scripts/README.md・scripts/74 など)には触らない。
- data/tracking/ は、無いときだけ作る(毎週の追跡が書き足すので)。
- 流したあと、置き換え漏れを gzip の中まで探す(scripts/81_scan_repo.py)。push はしない。
使い方: .venv/bin/python scripts/80_make_repo.py   (store/oxigraph は 62_oxigraph_load.py で rdf/ から作ったもの)"""
import os, re, io, gzip, glob, shutil, csv, json, subprocess, sys, pyoxigraph as ox
R = os.path.abspath(os.path.expanduser(os.environ.get('REPO', '../jp-procedure')))   # 既定は作業フォルダと同じ階層の jp-procedure
os.makedirs(R, exist_ok=True)
def mk(p): os.makedirs(os.path.join(R, p), exist_ok=True); return os.path.join(R, p)
def gz(path, data):   # 決まった形の gzip(日時 0、ファイル名なし)
    with open(path, 'wb') as f, gzip.GzipFile(filename='', mode='wb', fileobj=f, mtime=0) as g: g.write(data)
def put(path, text):
    if not os.path.exists(path) or open(path, encoding='utf-8').read() != text: open(path, 'w', encoding='utf-8').write(text)

# ---- 置き換え(上から順に当てる)
SCRATCH = os.environ.get('TMPDIR', '/private/tmp').rstrip('/')
HOME = os.path.expanduser('~'); WORK = os.getcwd()
def tilde(p): return '~' + p[len(HOME):] if p.startswith(HOME + '/') else p
REPL = [   # 形で置き換えるもの(公開してよい)。公開しない値の置き換えは REPL_PRIVATE のファイルから読む
    (r'/private/tmp/claude-[0-9]+/[^\s`)"\']*', '<一時フォルダ>'),
    (re.escape(WORK) + r'/?', ''), (re.escape(tilde(WORK)) + r'/?', ''),   # 作業フォルダ(このスクリプトを動かす場所)
    (re.escape(R) + r'/?', ''), (re.escape(tilde(R)) + r'/?', ''),         # 公開用のリポジトリ
    (re.escape(HOME), '~'),
    (r'@jp-procedure\.iam\.gserviceaccount\.com', '@<PROJECT_ID>.iam.gserviceaccount.com'),
    (r'pkg\.dev/jp-procedure/', 'pkg.dev/<PROJECT_ID>/'),
    (r'projects/jp-procedure\b(?!-)', 'projects/<PROJECT_ID>'),
    (r'--project([ =])jp-procedure\b(?!-)', r'--project\1<PROJECT_ID>'),
    (r'gs://jp-procedure_cloudbuild', 'gs://<PROJECT_ID>_cloudbuild'),
    (r'プロジェクト `jp-procedure`', 'プロジェクト `<PROJECT_ID>`'),
    (r'プロジェクト ID は `?jp-procedure`?', 'プロジェクト ID は `<PROJECT_ID>`'),
    (r'`GCP_PROJECT_ID` = `jp-procedure`', '`GCP_PROJECT_ID` = `<PROJECT_ID>`'),
    (r'P=jp-procedure\b(?!-)', 'P=<PROJECT_ID>'),
]
# 公開しない値(プロジェクト番号・組織・名前など)の置き換えは、公開しないファイルから読む(1 行に「正規表現<TAB>置き換え文字」)。
# 無ければ止める(置き換えずに写してしまわないように)
PRIV = os.environ.get('REPL_PRIVATE', 'out/repo_private_repl.tsv')
if not os.path.exists(PRIV): raise SystemExit(f'公開しない値の置き換えのファイル {PRIV} が無い')
REPL[4:4] = [tuple(line.rstrip('\n').split('\t')) for line in open(PRIV, encoding='utf-8') if line.strip() and not line.startswith('#')]   # 手元のパスのあと、ほかより先に、書いた順に当てる
def clean(t):
    for a, b in REPL: t = re.sub(a, b, t)
    return t

# ---- data/rdf(そのまま写す)
d = mk('data/rdf')
for f in sorted(glob.glob('rdf/*.ttl.gz')): shutil.copyfile(f, f'{d}/{os.path.basename(f)}')
# ---- vocab.ttl(語彙。w3id の def の転送先。GitHub Pages で gzip でないまま出す)
put(f'{R}/vocab.ttl', gzip.open('rdf/vocab.ttl.gz', 'rt', encoding='utf-8').read())
# ---- data/redactions.csv(伏せた所の一覧。手続ID・列・位置・種類・理由だけ。伏せた中身は書いていない)
put(f'{d}/../redactions.csv', open('redactions.csv', encoding='utf-8').read())
# ---- data/jsonld(展開形。空白ノードの名前を出てきた順に付け直す)
d = mk('data/jsonld')
for f in sorted(glob.glob('rdf/*.ttl.gz')):
    n = os.path.basename(f).replace('.ttl.gz', ''); buf = io.BytesIO()
    ox.serialize(ox.parse(gzip.open(f), ox.RdfFormat.TURTLE), buf, ox.RdfFormat.JSON_LD)
    names = {}; t = re.sub(rb'_:[0-9A-Za-z]+', lambda m: names.setdefault(m.group(0), b'_:b%d' % len(names)), buf.getvalue())
    gz(f'{d}/{n}.jsonld.gz', t)
# ---- data/csv(store/oxigraph に問いを投げる)
st = ox.Store.read_only('store/oxigraph'); PRE = open('queries/PREFIXES.rq').read()
Q = {'procedures_provisions.csv': """
SELECT ?procedure_id ?procedure_title ?ministry ?law_id ?law_title ?citation_text ?match_result ?provision_label ?provision_uri ?procedure_uri WHERE {
  ?procedure_uri a cpsv:PublicService ; dct:identifier ?procedure_id ; dct:title ?procedure_title ; cv:hasCompetentAuthority/skos:prefLabel ?ministry ; jpp:hasCitation ?c .
  ?c jpp:citationText ?citation_text ; jpp:matchResult/skos:notation ?match_result .
  OPTIONAL { ?c jpp:citedLaw ?law . ?law eli:id_local ?law_id ; rdfs:label ?law_title . }
  OPTIONAL { ?procedure_uri cv:hasLegalResource ?provision_uri . OPTIONAL { ?provision_uri rdfs:label ?provision_label . } }
} ORDER BY ?procedure_id""",
     'changes.csv': """
SELECT ?change_uri ?law_id ?law_title ?provision_label ?kind ?r0 ?r1 ?moved_to_label
       (GROUP_CONCAT(DISTINCT ?cand_label; separator=" / ") AS ?candidates) ?period_start ?period_end
       (COUNT(DISTINCT ?ps) AS ?procedure_count) (GROUP_CONCAT(DISTINCT ?pid; separator=" ") AS ?procedure_ids)
       (COUNT(DISTINCT ?rev) AS ?revisions_in_period) (GROUP_CONCAT(DISTINCT ?rvs; separator=" / ") AS ?reviews) ?provision_uri ?old_version ?new_version WHERE {
  ?change_uri a jpp:ProvisionChange ; jpp:provision ?provision_uri ; jpp:changeKind/skos:prefLabel ?kind ; jpp:oldVersion ?old_version ; jpp:affects ?ps ;
              dct:temporal [ dcat:startDate ?period_start ; dcat:endDate ?period_end ] .
  ?ps dct:identifier ?pid .
  ?provision_uri rdfs:label ?provision_label ; eli:is_part_of+ ?law . ?law eli:id_local ?law_id ; rdfs:label ?law_title .
  OPTIONAL { ?change_uri jpp:newVersion ?new_version } OPTIONAL { ?change_uri jpp:r0 ?r0 } OPTIONAL { ?change_uri jpp:r1 ?r1 }
  OPTIONAL { ?change_uri jpp:movedTo/rdfs:label ?moved_to_label } OPTIONAL { ?change_uri jpp:candidate/rdfs:label ?cand_label }
  OPTIONAL { ?change_uri jpp:lawRevisionInPeriod ?rev }
  OPTIONAL { ?change_uri jpp:review ?rv . ?rv jpp:reviewerType/skos:notation ?rvt ; jpp:reviewDate ?rvd ; jpp:reviewResult/skos:notation ?rvr . BIND(CONCAT(?rvt, " ", STR(?rvd), " ", ?rvr) AS ?rvs) }
} GROUP BY ?change_uri ?law_id ?law_title ?provision_label ?kind ?r0 ?r1 ?moved_to_label ?period_start ?period_end ?provision_uri ?old_version ?new_version
ORDER BY ?law_id ?change_uri"""}
d = mk('data/csv'); csv_rows = {}
for fn, q in Q.items():
    res = st.query(PRE + q); vs = [v.value for v in res.variables]
    rows = [['' if s[v] is None else s[v].value for v in vs] for s in res]
    # GROUP_CONCAT の中の並びは店の作りで変わりうるので、並べ直す
    for r in rows:
        for k, v in enumerate(vs):
            if v == 'procedure_ids': r[k] = ' '.join(sorted(r[k].split(' '))) if r[k] else ''
            if v in ('candidates', 'reviews'): r[k] = ' / '.join(sorted(r[k].split(' / '))) if r[k] else ''
    buf = io.StringIO(newline=''); w = csv.writer(buf); w.writerow(vs); w.writerows(rows)
    put(f'{d}/{fn}', buf.getvalue()); csv_rows[fn] = len(rows)
del st
# ---- stats.json(閲覧ページのはじめの画面の数。queries/ の問いで出す)
subprocess.run([sys.executable, 'scripts/75_make_stats.py', 'store/oxigraph', f'{R}/stats.json', f'{R}/data/rdf'], check=True, stdout=subprocess.DEVNULL)
# ---- changed.json(閲覧ページの「変わった手続の一覧」と、違う所の抜き出し)
subprocess.run([sys.executable, 'scripts/82_make_changed_list.py', 'store/oxigraph', f'{R}/changed.json'], check=True, stdout=subprocess.DEVNULL)
# ---- queries / shapes
d = mk('queries')
for f in sorted(glob.glob('queries/*.rq')): put(f'{d}/{os.path.basename(f)}', open(f, encoding='utf-8').read())
put(f'{mk("shapes")}/shapes.ttl', open('rdf/shapes.ttl', encoding='utf-8').read())
# ---- scripts(作り直しに要るものだけ。置き換えを当てる)
KEEP = ['00_convert.py', '04a_fetch_laws.py', '04b_match_laws.py', '11_fetch_all.py', '12_full_check.py', '16_fetch_revisions.py', '17_updated.py', '20_estimate.py', '21_fetch_new.py',
        '22_amend_compare.py', '30_moves.py', '40_fix.py', '41_numref_boundary.py', '42_fix_rules.py', '43_fix_rules3.py', '44_fix_rules4.py', '45_fix_rules5.py', '50_build_rdf.py',
        '54_build_expressions.py', '56_split_for_shacl.py', '57_count_checks.py', '58_shacl_worker.py', '59_shacl_split.py', '59b_make_broken.py', '61_build_changes.py', '62_oxigraph_load.py',
        '63_queries.py', '64_check_moved_text.py', '65_check_rules_module.py', '66_check_versions.py', '67_server_bench.py', '68_cloudrun_bench.py', '69_cloudrun_metrics.py',
        '70_weekly_track.py', '73_check_min_bounds.py', '75_make_stats.py', '78_make_human_check.py', 'human_check_template.html', '80_make_repo.py', '82_make_changed_list.py', '83_write_readme_numbers.py', '81_scan_repo.py',
        'change_rules.py', 'redact.py', 'clause.py', 'common.py', 'common_load.py', 'egov.py', 'moves_lib.py', 'rdf_config.py']
d = mk('scripts')
for f in KEEP:   # 80・81 は置き換えの形そのものを書いたものなので、置き換えを当てずに写す(当てると形が壊れる)
    t = open(f'scripts/{f}', encoding='utf-8').read(); put(f'{d}/{f}', t if f in ('80_make_repo.py', '81_scan_repo.py') else clean(t))
shutil.rmtree(f'{d}/__pycache__', ignore_errors=True)
# ---- reports(作業の進め方の記述を除き、置き換えを当てて写す)
d = mk('reports'); mk('reports/review')
DROP = [re.compile(r'^- .*push はしていない.*$'), re.compile(r'^- 外部への公開\(push 等\)はしていない.*$'), re.compile(r'^- 作業フォルダに `CLAUDE.md` を作り.*$')]
for f in sorted(glob.glob('*-report*.md')):
    if f.startswith('publish-prep'): continue
    lines = [l for l in open(f, encoding='utf-8').read().split('\n') if not any(p.match(l) for p in DROP)]
    t = '\n'.join(lines).replace('公開(push)はしていない。', '').replace('作業日: 2026-11-17〜18。 RDF は作っていない', '作業日: 2026-11-17〜18。RDF は作っていない')
    put(f'{d}/{f}', clean(t))
for f in sorted(glob.glob('review-*.csv')): shutil.copyfile(f, f'{d}/review/{f}')
# 人の抜き取り: 用紙(human-check.html)と結果(human-check-result.csv。作った人が 2026-11-20 に付けたもの)を写す。用紙の元の CSV は写さない
for f in ['human-check.html', 'human-check-result.csv']:
    if os.path.exists(f): shutil.copyfile(f, f'{d}/review/{f}')
if os.path.exists(f'{d}/review/human-check.csv'): os.remove(f'{d}/review/human-check.csv')
# ---- data/tracking(毎週の追跡の元。無いときだけ作る)
d = mk('data/tracking')
if not os.path.exists(f'{d}/law_revisions.csv.gz'):
    buf = io.StringIO(newline='')
    with open('out/law_revisions.csv', encoding='utf-8') as src:
        rd = csv.DictReader(src); w = csv.DictWriter(buf, fieldnames=['law_id', 'law_revision_id', 'amendment_enforcement_date', 'amendment_law_num', 'current_revision_status', 'source'], extrasaction='ignore')
        w.writeheader()
        for r in rd: r['source'] = 'law_revisions 2026-11-18'; w.writerow(r)
    gz(f'{d}/law_revisions.csv.gz', buf.getvalue().encode('utf-8'))
if not os.path.exists(f'{d}/state.json'):
    put(f'{d}/state.json', json.dumps({'checked_through': '2026-11-18', 'failed_laws': {}}, ensure_ascii=False, indent=1))
print('CSV の行:', csv_rows)
print('done')
# ---- README の数(データ・JSON-LD・CSV を写したあとに、店への問いとファイルの大きさから書き直す)
subprocess.run([sys.executable, 'scripts/83_write_readme_numbers.py', 'store/oxigraph', R], check=True)
