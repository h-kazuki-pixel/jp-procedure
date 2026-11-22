"""README の冒頭と閲覧ページ(view.html)の、JavaScript が無くても読める要約の数を、stats.json から書き込む。標準ライブラリだけ。
75_make_stats.py が stats.json を書いたあとに使う。印は <!-- s:キー -->数<!-- /s -->(印の中だけを書き直す。知らないキーがあれば止める)。
全体の数の確かめ(57_count_checks.py)が、数え直した数と、書き込んだ数を比べる。
キー:
  procedures       手続の数
  base_period      初めの期間(始め〜終わり)
  base_law_level   初めの期間に、根拠の法令に改正があった手続(法令の単位で知らせた場合。q7)
  base_notified    初めの期間に、根拠の条・項・号が変わった手続(q6)
  base_ratio       base_law_level ÷ base_notified(小数第 1 位)
  base_changes     初めの期間の改正の記録(条・項・号ごと。q6)
  ls_laws・ls_procedures  初めの期間に根拠の法令が廃止・失効した法令と手続(あとで補った分。q8)
  week_period・week_changes・week_notified  毎週の追跡の直近の期間と、その改正の記録・根拠の条・項・号が変わった手続"""
import re
BASE = ('2025-11-01', '2026-11-18')
def values(S):
    per = {(p['start'], p['end']): p for p in S['periods']}
    b = per[BASE]
    weeks = sorted(k for k in per if k[0] >= BASE[1])
    V = {'procedures': S['procedures'], 'base_period': f'{BASE[0]}〜{BASE[1]}', 'base_law_level': b['law_level'], 'base_notified': b['notified'],
         'base_ratio': b['ratio'], 'base_changes': b['changes'], 'ls_laws': b.get('law_status_laws', 0), 'ls_procedures': b.get('law_status_procedures', 0)}
    if weeks:
        w = per[weeks[-1]]; V.update(week_period=f'{w["start"]}〜{w["end"]}', week_changes=w['changes'], week_notified=w['notified'])
    return {k: (f'{v:,}' if isinstance(v, int) else str(v)) for k, v in V.items()}
MARK = re.compile(r'<!-- s:([a-z_]+) -->[^<]*<!-- /s -->')
def fill(text, V, name):
    def rep(m):
        k = m.group(1)
        if k not in V: raise SystemExit(f'{name} の印のキー {k} を知らない(または stats.json に無い)')
        return f'<!-- s:{k} -->{V[k]}<!-- /s -->'
    return MARK.sub(rep, text), len(MARK.findall(text))
def read(text): return re.findall(r'<!-- s:([a-z_]+) -->([^<]*)<!-- /s -->', text)
