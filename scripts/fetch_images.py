#!/usr/bin/env python3
"""A design fotóinak letöltése a Wikimedia Commons-ról a public/img mappába (CC BY-SA / PD; attribúció a láblécben).
Saját fotók: tedd ugyanezen a néven a public/img mappába – a szkript nem ír felül létező fájlt."""
import os, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'img')
IMG = {
  'aok.jpg':        'https://upload.wikimedia.org/wikipedia/commons/2/24/A_PTE_%C3%81OK_%C3%BAj_elm%C3%A9leti_t%C3%B6mbje.jpg',
  'rektorat.jpg':   'https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Rector%27s_Office%2C_University_of_P%C3%A9cs.JPG/1920px-Rector%27s_Office%2C_University_of_P%C3%A9cs.JPG',
  'kozepkori.jpg':  'https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Medival_University_of_Pecs_southern_side.JPG/1920px-Medival_University_of_Pecs_southern_side.JPG',
  'klinika.jpg':    'https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/A_400_%C3%A1gyas_klinika_az_%C3%BAj_elm%C3%A9leti_t%C3%B6mb_terasz%C3%A1r%C3%B3l_n%C3%A9zve.jpg/1920px-A_400_%C3%A1gyas_klinika_az_%C3%BAj_elm%C3%A9leti_t%C3%B6mb_terasz%C3%A1r%C3%B3l_n%C3%A9zve.jpg',
  'tudaskozpont.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Tud%C3%A1sk%C3%B6zpont_l%C3%A1tk%C3%A9pe_%28P%C3%A9cs%29.jpg/1920px-Tud%C3%A1sk%C3%B6zpont_l%C3%A1tk%C3%A9pe_%28P%C3%A9cs%29.jpg',
  'cathedral.jpg':  'https://upload.wikimedia.org/wikipedia/commons/2/29/Sz%C3%A9kesegyh%C3%A1z_%281796._sz%C3%A1m%C3%BA_m%C5%B1eml%C3%A9k%29_6.jpg',
}
os.makedirs(OUT, exist_ok=True)
for name, url in IMG.items():
    dst = os.path.join(OUT, name)
    if os.path.exists(dst):
        print('megvan:', name); continue
    import time
    UA = 'fvtp-build/1.0 (https://github.com/kresi-cloud/fvtp; gergely.kresak@gmail.com) python-urllib'
    ok = False
    for attempt, u in enumerate([url, url.replace('upload.wikimedia.org', 'thumb.wikimedia.org'), url]):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'image/jpeg,image/*;q=0.8'})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            open(dst, 'wb').write(data)
            print('letöltve:', name, len(data) // 1024, 'KB'); ok = True; break
        except Exception as e:  # a build ettől ne álljon le – a kép nélkül is megy az oldal
            print('próba', attempt + 1, 'nem sikerült:', name, e); time.sleep(3 + 3 * attempt)
    if not ok:
        print('NEM sikerült:', name)
