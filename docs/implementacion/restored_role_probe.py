"""Actual HTTP sessions against owned local restored engines; synthetic accounts only."""
import json
import os
import uuid
import requests


def run():
    if os.getenv('OPERATIONS_REAL_TESTS')!='1' or not os.getenv('OPERATIONS_BROWSER_WORK'):
        raise RuntimeError('Requires owned disposable browser runner')
    root='http://127.0.0.1:18015/api/'
    rows=[]
    for institution in ['hospital','pediatrico','laboratorio','odontologica']:
        for role in ['admin','medico','secretaria','enfermero']+(['laboratorista'] if institution=='laboratorio' else []):
            client=requests.Session()
            try:
                def request(method,path,body=None,expected=200):
                    response=client.request(method,root+path,json=body,headers={'X-CSRFToken':client.cookies.get('csrftoken','')},timeout=15)
                    assert response.status_code==expected,(institution,role,path,response.status_code)
                    return response.json() if response.content else None
                request('GET','auth/csrf/')
                prefix='DEMO-OPS-' if role=='admin' else 'DEMO-A5-'
                request('POST','auth/login/',{'username':prefix+role+'-'+institution,'password':'DEMO-Operations-2026-Only!'})
                me=request('GET','auth/me/');assert me['usuario']['institucion']==institution and me['usuario']['rol']==role
                request('GET','operaciones/')
                payload={'identificacion':'RESTORE-'+uuid.uuid4().hex[:10],'nombres':'DEMO','apellidos':'Roles restaurados','fecha_nacimiento':'2000-01-01'}
                if role=='enfermero':
                    request('POST','pacientes/',payload,expected=403)
                    patient=request('GET','pacientes/?limit=20&offset=0')['results'][0]['id']
                else:patient=request('POST','pacientes/',payload,expected=201)['id']
                request('GET',f'pacientes/{patient}/historial/',expected=403 if role=='secretaria' else 200)
                request('POST',f'pacientes/{patient}/consultas/',{'fecha':'2020-01-01','notas_evolucion':'DEMO roles restaurados'},expected=403 if role in {'secretaria','enfermero'} else 201)
                request('POST','auth/logout/',{},expected=204)
                request('GET','auth/me/',expected=401)
                rows.append({'institution':institution,'role':role,'session_permissions_logout':'passed'})
            finally:client.close()
    return {'scope':'HTTP on restored local copies; synthetic identity in SQLite','passed':len(rows),'cases':rows}
