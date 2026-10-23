"""Stop only labeled A5 containers and A5-specific local server processes (Linux)."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime',type=Path,required=True)
a=p.parse_args();root=a.runtime.resolve()
if root.name!='a5-runtime' or root.parent.name!='work':
    raise SystemExit('Solo work/a5-runtime dedicado')
names=[]
# Validate every container before mutating any of them.
for engine in ('postgres','mysql','mongo'):
    name='jennifer-a5-'+engine
    result=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
    if result.returncode:
        if 'No such object' in result.stderr or 'No such container' in result.stderr:
            continue
        raise SystemExit('Docker no disponible; no se ejecuta limpieza')
    data=json.loads(result.stdout)[0]
    if data['Config']['Labels'].get('codex.task')!='jennifer-a5':
        raise SystemExit('Se rechaza retirar un contenedor ajeno')
    if any(m['Type']!='volume' or not re.fullmatch('[a-f0-9]{64}',m.get('Name','')) for m in data['Mounts']):
        raise SystemExit('Montaje no desechable: requiere inspección del responsable')
    names.append(name)
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        argv=[x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
        if not argv:continue
        java=Path(argv[0]).name=='java' and '--project_id=demo-jennifer-a5' in argv
        frontend=Path(argv[0]).name=='node' and any(str(root/'frontend')+'/' in x and 'vite' in x for x in argv[1:])
        backend=(any(x.endswith('/docs/jennifer/a5/serve.py') or x=='docs/jennifer/a5/serve.py' for x in argv[1:])
                 and '--runtime' in argv and Path(argv[argv.index('--runtime')+1]).resolve()==root)
        if java or frontend or backend:
            os.kill(int(proc.name),signal.SIGTERM)
    except (FileNotFoundError,PermissionError,ProcessLookupError):pass
if names:
    subprocess.run(['docker','rm','--force','--volumes',*names],check=True,stdout=subprocess.DEVNULL)
print('Servicios A5 dedicados retirados; fuentes, logs y archivos locales conservados')
