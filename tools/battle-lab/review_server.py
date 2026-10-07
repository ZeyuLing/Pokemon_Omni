"""Loopback-only review workbench and explicitly human-gated pilot launcher."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from review_data import ReviewStore, ROOT, WORK, write_json

STATIC=ROOT/'adapters/battle-review'


class App:
    def __init__(self,store):
        self.store=store;self.token=secrets.token_urlsafe(32);self.lock=threading.RLock()
        self.process=None;self.job=None
        store.invalidate_runs()
        snapshots=sorted((store.work/'runs').glob('*/snapshot.json'))
        if snapshots:
            path=snapshots[-1]
            self.job={'id':path.parent.name,'out':str(path.parent),'cases':{c['id'] for c in json.loads(path.read_text('utf-8'))['cases']}}

    def job_status(self):
        if not self.job:return {'status':'not_started','message':'尚未使用任何未审批数据训练'}
        progress=Path(self.job['out'])/'progress.json'
        result=json.loads(progress.read_text('utf-8')) if progress.exists() else {'status':'starting'}
        if self.job.get('invalidated') or (progress.parent/'INVALIDATED.json').exists():
            result={'status':'invalidated','error':'审批已撤回或修改，本次权重禁止使用'}
        elif self.process and self.process.poll() is not None and self.process.returncode:
            result={'status':'failed','error':result.get('error','训练进程失败，请查看本地日志')}
        return {**result,'run_id':self.job['id']}

    def start(self):
        with self.lock:
            if self.process and self.process.poll() is None:raise ValueError('已有训练任务正在运行')
            snapshot=self.store.training_snapshot()
            run_id=time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(3)
            folder=self.store.work/'runs'/run_id;request=self.store.work/'requests'/(run_id+'.json')
            write_json(request,snapshot)
            logs=self.store.work/'logs';logs.mkdir(exist_ok=True)
            with (logs/(run_id+'.log')).open('wb') as output:
                self.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('review_train.py')),
                    '--snapshot',str(request),'--out',str(folder)],stdout=output,stderr=subprocess.STDOUT,
                    cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.job={'id':run_id,'out':str(folder),'cases':{x['id'] for x in snapshot['cases']}}
            return self.job_status()

    def review(self,body):
        with self.lock:
            result=self.store.review(body['id'],body['status'],body['sha256'],body.get('note',''),body.get('acknowledged') is True)
            self.store.invalidate_runs()
            if self.job and body['id'] in self.job['cases']:
                self.job['invalidated']=True
                if self.process and self.process.poll() is None:self.process.terminate()
                write_json(Path(self.job['out'])/'INVALIDATED.json',{'reason':'human review changed'})
            return result


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,code,value,content_type='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(code);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.valid_host():return self.respond(403,{'error':'Loopback host required'})
            parsed=urlparse(self.path);q={k:v[0] for k,v in parse_qs(parsed.query).items()}
            try:
                if parsed.path=='/api/info':return self.respond(200,{'summary':app.store.summary(),'token':app.token,'training':app.job_status()})
                if parsed.path=='/api/cases':return self.respond(200,app.store.list_rows(q.get('q',''),q.get('source',''),q.get('status',''),q.get('missing',''),max(0,int(q.get('offset',0))),30))
                if parsed.path.startswith('/api/case/'):
                    return self.respond(200,app.store.detail(parsed.path.rsplit('/',1)[-1]))
                if parsed.path=='/api/sample':
                    rows=app.store.list_rows(q.get('q',''),q.get('source',''),q.get('status',''),q.get('missing',''),0,len(app.store.rows))['rows']
                    return self.respond(200,{'id':secrets.choice(rows)['id'] if rows else None})
                if parsed.path=='/api/training':return self.respond(200,app.job_status())
                name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(parsed.path)
                if not name:return self.respond(404,{'error':'Not found'})
                kind={'html':'text/html','js':'text/javascript','css':'text/css'}[name.rsplit('.',1)[-1]]
                return self.respond(200,(STATIC/name).read_bytes(),kind+'; charset=utf-8')
            except KeyError:return self.respond(404,{'error':'未找到数据记录'})
            except Exception as exc:return self.respond(400,{'error':str(exc)})

        def do_POST(self):
            origins=(f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}')
            if not self.valid_host() or self.headers.get('Origin') not in origins or self.headers.get('X-Review-Token')!=app.token:
                return self.respond(403,{'error':'Local review session required'})
            try:
                size=int(self.headers.get('Content-Length',0))
                if size<1 or size>8192:raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(size))
                if self.path=='/api/review':return self.respond(200,app.review(body))
                if self.path=='/api/train':return self.respond(200,app.start())
                return self.respond(404,{'error':'Not found'})
            except (ValueError,KeyError) as exc:return self.respond(400,{'error':str(exc)})
    return Handler


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8792);args=p.parse_args()
    store=ReviewStore();server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(App(store)))
    print(f'Review workbench: http://127.0.0.1:{args.port}/ ({len(store.rows)} trajectories)',flush=True)
    server.serve_forever()
