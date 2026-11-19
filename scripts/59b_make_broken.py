"""比べの確かめ用に、手続 2,000 件の切り分け(test)を写して、わざと壊したもの(testbad)を作る。壊し方は下の表のとおり。"""
import os, shutil, gzip, re
S, D = 'out/shacl_chunks/test', 'out/shacl_chunks/testbad'
if os.path.exists(D): shutil.rmtree(D)
shutil.copytree(S, D, ignore=shutil.ignore_patterns('results'))
def edit(fn, f):
    p = f'{D}/{fn}.ttl.gz'; t = gzip.open(p, 'rt', encoding='utf-8').read(); t2, n = f(t); assert n == 1, (fn, n)
    gzip.open(p, 'wt', encoding='utf-8').write(t2); print(f'  {fn}: 1 か所')
B = 'https://w3id.org/jp-procedure/'
def drop_first(pat):   # pat に当たる最初の行を消す(行末の ; . は前の行に合わせる)
    def f(t):
        m = re.search(pat, t, re.M)
        if not m: return t, 0
        line = m.group(0)
        if line.endswith(' .'):   # 最後の行なら、前の行の ; を . にする
            i = t.rfind(' ;', 0, m.start()); return t[:i] + ' .' + t[i + 2:m.start()] + t[m.end() + 1:], 1
        return t[:m.start()] + t[m.end() + 1:], 1
    return f
print('# 壊したところ')
edit('P1', drop_first(r'^    dct:title .*;$'))                          # 手続の名前を 1 つ消す → ProcedureShape minCount
edit('P2', lambda t: (t.replace('code/match-result/article>', 'code/match-result/xxx>', 1), 1))   # 照合の結果を一覧に無い値に → sh:in
edit('S0', lambda t: (re.sub(r'(^    eli:is_part_of <[^>]+> ;$)', r'\1\n    eli:is_part_of <' + B + 'law/322AC0000000120> ;', t, count=1, flags=re.M), 1))   # is_part_of を 2 つに
edit('E1', drop_first(r'^    jpp:text .*;$'))                           # 本文を 1 つ消す
edit('E2', lambda t: (t.replace('    jpp:asOf "2025-11-01"^^xsd:date ;\n', '', 1), 1))   # 2025-11-01 の印を 1 つ消す → CitedProvisionShape(当たれば)
edit('R2', drop_first(r'^    jpp:sourceRow .*;$'))                      # 記録の行番号を 1 つ消す
edit('L', drop_first(r'^    eli:id_local .*;$'))                       # 法令の eli:id_local を 1 つ消す → LawShape(条・項・号を外す書き方にした後の確かめ)
edit('X0', drop_first(r'^    jpp:oldVersion .*;$'))                     # 改正の記録の旧い版を 1 つ消す → ChangeShape minCount
edit('X1', drop_first(r'^    jpp:movedTo .*;$'))                        # 移ったのに移った先を消す → ChangeShape の sh:or
edit('X2', lambda t: (re.sub(r'jpp:r1 "[0-9.]+"', 'jpp:r1 "1.500000"', t, count=1), 1))   # r1 を 1.5 に → maxInclusive
