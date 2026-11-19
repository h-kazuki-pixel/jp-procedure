"""自作 SHACL(rdf/shapes.ttl)で上限を外した 3 か所に、下限(1 つ以上)が効いているかを、小さな壊したデータで確かめる。.venv の python(pyshacl)。
1. 版(eli:LegalExpression)の jpp:asOf … 0 個で違反、1 個・3 個で違反なし
2. 照合できた最も深い条・項・号の eli:is_realized_by … 0 個で違反、2025-11-01 の版 1 つ + ほかの版 2 つ(計 3)で違反なし
3. 改正(jpp:LawRevision)の jpp:enforcementDate … 0 個で違反、期間の外の日付 1 個で違反なし(期間は 57 で確かめる)
"""
import sys, rdflib, pyshacl
SH = rdflib.Graph().parse(sys.argv[1] if len(sys.argv) > 1 else 'rdf/shapes.ttl')
P = '''@prefix eli: <http://data.europa.eu/eli/ontology#> . @prefix jpp: <https://w3id.org/jp-procedure/def#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . @prefix b: <https://example.org/t/> .
b:law a eli:LegalResource ; eli:id_local "X" . b:p a eli:LegalResourceSubdivision ; eli:is_part_of b:law .
'''
def ver(name, asofs, prov='b:p'):
    a = ' ; '.join(f'jpp:asOf "{d}"^^xsd:date' for d in asofs)
    return f'b:{name} a eli:LegalExpression ; eli:realizes {prov} ; eli:version_date "2025-06-01"^^xsd:date ; jpp:text "t"@ja ; jpp:lawRevision "r"' + (f' ; {a}' if a else '') + ' .\n'
CASES = [
    # (見出し, データ, 調べる性質, 違反を期待するか)。テスト用の条には jpp:level などを置いていないので、調べる性質の違反だけを見る
    ('1 asOf 0 個', ver('e', []), True),
    ('1 asOf 1 個', ver('e', ['2025-11-01']), False),
    ('1 asOf 3 個', ver('e', ['2025-11-01', '2026-11-18', '2026-11-25']), False),
    ('2 is_realized_by 0 個', 'b:c jpp:citedProvision b:q . b:q a eli:LegalResourceSubdivision ; eli:is_part_of b:law .\n', True),
    ('2 is_realized_by 3 個', 'b:c jpp:citedProvision b:p . b:p eli:is_realized_by b:e1, b:e2, b:e3 .\n' + ver('e1', ['2025-11-01']) + ver('e2', ['2026-11-18']) + ver('e3', ['2026-11-25']), False),
    ('3 enforcementDate 0 個', 'b:r a jpp:LawRevision ; jpp:revisionOf b:law .\n', True),
    ('3 enforcementDate 期間の外 1 個', 'b:r a jpp:LawRevision ; jpp:revisionOf b:law ; jpp:enforcementDate "2030-01-01"^^xsd:date .\n', False),
]
ok = True
for lab, ttl, want in CASES:
    g = rdflib.Graph().parse(data=P + ttl, format='turtle')
    conf, rg, _ = pyshacl.validate(g, shacl_graph=SH, advanced=True)
    SHN = rdflib.Namespace('http://www.w3.org/ns/shacl#')
    paths = sorted({str(rg.value(r, SHN.resultPath)).split('#')[-1].split('/')[-1] for r in rg.subjects(rdflib.RDF.type, SHN.ValidationResult)})
    prop = {'1': 'asOf', '2': 'is_realized_by', '3': 'enforcementDate'}[lab[0]]
    got = prop in paths; ok &= (got == want)
    print(f'  {lab}: {prop} の違反 {"あり" if got else "なし"}(期待: {"あり" if want else "なし"})(ほかの性質の違反: {", ".join(x for x in paths if x != prop) or "なし"}) {"OK" if got == want else "NG"}')
print('すべて期待どおり' if ok else '期待と違うものがある'); sys.exit(0 if ok else 1)
