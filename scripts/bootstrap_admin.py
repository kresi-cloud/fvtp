#!/usr/bin/env python3
"""Első admin meghívása (alapértelmezés: gergely.kresak@gmail.com, szerep: dekan, admin: true).
Használat: CLERK_SECRET_KEY=sk_... python3 scripts/bootstrap_admin.py [email] [https://fvtp.vercel.app]
Ha az e-mail már tag, csak az admin jelzőt állítja be a publicMetadata-ban."""
import json, os, sys, urllib.request, urllib.parse
KEY = os.environ.get('CLERK_SECRET_KEY') or sys.exit('CLERK_SECRET_KEY szükséges')
email = (sys.argv[1] if len(sys.argv) > 1 else 'gergely.kresak@gmail.com').lower()
site = sys.argv[2] if len(sys.argv) > 2 else 'https://fvtp.vercel.app'
H = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
def call(m, p, b=None):
    r = urllib.request.Request('https://api.clerk.com/v1' + p, method=m, headers=H, data=json.dumps(b).encode() if b else None)
    with urllib.request.urlopen(r) as x: return json.load(x)
users = call('GET', '/users?email_address=' + urllib.parse.quote(email))
if users:
    u = users[0]
    call('PATCH', f"/users/{u['id']}/metadata", {'public_metadata': {'admin': True, 'role': (u.get('public_metadata') or {}).get('role', 'dekan')}})
    print('már tag, admin jelző beállítva:', email)
else:
    r = call('POST', '/invitations', {'email_address': email, 'public_metadata': {'role': 'dekan', 'admin': True},
                                      'redirect_url': site + '/belepes.html', 'notify': True, 'ignore_existing': True})
    print('admin meghívó elküldve:', email, r['id'])
