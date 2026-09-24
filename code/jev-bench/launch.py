import pathlib,urllib.request,json,subprocess,sys,time,webbrowser
p=pathlib.Path(__file__).resolve().parent
url='http://127.0.0.1:8766'
def available():
 try:return json.load(urllib.request.urlopen(url+'/api/config',timeout=1)).get('service')=='jev-bench'
 except Exception:return False
if not available():
 (p/'data').mkdir(exist_ok=True)
 with (p/'data/server.log').open('ab') as log:subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8766','--no-access-log'],cwd=p,stdout=log,stderr=log,start_new_session=True)
 for _ in range(30):
  if available():break
  time.sleep(.2)
if not available():raise SystemExit('启动失败，请检查 data/server.log')
if '--no-open' not in sys.argv:webbrowser.open(url)
print(url)
