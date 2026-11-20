"""全体の数を見る確かめ(SHACL を使わない)。.venv の python で動かす。
切り分け(out/shacl_chunks/full)の主のファイルを 1 つずつ rdflib で読み、数と集合だけを残す。"""
import gzip, json, collections, resource, time, os, glob, rdflib, pyoxigraph as ox
from rdflib import RDF, URIRef, Namespace
D = 'out/shacl_chunks/full'; M = json.load(open(f'{D}/manifest.json'))
RDFDIR = os.environ.get('RDF_DIR', 'rdf')   # 公開用のリポジトリでは data/rdf
WEEKLY = sorted(glob.glob(f'{RDFDIR}/weekly/*.ttl.gz'))
CPSV = Namespace('http://purl.org/vocab/cpsv#'); CV = Namespace('http://data.europa.eu/m8g/'); ELI = Namespace('http://data.europa.eu/eli/ontology#')
DCT = Namespace('http://purl.org/dc/terms/'); JPP = Namespace('https://w3id.org/jp-procedure/def#'); DCAT = Namespace('http://www.w3.org/ns/dcat#')
P = [r['name'] for r in M['own'] if r['name'].startswith('P')]; R = [r['name'] for r in M['own'] if r['name'].startswith('R')]
S = [r['name'] for r in M['own'] if r['name'].startswith('S')]; E = [r['name'] for r in M['own'] if r['name'].startswith('E')]
SRC = {'changes': [r['name'] for r in M['own'] if r['name'].startswith('X')] + ['Xc'] + ['Ew' + r['name'][1:] for r in M['own'] if r['name'].startswith('E')], 'codes': ['C'], 'prov': ['V'], 'organisations': ['O'], 'laws': ['L'], 'provisions': S, 'expressions': E, 'procedures': P, 'records': R}
# 元のファイルを丸ごと読み直した数(pyoxigraph で流して数える)。
# 改正の記録は changes と weekly/ の重なりの無い和から、ほかのファイルにもあるトリプルを除いたもの(weekly/ は前の週や元のデータと同じトリプルを書くことがある。店は重なりを 1 つに数える)
def count(f): return sum(1 for _ in ox.parse(gzip.open(f), ox.RdfFormat.TURTLE))
def trip(q): return (q.subject, q.predicate, q.object)
CHSET = set()
for f in [f'{RDFDIR}/changes.ttl.gz'] + WEEKLY: CHSET.update(trip(q) for q in ox.parse(gzip.open(f), ox.RdfFormat.TURTLE))
REPARSE = {}; OVERLAP = collections.Counter()
for n in SRC:
    if n == 'changes': continue
    c = 0
    for q in ox.parse(gzip.open(f'{RDFDIR}/{n}.ttl.gz'), ox.RdfFormat.TURTLE):
        c += 1; t = trip(q)
        if t in CHSET: CHSET.discard(t); OVERLAP[n] += 1
    REPARSE[n] = c
REPARSE['changes'] = len(CHSET); del CHSET
BASE_LATE = set()   # 毎週の追跡が遅れて見つけた改正(jpp:enforcedBeforePeriod true の記録の見つけた改正)。施行期日の入る前の期間の「期間内の改正」には数えない
t0 = time.time()
CHG = set()   # changes の回(X・Xc・Ew)のトリプル(rdflib)。ほかの回にあるものは後で除く
typ = collections.defaultdict(set); typ_ex = set(); wreal = set(); wasof = collections.defaultdict(set); per_of = {}; objs = collections.defaultdict(list); ident = []; asof = collections.Counter(); real = set(); realized_by = set()
ntrip = collections.Counter(); ex_asof = collections.defaultdict(set); cited_of = {}; cit_of = {}; chg = {}; rev_of = {}; rev_date = {}; cit_law = {}; cit_mr = {}; periods = {}; rev_id = {}; sub_ch = set(); lawrev = {}; reviews = {}; review_ref = collections.Counter(); comp_of = collections.defaultdict(set); org_label = collections.defaultdict(set)
for src, files in SRC.items():
    for fn in files:
        g = rdflib.Graph(); g.parse(gzip.open(f'{D}/{fn}.ttl.gz'), format='turtle')
        if src == 'changes': CHG.update(g)
        else:
            ntrip[src] += len(g)
            if CHG: CHG.difference_update([t for t in g if t in CHG])
        for s, o in g.subject_objects(RDF.type): typ[o].add(s)
        if src == 'expressions': typ_ex.update(g.subjects(RDF.type, ELI.LegalExpression))
        if src in ('expressions', 'changes'): lawrev.update((x, str(o)) for x, o in g.subject_objects(JPP.lawRevision))
        if src == 'changes': sub_ch.update(g.subjects(RDF.type, ELI.LegalResourceSubdivision))
        for p in [JPP.affects, JPP.changeKind, JPP.provision, JPP.oldVersion, JPP.newVersion, JPP.matchResult, CV.hasCompetentAuthority, JPP.citedLaw, JPP.citedProvision, CV.hasLegalResource, JPP.hasCitation, JPP.describes, ELI.is_part_of, ELI.realizes]:
            objs[p].extend(g.objects(None, p))
        if src == 'procedures': ident.extend(str(o) for s, o in g.subject_objects(DCT.identifier) if (s, RDF.type, CPSV.PublicService) in g)
        if src == 'expressions':
            for s, o in g.subject_objects(JPP.asOf): asof[str(o)] += 1
            real.update(g.subject_objects(ELI.realizes)); realized_by.update((o, s) for s, o in g.subject_objects(ELI.is_realized_by))
            for s, o in g.subject_objects(JPP.asOf): ex_asof[s].add(str(o))
        if src == 'procedures':
            for s_, o in g.subject_objects(CV.hasCompetentAuthority): comp_of[s_].add(o)
        if src == 'organisations':
            for s_, o in g.subject_objects(rdflib.URIRef('http://www.w3.org/2004/02/skos/core#prefLabel')): org_label[s_].add(str(o))
        if src == 'procedures': cited_of.update({s: o for s, o in g.subject_objects(JPP.citedProvision)}); cit_of.update({s: o for s, o in g.subject_objects(JPP.hasCitation)})
        if src == 'procedures': cit_law.update(g.subject_objects(JPP.citedLaw)); cit_mr.update((s, str(o).rsplit('/', 1)[-1]) for s, o in g.subject_objects(JPP.matchResult))
        if src == 'changes':
            wreal.update(g.subject_objects(ELI.realizes))
            for x, o in g.subject_objects(JPP.asOf): wasof[x].add(str(o))
            for ch in g.subjects(RDF.type, JPP.ProvisionChange):
                pr = g.value(ch, DCT.temporal); per_of[ch] = str(pr).rsplit('/', 1)[-1]
                chg[ch] = dict(prov=g.value(ch, JPP.provision), kind=str(g.value(ch, JPP.changeKind)).rsplit('/', 1)[-1], old=g.value(ch, JPP.oldVersion), new=g.value(ch, JPP.newVersion),
                               aff=list(g.objects(ch, JPP.affects)), revs=list(g.objects(ch, JPP.lawRevisionInPeriod)))
            for rv in g.subjects(RDF.type, JPP.LawRevision): rev_of[rv] = g.value(rv, JPP.revisionOf); rev_date[rv] = str(g.value(rv, JPP.enforcementDate))
            for ch in g.subjects(JPP.enforcedBeforePeriod, None): BASE_LATE.update(g.objects(ch, JPP.foundRevision))
            for ch in g.subjects(RDF.type, JPP.ProvisionChange):
                chg[ch].update(found=g.value(ch, JPP.foundRevision), found_on=str(g.value(ch, JPP.foundOn) or ''), before=g.value(ch, JPP.enforcedBeforePeriod))
            for rv in g.subjects(RDF.type, JPP.LawRevision): rev_id[rv] = str(g.value(rv, DCT.identifier))
            for rv in g.subjects(RDF.type, JPP.Review): reviews[rv] = (str(g.value(rv, JPP.reviewerType)).rsplit('/', 1)[-1], str(g.value(rv, JPP.reviewResult)).rsplit('/', 1)[-1])
            review_ref.update(g.objects(None, JPP.review))
            for pr in g.subjects(RDF.type, DCT.PeriodOfTime): periods[str(pr).rsplit('/', 1)[-1]] = (str(g.value(pr, DCAT.startDate)), str(g.value(pr, DCAT.endDate)))
        del g
ntrip['changes'] = len(CHG); del CHG
ok_all = []
def chk(label, got, want):
    ok = got == want; ok_all.append(ok); print(f'  {"OK " if ok else "NG "} {label}: {got:,} = {want:,}' if isinstance(got, int) and not isinstance(got, bool) else f'  {"OK " if ok else "NG "} {label}: {got}')
print('# 切り分けで落ちたものが無いか(主のファイルのトリプル数の和 = 元のファイルを丸ごと読んだ数。改正の記録は changes と weekly/ の重なりを除いた数)')
for k in SRC: chk(f'{k} のトリプル', ntrip[k], REPARSE[k])
if OVERLAP: print('     weekly/・changes のトリプルのうち、ほかのファイルにもあるもの(重ねて数えない):', dict(OVERLAP))
ps, cit, rec, org, law, sub, ex = (typ[CPSV.PublicService], typ[JPP.LegalCitation], typ[JPP.SurveyRecord], typ[CV.PublicOrganisation], typ[ELI.LegalResource], typ[ELI.LegalResourceSubdivision], typ_ex)
print('\n# 手続・照合・記録')
chk('cpsv:PublicService の数', len(ps), 76275)
chk('dct:identifier の重なりの無い数', len(set(ident)), 76275)
chk('jpp:LegalCitation の数', len(cit), 76275)
chk('jpp:hasCitation の数(重なり無し)', len(set(objs[JPP.hasCitation])), 76275)
mr = collections.Counter(str(o).rsplit('/', 1)[-1] for o in objs[JPP.matchResult])
chk('照合の結果の数の合計 = 手続の数', sum(mr.values()), len(ps))
print('     照合の結果の内訳:', dict(mr.most_common()))
chk('jpp:SurveyRecord の数', len(rec), 76275)
chk('記録が指す手続の集合 = 手続の集合', set(objs[JPP.describes]) == ps, True)
print('\n# 組織・法令・条項号・本文の版')
chk('cv:PublicOrganisation の数', len(org), 25)
sp = collections.Counter()
g0 = rdflib.Graph(); g0.parse(gzip.open(f'{RDFDIR}/organisations.ttl.gz'), format='turtle')
chk('dct:spatial を持つ組織の数', len({s for s in g0.subjects(DCT.spatial, None) if s in org}), 25)
chk('dct:spatial の先が dct:Location', all((o, RDF.type, DCT.Location) in g0 for o in g0.objects(None, DCT.spatial)), True)
chk('所管の府省庁が組織の中にある', set(objs[CV.hasCompetentAuthority]) <= org, True)
print(f'     eli:LegalResource の数: {len(law):,} / eli:LegalResourceSubdivision の数: {len(sub):,}')
chk('照合した法令が法令の中にある', set(objs[JPP.citedLaw]) <= law, True)
chk('is_part_of の先が法令か条項号の中にある', set(objs[ELI.is_part_of]) <= (law | sub), True)
hl = objs[CV.hasLegalResource]
chk('cv:hasLegalResource の先が条項号か法令の中にある', set(hl) <= (sub | law), True)
chk('cv:hasLegalResource が条項号を指す数(50_build_rdf の「条・項・号へ」)', sum(o in sub for o in hl), 74544)
chk('cv:hasLegalResource が法令を指す数(「法令へ」: 条・項・号が決まらない行)', sum(o in law for o in hl), 1035)
chk('cv:hasLegalResource が無い手続の数(法令IDが決まらない)', len(ps) - len(hl), 696)
cp = set(objs[JPP.citedProvision])
chk('照合できた最も深い条項号の数', len(cp), 55924)
chk('eli:LegalExpression の数', len(ex), 90970)
chk('版がある条項号の数', len({p for _, p in real}), 55924)
chk('版がある条項号 = 照合できた最も深い条項号', {p for _, p in real} == cp, True)
chk('realizes と is_realized_by が逆向きで一致', real == realized_by, True)
chk('jpp:asOf 2025-11-01 の数 = 照合できた最も深い条項号の数', asof['2025-11-01'], len(cp))
chk('jpp:asOf 2026-11-18 の数 = 55,924 − 新版に無い 279 − 404 の 57 − 取っていない 20(54_build_expressions)', asof['2026-11-18'], 55924 - 279 - 57 - 20)
print('\n# 改正の記録: 2025-11-01〜2026-11-18 の分(rdf/changes.ttl.gz)')
import csv; csv.field_size_limit(10**9)
KIND = {'文言が変わった: 番号の参照だけ': 'wording-numref', '文言が変わった: それ以外': 'wording-other', '大きく書き換わった': 'rewritten', '入れ替わった→移った': 'swapped-moved', '入れ替わった→移った先が一つに決まらない': 'swapped-ambiguous', '入れ替わった→移った先なし': 'swapped-nodest', '無くなった→移った': 'removed-moved', '無くなった→移った先が一つに決まらない': 'removed-ambiguous', '無くなった→移った先なし': 'removed-nodest', '無くなった→判定できない': 'removed-undetermined'}
allchg = chg
chg = {k: v for k, v in allchg.items() if per_of[k] == '2025-11-01_2026-11-18'}
aff = [a for v in chg.values() for a in v['aff']]
chk('jpp:ProvisionChange の数 = 知らせる行の手続の、照合できた最も深い条・項・号の重なりの無い数', len(chg), len({cited_of[cit_of[a]] for a in aff}))
chk('jpp:ProvisionChange の数', len(chg), 2064)
chk('jpp:affects の数(手続の行)', len(aff), 3090)
chk('jpp:affects の重なりの無い数', len(set(aff)), 3090)
chk('jpp:affects の先が手続の中にある', set(aff) <= ps, True)
chk('改正の記録の条・項・号 = 当たる手続の照合できた最も深い条・項・号', all(cited_of[cit_of[a]] == v['prov'] for v in chg.values() for a in v['aff']), True)
got = collections.Counter(k for v in chg.values() for k in [v['kind']] * len(v['aff']))
if os.path.exists('out/fix6_compare.csv'):
    f6 = list(csv.DictReader(open('out/fix6_compare.csv', encoding='utf-8')))
    want = collections.Counter(KIND[r['新区分']] for r in f6 if r['新区分'] in KIND)
    chk('区分ごとの手続の行が out/fix6_compare.csv と同じ', dict(got) == dict(want), True)
else: print('     (out/fix6_compare.csv が無いので、区分ごとの行の照合は飛ばした)')
print('     区分ごと(改正の記録 / 手続の行):', {k: (sum(1 for v in chg.values() if v['kind'] == k), got[k]) for k in KIND.values()})
chk('旧い版が 2025-11-01 の版で、その条・項・号を realizes する', all('2025-11-01' in ex_asof[v['old']] and (v['old'], v['prov']) in real for v in chg.values()), True)
chk('新しい版があれば 2026-11-18 の版で、その条・項・号を realizes する', all(v['new'] is None or ('2026-11-18' in ex_asof[v['new']] and (v['new'], v['prov']) in real) for v in chg.values()), True)
chk('新しい版が無いのは「無くなった」の記録だけ', all((v['new'] is None) == v['kind'].startswith('removed') for v in chg.values()), True)
chk('期間内の改正が、その記録の法令のもの', all(str(rev_of[r]).split('/law/')[1] == str(v['prov']).split('/provision/')[1].split('/')[0] for v in chg.values() for r in v['revs']), True)
chk('期間内の改正の施行期日が、その記録の期間の中にある', all(per_of[k].split('_')[0] < rev_date[r] <= per_of[k].split('_')[1] for k, v in chg.items() for r in v['revs']), True)
base_rev = [r for r in rev_of if '2025-11-01' < rev_date[r] <= '2026-11-18' and r not in BASE_LATE]
chk('期間内の改正の節点の数(e-Gov の改正履歴で施行期日が 2025-11-02〜2026-11-18。改正の記録に結んでいないものも置く)', len(base_rev), 2840)
chk('期間内の改正の節点の法令の数', len({rev_of[r] for r in base_rev}), 1252)
chk('改正の節点の法令が、法令の中にある', {rev_of[r] for r in rev_of} <= law, True)
rev_laws = {rev_of[r] for r in base_rev}
lawlevel = {p for p, c in cit_of.items() if cit_mr.get(c) in ('article', 'paragraph', 'item') and cit_law.get(c) in rev_laws}
chk('法令の単位で知らせた場合の手続(条以上で照合でき、根拠の法令に期間内の改正がある)', len(lawlevel), 47352)
chk('知らせる手続が、法令の単位で知らせた場合の手続に含まれる', set(aff) <= lawlevel, True)
print(f'     法令の単位で知らせた場合との差: {len(lawlevel):,} / {len(set(aff)):,} = {len(lawlevel) / len(set(aff)):.1f} 倍')
print('\n# 区分を確かめた記録(jpp:Review)')
rc = collections.Counter(reviews.values())
chk('確かめの記録が、どれか 1 つの改正の記録から 1 回だけ指される', all(review_ref[r] == 1 for r in reviews) and set(review_ref) == set(reviews), True)
chk('別の AI が区分を決めた記録', rc[('other-ai', 'decided')], 3)
chk('人の抜き取りの記録(2026-11-20、23 件)', sum(v for (t, _), v in rc.items() if t == 'human'), 23)
chk('人の抜き取りの結果が「合う」', rc[('human', 'agree')], 23)
print('     種類と結果ごと:', dict(rc))
W = {k: v for k, v in allchg.items() if k not in chg}
print(f'\n# 改正の記録: 毎週の追跡の分(weekly/ のファイル {len(WEEKLY)}、記録 {len(W)})')
if W:
    allreal = real | wreal; allasof = collections.defaultdict(set)
    for d0 in (ex_asof, wasof):
        for k2, v2 in d0.items(): allasof[k2] |= v2
    waff = [(per_of[k], a) for k, v in W.items() for a in v['aff']]
    chk('手続への線の先が手続の中にある', {a for _, a in waff} <= ps, True)
    chk('同じ期間に同じ手続が 2 回出ない', len(waff) == len(set(waff)), True)
    chk('記録の条・項・号 = 当たる手続の照合できた最も深い条・項・号', all(cited_of[cit_of[a]] == v['prov'] for v in W.values() for a in v['aff']), True)
    # 旧い版は、期間の始めの時点で公開していたデータの版(その条・項・号の版のうち、jpp:asOf が期間の始め以前で最も新しいもの)
    vers_of = collections.defaultdict(set)
    for ex_, pv_ in allreal: vers_of[pv_].add(ex_)
    def pub_at(pv_, day):
        c = [(max(a for a in allasof[e] if a <= day), str(e)) for e in vers_of[pv_] if any(a <= day for a in allasof[e])]
        return URIRef(max(c)[1]) if c else None
    chk('旧い版が、期間の始めの時点で公開していたデータの版(その条・項・号の最も新しい版)で、その条・項・号を realizes する', all(v['old'] is not None and (v['old'], v['prov']) in allreal and pub_at(v['prov'], per_of[k].split('_')[0]) == v['old'] for k, v in W.items()), True)
    chk('新しい版があれば期間の終わりの版で、その条・項・号を realizes する', all(v['new'] is None or (per_of[k].split('_')[1] in allasof[v['new']] and (v['new'], v['prov']) in allreal) for k, v in W.items()), True)
    chk('新しい版が無いのは「無くなった」の記録だけ', all((v['new'] is None) == v['kind'].startswith('removed') for v in W.values()), True)
    chk('期間内の改正が、その記録の法令のもの', all(str(rev_of[r]).split('/law/')[1] == str(v['prov']).split('/provision/')[1].split('/')[0] for v in W.values() for r in v['revs']), True)
    chk('期間内の改正の施行期日が、その記録の期間の中にある', all(per_of[k].split('_')[0] < rev_date[r] <= per_of[k].split('_')[1] for k, v in W.items() for r in v['revs']), True)
    chk('見つけた改正がどの記録にもあり、その記録の法令のもの', all(v.get('found') is not None and v['found'] in rev_of and str(rev_of[v['found']]).split('/law/')[1] == str(v['prov']).split('/provision/')[1].split('/')[0] for v in W.values()), True)
    nv_rev = {}
    for x, r_ in lawrev.items(): nv_rev[x] = r_
    chk('見つけた改正の版の ID = 新しい版の版の ID(新しい版があるとき)', all(v['new'] is None or nv_rev.get(v['new']) == rev_id.get(v['found']) for v in W.values()), True)
    chk('見つけた日 = 期間の終わり', all(v.get('found_on') == per_of[k].split('_')[1] for k, v in W.items()), True)
    chk('施行期日が期間の始め以前の印(jpp:enforcedBeforePeriod)が、見つけた改正の施行期日が期間の始め以前の記録にだけある', all((v.get('before') is not None) == (rev_date.get(v['found'], '9999') <= per_of[k].split('_')[0]) for k, v in W.items()), True)
    print('     期間ごと:', dict(collections.Counter(per_of[k] for k in W)), '/ 施行期日が期間の始め以前の記録:', sum(1 for v in W.values() if v.get('before') is not None))
# 期間ごとの数(閲覧ページのはじめの画面の数)。ここでは SPARQL を使わずに数え、stats.json(75_make_stats.py が問いで出したもの)があれば比べる
print('\n# 期間ごとの数(改正の記録・知らせる手続・法令の単位で知らせた場合の手続)')
mine = {}
for k, (ps0, pe0) in sorted(periods.items(), key=lambda x: x[1]):
    chs = [v for c, v in allchg.items() if per_of[c] == k]
    # 期間に見つけた改正: 施行期日が期間の中にある改正(遅れて見つけたものを除く)と、その期間の記録が見つけた改正(queries/q7 と同じ)
    revl = {rev_of[r] for r in rev_of if ps0 < rev_date[r] <= pe0 and r not in BASE_LATE} | {rev_of[v['found']] for v in chs if v.get('found') is not None and v['found'] in rev_of}
    ll = {p for p, c in cit_of.items() if cit_mr.get(c) in ('article', 'paragraph', 'item') and cit_law.get(c) in revl}
    nt = {a for v in chs for a in v['aff']}
    mine[(ps0, pe0)] = (len(chs), len(nt), len(ll))
    print(f'     {ps0}〜{pe0}: 改正の記録 {len(chs):,} / 知らせる手続 {len(nt):,} / 法令の単位で知らせた場合の手続 {len(ll):,}(期間内の改正 {sum(1 for r in rev_of if ps0 < rev_date[r] <= pe0 and r not in BASE_LATE):,})')
    chk(f'{ps0}〜{pe0}: 知らせる手続が、法令の単位で知らせた場合の手続(期間に見つけた改正で数える)に含まれる', nt <= ll, True)
STATS = os.environ.get('STATS')
if STATS and os.path.exists(STATS):
    st = json.load(open(STATS, encoding='utf-8'))
    chk(f'{STATS} の手続の数', st['procedures'], len(ps))
    got = {(x['start'], x['end']): (x['changes'], x['notified'], x['law_level']) for x in st['periods']}
    chk(f'{STATS} の期間の集合 = 期間の節点の集合', set(got) == set(mine), True)
    for key in sorted(mine):
        chk(f'{STATS} {key[0]}〜{key[1]} の(改正の記録, 知らせる手続, 法令の単位)', got.get(key), mine[key])
    # 府省庁ごと(閲覧ページの「府省庁ごと」。75 が q3 で出したもの)を、所管と府省庁名と改正の記録から数え直して比べる
    if 'ministries' in st:
        from decimal import Decimal, ROUND_HALF_UP
        m = st['ministries']; k0 = f"{m['start']}_{m['end']}"
        chd = {a for c, v in allchg.items() if per_of[c] == k0 for a in v['aff']}
        byl = collections.defaultdict(set)
        for p_, os_ in comp_of.items():
            if p_ in ps:
                for o in os_:
                    for l in org_label[o]: byl[l].add(p_)
        mm = {l: (len(v), len(v & chd), float((Decimal(len(v & chd) * 100) / Decimal(len(v))).quantize(Decimal('0.01'), ROUND_HALF_UP))) for l, v in byl.items()}
        gm = {r['ministry']: (r['procedures'], r['changed'], r['percent']) for r in m['rows']}
        print(f'     府省庁ごと({m["start"]}〜{m["end"]}): {len(mm)} 府省庁、手続の和 {sum(v[0] for v in mm.values()):,}、変わった手続の和 {sum(v[1] for v in mm.values()):,}')
        chk(f'{STATS} の府省庁の集合 = 所管の府省庁名の集合', set(gm) == set(mm), True)
        chk(f'{STATS} の府省庁ごとの(手続, 変わった手続, 割合)が、数え直したものとすべて同じ', gm == mm, True)
        chk(f'{STATS} の府省庁ごとの変わった手続の和 = 知らせる手続の数', sum(v[1] for v in gm.values()), len(chd))
    else: chk(f'{STATS} に府省庁ごとの数がある', False, True)
else: print(f'     (環境変数 STATS の stats.json が無いので、問いで出した数との比べは飛ばした)')
# README の数(<!-- n:キー -->数<!-- /n -->。83_write_readme_numbers.py が店への問いで書いたもの)と、ここで数えた数を比べる
RD = os.environ.get('README')
if RD and os.path.exists(RD):
    import re
    REPO = os.path.dirname(os.path.abspath(RD))
    # 全体のトリプル = 切り分けで確かめた 9 つのファイル(と weekly/)+ 語彙(vocab。SHACL の切り分けには入れていない)
    mine2 = {'triples_total': sum(REPARSE.values()) + count(f'{RDFDIR}/vocab.ttl.gz'), 'procedures': len(ps), 'records': len(rec), 'organisations': len(org), 'laws': len(law),
             'subdivisions_added': len(sub_ch), 'subdivisions_base': len(sub) - len(sub_ch), 'expressions': len(typ[ELI.LegalExpression]),
             'versions_zero': sum(1 for v in lawrev.values() if v.endswith('_000000000000000')),
             'changes': len(allchg), 'change_rows': sum(len(v['aff']) for v in allchg.values()),
             'revisions': len(base_rev), 'revision_laws': len({rev_of[r] for r in base_rev}), 'revisions_linked': len({r for v in chg.values() for r in v['revs']}),
             'law_level': len(lawlevel)}
    for v in chg.values():
        k = v['kind']; mine2[f'kind_rec:{k}'] = mine2.get(f'kind_rec:{k}', 0) + 1; mine2[f'kind_rows:{k}'] = mine2.get(f'kind_rows:{k}', 0) + len(v['aff'])
    for f in glob.glob(f'{REPO}/data/rdf/*.ttl.gz'): mine2['size:data/rdf/' + os.path.basename(f)] = os.path.getsize(f)
    mine2['size:jsonld_total'] = sum(os.path.getsize(f) for f in glob.glob(f'{REPO}/data/jsonld/*.jsonld.gz'))
    for f in glob.glob(f'{REPO}/data/csv/*.csv'):
        mine2['size:data/csv/' + os.path.basename(f)] = os.path.getsize(f); mine2['csv_rows:' + os.path.basename(f)] = sum(1 for _ in csv.reader(open(f, encoding='utf-8'))) - 1
    if os.path.exists(f'{REPO}/data/redactions.csv'): mine2['size:data/redactions.csv'] = os.path.getsize(f'{REPO}/data/redactions.csv')
    print(f'\n# README の数({RD})')
    seen = {}
    for k, v in re.findall(r'<!-- n:([^ ]+) -->([^<]*)<!-- /n -->', open(RD, encoding='utf-8').read()):
        seen.setdefault(k, set()).add(int(v.replace(',', '')))
    chk('README の印のキーが、ここで数えられるものだけ', set(seen) <= set(mine2), True)
    for k in sorted(seen):
        if k in mine2: chk(f'README の {k}', sorted(seen[k]) if len(seen[k]) > 1 else next(iter(seen[k])), mine2[k])
else: print('\n     (環境変数 README が無いので、README の数との比べは飛ばした)')
import sys
print(f'\n確かめ {len(ok_all)} 項目のうち OK {sum(ok_all)} / 所要 {time.time()-t0:.0f} 秒 / メモリ最大 {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:,.0f} MB')
if not all(ok_all): sys.exit(3)
