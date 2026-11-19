"""RDF(*.ttl.gz と weekly/*.ttl.gz)の全部を、pyoxigraph のディスクの店に読み込む。.venv の python。
使い方: python3 scripts/62_oxigraph_load.py [RDF の場所] [店の場所]
  既定は、RDF の場所 = 環境変数 RDF_DIR か rdf、店の場所 = 環境変数 STORE か store/oxigraph。
  公開用のリポジトリでは: python3 scripts/62_oxigraph_load.py data/rdf store/oxigraph"""
import os, sys, gzip, time, glob, shutil, resource, subprocess, pyoxigraph as ox
D = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('STORE', 'store/oxigraph')   # 店の場所
if os.path.exists(D): shutil.rmtree(D)
os.makedirs(D)
st = ox.Store(D); T0 = time.time(); tot = 0
print(f'# pyoxigraph {ox.__version__} に読み込み(Store.bulk_load、ディスクの店 {D})')
RDF = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('RDF_DIR', 'rdf')
for f in sorted(glob.glob(f'{RDF}/*.ttl.gz') + glob.glob(f'{RDF}/weekly/*.ttl.gz')):
    t0 = time.time(); st.bulk_load(gzip.open(f), ox.RdfFormat.TURTLE); n = len(st) - tot; tot += n
    print(f'  {f}: {n:,} 個 / {time.time()-t0:.1f} 秒', flush=True)
st.optimize(); st.flush()
t = time.time() - T0
print(f'  計: {len(st):,} 個(重なりを除いた quad の数)/ 読み込み {t:.1f} 秒(optimize を含む)')
del st
du = subprocess.run(['du', '-sk', D], capture_output=True, text=True).stdout.split()[0]
print(f'  ディスクの大きさ: {int(du)*1024:,} バイト(du -sk)/ メモリ最大 {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:,.0f} MB')
