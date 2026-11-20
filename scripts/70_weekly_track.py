"""毎週の追跡。e-Gov 法令API v2 の一括ダウンロード(更新データ)で更新された法令と、施行日が来た改正のある法令のうち、
このデータが根拠に使う法令だけについて本文を取り直し、根拠の条・項・号を比べて、改正の記録(jpp:ProvisionChange)を足す。
判定の決まりは change_rules.py(第 5 版)。取得は 1 秒に 1 回まで(egov.py)。

使い方(公開用のリポジトリの一番上で):
  python3 scripts/70_weekly_track.py                       # 今日(日本時間)まで、過去 7 日の更新データ
  python3 scripts/70_weekly_track.py --today 2026-11-18 --days 1 --offline
  python3 scripts/70_weekly_track.py --since 2025-11-01 --only-bulk --offline --dry-run   # 作り直しの確かめ
比べ方:
  - 旧い側は、いつも「公開しているデータの文言」(data/rdf の本文の版と data/rdf/weekly/ の版。条・項・号ごとに jpp:asOf の最も新しいもの、
    無くなったと記録したものは「無い」)。e-Gov に前回の日付で取り直さない。手元の取得結果(data/api/cache)があっても無くても同じ結果になる。
  - 新しい側は、今日の日付で取った e-Gov の本文。文言が公開しているデータと違う条・項・号だけ、区分を決めるために、
    公開しているデータの版(law_revision_id)の本文を e-Gov から版の ID で取る(前回の日付では取らない)。
  - 版の ID が公開しているデータと同じで文言だけが違うもの(e-Gov が版を変えずに直したもの)は、改正の記録にせず、
    data/tracking/egov_corrections.csv に残す(公開しているデータの文言は直さない)。公開しているデータの版の本文を e-Gov が直していたときも同じ。
  - 改正の記録には、新しい文言の版の改正(jpp:foundRevision。法令番号・公布日・施行期日は e-Gov の値)と、見つけた日(jpp:foundOn)を書く。
    その改正の施行期日が比べた期間の始め以前(e-Gov が遅れて載せた改正)なら jpp:enforcedBeforePeriod true を付ける。記録は見つけた週の期間に置く。
取れなかったもの:
  - 更新データ(一括ダウンロード)が取れなかった日(状態が 200 でない・zip でない)は、法令API v1 の更新法令一覧(/api/1/updatelawlists/{日付})を引く。
    「取得結果が０件」なら「更新法令なし(v1 の一覧で 0 件)」として取り直しの対象から外す(e-Gov の説明に、更新の無い日の返し方の明記は無い。
    2026-11-20 に確かめた。土日・祝日などは更新データが HTTP 500、v1 の一覧が「取得結果が０件でした」だった)。
    v1 も取れないか、v1 に 1 件以上あるときは「確かめられなかった日」として state.json の pending_days に残し、次の実行でもう一度取る。
  - 更新データが取れた日も、v1 の一覧の件数と更新データの行数を比べて last_run.json の days に書く(合わなければ v1_mismatch に出す)。
  - 本文を取れなかった法令は failed_laws に残し、次の実行で、そのときの比べ始めからもう一度比べる。
  - 取れなかった日を後で取れたときは、その日の更新に出た法令を、取れなかった実行の比べ始めから比べる。
  - 取れなかったものがあっても、取れた分の記録は書き、確かめた日(checked_through)を進める。
  - 初めて取れなかった実行から 28 日以上続いているものは last_run.json の long_pending に出す(ワークフローが Issue にする)。
終わりの状態: 0(取れなかったものがあっても 0。数は last_run.json に書く)。"""
import sys, os, re, io, csv, gzip, json, time, glob, difflib, zipfile, argparse, datetime, collections, urllib.request, urllib.error
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import egov
from clause import article_index
import change_rules
from rdf_config import BASE, PREFIXES
ap = argparse.ArgumentParser()
ap.add_argument('--today'); ap.add_argument('--days', type=int, default=7); ap.add_argument('--since')
ap.add_argument('--only-bulk', action='store_true'); ap.add_argument('--offline', action='store_true'); ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--data', default='data/rdf'); ap.add_argument('--tracking', default='data/tracking'); ap.add_argument('--bulk-file', action='append', default=[], help='YYYYMMDD=保存済みの zip')
A = ap.parse_args()
JST = datetime.timezone(datetime.timedelta(hours=9))
today = datetime.date.fromisoformat(A.today) if A.today else datetime.datetime.now(JST).date()
os.makedirs(f'{A.tracking}/bulk', exist_ok=True)
state_fp = f'{A.tracking}/state.json'
state = json.load(open(state_fp)) if os.path.exists(state_fp) else {'checked_through': '2026-11-18', 'failed_laws': {}}
fail = []; log = []
def say(s): print(s, flush=True); log.append(s)
# ---- 1. 一括ダウンロードの更新データ(過去 N 日)と、法令API v1 の更新法令一覧
BULK = os.environ.get('EGOV_BULK_URL', 'https://laws.e-gov.go.jp/bulkdownload?file_section=3&update_date={d}&only_xml_flag=true')   # 試すときだけ変える
V1 = os.environ.get('EGOV_V1_URL', 'https://laws.e-gov.go.jp/api/1/updatelawlists/{d}')
given = dict(x.split('=', 1) for x in A.bulk_file)
upd = []   # (法令ID, law_revision_id, 施行日 YYYY-MM-DD, 未施行, 改正法令番号, 更新日)
_last = [0.0]
start_all = A.since or state['checked_through']; end = today.isoformat()
pending = state.setdefault('pending_days', {})     # 'YYYYMMDD': {'since': 初めて取れなかった実行の日, 'start': その実行の比べ始め, 'error': 最後の理由}
failed_since = state.setdefault('failed_since', {})   # 法令ID: 初めて取れなかった実行の日
day_start = {}   # 前に取れなかった日を今回取れたとき: その日 → 比べ始め
day_note = {}; v1_mismatch = []; no_update = []   # 日ごとの結果(last_run.json と status.json に書く)
NO_UPDATE = '更新法令なし(v1 の一覧で 0 件)'
def fetch(url):
    """1 秒に 1 回まで。戻り値: (状態, 中身)。通信エラーは (理由, None)"""
    wait = 1.05 - (time.time() - _last[0]); time.sleep(max(0, wait))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'jp-procedure-tracker'}), timeout=180) as r: return r.status, r.read()
    except urllib.error.HTTPError as e:
        try: body = e.read()
        except Exception: body = b''
        return e.code, body
    except (urllib.error.URLError, OSError) as e: return f'通信エラー {type(e).__name__}', None
    finally: _last[0] = time.time()
def v1_count(d):
    """法令API v1 の更新法令一覧の件数。0 件は「取得結果が０件」と返る(Code 1)。取れなければ (None, 理由)。取ったものは data/tracking/v1/ に残す"""
    fp = f'{A.tracking}/v1/{d}.xml'
    if os.path.exists(fp): raw = open(fp, 'rb').read(); st = '手元'
    elif A.offline: return None, '手元に無い(取らない)'
    else:
        st, raw = fetch(V1.format(d=d))
        if raw is None: return None, f'v1 {st}'
        if st not in (200, 404): return None, f'v1 HTTP {st}'   # 0 件は 404 と Code 1 で返る
    try: root = ET.fromstring(raw)
    except ET.ParseError: return None, f'v1 {st} XML でない({len(raw)} バイト)'
    code = (root.findtext('Result/Code') or '').strip(); msg = (root.findtext('Result/Message') or '').strip()
    if code == '0': n = len(root.findall('ApplData/LawNameListInfo'))
    elif code == '1' and '０件' in msg: n = 0
    else: return None, f'v1 {st} Code {code} {msg[:40]}'
    if st != '手元': os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'wb').write(raw)
    return n, ''
def unconfirmed(d, why):
    p = pending.setdefault(d, {'since': end, 'start': start_all}); p['error'] = why; fail.append(('bulk', d)); day_note[d] = f'確かめられなかった({why})'
    say(f'  更新データ {d}: 確かめられなかった({why})。次の実行でもう一度取る')
def bulk_failed(d, why):
    n, err = v1_count(d)
    if n == 0:
        if d in pending: pending.pop(d); say(f'  更新データ {d}: 前に確かめられなかった日。v1 の一覧で 0 件なので、取り直しの対象から外す')
        no_update.append(d); day_note[d] = f'{NO_UPDATE}。更新データは {why}'; say(f'  更新データ {d}: {why}。{NO_UPDATE}'); return
    unconfirmed(d, why + (f' / v1 の一覧 {n} 件' if n else f' / {err}'))
days = sorted({(today - datetime.timedelta(days=k)).strftime('%Y%m%d') for k in range(1, A.days + 1)} | set(pending), reverse=True)
for d in days:
    fp = given.get(d, f'{A.tracking}/bulk/{d}.zip')
    if not os.path.exists(fp):
        if A.offline: say(f'  更新データ {d}: 手元に無い(取らない)'); continue
        st, raw = fetch(BULK.format(d=d))
        if raw is None: bulk_failed(d, st); continue
        if st != 200: bulk_failed(d, f'HTTP {st}'); continue
        if not zipfile.is_zipfile(io.BytesIO(raw)): bulk_failed(d, f'zip でない({len(raw)} バイト)'); continue
        open(fp, 'wb').write(raw)
    raw = open(fp, 'rb').read()
    try: z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile: unconfirmed(d, f'手元のファイルが zip でない({len(raw)} バイト)'); continue
    if d in pending: day_start[d] = pending.pop(d)['start']; say(f'  更新データ {d}: 前に確かめられなかった日を、今回取れた(比べ始め {day_start[d]})')
    cn = [n for n in z.namelist() if n.lower().endswith('.csv')]
    rows = list(csv.DictReader(io.StringIO(z.read(cn[0]).decode('utf-8-sig')))) if cn else []
    for r in rows:
        tail = r['本文URL'].rstrip('/').rsplit('/', 1)[-1]; m = re.match(r'(\d{8})_', tail)
        ed = f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}' if m else ''
        upd.append((r['法令ID'], f'{r["法令ID"]}_{tail}', ed, r['未施行'].strip() != '', r['改正法令番号'], d))
    n1, err = v1_count(d)
    if n1 is None: day_note[d] = f'更新データ {len(rows)} 行(v1 の一覧と比べられなかった: {err})'
    elif n1 == len(rows): day_note[d] = f'更新データ {len(rows)} 行(v1 の一覧 {n1} 件。合う)'
    else: day_note[d] = f'更新データ {len(rows)} 行(v1 の一覧 {n1} 件。合わない)'; v1_mismatch.append({'day': d, 'bulk_rows': len(rows), 'v1': n1})
    say(f'  更新データ {d}: {day_note[d]}')
law_start = {}   # 前に取れなかった日に出た法令 → 比べ始め
for lid, rid, ed, un, num, d in upd:
    if d in day_start: law_start[lid] = min(law_start.get(lid, day_start[d]), day_start[d])
# ---- 2. 改正履歴(手元の分に、更新データの行を足す)
rv_fp = f'{A.tracking}/law_revisions.csv.gz'
REV = {}
if os.path.exists(rv_fp):
    for r in csv.DictReader(gzip.open(rv_fp, 'rt', encoding='utf-8')): REV[r['law_revision_id']] = r
for lid, rid, ed, un, num, d in upd:
    REV.setdefault(rid, {'law_id': lid, 'law_revision_id': rid, 'amendment_enforcement_date': ed, 'amendment_law_num': num, 'current_revision_status': 'UnEnforced' if un else '', 'source': f'bulk {d}'})
# ---- 3. このデータが根拠に使う条・項・号
cited = collections.defaultdict(set); cur = None
for line in gzip.open(f'{A.data}/procedures.ttl.gz', 'rt', encoding='utf-8'):
    m = re.match(r'^<' + re.escape(BASE) + r'record/r7/([^/>]+)/citation>', line)
    if m: cur = m.group(1); continue
    if line.startswith('<'): cur = None; continue
    m = re.match(r'\s+jpp:citedProvision <' + re.escape(BASE) + r'([^>]+)>', line)
    if m and cur: cited[m.group(1)].add(cur)
level = {}; plabel = {}
WEEKLY = sorted(glob.glob(f'{A.data}/weekly/*.ttl.gz'))
for fn in [f'{A.data}/provisions.ttl.gz', f'{A.data}/changes.ttl.gz'] + WEEKLY:
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        m = re.match(r'^<' + re.escape(BASE) + r'(provision/[^>]+)> a eli:LegalResourceSubdivision', line)
        if m: cur = m.group(1); continue
        if line.startswith('<'): cur = None; continue
        m = re.match(r'\s+jpp:level <[^>]+/level/(\w+)>', line)
        if m and cur: level[cur] = m.group(1)
        m = re.match(r'\s+rdfs:label "((?:[^"\\]|\\.)*)"@ja', line)
        if m and cur: plabel[cur] = m.group(1)
# 公開しているデータの文言(旧い側): 本文の版(expressions と weekly/ の版)のうち jpp:asOf の最も新しいもの。無くなったと記録した(新しい版の無い改正の記録)のがそれより後なら「無い」
UNESC = {'\\\\': '\\', '\\"': '"', '\\n': '\n', '\\r': '\r', '\\t': '\t'}
def unesc(s): return re.sub(r'\\[\\"nrt]', lambda m: UNESC[m.group(0)], s)
pub_ex = {}; pub_rm = {}   # 条・項・号 → (asOf, 版の path, law_revision_id, 文言) / 条・項・号 → 無くなったと記録した期間の終わり
def read_pub():
    for fn in [f'{A.data}/expressions.ttl.gz', f'{A.data}/changes.ttl.gz'] + WEEKLY:
        blk = None
        def flush(b):
            if not b: return
            if b['type'] == 'ex' and b.get('pv') in cited and b.get('asof'):
                k = (max(b['asof']), b['s'], b.get('rid', ''), b.get('text'))
                if b['pv'] not in pub_ex or k[0] > pub_ex[b['pv']][0]: pub_ex[b['pv']] = k
            if b['type'] == 'ch' and not b.get('new') and b.get('pv') in cited:
                pub_rm[b['pv']] = max(pub_rm.get(b['pv'], ''), b['end'])
        for line in gzip.open(fn, 'rt', encoding='utf-8'):
            if line.startswith('<'):
                flush(blk); blk = None
                m = re.match(r'^<' + re.escape(BASE) + r'([^>]+)> a (eli:LegalExpression|jpp:ProvisionChange) ', line)
                if m: blk = {'type': 'ex' if m.group(2) == 'eli:LegalExpression' else 'ch', 's': m.group(1), 'asof': []}
                continue
            if blk is None: continue
            m = re.match(r'\s+(eli:realizes|jpp:provision) <' + re.escape(BASE) + r'([^>]+)>', line)
            if m: blk['pv'] = m.group(2); continue
            m = re.match(r'\s+jpp:lawRevision "([^"]*)"', line)
            if m: blk['rid'] = m.group(1); continue
            m = re.match(r'\s+jpp:text "((?:[^"\\]|\\.)*)"@ja', line)
            if m: blk['text'] = unesc(m.group(1)); continue
            m = re.match(r'\s+jpp:asOf "([0-9-]+)"', line)
            if m: blk['asof'].append(m.group(1)); continue
            m = re.match(r'\s+dct:temporal <[^>]+/period/[0-9-]+_([0-9-]+)>', line)
            if m: blk['end'] = m.group(1); continue
            if re.match(r'\s+jpp:newVersion ', line): blk['new'] = True
        flush(blk)
read_pub()
BASE_END = '2026-11-18'   # 初めに比べた期間の終わり(この日の版が、公開しているデータの初めの「今の版」)
def pub_state(pv):
    """('ex', asOf, 版の path, law_revision_id, 文言) / ('absent', 無くなった日) / ('none', 理由)"""
    e = pub_ex.get(pv); r = pub_rm.get(pv)
    if r and (not e or r >= e[0]): return ('absent', r)
    if not e: return ('none', '公開しているデータに版が無い')
    if e[0] < BASE_END: return ('none', f'公開しているデータに {BASE_END} 以後の版が無い(初めの比べで本文が取れなかったか、取っていない)')
    return ('ex',) + e
by_law = collections.defaultdict(list)
for pv, procs in cited.items(): by_law[pv.split('/')[1]].append((pv, procs))
# ---- 4. 対象の法令
bulk_laws = {u[0] for u in upd}
due_laws = {r['law_id'] for r in REV.values() if start_all < (r['amendment_enforcement_date'] or '') <= end}
targets = (bulk_laws | (set() if A.only_bulk else due_laws) | set(state['failed_laws'])) & set(by_law)
say(f'# 期間 {start_all} 〜 {end}: 更新データの法令 {len(bulk_laws)}、施行日が来た改正のある法令 {len(due_laws)}、前回取れなかった法令 {len(state["failed_laws"])} → このデータが使う法令 {len(targets)}')
# ---- 5. 比べる
DEP = {'article': '条', 'paragraph': '項', 'item': '号'}
def pos_of(pv):
    s = pv.split('/')[2:]; sup = s[0].startswith('suppl-')
    return {'附則': sup, '条': s[0].replace('suppl-', ''), '項': s[1] if len(s) > 1 else None, '号': s[2] if len(s) > 2 else None}
def index_of(b):
    lb = [c for c in b['law_full_text']['children'] if isinstance(c, dict) and c['tag'] == 'LawBody'][0]
    return article_index(lb)
def load(lid, asof):
    b = egov.get(f'/law_data/{lid}', {'asof': asof, 'response_format': 'json', 'json_format': 'full'}, offline=A.offline, refresh_404=True)
    if b.get('_status') != 200: return None, None, b.get('_status')
    return index_of(b), b.get('revision_info', {}), 200
def load_rev(rid):   # 公開しているデータの版を、版の ID で取る(日付では取らない)
    b = egov.get(f'/law_data/{rid}', {'response_format': 'json', 'json_format': 'full'}, offline=A.offline, refresh_404=True)
    if b.get('_status') != 200: return None, b.get('_status')
    return index_of(b), 200
def norm(s): return change_rules.WS.sub('', s or '')
def elem_text(idx, p, dep): e, _ = change_rules.old_elem(idx, p, dep); return change_rules.text(e).strip() if e is not None else None
def diff_txt(a, b):
    if a is None or b is None: return f'「{(a or "(要素が無い)")[:40]}」→「{(b or "(要素が無い)")[:40]}」'
    ops = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if o[0] != 'equal']
    cut = lambda s: s if len(s) <= 40 else s[:40] + '…'
    return ' / '.join(f'「{cut(a[i1:i2])}」→「{cut(b[j1:j2])}」' for _, i1, i2, j1, j2 in ops)
corr_fp = f'{A.tracking}/egov_corrections.csv'; CORR_COLS = ['法令ID', '条・項・号', '版の ID', '見つけた日', '違う所']
corr = list(csv.DictReader(open(corr_fp, encoding='utf-8'))) if os.path.exists(corr_fp) else []
corr_new = []
def correction(lid, pv, rid, a, b):
    row = {'法令ID': lid, '条・項・号': plabel.get(pv, pv), '版の ID': rid, '見つけた日': end, '違う所': diff_txt(a, b)}
    key = lambda r: (r['法令ID'], r['条・項・号'], r['版の ID'], r['違う所'])
    if key(row) not in {key(r) for r in corr}: corr.append(row); corr_new.append(row)
recs = []; cnt = collections.Counter(); skipped = []   # skipped: 比べられなかった条・項・号と、本文が取れなかった法令(中身を last_run.json に書く)
for lid in sorted(targets):
    start = A.since or min(x for x in (state['failed_laws'].get(lid), law_start.get(lid), start_all) if x)
    if start >= end: cnt['期間が無い(すでに確かめた)'] += 1; continue
    ni, nrv, nst = load(lid, end)
    def law_fail(why, provs):
        cnt[why.split('(')[0]] += 1; skipped.append({'law': lid, 'provisions': provs, 'reason': why})
        if not (A.offline and '未取得' in why): fail.append(('law', lid)); failed_since.setdefault(lid, end)
        state['failed_laws'][lid] = start
    if ni is None: law_fail(f'本文が取れない(新 {end}: {nst})', sorted(pv for pv, _ in by_law[lid])); continue
    nrid = nrv.get('law_revision_id', ''); olds = {}; caches = collections.defaultdict(dict); bad = []
    for pv, procs in sorted(by_law[lid]):
        dep = DEP.get(level.get(pv)); p = pos_of(pv)
        if dep is None: cnt['深さが分からない'] += 1; continue
        ps = pub_state(pv); nt = elem_text(ni, p, dep)
        if ps[0] == 'none': cnt['比べられない'] += 1; skipped.append({'law': lid, 'provisions': [pv], 'reason': '比べられない: ' + ps[1]}); continue
        if ps[0] == 'absent':
            if nt is None: cnt['無いまま(公開しているデータで無くなったと記録した)'] += 1; continue
            cnt['比べられない'] += 1; skipped.append({'law': lid, 'provisions': [pv], 'reason': f'比べられない: 公開しているデータで無くなった({ps[1]})条・項・号が、新しい版にある'}); continue
        _, pasof, pex, prid, ptext = ps
        if nt is not None and norm(nt) == norm(ptext): cnt['文言が同じ'] += 1; continue
        if prid == nrid:   # 版の ID が同じで文言だけが違う: e-Gov が版を変えずに直した。改正の記録にしない
            correction(lid, pv, prid, ptext, nt); cnt['版を変えない直し(e-Gov)'] += 1; continue
        if prid not in olds: olds[prid] = load_rev(prid)
        oi, ost = olds[prid]
        if oi is None: bad.append(pv); continue
        ot = elem_text(oi, p, dep)
        if ot is None or norm(ot) != norm(ptext):   # 公開しているデータの版の本文を、e-Gov が版を変えずに直していた
            correction(lid, pv, prid, ptext, ot); cnt['版を変えない直し(e-Gov。公開しているデータの版)'] += 1
            if ot is None: cnt['比べられない'] += 1; skipped.append({'law': lid, 'provisions': [pv], 'reason': '比べられない: 公開しているデータの版の要素が、e-Gov の今の同じ版に無い'}); continue
        x = change_rules.classify(oi, ni, p, dep, caches[prid])   # 区分は、公開しているデータの版と新しい版の本文で決める(直しは改正に数えない)
        if x is None: cnt['文言が同じ(e-Gov の直しを除くと)'] += 1; continue
        if x['kind'] == '比べられない': cnt['比べられない'] += 1; skipped.append({'law': lid, 'provisions': [pv], 'reason': '比べられない: ' + x.get('rule', '')}); continue
        cnt[x['kind']] += 1
        recs.append(dict(lid=lid, pv=pv, procs=sorted(procs), start=start, end=end, old_ex=pex, nrv=nrv, ni=ni, p=p, dep=dep, **x))
    if bad: law_fail(f'本文が取れない(公開しているデータの版 {", ".join(sorted(k for k, v in olds.items() if v[0] is None))}: {", ".join(sorted({str(v[1]) for v in olds.values() if v[0] is None}))})', bad)
    else: state['failed_laws'].pop(lid, None); failed_since.pop(lid, None)
say(f'  比べた結果(条・項・号): {dict(cnt)}')
say(f'  足す改正の記録: {len(recs)}(手続の行 {sum(len(r["procs"]) for r in recs)})')
# 期間内に施行期日がある改正は、改正の記録に結ぶものだけでなく、このデータにある法令のものをすべて置く(61_build_changes.py と同じ形)。
# 根拠の法令に期間内の改正がある手続(法令の単位で知らせた場合の数)を、問いで数えられるようにするため。記録が 0 件の週でも置く。
LAWS = set(re.findall(r'^<' + re.escape(BASE) + r'law/([0-9A-Za-z]+)> a eli:LegalResource', gzip.open(f'{A.data}/laws.ttl.gz', 'rt', encoding='utf-8').read(), flags=re.M))
win_revs = sorted(x['law_revision_id'] for x in REV.values() if x['law_id'] in LAWS and start_all < (x['amendment_enforcement_date'] or '') <= end)
say(f'  期間内に施行期日がある改正(このデータの法令): {len(win_revs)}(法令 {len({REV[x]["law_id"] for x in win_revs})})')
# ---- 6. 書き出し
def lit(s, lang=None, dt=None):
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return f'"{s}"' + (f'@{lang}' if lang else f'^^xsd:{dt}' if dt else '')
def iri(path): return f'<{BASE}{path}>'
KIND = {'文言が変わった: 番号の参照だけ': 'wording-numref', '文言が変わった: それ以外': 'wording-other', '大きく書き換わった': 'rewritten',
        '入れ替わった→移った': 'swapped-moved', '入れ替わった→移った先が一つに決まらない': 'swapped-ambiguous', '入れ替わった→移った先なし': 'swapped-nodest',
        '無くなった→移った': 'removed-moved', '無くなった→移った先が一つに決まらない': 'removed-ambiguous', '無くなった→移った先なし': 'removed-nodest', '無くなった→判定できない': 'removed-undetermined'}
def seg_art(sup, num): return ('suppl-' if sup else '') + num
def lab_art(sup, num): s = num.split('_'); return ('附則' if sup else '') + f'第{s[0]}条' + ''.join(f'の{x}' for x in s[1:])
def lab_sub(num, kind): s = num.split('_'); return f'第{s[0]}{kind}' + ''.join(f'の{x}' for x in s[1:])
known = set(level)
def node_for(lid, pos, out):
    sup, art, pn, it = pos; a = f'provision/{lid}/{seg_art(sup, art)}'; cur = a; lab = lab_art(sup, art)
    chain = [(a, 'article', f'law/{lid}', lab, art)]
    if pn is not None: q = f'{a}/{pn}'; chain.append((q, 'paragraph', a, lab + lab_sub(pn, '項'), pn)); cur = q
    if pn is not None and it is not None: r = f'{cur}/{it}'; chain.append((r, 'item', cur, chain[-1][3] + lab_sub(it, '号'), it)); cur = r
    for path, lv, parent, l, num in chain:
        if path not in known: known.add(path); out.append((path, lv, parent, l, num))
    return cur
for r in recs:   # 新しい文言の版の改正(見つけた改正)。改正履歴に無ければ、本文の revision_info から足す
    rv = r['nrv']; rid = rv.get('law_revision_id', '')
    if rid and rid not in REV: REV[rid] = {'law_id': r['lid'], 'law_revision_id': rid, 'amendment_enforcement_date': rv.get('amendment_enforcement_date') or '', 'amendment_law_num': rv.get('amendment_law_num') or '',
                                           'current_revision_status': rv.get('current_revision_status') or '', 'source': f'law_data {end}'}
    if rid and rv.get('amendment_promulgate_date'): REV[rid]['amendment_promulgate_date'] = rv['amendment_promulgate_date']
if (recs or win_revs) and not A.dry_run:
    os.makedirs(f'{A.data}/weekly', exist_ok=True)
    PER = f'{start_all}_{end}'; fn = f'{A.data}/weekly/changes_{PER}.ttl.gz'
    f = gzip.open(fn, 'wt', encoding='utf-8')
    for k, v in PREFIXES.items(): f.write(f'@prefix {k}: <{v}> .\n')
    f.write('@prefix dcat: <http://www.w3.org/ns/dcat#> .\n\n')
    def s(subj, pos): pos = [(p, o) for p, o in pos if o is not None]; f.write(subj + ' ' + ' ;\n    '.join(f'{p} {o}' for p, o in pos) + ' .\n')
    ACT = iri(f'activity/weekly-track/{end}')
    s(ACT, [('a', 'prov:Activity'), ('rdfs:label', lit(f'毎週の追跡 {end}(scripts/70_weekly_track.py)', 'ja')), ('prov:used', iri('source/egov-law-api-v2')),
            ('prov:qualifiedAssociation', f'[ a prov:Association ; prov:agent {iri("agent/70_weekly_track")} ; prov:hadPlan {iri("plan/change-rules/" + change_rules.VERSION)} ]'),
            ('prov:endedAtTime', lit(datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), dt='dateTime'))])
    s(iri('agent/70_weekly_track'), [('a', 'prov:SoftwareAgent'), ('rdfs:label', lit('scripts/70_weekly_track.py'))])
    periods = {f'{start_all}_{end}'}; newnodes = []; revs_used = set(win_revs)
    s(iri(f'period/{start_all}_{end}'), [('a', 'dct:PeriodOfTime'), ('dcat:startDate', lit(start_all, dt='date')), ('dcat:endDate', lit(end, dt='date'))])
    for r in recs:
        per = f'{r["start"]}_{r["end"]}'
        if per not in periods:
            periods.add(per); s(iri(f'period/{per}'), [('a', 'dct:PeriodOfTime'), ('dcat:startDate', lit(r['start'], dt='date')), ('dcat:endDate', lit(r['end'], dt='date'))])
        vers = {'old': r['old_ex']}   # 旧い版は公開しているデータの版(書き直さない)
        rid = r['nrv'].get('law_revision_id', ''); t = elem_text(r['ni'], r['p'], r['dep'])
        if t is not None:
            ex = f'{r["pv"]}/version/{rid}'; vers['new'] = ex
            vd = (REV.get(rid) or {}).get('amendment_enforcement_date') or r['nrv'].get('amendment_enforcement_date')
            s(iri(ex), [('a', 'eli:LegalExpression'), ('eli:realizes', iri(r['pv'])), ('eli:version_date', lit(vd, dt='date') if vd else None), ('jpp:lawRevision', lit(rid)),
                        ('eli:language', '<http://publications.europa.eu/resource/authority/language/JPN>'), ('jpp:text', lit(t, 'ja')), ('jpp:asOf', lit(r['end'], dt='date'))])
            s(iri(r['pv']), [('eli:is_realized_by', iri(ex))])
        mv = node_for(r['lid'], r['moved'], newnodes) if r['moved'] else None
        cands = [node_for(r['lid'], pos, newnodes) for _, pos, _ in r['cands']]
        revs = [x['law_revision_id'] for x in REV.values() if x['law_id'] == r['lid'] and r['start'] < (x['amendment_enforcement_date'] or '') <= r['end']]
        revs_used.update(revs); found = rid if rid in REV else None
        if found: revs_used.add(found)
        fed = (REV.get(found) or {}).get('amendment_enforcement_date') or ''
        def dec(x): return lit(f'{float(x):.6f}', dt='decimal') if x is not None else None
        pos = [('a', 'jpp:ProvisionChange'), ('jpp:provision', iri(r['pv'])), ('dct:temporal', iri(f'period/{per}')), ('jpp:changeKind', iri(f'code/change-kind/{KIND[r["kind"]]}')),
               ('jpp:oldVersion', iri(vers['old'])), ('jpp:newVersion', iri(vers['new']) if 'new' in vers else None), ('jpp:movedTo', iri(mv) if mv else None)]
        pos += [('jpp:candidate', iri(x)) for x in dict.fromkeys(cands)] + [('jpp:r0', dec(r['r0'])), ('jpp:r1', dec(r['r1'])), ('prov:wasGeneratedBy', ACT)]
        pos += [('jpp:lawRevisionInPeriod', iri(f'law/{r["lid"]}/revision/{x}')) for x in revs]
        pos += [('jpp:foundRevision', iri(f'law/{r["lid"]}/revision/{found}') if found else None), ('jpp:foundOn', lit(end, dt='date')),
                ('jpp:enforcedBeforePeriod', 'true' if found and fed and fed <= r['start'] else None)]
        pos += [('jpp:affects', iri(f'procedure/{p}')) for p in r['procs']]
        s(iri(f'change/{r["pv"][len("provision/"):]}/{per}'), pos)
    for x in sorted(revs_used):
        rr = REV[x]
        s(iri(f'law/{rr["law_id"]}/revision/{x}'), [('a', 'jpp:LawRevision'), ('dct:identifier', lit(x)), ('jpp:revisionOf', iri(f'law/{rr["law_id"]}')),
                                                    ('jpp:enforcementDate', lit(rr['amendment_enforcement_date'], dt='date') if rr['amendment_enforcement_date'] else None), ('jpp:amendmentLawNum', lit(rr['amendment_law_num']) if rr.get('amendment_law_num') else None),
                                                    ('jpp:promulgationDate', lit(rr['amendment_promulgate_date'], dt='date') if re.fullmatch(r'\d{4}-\d{2}-\d{2}', rr.get('amendment_promulgate_date') or '') else None)])
    for path, lv, parent, l, num in newnodes:
        s(iri(path), [('a', 'eli:LegalResourceSubdivision'), ('eli:is_part_of', iri(parent)), ('eli:number', lit(num)), ('rdfs:label', lit(l, 'ja')), ('jpp:level', iri(f'code/level/{lv}')),
                      ('rdfs:comment', lit(f'改正の記録の移った先・候補として足した条・項・号({end} 版の番号)', 'ja'))])
    f.close(); say(f'  書いたファイル: {fn}')
if not A.dry_run:
    state['checked_through'] = end   # 取れなかった日・法令は pending_days・failed_laws に残してあり、次の実行で取り直す
    json.dump(state, open(state_fp, 'w'), ensure_ascii=False, indent=1)
    # 中身が同じなら同じバイトになるように、gzip の頭の日時を 0 にし、ファイル名を入れない
    with open(rv_fp, 'wb') as raw, io.TextIOWrapper(gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0), encoding='utf-8', newline='') as g:
        w = csv.DictWriter(g, fieldnames=['law_id', 'law_revision_id', 'amendment_enforcement_date', 'amendment_law_num', 'current_revision_status', 'source', 'amendment_promulgate_date'], extrasaction='ignore')
        w.writeheader(); [w.writerow(r) for r in REV.values()]
    # 版を変えない直し(e-Gov)の一覧。前の実行の分に、新しく見つけたものを足す
    if corr or os.path.exists(corr_fp):
        with open(corr_fp, 'w', encoding='utf-8', newline='') as f_:
            w = csv.DictWriter(f_, fieldnames=CORR_COLS); w.writeheader(); w.writerows(corr)
lim = (today - datetime.timedelta(days=28)).isoformat()
long_pending = [{'day': d, 'since': v['since'], 'error': v.get('error')} for d, v in sorted(pending.items()) if v['since'] <= lim] + \
               [{'law': l, 'since': s_} for l, s_ in sorted(failed_since.items()) if s_ <= lim and l in state['failed_laws']]
if fail: say(f'取れなかったもの(次の実行でもう一度取る): {fail}')
if corr_new: say(f'  版を変えない直し(e-Gov)を新しく見つけた: {len(corr_new)}(改正の記録にしない。{corr_fp} に書いた)')
if v1_mismatch: say(f'  v1 の一覧の件数と更新データの行数が合わない日: {v1_mismatch}')
json.dump({'period': [start_all, end], 'targets': len(targets), 'records': len(recs), 'rows': sum(len(r['procs']) for r in recs), 'revisions': len(win_revs), 'counts': dict(cnt), 'failures': fail,
           'unconfirmed_days': sorted(pending), 'unconfirmed_laws': sorted(state['failed_laws']), 'long_pending': long_pending, 'skipped': skipped,
           'days': {d: day_note[d] for d in sorted(day_note)}, 'no_update_days': sorted(no_update), 'v1_mismatch': v1_mismatch, 'corrections_new': corr_new, 'log': log},
          open(f'{A.tracking}/last_run.json', 'w'), ensure_ascii=False, indent=1)
