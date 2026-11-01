# -*- coding: utf-8 -*-
import os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
os.makedirs(DATA, exist_ok=True)

opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", "Mozilla/5.0")]
urllib.request.install_opener(opener)

url = "https://www.bmi.gv.at/412/nationalratswahlen/nationalratswahl_2024/"
html = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "replace")
open(os.path.join(DATA, "_bmi_page.html"), "w", encoding="utf-8").write(html)
xlsx = re.findall(r'href="([^"]+\.xlsx)"', html, re.I)
print("xlsx links:", xlsx)
for href in xlsx:
    if href.startswith("/"):
        full = "https://www.bmi.gv.at" + href
    elif href.startswith("http"):
        full = href
    else:
        full = "https://www.bmi.gv.at/412/nationalratswahlen/nationalratswahl_2024/" + href
    print("try", full)
    try:
        out = os.path.join(DATA, "nr2024-bmi.xlsx")
        urllib.request.urlretrieve(full, out)
        print("saved", out, os.path.getsize(out))
        break
    except Exception as e:
        print("fail", e)
