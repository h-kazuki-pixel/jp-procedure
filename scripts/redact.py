"""調査の記録の自由記述から、個人の連絡先(個人の氏名・個人あての電話番号・メールアドレス)を伏せる。
伏せる所の一覧は redactions.csv(公開用のリポジトリでは data/redactions.csv)。一覧には手続ID・列・位置・種類・理由だけを書き、伏せた中身は書かない。
50_build_rdf.py が調査の記録を書くときに当てる。元のデータ(data/raw・data/r7.csv)は変えない。"""
import csv, os
MARK = '(個人の連絡先のため伏せた)'
HERE = os.path.dirname(os.path.abspath(__file__))
def _find():
    for p in [os.environ.get('REDACTIONS', ''), 'redactions.csv', 'data/redactions.csv', os.path.join(HERE, '..', 'data', 'redactions.csv')]:
        if p and os.path.exists(p): return p
    raise FileNotFoundError('redactions.csv が見つからない')
RULES = {}
for r in csv.DictReader(open(_find(), encoding='utf-8')):
    RULES.setdefault((r['procedure_id'], r['column']), []).append((int(r['start']), int(r['end']), int(r['value_length'])))
used = set()
def apply(pid, column, value):
    """一覧に当たる値なら、その位置を MARK に置き換えて返す。値の長さが一覧と違えば止める(元のデータが変わったら、一覧を作り直す)。"""
    spans = RULES.get((pid, column))
    if not spans: return value
    for s, e, n in sorted(spans, reverse=True):
        if len(value) != n: raise ValueError(f'伏せる所の一覧と値の長さが違う: 手続ID {pid} 列 {column}({len(value)} ≠ {n})')
        value = value[:s] + MARK + value[e:]
    used.add((pid, column)); return value
def unused(): return sorted(set(RULES) - used)
