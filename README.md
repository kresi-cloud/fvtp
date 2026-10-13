# fvtp – Felsőoktatási Vezetői Tájékoztató Portál (Vercel)

Napi frissítésű, meghívásos belépésű statikus oldal a portál-artifactból építve.
Design: sötét/világos téma, lila akcent, Satoshi betű; a fejlécben témakapcsoló, csengő (elkészült elemzések), Kilépés.

## Mappa

| | |
|---|---|
| `build.py` | az artifact HTML-jéből (`../aok-vezetoi-brief-portal.html`) és a `../portal-data` adatokból előállítja a `public/` mappát |
| `public/` | a kész oldal: `index.html`, `belepes.html`, `theme.css`, `data/*.json`, `img/*.jpg` |
| `src/belepes.html` | a belépőoldal sablonja (Clerk-kulcs és kapcsolat e-mail a buildkor kerül bele) |
| `middleware.js` | Vercel Edge: belépés nélkül minden oldal a belépőre irányít |
| `api/invitations.js` | meghívók listázása/küldése/visszavonása, tagok eltávolítása – csak adminnak |
| `scripts/fetch_images.py` | a fotók letöltése a Wikimedia Commons-ról (`public/img`) |
| `scripts/bootstrap_admin.py` | az első admin (gergely.kresak@gmail.com) meghívása |
| `scripts/invite.py` | meghívó parancssorból |
| `scripts/daily.sh` | napi: adatok → build → git push |
| `fvtp.config.json` | nyilvános beállítások: Clerk publishable key, kapcsolat e-mail, admin e-mailek |

## Feltöltés – lépésről lépésre (kb. 20 perc)

### 1. Clerk (belépés: Google + e-mail kód, csak meghívottaknak)
1. https://dashboard.clerk.com → *Create application*, név: `fvtp`. Sign-in módok: **Email** (email code) és **Google** – a jelszót kapcsold ki.
2. *Configure → Restrictions → Sign-up mode:* **Restricted** (csak meghívott e-mail regisztrálhat/léphet be).
3. *Configure → Sessions:* inaktivitási lejárat tetszés szerint (pl. 7 nap).
4. *API keys:* másold ki a **Publishable key**-t (`pk_…`) és a **Secret key**-t (`sk_…`).
5. `fvtp.config.json`: írd be a publishable key-t és a kapcsolat e-mailt (minta: `fvtp.config.example.json`). A secret key **nem** kerül fájlba.

### 2. Fotók
`python3 scripts/fetch_images.py` – 5 fotót tölt le a `public/img` mappába (CC BY-SA / közkincs; a lábléc hozza az attribúciót).
Saját fotóval ugyanezen a néven cserélhetők: `campus.jpg`, `reading-room.jpg`, `library.jpg`, `cathedral.jpg`, `city.jpg`.

### 3. Build
```
python3 build.py            # → public/index.html, public/belepes.html, public/data/*
```
Ezt minden artifact-módosítás után újra kell futtatni; a build a saját változtatásait (téma, belépés, csengő, meghívás-menü) cserékkel teszi rá az artifact HTML-jére, és jelzi, ha egy csere már nem talál.

### 4. Vercel
```
npm i -g vercel
vercel login
vercel link          # új projekt, név: fvtp  → ha a név foglalt, a CLI szól; tartalék: fvtp-portal, fvtp-pte, vezetoi-portal
vercel env add CLERK_SECRET_KEY production            # sk_…
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production   # pk_…
vercel env add ADMIN_EMAILS production                # gergely.kresak@gmail.com
vercel deploy --prod
```
A `fvtp.vercel.app` cím szabadságát csak a `vercel link` tudja ellenőrizni (a Vercel foglaltsága kívülről nem kérdezhető le).
Saját domain: *Project → Settings → Domains*. A Clerkben *Configure → Domains* alatt add hozzá az éles domaint (a `*.vercel.app` fejlesztői kulccsal is megy).

### 5. Első admin
```
CLERK_SECRET_KEY=sk_… python3 scripts/bootstrap_admin.py gergely.kresak@gmail.com https://fvtp.vercel.app
```
A meghívó e-mailből belépve megjelenik a **Meghívások** menü: innen hívható meg és vonható vissza bárki (nézet-szerepkörrel, opcionálisan admin joggal), illetve távolítható el tag.

## Napi frissítés
A legegyszerűbb: GitHub-repó + Vercel Git-integráció (*Vercel → Add New → Project → Import Git repo*). Ezután
minden push automatikusan újratelepít. A napi feladat (ütemezett Claude-feladat vagy cron) a `scripts/daily.sh`-t futtatja:
adatok frissítése (`tools/portal_update.py`), db-export (hírek, digestek), build, commit, push.
Repo nélkül: `vercel deploy --prod` a build után (a Vercel-token `VERCEL_TOKEN` változóban).

## Megjegyzések
- A hírfigyelő a Vercelen nem az artifact adatbázisából, hanem a `public/data/hirek.json` + `digest.json` fájlokból olvas (a build exportálja).
- Az oldalon sehol nem szerepel intézménynév vagy logó; a fotók helyszíne természetesen felismerhető.
- `X-Robots-Tag: noindex` – a keresők nem indexelik.
