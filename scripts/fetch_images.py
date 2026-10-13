#!/usr/bin/env python3
"""A design fotóinak letöltése a Wikimedia Commons-ról a public/img mappába (CC BY-SA / PD; attribúció a láblécben).
Saját fotók: tedd ugyanezen a néven a public/img mappába – a szkript nem ír felül létező fájlt."""
import os, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'public', 'img')
IMG = {
  'campus.jpg':       'https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/A_400_%C3%A1gyas_klinika_az_%C3%BAj_elm%C3%A9leti_t%C3%B6mb_terasz%C3%A1r%C3%B3l_n%C3%A9zve.jpg/1920px-A_400_%C3%A1gyas_klinika_az_%C3%BAj_elm%C3%A9leti_t%C3%B6mb_terasz%C3%A1r%C3%B3l_n%C3%A9zve.jpg',
  'reading-room.jpg': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Tud%C3%A1sk%C3%B6zpont_egyik_olvas%C3%B3terme_%28P%C3%A9cs%29.jpg/1920px-Tud%C3%A1sk%C3%B6zpont_egyik_olvas%C3%B3terme_%28P%C3%A9cs%29.jpg',
  'library.jpg':      'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Tud%C3%A1sk%C3%B6zpont_l%C3%A1tk%C3%A9pe_%28P%C3%A9cs%29.jpg/1920px-Tud%C3%A1sk%C3%B6zpont_l%C3%A1tk%C3%A9pe_%28P%C3%A9cs%29.jpg',
  'cathedral.jpg':    'https://upload.wikimedia.org/wikipedia/commons/2/29/Sz%C3%A9kesegyh%C3%A1z_%281796._sz%C3%A1m%C3%BA_m%C5%B1eml%C3%A9k%29_6.jpg',
  'city.jpg':         'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/P%C3%A9cs-Ur%C3%A1nv%C3%A1ros_panor%C3%A1ma.jpg/1920px-P%C3%A9cs-Ur%C3%A1nv%C3%A1ros_panor%C3%A1ma.jpg',
}
os.makedirs(OUT, exist_ok=True)
for name, url in IMG.items():
    dst = os.path.join(OUT, name)
    if os.path.exists(dst):
        print('megvan:', name); continue
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'fvtp-build/1.0 (static site images; contact via repo)'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        open(dst, 'wb').write(data)
        print('letöltve:', name)
    except Exception as e:  # a build ettől ne álljon le – a kép nélkül is megy az oldal
        print('NEM sikerült:', name, e)
