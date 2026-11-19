"""Cloud Monitoring から Cloud Run の指標を読む(読むだけ)。標準ライブラリだけ。
引数: プロジェクト ID、サービス名、さかのぼる分。環境変数 ACCESS_TOKEN に `gcloud auth print-access-token` の値。
- container/memory/utilizations: メモリの使用率(上限 1 GiB に対する割合。分布の平均と、分布から読める最大の区間)
- container/startup_latencies: 立ち上がりの時間(ミリ秒の分布)
- container/instance_count: 動いていた台数
"""
import datetime as dt, json, os, sys, urllib.parse, urllib.request

PROJ, SVC, MIN = sys.argv[1], sys.argv[2], int(sys.argv[3])
TOK = os.environ['ACCESS_TOKEN']
end = dt.datetime.now(dt.timezone.utc); start = end - dt.timedelta(minutes=MIN)


def ts(metric, aligner=None):
    p = {'filter': f'metric.type="run.googleapis.com/{metric}" AND resource.labels.service_name="{SVC}"',
         'interval.startTime': start.isoformat(), 'interval.endTime': end.isoformat()}
    url = f'https://monitoring.googleapis.com/v3/projects/{PROJ}/timeSeries?' + urllib.parse.urlencode(p)
    r = urllib.request.urlopen(urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOK}))
    return json.load(r).get('timeSeries', [])


def bounds(d):
    o = d.get('bucketOptions', {})
    if 'exponentialBuckets' in o:
        e = o['exponentialBuckets']; n, g, s = e['numFiniteBuckets'], e['growthFactor'], e.get('scale', 1)
        return [s * g ** i for i in range(n + 1)]
    if 'explicitBuckets' in o: return o['explicitBuckets']['bounds']
    if 'linearBuckets' in o:
        l = o['linearBuckets']; return [l.get('offset', 0) + l['width'] * i for i in range(l['numFiniteBuckets'] + 1)]
    return []


def top_bucket(d):
    c = [int(x) for x in d.get('bucketCounts', [])]; b = bounds(d)
    k = max((i for i, x in enumerate(c) if x), default=None)
    if k is None: return None
    lo = b[k - 1] if k >= 1 and k - 1 < len(b) else 0; hi = b[k] if k < len(b) else float('inf')
    return lo, hi


for m in ['container/memory/utilizations', 'container/startup_latencies', 'container/instance_count']:
    print(f'# {m}')
    for s in ts(m):
        lab = s['metric'].get('labels', {})
        for pt in sorted(s['points'], key=lambda p: p['interval']['endTime']):
            v = pt['value']; t = pt['interval']['endTime']
            if 'distributionValue' in v:
                d = v['distributionValue']; tb = top_bucket(d)
                print(f'  {t} {lab} 数 {d.get("count")} 平均 {d.get("mean", 0):.4f} 最大の区間 {tb[0]:.4f}〜{tb[1]:.4f}' if tb else f'  {t} {lab} 数 0')
            else:
                print(f'  {t} {lab} {v}')
