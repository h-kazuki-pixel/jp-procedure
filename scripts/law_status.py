"""根拠の法令の廃止・失効の判定。毎週の追跡(70_weekly_track.py)と、初めの期間の補い(60_law_status_supplement.py)が使う。標準ライブラリだけ。

取り方(e-Gov 法令API v2 の法令一覧取得API):
  GET https://laws.e-gov.go.jp/api/2/laws?repeal_status=Repeal,Expire,Suspend,LossOfEffectiveness&limit=1000&offset=0&omit_current_revision_info=true&response_format=json
  (next_offset があれば offset を進めて続きを取る)。2026-11-21 の時点で 571 法令、1 回で取れた。
使う値(laws[].revision_info): repeal_status(廃止等の状態)・repeal_date(その日)・current_revision_status(今の版の状態)。法令ID は law_info.law_id。
判定:
  - current_revision_status が Repeal で、repeal_date がある法令だけを「廃止・失効した」とみなす。
    UnEnforced など(廃止の版が施行前と返るもの)と日付の無いものは分類せず、last_run.json の law_status_unclear に出す。
    初めの期間の補い(60)では、分類しない法令にも、e-Gov が返した値だけを jpp:LawStatusUnclear として持たせる(閲覧ページで「確認できず」と出す)。
  - repeal_date が比べる期間(始め < 日付 ≤ 終わり)の中: 区分「根拠の法令が廃止・失効した」の記録(jpp:LawStatusChange)にし、
    その法令を根拠に挙げる(jpp:citedLaw)すべての手続に付ける。文言の比べ(jpp:ProvisionChange)とは別に数える。
  - 期間の始め以前: 変化に数えない。法令の状態(jpp:LawStatus)として持たせるだけにする。
  - 一覧に無い法令は、廃止・失効の記録が無い(e-Gov の一覧で状態が None)。"""
import urllib.parse
STATUSES = 'Repeal,Expire,Suspend,LossOfEffectiveness'
CODE = {'Repeal': 'repeal', 'Expire': 'expire', 'Suspend': 'suspend', 'LossOfEffectiveness': 'loss-of-effectiveness'}
API = 'https://laws.e-gov.go.jp/api/2'
def params(offset=0): return {'repeal_status': STATUSES, 'limit': '1000', 'offset': str(offset), 'response_format': 'json', 'omit_current_revision_info': 'true'}
def source_url(offset=0): return f'{API}/laws?' + urllib.parse.urlencode(sorted(params(offset).items()))
def fetch(egov, offline=False, refresh=True):
    """一覧を取る。戻り値: ({法令ID: revision_info}, 取った URL の一覧, 失敗の理由 or None)"""
    out, urls, off = {}, [], 0
    while True:
        b = egov.get('/laws', params(off), offline=offline, refresh=refresh and not offline)
        urls.append(source_url(off))
        if b.get('_status') != 200: return None, urls, f'法令一覧 {b.get("_status")}'
        for x in b.get('laws', []): out[x['law_info']['law_id']] = x['revision_info']
        nxt = b.get('next_offset')
        if not nxt or nxt >= (b.get('total_count') or 0): return out, urls, None
        off = nxt
def judge(info, start, end):
    """'in-period'(期間の中で廃止・失効)/ 'before'(期間の始め以前)/ 'after' / 'unclear'(分類しない)"""
    d = info.get('repeal_date') or ''
    if info.get('current_revision_status') != 'Repeal' or not d or info.get('repeal_status') not in CODE: return 'unclear'
    if d <= start: return 'before'
    if d <= end: return 'in-period'
    return 'after'
def status_node(s, iri, lit, lid, info, checked, src):
    """法令の状態(jpp:LawStatus)。法令ごとに 1 つ(公開しているデータに無いときだけ書く)"""
    s(iri(f'law/{lid}/status'), [('a', 'jpp:LawStatus'), ('jpp:statusOf', iri(f'law/{lid}')), ('jpp:repealStatus', iri(f'code/repeal-status/{CODE[info["repeal_status"]]}')),
                                 ('jpp:repealDate', lit(info['repeal_date'], dt='date')), ('dct:source', f'<{src}>'), ('jpp:checkedOn', lit(checked, dt='date'))])
def unclear_node(s, iri, lit, lid, info, checked, src):
    """分類しない法令(廃止・失効の記録はあるが、今の版の状態が Repeal でない、または日付が無い)。e-Gov が返した値をそのまま持たせる(jpp:LawStatusUnclear)"""
    s(iri(f'law/{lid}/status-unclear'), [('a', 'jpp:LawStatusUnclear'), ('jpp:statusOf', iri(f'law/{lid}')),
                                         ('jpp:repealStatus', iri(f'code/repeal-status/{CODE[info["repeal_status"]]}') if info.get('repeal_status') in CODE else None),
                                         ('jpp:repealDate', lit(info['repeal_date'], dt='date') if info.get('repeal_date') else None),
                                         ('jpp:currentRevisionStatus', lit(info.get('current_revision_status') or '')), ('dct:source', f'<{src}>'), ('jpp:checkedOn', lit(checked, dt='date'))])
def change_node(s, iri, lit, lid, info, per, found, src, act, procs, recheck=None):
    """区分「根拠の法令が廃止・失効した」の記録(jpp:LawStatusChange)。法令 × 期間ごとに 1 つ"""
    s(iri(f'law/{lid}/repeal/{per}'), [('a', 'jpp:LawStatusChange'), ('jpp:law', iri(f'law/{lid}')), ('jpp:changeKind', iri('code/change-kind/law-repealed')),
                                        ('dct:temporal', iri(f'period/{per}')), ('jpp:repealStatus', iri(f'code/repeal-status/{CODE[info["repeal_status"]]}')),
                                        ('jpp:repealDate', lit(info['repeal_date'], dt='date')), ('dct:source', f'<{src}>'), ('jpp:foundOn', lit(found, dt='date')),
                                        ('jpp:recheckReason', iri(f'code/recheck-reason/{recheck}') if recheck else None), ('prov:wasGeneratedBy', act)]
      + [('jpp:affects', iri(f'procedure/{p}')) for p in sorted(procs)])
