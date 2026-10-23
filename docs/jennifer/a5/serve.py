"""Run only the prepared disposable A5 backend; no change to project settings."""
import argparse
import json
import os
from pathlib import Path
import sys

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--runtime',type=Path,required=True)
p.add_argument('--audit',action='store_true')
a=p.parse_args()
root=a.runtime.resolve()
if root.parent.name!='work' or root.name!='a5-runtime':
    raise SystemExit('Solo work/a5-runtime dedicado')
sys.path[:0]=[str(root),str(root/'backend')]
os.environ.update(json.loads((root/'server.json').read_text()))
import django
django.setup()
from django.core.management import call_command
if a.audit:
    call_command('audit_clinical_providers',require_all=True)
else:
    call_command('runserver','127.0.0.1:18005',use_reloader=False)
