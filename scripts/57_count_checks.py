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
rev_found = {}   # 毎週の追跡が初めて足した改正 → 初めて見つけた日(jpp:firstFoundOn)。見つけた日が期間の終わりより後なら、その期間の「期間内の改正」には数えない
t0 = time.time()
CHG = set()   # changes の回(X・Xc・Ew)のトリプル(rdflib)。ほかの回にあるものは後で除く
typ = collections.defaultdict(set); typ_ex = set(); wreal = set(); wasof = collections.defaultdict(set); per_of = {}; objs = collections.defaultdict(list); ident = []; asof = collections.Counter(); real = set(); realized_by = set()
ntrip = collections.Counter(); ex_asof = collections.defaultdict(set); cited_of = {}; cit_of = {}; chg = {}; rev_of = {}; rev_date = {}; cit_law = {}; cit_mr = {}; lsc = {}; lst = {}; unc = {}; periods = {}; rev_id = {}; sub_ch = set(); lawrev = {}; reviews = {}; review_ref = collections.Counter(); comp_of = collections.defaultdict(set); org_label = collections.defaultdict(set); title_of = collections.defaultdict(set)
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
            for s_, o in g.subject_objects(DCT.title): title_of[s_].add(str(o))
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
                               aff=list(g.objects(ch, JPP.affects)), revs=list(g.objects(ch, JPP.lawRevisionInPeriod)), moved=g.value(ch, JPP.movedTo))
            for rv in g.subjects(RDF.type, JPP.LawRevision): rev_of[rv] = g.value(rv, JPP.revisionOf); rev_date[rv] = str(g.value(rv, JPP.enforcementDate))
            for rv in g.subjects(RDF.type, JPP.LawRevision):
                if g.value(rv, JPP.firstFoundOn) is not None: rev_found[rv] = str(g.value(rv, JPP.firstFoundOn))
            for ch in g.subjects(RDF.type, JPP.ProvisionChange):
                chg[ch].update(found=g.value(ch, JPP.foundRevision), found_on=str(g.value(ch, JPP.foundOn) or ''), before=g.value(ch, JPP.enforcedBeforePeriod), recheck=g.value(ch, JPP.recheckReason))
            for rv in g.subjects(RDF.type, JPP.LawRevision): rev_id[rv] = str(g.value(rv, DCT.identifier))
            for c in g.subjects(RDF.type, JPP.LawStatusChange):
                lsc[c] = dict(law=g.value(c, JPP.law), per=str(g.value(c, DCT.temporal)).rsplit('/', 1)[-1], date=str(g.value(c, JPP.repealDate)), aff=set(g.objects(c, JPP.affects)))
            for c in g.subjects(RDF.type, JPP.LawStatus): lst[g.value(c, JPP.statusOf)] = str(g.value(c, JPP.repealDate))
            for c in g.subjects(RDF.type, JPP.LawStatusUnclear): unc[g.value(c, JPP.statusOf)] = str(g.value(c, JPP.currentRevisionStatus))
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
base_rev = [r for r in rev_of if '2025-11-01' < rev_date[r] <= '2026-11-18' and rev_found.get(r, '') <= '2026-11-18']
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
    chk('遅れて載った印(jpp:enforcedBeforePeriod)が、見つけた改正を週の追跡が初めて足し(jpp:firstFoundOn)、その施行期日が期間の始め以前の記録にだけある', all((v.get('before') is not None) == (v['found'] in rev_found and rev_date.get(v['found'], '9999') <= per_of[k].split('_')[0]) for k, v in W.items()), True)
    chk('あとで比べた理由(jpp:recheckReason)は、旧い版に 2026-11-18 以後の確かめた日が無い(初めのデータに新しい版が無かった)記録にだけある', all((v.get('recheck') is not None) == (max(allasof[v['old']]) < '2026-11-18') for k, v in W.items()), True)
    chk('移った先のある記録は、移った先に期間の終わりの版(文言)がある', all(v['moved'] is None or any((e_, v['moved']) in allreal and per_of[k].split('_')[1] in allasof[e_] for e_ in vers_of[v['moved']]) for k, v in W.items()), True)
    added = {x for x, a in wasof.items() if x in ex_asof}   # 公開しているデータの版に、毎週の追跡が確かめた日だけを足したもの
    print(f'     毎週の追跡が確かめた日だけを足した版: {len(added):,}(新しく書いた版 {len([x for x in wasof if x not in ex_asof]):,})')
    print('     期間ごと:', dict(collections.Counter(per_of[k] for k in W)), '/ 施行期日が期間の始め以前の記録:', sum(1 for v in W.values() if v.get('before') is not None))
# 期間ごとの数(閲覧ページのはじめの画面の数)。ここでは SPARQL を使わずに数え、stats.json(75_make_stats.py が問いで出したもの)があれば比べる
print('\n# 期間ごとの数(改正の記録・知らせる手続・法令の単位で知らせた場合の手続)')
mine = {}
for k, (ps0, pe0) in sorted(periods.items(), key=lambda x: x[1]):
    chs = [v for c, v in allchg.items() if per_of[c] == k]
    # 期間に見つけた改正: 施行期日が期間の中にある改正(遅れて見つけたものを除く)と、その期間の記録が見つけた改正(queries/q7 と同じ)
    revl = {rev_of[r] for r in rev_of if ps0 < rev_date[r] <= pe0 and rev_found.get(r, '') <= pe0} | {rev_of[v['found']] for v in chs if v.get('found') is not None and v['found'] in rev_of}
    ll = {p for p, c in cit_of.items() if cit_mr.get(c) in ('article', 'paragraph', 'item') and cit_law.get(c) in revl}
    nt = {a for v in chs for a in v['aff']}
    mine[(ps0, pe0)] = (len(chs), len(nt), len(ll))
    print(f'     {ps0}〜{pe0}: 改正の記録 {len(chs):,} / 知らせる手続 {len(nt):,} / 法令の単位で知らせた場合の手続 {len(ll):,}(期間内の改正 {sum(1 for r in rev_of if ps0 < rev_date[r] <= pe0 and rev_found.get(r, '') <= pe0):,})')
    chk(f'{ps0}〜{pe0}: 知らせる手続が、法令の単位で知らせた場合の手続(期間に見つけた改正で数える)に含まれる', nt <= ll, True)
# 根拠の法令が廃止・失効した記録(jpp:LawStatusChange。条文の文言の比べとは別に数える)と、法令の状態(jpp:LawStatus)
print(f'\n# 根拠の法令の廃止・失効(記録 {len(lsc)}・法令の状態 {len(lst)})')
law_cites = collections.defaultdict(set)
for p_, c_ in cit_of.items():
    if c_ in cit_law: law_cites[cit_law[c_]].add(p_)
ls_mine = {}
if lsc:
    chk('廃止・失効の記録の手続が手続の中にある', all(v['aff'] <= ps for v in lsc.values()), True)
    chk('廃止・失効の記録の手続 = その法令を根拠に挙げる(jpp:citedLaw)すべての手続', all(v['aff'] == law_cites[v['law']] for v in lsc.values()), True)
    chk('廃止・失効の日が、その記録の期間の中にある', all(periods[v['per']][0] < v['date'] <= periods[v['per']][1] for v in lsc.values()), True)
    chk('同じ法令・同じ期間の記録が 2 つ無い', len({(v['law'], v['per']) for v in lsc.values()}) == len(lsc), True)
    chk('廃止・失効の記録の法令に、同じ日の法令の状態がある', all(lst.get(v['law']) == v['date'] for v in lsc.values()), True)
    for k, (s0, e0) in sorted(periods.items(), key=lambda x: x[1]):
        vs = [v for v in lsc.values() if v['per'] == k]
        ls_mine[(s0, e0)] = (len({v['law'] for v in vs}), len(set().union(*[v['aff'] for v in vs])) if vs else 0)
        if vs: print(f'     {s0}〜{e0}: 法令 {ls_mine[(s0, e0)][0]:,} / 手続 {ls_mine[(s0, e0)][1]:,}')
if lst: chk('法令の状態の法令が、法令の中にある', set(lst) <= law, True)
if unc:
    print(f'     分類しない法令 {len(unc)}・その手続 {len(set().union(*[law_cites[l] for l in unc])):,}')
    chk('分類しない法令が、法令の中にある', set(unc) <= law, True)
    chk('分類しない法令に、廃止・失効の記録も法令の状態も無い', not (set(unc) & (set(lst) | {v['law'] for v in lsc.values()})), True)
    chk('分類しない法令の今の版の状態が Repeal でない', all(v != 'Repeal' for v in unc.values()), True)
STATS = os.environ.get('STATS')
if STATS and os.path.exists(STATS):
    st = json.load(open(STATS, encoding='utf-8'))
    chk(f'{STATS} の手続の数', st['procedures'], len(ps))
    got = {(x['start'], x['end']): (x['changes'], x['notified'], x['law_level']) for x in st['periods']}
    chk(f'{STATS} の期間の集合 = 期間の節点の集合', set(got) == set(mine), True)
    got_ls = {(x['start'], x['end']): (x.get('law_status_laws', 0), x.get('law_status_procedures', 0)) for x in st['periods']}
    chk(f'{STATS} の期間ごとの(廃止・失効した法令, その手続)が、数え直したものと同じ', {k: v for k, v in got_ls.items() if v != (0, 0)} == {k: v for k, v in ls_mine.items() if v != (0, 0)}, True)
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
             'law_level': len(lawlevel),
             'changes_base': len(chg), 'change_rows_base': sum(len(v['aff']) for v in chg.values()),
             'changes_weekly': len(allchg) - len(chg), 'change_rows_weekly': sum(len(v['aff']) for k, v in allchg.items() if k not in chg),
             'law_status_laws': len({v['law'] for v in lsc.values()}), 'law_status_rows': sum(len(v['aff']) for v in lsc.values())}
    # 名と所管府省庁が同じ手続(手続 ID が別)の組と、その手続の数(数の断り)
    same = collections.defaultdict(set)
    for p_ in ps:
        for t_ in title_of[p_]:
            for o_ in comp_of[p_]: same[(t_, o_)].add(p_)
    same = [len(v) for v in same.values() if len(v) > 1]; mine2['same_name_groups'] = len(same); mine2['same_name_rows'] = sum(same)
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
    chk('README に数の断り(名と府省庁が同じ組・件)の印がある', {'same_name_groups', 'same_name_rows'} <= set(seen), True)
    # 閲覧ページ(README の隣の view.html)の <!-- n: --> の数(数の断り)
    vp_ = os.path.join(REPO, 'view.html')
    if os.path.exists(vp_):
        vseen = re.findall(r'<!-- n:([^ ]+) -->([^<]*)<!-- /n -->', open(vp_, encoding='utf-8').read())
        print(f'\n# view.html の数(<!-- n: -->、{len(vseen)} か所)')
        chk('view.html に数の断りの印がある', {'same_name_groups', 'same_name_rows'} <= {k for k, _ in vseen}, True)
        for k, v in vseen: chk(f'view.html の {k}', int(v.replace(',', '')) if k in mine2 else None, mine2.get(k, 'ここで数えられないキー'))
else: print('\n     (環境変数 README が無いので、README の数との比べは飛ばした)')
# README の冒頭と閲覧ページの要約の数(<!-- s:キー -->。75 が stats.json から書き込んだもの)を、ここで数え直した数と比べる
if STATS and os.path.exists(STATS):
    import re
    BP = ('2025-11-01', '2026-11-18')
    wk = sorted(k for k in mine if k[0] >= BP[1])
    exp = {'procedures': len(ps), 'base_period': f'{BP[0]}〜{BP[1]}', 'base_law_level': mine[BP][2], 'base_notified': mine[BP][1],
           'base_ratio': round(mine[BP][2] / mine[BP][1], 1), 'base_changes': mine[BP][0], 'ls_laws': ls_mine.get(BP, (0, 0))[0], 'ls_procedures': ls_mine.get(BP, (0, 0))[1]}
    if wk: exp.update(week_period=f'{wk[-1][0]}〜{wk[-1][1]}', week_changes=mine[wk[-1]][0], week_notified=mine[wk[-1]][1])
    exp = {k: (f'{v:,}' if isinstance(v, int) else str(v)) for k, v in exp.items()}
    SD = os.path.dirname(os.path.abspath(STATS))
    for fn, need in [('README.md', ['procedures', 'base_period', 'base_law_level', 'base_notified', 'base_ratio', 'ls_laws', 'ls_procedures', 'week_period', 'week_changes']),
                     ('view.html', ['procedures', 'base_period', 'base_law_level', 'base_notified', 'ls_laws', 'ls_procedures', 'week_changes'])]:
        fp = os.path.join(SD, fn)
        if not os.path.exists(fp): chk(f'{fn} がある(stats.json の隣)', False, True); continue
        got = re.findall(r'<!-- s:([a-z_]+) -->([^<]*)<!-- /s -->', open(fp, encoding='utf-8').read())
        print(f'\n# {fn} の要約の数(<!-- s: -->、{len(got)} か所)')
        chk(f'{fn} の要約に、要る印がすべてある', set(need) <= {k for k, _ in got}, True)
        chk(f'{fn} の印のキーが、ここで数えられるものだけ', {k for k, _ in got} <= set(exp), True)
        for k, v in got:
            if k in exp: chk(f'{fn} の {k}', v, exp[k])
# 例の文(<!-- e:手続ID -->。83 が店への問いで書いたもの)の額・日付・法令の名を、公開データのファイルを直に読んだ値と比べる。
# 手続 18109: 根拠の法令の状態(jpp:LawStatusChange)の法令の名・日付・状態。手続 107294: 改正の記録 2 つ(初めの期間と毎週の追跡)の旧い文言・新しい文言の、違う額と、毎週の追跡が見つけた改正の施行期日
if STATS and os.path.exists(STATS):
    import re, html as _html
    SD = os.path.dirname(os.path.abspath(STATS)); BASEU = 'https://w3id.org/jp-procedure/'
    EXID = {'18109': 'status', '107294': 'amount'}
    pu = {i: URIRef(BASEU + 'procedure/' + i) for i in EXID}
    ex_ls = {i: [v for v in lsc.values() if pu[i] in v['aff'] and v['per'] == '2025-11-01_2026-11-18'] for i in EXID}
    ex_ch = {i: sorted([(per_of[c], v) for c, v in allchg.items() if pu[i] in v['aff']], key=lambda x: x[0]) for i in EXID}
    need = set(pu.values()) | {v['law'] for i in EXID for v in ex_ls[i]} | {x for i in EXID for _, v in ex_ch[i] for x in (v['prov'], v['old'], v['new'], v.get('found'))}
    need.discard(None)
    # ファイルを 1 回だけ読み通す: 例の主語のトリプルすべてと、すべての主語の rdfs:label・skos:prefLabel・eli:is_part_of
    LBL, PREF, PART = 'http://www.w3.org/2000/01/rdf-schema#label', 'http://www.w3.org/2004/02/skos/core#prefLabel', str(ELI.is_part_of)
    G = collections.defaultdict(lambda: collections.defaultdict(set))
    subs = {str(x) for x in need} | {str(c) for c in lsc if any(pu[i] in lsc[c]['aff'] for i in EXID)}
    for f in sorted(glob.glob(f'{RDFDIR}/*.ttl.gz')) + WEEKLY:
        for q in ox.parse(gzip.open(f), ox.RdfFormat.TURTLE):
            if q.subject.value in subs or q.predicate.value in (LBL, PREF, PART): G[q.subject.value][q.predicate.value].add(q.object.value)
    TXT, ORG = str(JPP.text), str(CV.hasCompetentAuthority)
    one_ = lambda s_, p_: next(iter(G[str(s_)][p_])) if s_ is not None and len(G[str(s_)][p_]) == 1 else None
    def law_of(p_):
        x = str(p_)
        while x and PART in G[x]: x = one_(x, PART)
        return x
    AMT = re.compile(r'[〇一二三四五六七八九十百千万億]+円')
    def diff_amt(a, b):
        A_, B_ = AMT.findall(a or ''), AMT.findall(b or '')
        d = [(x, y) for x, y in zip(A_, B_) if x != y]
        return d[0] if len(A_) == len(B_) and len(d) == 1 else None
    exp_ex = {}
    for i, kind in EXID.items():
        t = one_(pu[i], 'http://purl.org/dc/terms/title'); o = one_(one_(pu[i], ORG), PREF)
        if kind == 'status' and len(ex_ls[i]) == 1:
            v = ex_ls[i][0]; c = next(c for c in lsc if lsc[c] is v)
            exp_ex[i] = {'title': t, 'org': o, 'law': one_(v['law'], LBL), 'date': v['date'], 'status': one_(one_(c, str(JPP.repealStatus)), PREF)}
        if kind == 'amount' and len(ex_ch[i]) == 2:
            (p0, v0), (p1, v1) = ex_ch[i]
            exp_ex[i] = {'title': t, 'law': one_(law_of(v0['prov']), LBL), 'prov': one_(v0['prov'], LBL), 'base': diff_amt(one_(v0['old'], TXT), one_(v0['new'], TXT)),
                         'week': diff_amt(one_(v1['old'], TXT), one_(v1['new'], TXT)), 'date': one_(v1.get('found'), str(JPP.enforcementDate)), 'periods': (p0, p1)}
    print(f'\n# 例の文(<!-- e: -->)と公開データ: {exp_ex}')
    chk('例の手続 2 つの値が、公開データから 1 つずつ決まる', sorted(k for k, v in exp_ex.items() if all(x is not None for x in v.values())), sorted(EXID))
    def check_sentence(where, i, tx):
        e = exp_ex.get(i)
        if not e: return
        if EXID[i] == 'status':
            m = re.search(r'手続「(.+?)」\((.+?)\)が根拠に挙げる(?:規則|法令)\((.+?)\)は、e-Gov で (\d{4}-\d{2}-\d{2}) に(.+?)と記録されています。', tx)
            chk(f'{where} の例 {i}: 手続の名・府省庁・法令の名・日付・状態', m.groups() if m else None, (e['title'], e['org'], e['law'], e['date'], e['status']))
        else:
            m = re.search(r'^(.+?) (第.+?)の額が「(.+?)」から「(.+?)」に変わりました\(初めの期間\)。(\d{4}-\d{2}-\d{2}) 施行の改正で、「(.+?)」から「(.+?)」に変わりました\(毎週の追跡\)。$', tx)
            chk(f'{where} の例 {i}: 法令の名・条項・額(初めの期間)・日付・額(毎週の追跡)', m.groups() if m else None, (e['law'], e['prov'], *e['base'], e['date'], *e['week']))
    for fn in ['README.md', 'view.html']:
        fp = os.path.join(SD, fn)
        if not os.path.exists(fp): continue
        src_ = open(fp, encoding='utf-8').read()
        got = dict(re.findall(r'<!-- e:([0-9]+) -->([^<]*)<!-- /e -->', src_))
        chk(f'{fn} に例の印が 2 つ(18109・107294)', sorted(got), sorted(EXID))
        for i, tx in got.items():
            tx = _html.unescape(tx)
            if fn == 'README.md':
                m = re.match(r'\[手続 ([0-9]+)「(.+?)」\]\(https://h-kazuki-pixel\.github\.io/jp-procedure/view\.html#/procedure/([0-9]+)\): (.*)$', tx)
                chk(f'README の例 {i} のリンク(手続ID・手続の名)', (m.group(1), m.group(2), m.group(3)) if m else None, (i, exp_ex.get(i, {}).get('title'), i))
                tx = m.group(4) if m else tx
            check_sentence(fn, i, tx)
        if fn == 'view.html':
            for nm in ['name="description"', 'property="og:description"']:
                m = re.search(r'<meta ' + nm + r' content="[^"]*?例: ([^"]*)">', src_)
                chk(f'view.html の meta {nm} に例の文がある', m is not None, True)
                if m: check_sentence(f'view.html の meta {nm}', '18109', _html.unescape(m.group(1)))
    # status.json の週ごとの「根拠の条文が変わった手続」(procedures。はじめの画面の「毎週の追跡」の札)を、ここで数えた数と比べる
    sp = os.path.join(SD, 'status.json')
    if os.path.exists(sp):
        for w in json.load(open(sp, encoding='utf-8'))['weeks']:
            k = tuple(w['period'])
            chk(f'status.json の {k[0]}〜{k[1]} の改正の記録・根拠の条文が変わった手続', (w['records'], w.get('procedures')), (mine[k][0], mine[k][1]) if k in mine else (0, 0))
import sys
print(f'\n確かめ {len(ok_all)} 項目のうち OK {sum(ok_all)} / 所要 {time.time()-t0:.0f} 秒 / メモリ最大 {(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)) / 2**20:,.0f} MB')
if not all(ok_all): sys.exit(3)
