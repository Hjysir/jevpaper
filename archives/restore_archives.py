"""Verify and restore evidence archives. Does not execute their contents."""
from pathlib import Path
import argparse, hashlib, json, tarfile

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--archive');p.add_argument('--extract',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    records=json.loads((root/'archives/index.json').read_text())
    if args.archive:
        records=[r for r in records if r['archive']==args.archive]
        if not records:raise SystemExit('Unknown archive')
    for r in records:
        dest=out/r['archive']
        if dest.exists():raise SystemExit('Refusing to overwrite '+str(dest))
        total=hashlib.sha256();size=0
        with dest.open('xb') as f:
            for part in r['parts']:
                data=(root/part['path']).read_bytes()
                if len(data)!=part['bytes'] or hashlib.sha256(data).hexdigest()!=part['sha256']:raise ValueError('Part checksum mismatch: '+part['path'])
                total.update(data);size+=len(data);f.write(data)
        if size!=r['bytes'] or total.hexdigest()!=r['sha256']:raise ValueError('Archive checksum mismatch')
        if args.extract:
            target=out/'extracted';target.mkdir(exist_ok=True)
            with tarfile.open(dest,'r:xz') as t:
                for member in t:
                    path=Path(member.name)
                    if not member.isfile() or path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive member')
                    output=target/path
                    if output.exists():raise ValueError('Refusing to overwrite '+str(output))
                    output.parent.mkdir(parents=True,exist_ok=True)
                    with t.extractfile(member) as src,output.open('xb') as dst:
                        while block:=src.read(1024*1024):dst.write(block)
        print('Verified',r['archive'],size)
if __name__=='__main__':main()
