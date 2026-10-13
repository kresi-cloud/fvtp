#!/usr/bin/env python3
"""Meghívó küldése a Clerk Backend API-n át (csak meghívott e-mail tud regisztrálni/belépni).

Használat:  CLERK_SECRET_KEY=sk_... python3 scripts/invite.py nev@pte.hu dekan [https://fvtp.vercel.app]
Szerepek:   dekan | dh_tud | dh_okt | intezet | hivatal   (a portál nézete; a meghívó publicMetadata.role mezőjébe kerül)
Lista:      CLERK_SECRET_KEY=sk_... python3 scripts/invite.py --list
"""
import json, os, sys, urllib.request

KEY = os.environ.get('CLERK_SECRET_KEY')
if not KEY:
    sys.exit('CLERK_SECRET_KEY környezeti változó szükséges (Clerk Dashboard → API keys → Secret key).')
H = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}

def call(method, path, body=None):
    req = urllib.request.Request('https://api.clerk.com/v1' + path, method=method, headers=H,
                                 data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req) as r:
        return json.load(r)

if '--list' in sys.argv:
    for inv in call('GET', '/invitations?status=pending&limit=100'):
        print(inv['email_address'], (inv.get('public_metadata') or {}).get('role', ''), inv['status'])
    sys.exit()
if len(sys.argv) < 3:
    sys.exit(__doc__)
email, role = sys.argv[1], sys.argv[2]
site = sys.argv[3] if len(sys.argv) > 3 else 'https://fvtp.vercel.app'
assert role in ('dekan', 'dh_tud', 'dh_okt', 'intezet', 'hivatal'), 'ismeretlen szerep'
r = call('POST', '/invitations', {'email_address': email, 'public_metadata': {'role': role},
                                  'redirect_url': site + '/belepes.html', 'notify': True, 'ignore_existing': True})
print('meghívó elküldve:', r['email_address'], '→', role, '| id:', r['id'])
