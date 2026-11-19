"""毎週の追跡。e-Gov 法令API v2 の一括ダウンロード(更新データ)で更新された法令と、施行日が来た改正のある法令のうち、
このデータが根拠に使う法令だけについて本文を取り直し、根拠の条・項・号を比べて、改正の記録(jpp:ProvisionChange)を足す。
判定の決まりは change_rules.py(第 5 版)。取得は 1 秒に 1 回まで(egov.py)。

使い方(公開用のリポジトリの一番上で):
  python3 scripts/70_weekly_track.py                       # 今日(日本時間)まで、過去 7 日の更新データ
  python3 scripts/70_weekly_track.py --today 2026-11-18 --days 1 --offline
  python3 scripts/70_weekly_track.py --since 2025-11-01 --only-bulk --offline --dry-run   # 作り直しの確かめ
終わりの状態: 正常なら 0、取得に失敗した日・法令があれば 1(GitHub Actions はこれで失敗を知る)。"""
import sys, os, re, io, csv, gzip, json, time, zipfile, argparse, datetime, collections, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import egov
from clause import article_index
import change_rules
from rdf_config import BASE, PREFIXES
ap = argparse.ArgumentParser()
ap.add_argument('--today'); ap.add_argument('--days', type=int, default=7); ap.add_argument('--since')
ap.add_argument('--only-bulk', action='store_true'); ap.add_argument('--offline', action='store_true'); ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--data', default='data/rdf'); ap.add_argument('--tracking', default='data/tracking'); ap.add_argument('--bulk-file', action='append', default=[], help='YYYYMMDD=保存済みの zip')
A = ap.parse_args()
JST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.date.fromisoformat(A.today) if A.today else datetime.datetime.now(JST).date()
os.makedirs(f'{A.tracking}/bulk', exist_ok=True)
state_fp = f'{A.tracking}/state.json'
state = json.load(open(state_fp)) if os.path.exists(state_fp) else {'checked_through': '2026-11-18', 'failed_laws': {}}
fail = []; log = []
def say(s): print(s, flush=True); log.append(s)
# ---- 1. 一括ダウンロードの更新データ(過去 N 日)
BULK = 'https://laws.e-gov.go.jp/bulkdownload?file_section=3&update_date={d}&only_xml_flag=true'
given = dict(x.split('=', 1) for x in A.bulk_file)
upd = []   # (法令ID, law_revision_id, 施行日 YYYY-MM-DD, 未施行, 改正法令番号, 更新日)
_last = [0.0]
for k in range(1, A.days + 1):
    d = (today - datetime.timedelta(days=k)).strftime('%Y%m%d'); fp = given.get(d, f'{A.tracking}/bulk/{d}.zip')
    if not os.path.exists(fp):
        if A.offline: say(f'  更新データ {d}: 手元に無い(取らない)'); continue
        wait = 1.05 - (time.time() - _last[0]); time.sleep(max(0, wait))
        try:
            with urllib.request.urlopen(urllib.request.Request(BULK.format(d=d), headers={'User-Agent': 'jp-procedure-tracker'}), timeout=180) as r: raw = r.read()
        except urllib.error.URLError as e: say(f'  更新データ {d}: 取れなかった({e})'); fail.append(('bulk', d)); continue
        finally: _last[0] = time.time()
        open(fp, 'wb').write(raw)
    raw = open(fp, 'rb').read()
    try: z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile: say(f'  更新データ {d}: zip でない({len(raw)} バイト)。更新の無い日とみなす'); continue
    cn = [n for n in z.namelist() if n.lower().endswith('.csv')]
    rows = list(csv.DictReader(io.StringIO(z.read(cn[0]).decode('utf-8-sig')))) if cn else []
    for r in rows:
        tail = r['本文URL'].rstrip('/').rsplit('/', 1)[-1]; m = re.match(r'(\d{8})_', tail)
        ed = f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}' if m else ''
        upd.append((r['法令ID'], f'{r["法令ID"]}_{tail}', ed, r['未施行'].strip() != '', r['改正法令番号'], d))
    say(f'  更新データ {d}: {len(rows)} 行')
# ---- 2. 改正履歴(手元の分に、更新データの行を足す)
rv_fp = f'{A.tracking}/law_revisions.csv.gz'
REV = {}
if os.path.exists(rv_fp):
    for r in csv.DictReader(gzip.open(rv_fp, 'rt', encoding='utf-8')): REV[r['law_revision_id']] = r
for lid, rid, ed, un, num, d in upd:
    REV.setdefault(rid, {'law_id': lid, 'law_revision_id': rid, 'amendment_enforcement_date': ed, 'amendment_law_num': num, 'current_revision_status': 'UnEnforced' if un else '', 'source': f'bulk {d}'})
# ---- 3. このデータが根拠に使う条・項・号
cited = collections.defaultdict(set); cur = None
for line in gzip.open(f'{A.data}/procedures.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'record/r7/([^/>]+)/citation>', line)
    if m: cur = m.group(1); continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:citedProvision <' + re.escape(BASE) + r'([^>]+)>', line)
    if m and cur: cited[m.group(1)].add(cur)
level = {}
for fn in ['provisions', 'changes']:
    for line in gzip.open(f'{A.data}/{fn}.ttl.gz', 'rt', encoding='utf-8'):
        m = re.match(r'^<' + re.escape(BASE) + r'(provision/[^>]+)> a eli:LegalResourceSubdivision', line)
        if m: cur = m.group(1); continue
        if line.startswith('<'): cur = None; continue
        m = re.match(r'\s+jpp:level <[^>]+/level/(\w+)>', line)
        if m and cur: level[cur] = m.group(1)
by_law = collections.defaultdict(list)
for pv, procs in cited.items(): by_law[pv.split('/')[1]].append((pv, procs))
# ---- 4. 対象の法令
start_all = A.since or state['checked_through']; end = today.isoformat()
bulk_laws = {u[0] for u in upd}
due_laws = {r['law_id'] for r in REV.values() if start_all < (r['amendment_enforcement_date'] or '') <= end}
targets = (bulk_laws | (set() if A.only_bulk else due_laws) | set(state['failed_laws'])) & set(by_law)
say(f'# 期間 {start_all} 〜 {end}: 更新データの法令 {len(bulk_laws)}、施行日が来た改正のある法令 {len(due_laws)}、前回失敗した法令 {len(state["failed_laws"])} → このデータが使う法令 {len(targets)}')
# ---- 5. 比べる
DEP = {'article': '条', 'paragraph': '項', 'item': '号'}
def pos_of(pv):
    s = pv.split('/')[2:]; sup = s[0].startswith('suppl-')
    return {'附則': sup, '条': s[0].replace('suppl-', ''), '項': s[1] if len(s) > 1 else None, '号': s[2] if len(s) > 2 else None}
def load(lid, asof):
    b = egov.get(f'/law_data/{lid}', {'asof': asof, 'response_format': 'json', 'json_format': 'full'}, offline=A.offline)
    if b.get('_status') != 200: return None, None, b.get('_status')
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    return article_index(lb), b.get('revision_info', {}), 200
recs = []; cnt = collections.Counter()
for lid in sorted(targets):
    start = state['failed_laws'].get(lid, start_all) if not A.since else A.since
    if start >= end: cnt['期間が無い(すでに確かめた)'] += 1; continue
    oi, orv, ost = load(lid, start); ni, nrv, nst = load(lid, end)
    if oi is None or ni is None:
        cnt[f'本文が取れない(旧 {ost} / 新 {nst})'] += 1
        if not (A.offline and '未取得' in (str(ost), str(nst))): fail.append(('law', lid))
        state['failed_laws'][lid] = start; continue
    state['failed_laws'].pop(lid, None); cache = {}
    for pv, procs in by_law[lid]:
        dep = DEP.get(level.get(pv)); p = pos_of(pv)
        if dep is None: cnt['深さが分からない'] += 1; continue
        x = change_rules.classify(oi, ni, p, dep, cache)
        if x is None: cnt['文言が同じ'] += 1; continue
        if x['kind'] == '比べられない': cnt['比べられない'] += 1; continue
        cnt[x['kind']] += 1
        recs.append(dict(lid=lid, pv=pv, procs=sorted(procs), start=start, end=end, orv=orv, nrv=nrv, oi=oi, ni=ni, p=p, dep=dep, **x))
say(f'  比べた結果(条・項・号): {dict(cnt)}')
say(f'  足す改正の記録: {len(recs)}(手続の行 {sum(len(r["procs"]) for r in recs)})')
# 期間内に施行期日がある改正は、改正の記録に結ぶものだけでなく、このデータにある法令のものをすべて置く(61_build_changes.py と同じ形)。
# 根拠の法令に期間内の改正がある手続(法令の単位で知らせた場合の数)を、問いで数えられるようにするため。記録が 0 件の週でも置く。
LAWS = set(re.findall(r'^<' + re.escape(BASE) + r'law/([0-9A-Za-z]+)> a eli:LegalResource', gzip.open(f'{A.data}/laws.ttl.gz', 'rt', encoding='utf-8').read(), flags=re.M))
win_revs = sorted(x['law_revision_id'] for x in REV.values() if x['law_id'] in LAWS and start_all < (x['amendment_enforcement_date'] or '') <= end)
say(f'  期間内に施行期日がある改正(このデータの法令): {len(win_revs)}(法令 {len({REV[x]["law_id"] for x in win_revs})})')
# ---- 6. 書き出し
def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(path): return f'<{BASE}{path}>'
KIND = {'文言が変わった: 番号の参照だけ': 'wording-numref', '文言が変わった: それ以外': 'wording-other', '大きく書き換わった': 'rewritten',
        '入れ替わった→移った': 'swapped-moved', '入れ替わった→移った先が一つに決まらない': 'swapped-ambiguous', '入れ替わった→移った先なし': 'swapped-nodest',
        '無くなった→移った': 'removed-moved', '無くなった→移った先が一つに決まらない': 'removed-ambiguous', '無くなった→移った先なし': 'removed-nodest', '無くなった→判定できない': 'removed-undetermined'}
def seg_art(sup, num): return ('suppl-' if sup else '') + num
def lab_art(sup, num): s = num.split('_'); return ('附則' if sup else '') + f'第{s[0]}条' + ''.join(f'の{x}' for x in s[1:])
def lab_sub(num, kind): s = num.split('_'); return f'第{s[0]}{kind}' + ''.join(f'の{x}' for x in s[1:])
known = set(level)
def node_for(lid, pos, out):
    sup, art, pn, it = pos; a = f'provision/{lid}/{seg_art(sup, art)}'; cur = a; lab = lab_art(sup, art)
    chain = [(a, 'article', f'law/{lid}', lab, art)]
    if pn is not None: q = f'{a}/{pn}'; chain.append((q, 'paragraph', a, lab + lab_sub(pn, '項'), pn)); cur = q
    if pn is not None and it is not None: r = f'{cur}/{it}'; chain.append((r, 'item', cur, chain[-1][3] + lab_sub(it, '号'), it)); cur = r
    for path, lv, parent, l, num in chain:
        if path not in known: known.add(path); out.append((path, lv, parent, l, num))
    return cur
def elem_text(idx, p, dep): e, _ = change_rules.old_elem(idx, p, dep); return change_rules.text(e).strip() if e is not None else None
if (recs or win_revs) and not A.dry_run:
    os.makedirs(f'{A.data}/weekly', exist_ok=True)
    PER = f'{start_all}_{end}'; fn = f'{A.data}/weekly/changes_{PER}.ttl.gz'
    f = gzip.open(fn, 'wt', encoding='utf-8')
    for k, v in PREFIXES.items(): f.write(f'@prefix {k}: <{v}> .\n')
    f.write('@prefix dcat: <http://www.w3.org/ns/dcat#> .\n\n')
    def s(subj, pos): pos = [(p, o) for p, o in pos if o is not None]; f.write(subj + ' ' + ' ;\n    '.join(f'{p} {o}' for p, o in pos) + ' .\n')
    ACT = iri(f'activity/weekly-track/{end}')
    s(ACT, [('a', 'prov:Activity'), ('rdfs:label', lit(f'毎週の追跡 {end}(scripts/70_weekly_track.py)', 'ja')), ('prov:used', iri('source/egov-law-api-v2')),
            ('prov:qualifiedAssociation', f'[ a prov:Association ; prov:agent {iri("agent/70_weekly_track")} ; prov:hadPlan {iri("plan/change-rules/" + change_rules.VERSION)} ]'),
            ('prov:endedAtTime', lit(datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), dt='dateTime'))])
    s(iri('agent/70_weekly_track'), [('a', 'prov:SoftwareAgent'), ('rdfs:label', lit('scripts/70_weekly_track.py'))])
    periods = {f'{start_all}_{end}'}; newnodes = []; revs_used = set(win_revs)
    s(iri(f'period/{start_all}_{end}'), [('a', 'dct:PeriodOfTime'), ('dcat:startDate', lit(start_all, dt='date')), ('dcat:endDate', lit(end, dt='date'))])
    for r in recs:
        per = f'{r["start"]}_{r["end"]}'
        if per not in periods:
            periods.add(per); s(iri(f'period/{per}'), [('a', 'dct:PeriodOfTime'), ('dcat:startDate', lit(r['start'], dt='date')), ('dcat:endDate', lit(r['end'], dt='date'))])
        vers = {}
        for side, idx, rv, asof in [('old', r['oi'], r['orv'], r['start']), ('new', r['ni'], r['nrv'], r['end'])]:
            t = elem_text(idx, r['p'], r['dep'])
            if t is None: continue
            rid = rv.get('law_revision_id', ''); ex = f'{r["pv"]}/version/{rid}'; vers[side] = ex
            vd = (REV.get(rid) or {}).get('amendment_enforcement_date') or rv.get('amendment_enforcement_date')
            s(iri(ex), [('a', 'eli:LegalExpression'), ('eli:realizes', iri(r['pv'])), ('eli:version_date', lit(vd, dt='date') if vd else None), ('jpp:lawRevision', lit(rid)),
                        ('eli:language', '<http://publications.europa.eu/resource/authority/language/JPN>'), ('jpp:text', lit(t, 'ja')), ('jpp:asOf', lit(asof, dt='date'))])
            s(iri(r['pv']), [('eli:is_realized_by', iri(ex))])
        if vers.get('new') == vers.get('old'): vers.pop('new', None)
        mv = node_for(r['lid'], r['moved'], newnodes) if r['moved'] else None
        cands = [node_for(r['lid'], pos, newnodes) for _, pos, _ in r['cands']]
        revs = [x['law_revision_id'] for x in REV.values() if x['law_id'] == r['lid'] and r['start'] < (x['amendment_enforcement_date'] or '') <= r['end']]
        revs_used.update(revs)
        def dec(x): return lit(f'{float(x):.6f}', dt='decimal') if x is not None else None
        pos = [('a', 'jpp:ProvisionChange'), ('jpp:provision', iri(r['pv'])), ('dct:temporal', iri(f'period/{per}')), ('jpp:changeKind', iri(f'code/change-kind/{KIND[r["kind"]]}')),
               ('jpp:oldVersion', iri(vers['old'])), ('jpp:newVersion', iri(vers['new']) if 'new' in vers else None), ('jpp:movedTo', iri(mv) if mv else None)]
        pos += [('jpp:candidate', iri(x)) for x in dict.fromkeys(cands)] + [('jpp:r0', dec(r['r0'])), ('jpp:r1', dec(r['r1'])), ('prov:wasGeneratedBy', ACT)]
        pos += [('jpp:lawRevisionInPeriod', iri(f'law/{r["lid"]}/revision/{x}')) for x in revs] + [('jpp:affects', iri(f'procedure/{p}')) for p in r['procs']]
        s(iri(f'change/{r["pv"][len("provision/"):]}/{per}'), pos)
    for x in sorted(revs_used):
        rr = REV[x]
        s(iri(f'law/{rr["law_id"]}/revision/{x}'), [('a', 'jpp:LawRevision'), ('dct:identifier', lit(x)), ('jpp:revisionOf', iri(f'law/{rr["law_id"]}')),
                                                    ('jpp:enforcementDate', lit(rr['amendment_enforcement_date'], dt='date')), ('jpp:amendmentLawNum', lit(rr['amendment_law_num']) if rr.get('amendment_law_num') else None)])
    for path, lv, parent, l, num in newnodes:
        s(iri(path), [('a', 'eli:LegalResourceSubdivision'), ('eli:is_part_of', iri(parent)), ('eli:number', lit(num)), ('rdfs:label', lit(l, 'ja')), ('jpp:level', iri(f'code/level/{lv}')),
                      ('rdfs:comment', lit(f'改正の記録の移った先・候補として足した条・項・号({end} 版の番号)', 'ja'))])
    f.close(); say(f'  書いたファイル: {fn}')
if not A.dry_run:
    if not fail: state['checked_through'] = end
    json.dump(state, open(state_fp, 'w'), ensure_ascii=False, indent=1)
    with gzip.open(rv_fp, 'wt', encoding='utf-8', newline='') as g:
        w = csv.DictWriter(g, fieldnames=['law_id', 'law_revision_id', 'amendment_enforcement_date', 'amendment_law_num', 'current_revision_status', 'source'], extrasaction='ignore')
        w.writeheader(); [w.writerow(r) for r in REV.values()]
json.dump({'period': [start_all, end], 'targets': len(targets), 'records': len(recs), 'rows': sum(len(r['procs']) for r in recs), 'revisions': len(win_revs), 'counts': dict(cnt), 'failures': fail, 'log': log},
          open(f'{A.tracking}/last_run.json', 'w'), ensure_ascii=False, indent=1)
if fail: say(f'失敗: {fail}'); sys.exit(1)
