#!/usr/bin/env python3
"""fvtp – statikus Vercel-oldal építése a portál-artifact HTML-jéből.

Használat:  python3 build.py [--src <artifact.html>] [--data <portal-data mappa>]
Kimenet:    public/index.html + public/data/*.json

A forrás-HTML-t NEM szerkesztjük kézzel: minden eltérés (téma, belépés, csengő, db-fallback)
itt, szöveges cserékkel kerül rá, így az artifact UX-változásai minden buildnél átjönnek.
Ha egy csere nem talál (mert az artifact kódja változott), a szkript figyelmeztet, de nem áll le.
"""
import argparse, json, os, re, shutil, sys, glob, datetime

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

# 1) betűtípus: Satoshi (Fontshare) a Google-font helyett
rep('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@600&display=swap">',
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
    '<link rel="preconnect" href="https://api.fontshare.com"><link rel="stylesheet" href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700&display=swap">\n'
    '<link rel="icon" href="/favicon.svg" type="image/svg+xml">', 'font-link')

# 2) téma-CSS a saját stíluslap UTÁN (felülírja a tokeneket)
rep('</style>', '</style>\n<link rel="stylesheet" href="/theme.css">', 'theme-link')

# 3) szerep-legördülő ki (a JS továbbra is hivatkozik rá, ezért csak rejtjük) + kilépés gomb (Clerk signOut)
rep('<select class="role" id="roleSel" aria-label="Demó: szerepkör váltása">',
    '<button class="tb-btn hv-theme" type="button" id="hvTheme" aria-label="Világos / sötét téma" title="Világos / sötét téma"><svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg><svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4"/></svg></button>\n        <button class="tb-btn hv-logout" type="button" id="hvLogout" title="Kilépés">Kilépés</button>\n        <select class="role" id="roleSel" hidden aria-label="Szerepkör">', 'roleSel')

# 4) csengő: a rendszerben lekért, elkészült elemzések (háttérelemzések + kész dossziék)
rep('const n=ALERTS.filter(a=>a.roles.includes(role)).length;$("#bellN").textContent=n;$("#bellN").hidden=n===0;',
    'const n=((BF&&BF.analyses)||[]).length+DOSSZIEK.filter(d=>d.st==="elo").length;$("#bellN").textContent=n;$("#bellN").hidden=n===0;', 'bell-count')
rep('$("#bellBtn").addEventListener("click",()=>show("kezdolap"));',
    r'''$("#bellBtn").addEventListener("click",()=>{
  let p=$("#hvBell");if(p){p.remove();return;}
  const an=((BF&&BF.analyses)||[]).slice().sort((a,b)=>(b.date||"").localeCompare(a.date||""));
  const ds=DOSSZIEK.filter(d=>d.st==="elo");
  p=document.createElement("div");p.id="hvBell";p.className="hv-bell";
  p.innerHTML=`<div class="hv-bell-h"><b>Elkészült elemzések</b><span>${an.length+ds.length} tétel</span></div>
    ${ds.length?`<div class="hv-bell-sec">Dossziék</div>`+ds.map(d=>`<button class="hv-bell-row" data-hv-dosszie="${d.id}"><span>${esc(d.t)}</span><small>${fmtS(d.date)}</small></button>`).join(""):""}
    ${an.length?`<div class="hv-bell-sec">Háttérelemzések</div>`+an.map(x=>`<a class="hv-bell-row" href="${esc(x.url)}" target="_blank" rel="noopener"><span>${esc(x.title)}</span><small>${x.date?fmtS(x.date):""}</small></a>`).join(""):""}
    ${!an.length&&!ds.length?'<div class="empty">Még nincs elkészült elemzés.</div>':""}`;
  document.body.appendChild(p);
  p.addEventListener("click",e=>{const b=e.target.closest("[data-hv-dosszie]");if(b){openSl=null;openDosszie=b.dataset.hvDosszie;show("dosszie");renderDosszieReader();p.remove();}});
  setTimeout(()=>document.addEventListener("click",function h(e){if(!p.contains(e.target)&&!e.target.closest("#bellBtn")){p.remove();document.removeEventListener("click",h);}}),0);
});''', 'bell-click')

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
(function(){let t="dark";try{t=localStorage.getItem("fvtp-theme")||"dark";}catch(e){}document.documentElement.setAttribute("data-theme",t);
document.addEventListener("DOMContentLoaded",()=>{const b=document.getElementById("hvTheme");if(!b)return;b.addEventListener("click",()=>{const n=document.documentElement.getAttribute("data-theme")==="light"?"dark":"light";document.documentElement.setAttribute("data-theme",n);try{localStorage.setItem("fvtp-theme",n);}catch(e){}});});})();
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
html += '''\n<footer class="hv-foot wrap"><span>Napi frissítés · utolsó build: ''' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC') + '''</span><span>Fotók: Harta Viktor, Ruprech Judit (CC BY-SA 4.0), takacsja (CC BY-SA 2.5), Szajci (PD) – Wikimedia Commons</span></footer>\n'''

CLAUDE_RE = re.compile(r'''https?://(?:www\.)?claude\.ai/[^\s)\]"'<>]*''')
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

# adatok – a claude.ai-ra (artifactokra) mutató linkek a nyilvános oldalon nem jelenhetnek meg
MDLINK_RE = re.compile(r'\[([^\]]+)\]\((https?://(?:www\.)?claude\.ai/[^)]*)\)')
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
        write_json(json.load(open(src, encoding='utf-8')), f)
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
