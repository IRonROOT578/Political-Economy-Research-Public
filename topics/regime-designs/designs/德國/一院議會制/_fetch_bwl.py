# -*- coding: utf-8 -*-
"""Fetch Bundestag 2025 Wahlkreis CSV from Bundeswahlleiterin."""
import os
import re
import ssl
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
os.makedirs(DATA, exist_ok=True)
CTX = ssl._create_unverified_context()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 regime-designs"})
    with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
        return r.read()


def main():
    page = get("https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse.html").decode(
        "utf-8", "replace"
    )
    links = re.findall(r'href="([^"]+)"', page)
    csvs = [L for L in links if "csv" in L.lower() or "kerg" in L.lower() or L.endswith(".csv")]
    print("found", len(csvs), "csv-ish links")
    for L in csvs:
        print(" ", L)
        if L.startswith("http"):
            full = L
        else:
            full = urllib.parse.urljoin(
                "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse.html", L
            )
        try:
            print("  GET", full)
            raw = get(full)
            name = os.path.basename(urllib.parse.urlparse(full).path) or "download.csv"
            path = os.path.join(DATA, name)
            with open(path, "wb") as f:
                f.write(raw)
            print("  saved", path, len(raw), "bytes; head:", raw[:160])
        except Exception as e:
            print("  FAIL", type(e).__name__, e)


if __name__ == "__main__":
    main()
