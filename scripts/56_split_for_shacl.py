"""SHACL を分けて通すための切り分け(rdflib は使わない。50/54 が書いた Turtle は、行頭が < の行から主語ごとのかたまりになっている)。
使い方: python3 -I scripts/56_split_for_shacl.py test|full
test: 手続ID の並びで最初の 2,000 件と、それにつながる記録・法令・条項号・本文の版だけを切り出す。"""
import sys, os, re, gzip, json, collections, glob
MODE = sys.argv[1]; assert MODE in ('test', 'full')
RDF = os.environ.get('RDF_DIR', 'rdf')   # 公開用のリポジトリでは data/rdf
OUT = f'out/shacl_chunks/{MODE}'; os.makedirs(OUT, exist_ok=True)
NB = {'test': dict(P=4, S=2, E=3), 'full': dict(P=10, S=4, E=10)}[MODE]
B = 'https://w3id.org/jp-procedure/'
def blocks(name):
    head, cur = [], None
    for line in gzip.open(name if name.endswith('.gz') else f'{RDF}/{name}.ttl.gz', 'rt', encoding='utf-8'):
        if line.startswith('@prefix'): head.append(line); continue
        if line.startswith('<'):
            if cur: yield cur
            cur = [line]
        elif line.startswith('    '): cur.append(line)
        elif line.strip() == '': continue
        else: raise ValueError(f'{name}: 想定外の行 {line[:80]!r}')
    if cur: yield cur
HEAD = ''.join(l for l in gzip.open(f'{RDF}/codes.ttl.gz', 'rt', encoding='utf-8') if l.startswith('@prefix'))
HEAD += ''.join(l for l in gzip.open(f'{RDF}/changes.ttl.gz', 'rt', encoding='utf-8') if l.startswith('@prefix') and l not in HEAD)   # changes だけが dcat を使う
SUBJ = re.compile(r'^<([^>]+)>')
def subj(b): return SUBJ.match(b[0]).group(1)
def pid_key(p): m = re.match(r'^([A-Za-z]*)(\d+)$', p); return (m.group(1), int(m.group(2))) if m else (p, 0)
def proc_id(s):
    m = re.match(re.escape(B) + r'(?:procedure/|record/r7/)([^/]+)(?:/citation)?$', s); return m.group(1)
def law_of(s): return re.match(re.escape(B) + r'(?:provision|law)/([^/]+)', s).group(1)
def write(fn, bl):
    with gzip.open(f'{OUT}/{fn}.ttl.gz', 'wt', encoding='utf-8') as f:
        f.write(HEAD)
        for b in bl: f.write(''.join(b))
    with open(f'{OUT}/{fn}.focus.txt', 'w') as f:
        for b in bl: f.write(subj(b) + '\n')
def bins(keys, weight, n):   # 並べたキーを、重さがほぼ同じになるように n 個の連続した範囲に分ける
    tot = sum(weight[k] for k in keys); out, cur, acc = [], [], 0
    for k in keys:
        cur.append(k); acc += weight[k]
        if acc >= tot * (len(out) + 1) / n and len(out) < n - 1: out.append(cur); cur = []
    if cur: out.append(cur)
    return out
log = []
# 手続(手続とその照合のかたまり)
proc = collections.defaultdict(list); cited = collections.defaultdict(list); citedlaw = collections.defaultdict(set)
for b in blocks('procedures'):
    s = subj(b); pid = proc_id(s); proc[pid].append(b)
    for l in b:
        m = re.match(r'\s+jpp:citedProvision <([^>]+)>', l)
        if m: cited[pid].append((s, m.group(1)))
        m = re.match(r'\s+jpp:citedLaw <([^>]+)>', l)
        if m: citedlaw[pid].add(law_of(m.group(1)))
ids = sorted(proc, key=pid_key)
if MODE == 'test': ids = ids[:2000]
ids_set = set(ids)
laws_sel = set().union(*(citedlaw[p] for p in ids)) | {law_of(o) for p in ids for _, o in cited[p]}
pb = bins(ids, {p: 1 for p in ids}, NB['P'])
runs = []
for k, g in enumerate(pb):
    write(f'P{k}', [b for p in g for b in proc[p]])
    log.append(f'P{k}: 手続ID {g[0]} 〜 {g[-1]}、手続 {len(g):,}')
# 記録(同じ手続ID の範囲で分ける)
rec = {}
for b in blocks('records'):
    pid = proc_id(subj(b))
    if pid in ids_set: rec[pid] = b
assert len(rec) == len(ids), (len(rec), len(ids))
for k, g in enumerate(pb):
    write(f'R{k}', [rec[p] for p in g]); log.append(f'R{k}: 手続ID {g[0]} 〜 {g[-1]}、記録 {len(g):,}')
# 法令・条項号・本文の版(法令ID で分ける)
law_b = [b for b in blocks('laws') if MODE == 'full' or law_of(subj(b)) in laws_sel]
write('L', law_b); log.append(f'L: 法令 {len(law_b):,}')
prov = collections.defaultdict(list)
for b in blocks('provisions'):
    l = law_of(subj(b))
    if MODE == 'full' or l in laws_sel: prov[l].append(b)
expr = collections.defaultdict(list)
for b in blocks('expressions'):
    l = law_of(subj(b))
    if MODE == 'full' or l in laws_sel: expr[l].append(b)
lk = sorted(set(prov) | set(expr))
for k, g in enumerate(bins(lk, {l: sum(len(b) for b in prov.get(l, [])) + 1 for l in lk}, NB['S'])):
    write(f'S{k}', [b for l in g for b in prov.get(l, [])]); log.append(f'S{k}: 法令ID {g[0]} 〜 {g[-1]}、条項号 {sum(len(prov.get(l, [])) for l in g):,}')
cited_by_law = collections.defaultdict(list)
for p in ids:
    for s, o in cited[p]: cited_by_law[law_of(o)].append((s, o))
eb = bins(lk, {l: sum(len(''.join(b)) for b in expr.get(l, [])) + 1 for l in lk}, NB['E'])
for k, g in enumerate(eb):
    write(f'E{k}', [b for l in g for b in expr.get(l, [])])
    tri = [(s, o) for l in g for s, o in cited_by_law.get(l, [])]
    with gzip.open(f'{OUT}/Ec{k}.ttl.gz', 'wt', encoding='utf-8') as f:
        f.write(HEAD); f.writelines(f'<{s}> jpp:citedProvision <{o}> .\n' for s, o in tri)
    with open(f'{OUT}/E{k}.focus.txt', 'a') as f: f.writelines(o + '\n' for o in sorted({o for _, o in tri}))
    log.append(f'E{k}: 法令ID {g[0]} 〜 {g[-1]}、かたまり {sum(len(expr.get(l, [])) for l in g):,}、照合した条項号への参照 {len(tri):,}')
# 改正の記録(本文の版と同じ法令ID の範囲。法令に属さないもの=区分のコード表・期間・作業は Xc)
law_bin = {l: k for k, g in enumerate(eb) for l in g}
xb = collections.defaultdict(list); xc = []; ewb = collections.defaultdict(list); nolaw = {}
WEEKLY = sorted(glob.glob(f'{RDF}/weekly/*.ttl.gz'))   # 毎週の追跡が足した改正の記録
VER = re.compile(re.escape(B) + r'provision/[^>]+/version/')
for src in ['changes'] + WEEKLY:
    for b in blocks(src):
        m = re.match(re.escape(B) + r'(?:change|provision|law)/([^/]+)', subj(b))
        if not m: xc.append(b); continue
        l = m.group(1)
        if not (MODE == 'full' or l in laws_sel): continue
        # 毎週の追跡の版と「条・項・号 → 版」の線は、本文の版の回(Ew)へ。条・項・号の本体は provisions にあるので、改正の記録の回では対象にしない
        if src != 'changes' and (VER.match(subj(b)) or (len(b) == 1 and ' eli:is_realized_by ' in b[0])): ewb[law_bin[l]].append(b)
        else:
            # 期間内の改正の節点は、条・項・号も本文の版も無い法令にも置く(法令の単位の数のため)。その法令は順に回へ割り振る
            if l not in law_bin: law_bin[l] = nolaw.setdefault(l, len(nolaw) % len(eb))
            xb[law_bin[l]].append(b)
for k in range(len(eb)):
    write(f'X{k}', xb[k]); write(f'Ew{k}', ewb[k]); log.append(f'X{k}: 改正の記録などのかたまり {len(xb[k]):,} / Ew{k}: 毎週の追跡の版など {len(ewb[k]):,}')
write('Xc', xc); log.append(f'X: 条・項・号も本文の版も無い法令の改正の節点など、法令 {len(nolaw):,}')
# 組織・コード表・出典はそのまま
for n, fn in [('organisations', 'O'), ('codes', 'C'), ('prov', 'V')]:
    write(fn, list(blocks(n)))
# 語彙はそのまま写す(eli:LegalResourceSubdivision rdfs:subClassOf eli:LegalResource を sh:class が見るため、どの回にも入れる)
import shutil; shutil.copy(f'{RDF}/vocab.ttl.gz', f'{OUT}/Vo.ttl.gz')
# 型だけの索引(sh:class を確かめるため): コード表・組織・法令・条項号の rdf:type
TY = re.compile(r'^<([^>]+)> a ([^ ;.]+)')
with gzip.open(f'{OUT}/typeindex.ttl.gz', 'wt', encoding='utf-8') as f:
    f.write(HEAD); n = 0
    for fn in ['C', 'O', 'L', 'Xc'] + [f'S{k}' for k in range(NB['S'])]:
        for line in gzip.open(f'{OUT}/{fn}.ttl.gz', 'rt', encoding='utf-8'):
            m = TY.match(line)
            if m: f.write(f'<{m.group(1)}> a {m.group(2)} .\n'); n += 1
    # 改正の記録の移った先・候補として足した条・項・号(X の回にある)の型も入れる。毎週の追跡が、その版(eli:realizes の先)を本文の版の回に書くため
    for fn in [f'X{k}' for k in range(len(eb))]:
        for line in gzip.open(f'{OUT}/{fn}.ttl.gz', 'rt', encoding='utf-8'):
            m = TY.match(line)
            if m and m.group(2) == 'eli:LegalResourceSubdivision': f.write(f'<{m.group(1)}> a {m.group(2)} .\n'); n += 1
log.append(f'typeindex: rdf:type {n:,} 行(コード表・組織・法令・条項号・改正の記録の区分など)')
P = [f'P{k}' for k in range(len(pb))]; R = [f'R{k}' for k in range(len(pb))]; S = [f'S{k}' for k in range(NB['S'])]; E = [f'E{k}' for k in range(len(eb))]
own = [dict(name=x, data=[x, 'typeindex'], focus=[x], shapes=['ProcedureShape', 'CitationShape']) for x in P] + \
      [dict(name=x, data=[x], focus=[x], shapes=['RecordShape']) for x in R] + \
      [dict(name=x, data=[x, 'typeindex'], focus=[x], shapes=['SubdivisionShape', 'LawShape']) for x in S] + \
      [dict(name='L', data=['L'], focus=['L'], shapes=['LawShape'])] + \
      [dict(name=x, data=[x, 'Ec' + x[1:], 'Ew' + x[1:], 'typeindex'], focus=[x, 'Ew' + x[1:]], shapes=['ExpressionShape', 'CitedProvisionShape']) for x in E] + \
      [dict(name='X' + x[1:], data=['X' + x[1:], x, 'Ew' + x[1:], 'typeindex', 'Xc'], focus=['X' + x[1:]], shapes=['ChangeShape', 'RevisionShape', 'ReviewShape', 'SubdivisionShape', 'LawShape', 'LawStatusChangeShape', 'LawStatusShape', 'LawStatusUnclearShape']) for x in E]
off = [dict(name=x, data=[x, 'typeindex'], focus=[x], shapes=None) for x in P] + \
      [dict(name=x, data=[x, 'typeindex'], focus=[x], shapes=None) for x in ['O', 'L', 'C'] + S] + \
      [dict(name='X' + x[1:], data=['X' + x[1:], 'typeindex', 'Xc'], focus=['X' + x[1:]], shapes=None) for x in E] + [dict(name='Xc', data=['Xc', 'typeindex'], focus=['Xc'], shapes=None)]   # 条・項・号も eli:LegalResource の下位クラスなので公式の LegalResourceShape の対象
whole = ['C', 'V', 'O', 'L', 'typeindex', 'Xc'] + P + R + S + E + ['Ec' + x[1:] for x in E] + ['X' + x[1:] for x in E] + ['Ew' + x[1:] for x in E]
for r in own + off: r['data'].append('Vo')
whole.append('Vo')
json.dump(dict(weekly=[os.path.basename(f) for f in WEEKLY], mode=MODE, own=own, official=off, whole=whole, n_proc=len(ids), laws=len(laws_sel)), open(f'{OUT}/manifest.json', 'w'), ensure_ascii=False, indent=1)
print(f'# 切り分け {MODE}: 手続 {len(ids):,}、法令 {len(laws_sel) if MODE == "test" else len(law_b):,}')
for l in log: print('  ' + l)
