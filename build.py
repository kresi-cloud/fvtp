#!/usr/bin/env python3
"""fvtp – statikus Vercel-oldal építése a portál-artifact HTML-jéből.

Használat:  python3 build.py [--src <artifact.html>] [--data <portal-data mappa>]
Kimenet:    public/index.html + public/data/*.json

A forrás-HTML-t NEM szerkesztjük kézzel: minden eltérés (téma, belépés, csengő, db-fallback)
itt, szöveges cserékkel kerül rá, így az artifact UX-változásai minden buildnél átjönnek.
Ha egy csere nem talál (mert az artifact kódja változott), a szkript figyelmeztet, de nem áll le.
"""
import argparse, json, os, re, shutil, sys, glob, datetime
CLAUDE_RE = re.compile(r'''https?://(?:www\.)?claude\.ai/[^\s)\]"'<>]*''')
MDLINK_RE = re.compile(r'\[([^\]]+)\]\((https?://(?:www\.)?claude\.ai/[^)]*)\)')

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.join(HERE, '..', 'aok-vezetoi-brief-portal.html'))
ap.add_argument('--data', default=os.path.join(HERE, '..', 'portal-data'))
a = ap.parse_args()

# beállítások: fvtp.config.json (publishable key, kapcsolat e-mail) – a secret key SOHA nem kerül ide
cfg = {}
cfg_path = os.path.join(HERE, 'fvtp.config.json')
if os.path.exists(cfg_path):
    cfg = json.load(open(cfg_path, encoding='utf-8'))
PK = os.environ.get('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY') or cfg.get('clerkPublishableKey', '')
CONTACT = cfg.get('contactEmail', '')
ADMINS = cfg.get('adminEmails', ['gergely.kresak@gmail.com'])
def frontend_api(pk):
    # pk_test_<base64(frontendapi$)> → frontend API host
    import base64
    try:
        return base64.b64decode(pk.split('_', 2)[2] + '==').decode().rstrip('$')
    except Exception:
        return ''
FA = frontend_api(PK) if PK else ''

html = open(a.src, encoding='utf-8').read()
# az Artifact „read” által mentett példány egy burkoló első és utolsó sorral érkezik – ezeket levágjuk
if not html.lstrip().startswith('<title>') and '\n<title>' in html:
    lines = html.split('\n')
    first = next(i for i, l in enumerate(lines) if l.startswith('<title>'))
    last = max(i for i, l in enumerate(lines) if '</script>' in l)
    html = '\n'.join(lines[first:last + 1]) + '\n'
warn = []

def rep(old, new, what, count=1):
    global html
    if old not in html:
        warn.append(what); return
    html = html.replace(old, new, count)

# 1) betűtípus: a honlapon Satoshi (Fontshare); az artifact Figtree-t tölt (Google Fonts)
rep('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;700&display=swap">',
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
    '<link rel="preconnect" href="https://api.fontshare.com"><link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap">\n'
    '<link rel="icon" href="/favicon.svg" type="image/svg+xml">', 'font-link')

# 3) kilépés gomb (Clerk signOut) – a téma-kapcsoló és a rejtett szerep-legördülő már az artifactban van
rep('<select class="role" id="roleSel" hidden aria-label="Szerepkör">',
    '<button class="tb-btn hv-logout" type="button" id="hvLogout" title="Kilépés">Kilépés</button>\n        <select class="role" id="roleSel" hidden aria-label="Szerepkör">', 'logout')

# 4b) Meghívások menü + nézet (csak adminnak jelenik meg; a tartalmat a /api/invitations adja)
rep('<button role="tab" data-view="feliratkozas" aria-selected="false">Feliratkozás</button>',
    '<button role="tab" data-view="feliratkozas" aria-selected="false">Feliratkozás</button>\n      <button role="tab" data-view="meghivas" aria-selected="false" id="hvAdminTab" hidden>Meghívások</button>', 'admin-tab')
rep('<section class="view" id="v-feliratkozas" hidden>', '''<section class="view" id="v-meghivas" hidden>
  <div class="page-head"><div><div class="eyebrow">Adminisztráció</div><h1>Meghívások</h1></div></div>
  <div class="cols"><div class="col-main">
    <div class="card"><h3>Új meghívó</h3>
      <form id="hvInvForm" class="form" style="display:grid;grid-template-columns:minmax(0,1fr) 180px auto auto;gap:10px;align-items:end;margin-top:12px">
        <label>E-mail<input type="email" id="hvInvEmail" required placeholder="nev@pte.hu"></label>
        <label>Nézet<select id="hvInvRole"><option value="dekan">Vezető</option><option value="dh_tud">Tudományos helyettes</option><option value="dh_okt">Oktatási helyettes</option><option value="intezet">Egységvezető</option><option value="hivatal">Hivatalvezető</option></select></label>
        <label style="display:flex;gap:6px;align-items:center;padding-bottom:10px"><input type="checkbox" id="hvInvAdmin" style="width:auto"> admin</label>
        <button class="btn primary" type="submit">Meghívó küldése</button>
      </form><p class="hv-msg" id="hvInvMsg" style="margin-top:10px;color:var(--muted-fg)"></p></div>
    <div class="sec"><div class="sec-head"><h2>Függő meghívók</h2><span id="hvInvN"></span></div><div class="rows" id="hvInvList"></div></div>
    <div class="sec"><div class="sec-head"><h2>Tagok</h2><span id="hvUsrN"></span></div><div class="rows" id="hvUsrList"></div></div>
  </div><aside class="rail"><div class="card"><h3>Hogyan működik</h3><p style="color:var(--muted-fg);margin-top:8px">Csak meghívott e-mail-cím tud belépni (Google-fiókkal vagy e-mail kóddal). A meghívó 30 napig érvényes; visszavonás után a cím nem léphet be. Tag eltávolítása azonnali.</p></div></aside></div>
</section>
<section class="view" id="v-feliratkozas" hidden>''', 'admin-view')

# 4c) Dosszié-kérés → /api/dosszie (GitHub issue), helyi „készül” sor marad
rep('''$("#dosszieForm").addEventListener("submit",e=>{e.preventDefault();const t=$("#dTema").value.trim();if(!t)return;''',
    '''$("#dosszieForm").addEventListener("submit",e=>{e.preventDefault();const t=$("#dTema").value.trim();if(!t)return;
  fetch("/api/dosszie",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({t,dontes:$("#dDontes").value,kor:$("#dKor").value,hatar:$("#dHatar").value,storyline:openSl||""})}).then(r=>r.json()).then(j=>{if(j.ok)toast("Dosszié-kérés továbbítva (#"+j.issue+"), a következő frissítéskor készül.");else toast("A kérés helyben rögzítve, továbbítás nem sikerült: "+(j.error||""));}).catch(()=>toast("A kérés helyben rögzítve, továbbítás nem sikerült."));''', 'dosszie-post')

# 5) adatbázis helyett statikus fájlok (hírfigyelő hírek + digestek)
rep('if(!db){st.textContent="adatbázis nem elérhető ebben a nézetben";return;}',
    '''if(!db){try{const [h,d]=await Promise.all([fetch("data/hirek.json",{cache:"no-store"}).then(r=>r.json()),fetch("data/digest.json",{cache:"no-store"}).then(r=>r.json())]);
      hirek=h;hirek.sort((a,b)=>a.date<b.date?1:a.date>b.date?-1:0);digests=d;st.textContent=hirek.length+" hír";renderHirek();renderDigest();syncBriefIssues();}catch(e){st.textContent="hírek nem tölthetők";}return;}''', 'db-fallback')

# 6) Clerk: szerep a felhasználó publicMetadata.role mezőjéből (a meghívón állítható), kilépés gomb
rep('<script>', '''<script>window.HV_ADMIN_EMAILS=''' + json.dumps(ADMINS) + ''';
</script>\n<script async crossorigin="anonymous" data-clerk-publishable-key="''' + PK + '''" src="https://''' + FA + '''/npm/@clerk/clerk-js@5/dist/clerk.browser.js"></script>
<script>
window.addEventListener("load",async()=>{try{await Clerk.load();if(!Clerk.user){location.replace("/belepes.html");return;}
  const r=(Clerk.user.publicMetadata||{}).role;const ROLE_OK=["dekan","dh_tud","dh_okt","intezet","hivatal"];
  if(ROLE_OK.includes(r)){const k="aok-brief-portal";const s=JSON.parse(localStorage.getItem(k)||"{}");if(s.role!==r){s.role=r;localStorage.setItem(k,JSON.stringify(s));const sel=document.getElementById("roleSel");if(sel){sel.value=r;sel.dispatchEvent(new Event("change"));}}}
  const isAdmin=(Clerk.user.publicMetadata||{}).admin===true||(window.HV_ADMIN_EMAILS||[]).includes((Clerk.user.primaryEmailAddress||{}).emailAddress);
  if(isAdmin){const t=document.getElementById("hvAdminTab");if(t)t.hidden=false;hvAdminInit();}
  const lb=document.getElementById("hvLogout");if(lb){lb.title="Kilépés – "+(Clerk.user.primaryEmailAddress?Clerk.user.primaryEmailAddress.emailAddress:"");lb.addEventListener("click",()=>Clerk.signOut({redirectUrl:"/belepes.html"}));}
}catch(e){console.warn("Clerk",e);}});
function hvAdminInit(){
  const E=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const RN={dekan:"Vezető",dh_tud:"Tud. helyettes",dh_okt:"Okt. helyettes",intezet:"Egységvezető",hivatal:"Hivatalvezető"};
  const msg=t=>{document.getElementById("hvInvMsg").textContent=t;};
  async function api(method,qs,body){const r=await fetch("/api/invitations"+(qs||""),{method,headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error||r.status);return j;}
  async function load(){try{const d=await api("GET");
    document.getElementById("hvInvN").textContent=d.invitations.length+" függő";
    document.getElementById("hvInvList").innerHTML=d.invitations.length?d.invitations.map(i=>`<div class="row"><span class="pill elokesz">meghívva</span><span><span class="t">${E(i.email)}</span><span class="s">${E(RN[i.role]||i.role)}${i.admin?" · admin":""} · ${new Date(i.created).toLocaleDateString("hu-HU")}</span></span><button class="btn sm" data-hv-revoke="${E(i.id)}">Visszavonás</button></div>`).join(""):'<div class="empty">Nincs függő meghívó.</div>';
    document.getElementById("hvUsrN").textContent=d.users.length+" tag";
    document.getElementById("hvUsrList").innerHTML=d.users.map(u=>`<div class="row"><span class="pill elo">tag</span><span><span class="t">${E(u.name||u.email)}</span><span class="s">${E(u.email)} · ${E(RN[u.role]||u.role||"nézet nincs beállítva")}${u.admin?" · admin":""}${u.lastSignIn?" · utoljára: "+new Date(u.lastSignIn).toLocaleDateString("hu-HU"):""}</span></span>${u.email===d.me?"":`<button class="btn sm" data-hv-user="${E(u.id)}">Eltávolítás</button>`}</div>`).join("");
  }catch(e){msg("Hiba: "+e.message);}}
  document.getElementById("hvInvForm").addEventListener("submit",async e=>{e.preventDefault();msg("küldés…");try{await api("POST","",{email:document.getElementById("hvInvEmail").value,role:document.getElementById("hvInvRole").value,admin:document.getElementById("hvInvAdmin").checked});msg("Meghívó elküldve.");e.target.reset();load();}catch(er){msg("Hiba: "+er.message);}});
  document.getElementById("v-meghivas").addEventListener("click",async e=>{const b=e.target.closest("[data-hv-revoke],[data-hv-user]");if(!b)return;
    if(b.dataset.hvRevoke){if(!confirm("Meghívó visszavonása?"))return;try{await api("DELETE","?id="+b.dataset.hvRevoke);load();}catch(er){msg("Hiba: "+er.message);}}
    else{if(!confirm("Tag eltávolítása? Újra csak meghívóval léphet be."))return;try{await api("DELETE","?user="+b.dataset.hvUser);load();}catch(er){msg("Hiba: "+er.message);}}});
  document.getElementById("hvAdminTab").addEventListener("click",load);
}
</script>
<script>''', 'clerk-boot')

# 7) lábléc: képek forrása (CC) – a design nem nevez intézményt
html += '''\n<footer class="hv-foot wrap"><span>Napi frissítés · utolsó build: ''' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC') + '''</span></footer>\n'''

html = CLAUDE_RE.sub('', html)
html += '''\n<script>/* nyilvános oldal: üres vagy claude.ai-ra mutató link nem kattintható */
(function(){const fix=r=>r.querySelectorAll('a[href]').forEach(a=>{const h=a.getAttribute('href')||'';if(h===''||h==='undefined'||/claude\\.ai\\//i.test(h)){a.removeAttribute('href');a.removeAttribute('target');a.classList.add('hv-nolink');}});
fix(document);new MutationObserver(ms=>ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.nodeType===1){if(n.matches&&n.matches('a'))fix(n.parentNode||document);else fix(n);}}))).observe(document.body,{childList:true,subtree:true});})();
</script>\n'''
os.makedirs(os.path.join(HERE, 'public', 'data'), exist_ok=True)
open(os.path.join(HERE, 'public', 'index.html'), 'w', encoding='utf-8').write(html)
# belépőoldal a sablonból
bel = open(os.path.join(HERE, 'src', 'belepes.html'), encoding='utf-8').read()
bel = bel.replace('__CLERK_PUBLISHABLE_KEY__', PK).replace('__CLERK_FRONTEND_API__', FA).replace('__CONTACT_EMAIL__', CONTACT)
open(os.path.join(HERE, 'public', 'belepes.html'), 'w', encoding='utf-8').write(bel)
if not PK:
    warn.append('fvtp.config.json: clerkPublishableKey hiányzik (a belépés nem fog működni)')

# háttérelemzések: saját oldalként a /elemzesek/ alatt (src/elemzesek/*.md, *.raw.html)
ELEMZES_ID = {'9vTPoC7fSLJrv2ma4hFxYu': 'el-kitol-fugg', '4oReAR1hmisRfHV5W9Nb3w': 'el-kiktol-fugg',
              'BSkV6oxg5kxeSKBckUQfhB': 'el-ki-nyer', '6k2vZSni9Nx8ChBbtRNjnp': 'el-vezetoi-halo'}
def local_elemzes(url):
    m = re.search(r'claude\.ai/(?:code/)?artifact/([A-Za-z0-9-]+)', url or '')
    if m and m.group(1) in ELEMZES_ID and os.path.exists(os.path.join(HERE, 'public', 'elemzesek', ELEMZES_ID[m.group(1)] + '.html')):
        return '/elemzesek/' + ELEMZES_ID[m.group(1)]
    return None
def build_elemzesek():
    import markdown
    src = os.path.join(HERE, 'src', 'elemzesek'); out = os.path.join(HERE, 'public', 'elemzesek')
    if not os.path.isdir(src): return
    os.makedirs(out, exist_ok=True)
    tpl = open(os.path.join(HERE, 'src', 'elemzes-sablon.html'), encoding='utf-8').read()
    today = datetime.date.today().isoformat()
    for f in sorted(os.listdir(src)):
        fp = os.path.join(src, f)
        if f.endswith('.raw.html'):
            shutil.copy(fp, os.path.join(out, f.replace('.raw.html', '.html'))); continue
        if not f.endswith('.md'): continue
        md = open(fp, encoding='utf-8').read()
        lines = md.split('\n'); title = lines[0].lstrip('# ').strip()
        body = '\n'.join(lines[1:])
        body = re.sub(r'^\w{3} \d{1,2}, \d{4} · @.*$', '', body, flags=re.M)          # dátum- és említés-chip sor
        for aid, slug in ELEMZES_ID.items():                                           # elemzések közti hivatkozás → helyi
            body = re.sub(r'https?://claude\.ai/(?:code/)?artifact/' + aid, '/elemzesek/' + slug, body)
        body = MDLINK_RE.sub(lambda m: m.group(1), body); body = CLAUDE_RE.sub('', body)
        body = re.sub(r'&#91;embedded content: ([^\n]*?)\\?\]', lambda m: '<div class="ph">Beágyazott tábla/ábra – az eredeti dokumentumban: ' + m.group(1).replace('\\_', '_') + '</div>', body)
        html_body = '<h1>' + title + '</h1>\n' + markdown.markdown(body, extensions=['tables', 'sane_lists'])
        page = tpl.replace('__TITLE__', title).replace('__BODY__', html_body).replace('__DATE__', today)
        open(os.path.join(out, f[:-3] + '.html'), 'w', encoding='utf-8').write(page)
build_elemzesek()

# adatok – a claude.ai-ra (artifactokra) mutató linkek a nyilvános oldalon nem jelenhetnek meg
n_strip = [0]
def is_claude(v):
    return isinstance(v, str) and CLAUDE_RE.match(v.strip() or 'x') is not None
def clean_text(t):
    t2 = MDLINK_RE.sub(lambda m: m.group(1), t)
    t2 = CLAUDE_RE.sub('', t2)
    if t2 != t: n_strip[0] += 1
    return t2
def sanitize(o):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(v, str) and is_claude(v):
                loc = local_elemzes(v)
                if loc: out[k] = loc; continue     # háttérelemzés → saját oldal
                n_strip[0] += 1; continue          # url / source_url mező kihagyva
            out[k] = sanitize(v)
        return out
    if isinstance(o, list):
        res = []
        for v in o:
            # [címke, url] forráspár claude.ai-url-lel → kihagyjuk
            if isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) for x in v) and is_claude(v[1]):
                n_strip[0] += 1; continue
            res.append(sanitize(v))
        return res
    if isinstance(o, str):
        return clean_text(o)
    return o
def write_json(obj, name):
    json.dump(sanitize(obj), open(os.path.join(HERE, 'public', 'data', name), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for f in ('briefek.json', 'storylines.json'):
    src = os.path.join(a.data, f)
    if os.path.exists(src):
        obj = json.load(open(src, encoding='utf-8'))
        if f == 'briefek.json':
            for an in obj.get('analyses', []):   # háttérelemzés → saját oldal (azonosító = oldal neve)
                if an.get('id') and os.path.exists(os.path.join(HERE, 'public', 'elemzesek', an['id'] + '.html')):
                    an['url'] = '/elemzesek/' + an['id']
        write_json(obj, f)
    else:
        warn.append('hiányzik: ' + src)
# db-export (ArtifactData out_dir szerkezet) → egyetlen tömb
for coll in ('hirek', 'digest'):
    rows = []
    for p in sorted(glob.glob(os.path.join(a.data, 'dbexport', coll, '*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        d.setdefault('id', os.path.splitext(os.path.basename(p))[0])
        rows.append(d)
    if rows or not os.path.exists(os.path.join(HERE, 'public', 'data', coll + '.json')):
        write_json(rows, coll + '.json')

print('build kész → public/index.html', f'({len(html)//1024} KB)', '· kiszűrt claude.ai-hivatkozás:', n_strip[0])
for w in warn:
    print('FIGYELEM, nem talált csere:', w)
sys.exit(1 if warn else 0)
