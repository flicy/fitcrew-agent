"""Local-only WXML/WXSS comparison harness. Not a mini-program runtime or backend."""
import html, json, re, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
ROOT=Path(__file__).resolve().parents[2]
MINI=ROOT/'apps/wechat-mini'
BASELINE='f8da3c2'
PAGES=['today','journey','experiments','log','profile']
def source(path, before=False):
    if before:
        result=subprocess.run(['git','show',f'{BASELINE}:apps/wechat-mini/{path}'],cwd=ROOT,capture_output=True,text=True)
        return result.stdout if result.returncode==0 else ''
    p=MINI/path
    return p.read_text() if p.exists() else ''
def ast(text):
    text=re.sub(r'\{\{.*?\}\}',lambda m:html.escape(html.unescape(m.group()),quote=True),text,flags=re.S)
    text=re.sub(r'\b(wx:else|scroll-x|scroll-y|enhanced)(?=\s|/?>)(?!\s*=)', r'\1=""', text)
    root=ET.fromstring('<root xmlns:wx="wx">'+text+'</root>')
    def node(el):
        out={'tag':el.tag,'attrs':{k.replace('{wx}','wx:'):v for k,v in el.attrib.items()},'children':[]}
        if el.text:out['children'].append(el.text)
        for child in el:
            out['children'].append(node(child))
            if child.tail:out['children'].append(child.tail)
        return out
    return node(root)
def bundle(before):
    modules={}
    for p in MINI.rglob('*.js'):
        rel=p.relative_to(MINI).as_posix()
        if rel.startswith(('pages/','lib/')) or rel=='config.js':modules[rel]=source(rel,before)
    return {'pages':{name:ast(source(f'pages/{name}/index.wxml',before)) for name in PAGES},
        'css':{name:source('app.wxss',before)+'\n'+source(f'pages/{name}/index.wxss',before) for name in PAGES},
        'status':ast(source('templates/status.wxml',before)), 'modules':modules,
        'config':json.loads(source('app.json',before))}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url=urlsplit(self.path)
        if url.path=='/bundle':
            body=json.dumps(bundle(parse_qs(url.query).get('version')==['before']),ensure_ascii=False).encode();mime='application/json'
        elif url.path.startswith('/assets/tabs/'):
            path=(MINI/url.path[1:]).resolve()
            if not path.is_relative_to(MINI/'assets/tabs') or not path.is_file():self.send_error(404);return
            body=path.read_bytes();mime='image/png'
        else:
            path=Path(__file__).parent/('index.html' if url.path=='/' else url.path.lstrip('/'))
            if path.parent!=Path(__file__).parent or not path.is_file():self.send_error(404);return
            body=path.read_bytes();mime='text/javascript' if path.suffix=='.js' else 'text/html; charset=utf-8'
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8768)
    port=parser.parse_args().port
    print(f'FitCrew source preview: http://127.0.0.1:{port} (synthetic fixtures only)',flush=True)
    HTTPServer(('127.0.0.1',port),Handler).serve_forever()
