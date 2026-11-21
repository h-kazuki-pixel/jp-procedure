"""e-Gov 法令API v2 の取得。1秒に1回まで。取得結果は data/api/cache に保存し、あれば取り直さない。"""
import gzip, hashlib, json, os, time, urllib.parse, urllib.request
BASE = os.environ.get('EGOV_API_BASE', 'https://laws.e-gov.go.jp/api/2')   # 試すときだけ変える
CACHE = os.environ.get('EGOV_CACHE', 'data/api/cache'); os.makedirs(CACHE, exist_ok=True)   # 置き場所は環境変数でも変えられる
LOG = os.environ.get('EGOV_LOG', 'data/api/requests.log')
_last = [0.0]
def get(path, params=None, offline=False, refresh_404=False, refresh=False):
    """refresh_404: 手元に残した答えが 404 なら、残したものを使わずに取り直す(毎週の追跡で、前に取れなかった本文を取り直すとき)
    refresh: 手元に残した答えがあっても取り直し、残したものを新しい答えで置き換える(毎週の追跡で、廃止・失効の一覧を毎回取るとき)"""
    q = urllib.parse.urlencode(sorted((params or {}).items()))
    url = f'{BASE}{urllib.parse.quote(path)}' + (f'?{q}' if q else '')
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    fp = os.path.join(CACHE, key + '.json')
    for f_, op in ((fp, open), (fp + '.gz', lambda p, **k: gzip.open(p, 'rt', **k))):
        if os.path.exists(f_):
            with op(f_, encoding='utf-8') as f: body = json.load(f)['body']
            if not ((refresh_404 and body.get('_status') == 404) or refresh) or offline: return body
    if offline: return {'_status': '未取得'}
    wait = 1.05 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    req = urllib.request.Request(url, headers={'User-Agent': os.environ.get('EGOV_UA', 'jp-procedure-script'), 'Accept': 'application/json'})
    status, body = None, None
    for attempt, backoff in enumerate([10, 30, 60, None]):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                status = r.status; body = json.loads(r.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as e:
            status = e.code
            try: body = json.loads(e.read().decode('utf-8'))
            except Exception: body = None
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:  # 通信エラー: 待って取り直す
            status = f'通信エラー:{type(e).__name__}'
            with open(LOG, 'a') as f: f.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}\t{status}\t{url}\n')
            if backoff is None: break
            time.sleep(backoff)
        finally:
            _last[0] = time.time()
    with open(LOG, 'a') as f: f.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}\t{status}\t{url}\n')
    body = {'_status': status, **(body if isinstance(body, dict) else {'_raw': body})}
    if status in (200, 404):  # 一時的エラーはキャッシュしない
        with gzip.open(fp + '.gz', 'wt', encoding='utf-8') as f: json.dump({'url': url, 'body': body}, f, ensure_ascii=False)
        if os.path.exists(fp): os.remove(fp)   # 古い形(gzip でない)の答えが残っていると、取り直した答えより先に読まれるため
    return body
