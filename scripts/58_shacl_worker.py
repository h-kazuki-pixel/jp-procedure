"""1 回分の SHACL。.venv の python で、1 回ごとに別のプロセスとして動かす(メモリの最大をその回だけで測るため)。
引数: 切り分けのフォルダ、回の JSON、出力 JSON、形のファイル"""
import sys, json, gzip, time, resource, rdflib, pyshacl
from rdflib.collection import Collection
D, run, out, shapes_file = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]
SH = rdflib.Namespace('http://www.w3.org/ns/shacl#'); JPP = rdflib.Namespace('https://w3id.org/jp-procedure/def#')
t0 = time.time()
g = rdflib.Graph()
for n in run['data']: g.parse(gzip.open(f'{D}/{n}.ttl.gz'), format='turtle')
full = rdflib.Graph(); full.parse(shapes_file, format='turtle')
if run.get('shapes'):   # 名前を挙げた形と、そこから空白ノードでたどれるものだけを使う
    sh = rdflib.Graph(); [sh.bind(p, n) for p, n in full.namespaces()]
    todo = [JPP[s] for s in run['shapes']]; seen = set()
    while todo:
        s = todo.pop()
        if s in seen: continue
        seen.add(s)
        for p, o in full.predicate_objects(s):
            sh.add((s, p, o))
            if isinstance(o, rdflib.BNode): todo.append(o)
else: sh = full
t1 = time.time()
conf, rg, _ = pyshacl.validate(g, shacl_graph=sh, inference='none', allow_warnings=True)
t2 = time.time()
focus = None
if run.get('focus') is not None:
    focus = set()
    for n in run['focus']: focus.update(l.strip() for l in open(f'{D}/{n}.focus.txt'))
def pstr(p, gr):
    if p is None: return '-'
    if isinstance(p, rdflib.BNode):
        try: return '(' + ' / '.join(pstr(x, gr) for x in Collection(gr, p)) + ')'
        except Exception: return '[' + ', '.join(f'{pstr(a, gr)}={pstr(b, gr)}' for a, b in gr.predicate_objects(p)) + ']'
    return rg.namespace_manager.normalizeUri(p) if isinstance(p, rdflib.URIRef) else str(p)
parent = {}
for ns, ps in sh.subject_objects(SH.property): parent[ps] = ns
res, dropped = [], 0
for r in rg.subjects(rdflib.RDF.type, SH.ValidationResult):
    f = rg.value(r, SH.focusNode)
    if focus is not None and str(f) not in focus: dropped += 1; continue
    ss = rg.value(r, SH.sourceShape)
    ssl = pstr(ss, sh) if not isinstance(ss, rdflib.BNode) else f'{pstr(parent.get(ss), sh)} の性質 {pstr(sh.value(ss, SH.path), sh)}'
    res.append(dict(focus=str(f), cls='/'.join(sorted(pstr(o, g) for o in g.objects(f, rdflib.RDF.type))) or '(型なし)',
                    path=pstr(rg.value(r, SH.resultPath), rg), comp=pstr(rg.value(r, SH.sourceConstraintComponent), rg).replace('sh:', ''),
                    sev=pstr(rg.value(r, SH.resultSeverity), rg).replace('sh:', ''), shape=ssl, value=str(rg.value(r, SH.value)),
                    msg=str(rg.value(r, SH.resultMessage))[:200]))
json.dump(dict(name=run['name'], triples=len(g), conforms=conf, results=res, dropped_outside_focus=dropped,
               load_s=round(t1 - t0, 1), validate_s=round(t2 - t1, 1), maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)), open(out, 'w'), ensure_ascii=False)
