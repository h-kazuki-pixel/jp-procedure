"""queries/*.rq を店に対して回す。1 回目と 2 回目の時間、結果の件数、最初の 5 件を書く。.venv の python。
使い方: python3 scripts/63_queries.py [店の場所] [問いの場所]   既定は store/oxigraph と queries"""
import os, sys, glob, time, pyoxigraph as ox
STORE = sys.argv[1] if len(sys.argv) > 1 else 'store/oxigraph'; QD = sys.argv[2] if len(sys.argv) > 2 else 'queries'
st = ox.Store.read_only(STORE)
PRE = open(os.path.join(QD, 'PREFIXES.rq')).read()
def val(t):
    if t is None: return ''
    v = t.value; return v if len(v) <= 160 else v[:160] + f'…(全 {len(v)} 字)'
for f in sorted(glob.glob(os.path.join(QD, 'q*.rq'))):
    q = PRE + open(f).read(); times = []
    for _ in range(2):
        t0 = time.time(); res = st.query(q); vars_ = [v.value for v in res.variables]; rows = [[val(s[v]) for v in vars_] for s in res]; times.append(time.time() - t0)
    print(f'\n# {f}\n  時間: 1 回目 {times[0]:.3f} 秒 / 2 回目 {times[1]:.3f} 秒 / 結果 {len(rows):,} 件')
    print('  | ' + ' | '.join(vars_) + ' |')
    for r in rows[:5]: print('  | ' + ' | '.join(r) + ' |')
    if f.endswith(('q2_changed_by_kind.rq', 'q3_changed_by_ministry.rq')):
        print('  (全件)'); [print('  | ' + ' | '.join(r) + ' |') for r in rows[5:]]
        if 'q2' in f: print(f'  手続の計 {sum(int(r[1]) for r in rows):,} / 改正の記録の計 {sum(int(r[2]) for r in rows):,}')
        else: print(f'  手続の計 {sum(int(r[1]) for r in rows):,} / 変わった手続の計 {sum(int(r[2]) for r in rows):,}')
    if f.endswith('q4_old_new_text.rq'):
        import difflib
        full = [[s[v].value if s[v] is not None else '' for v in vars_] for s in st.query(q)]
        ti = vars_.index('text')
        for r in full: print(f'  全文({r[vars_.index("asOf")]}): {r[ti]}')
        if len(full) == 2:
            a, b = full[0][ti], full[1][ti]
            for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if op[0] != 'equal': print(f'  違い: {op[0]} 旧「{a[op[1]:op[2]]}」→ 新「{b[op[3]:op[4]]}」')
