# -*- coding: utf-8 -*-
"""下載中選會 votedata.zip（約 110MB）到 資料/raw/。"""
import os
import ssl
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "資料", "raw")
os.makedirs(RAW, exist_ok=True)
URL = "https://data.cec.gov.tw/%E9%81%B8%E8%88%89%E8%B3%87%E6%96%99%E5%BA%AB/votedata.zip"
DEST = os.path.join(RAW, "votedata.zip")
CTX = ssl._create_unverified_context()


def main():
    if os.path.isfile(DEST) and os.path.getsize(DEST) > 50_000_000:
        print("already have", DEST, os.path.getsize(DEST))
        return
    print("GET", URL)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 regime-designs"})
    with urllib.request.urlopen(req, context=CTX, timeout=600) as r, open(DEST, "wb") as f:
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
            if n % (10 << 20) == 0:
                print(" ", n // (1 << 20), "MB")
    print("saved", DEST, os.path.getsize(DEST))


if __name__ == "__main__":
    main()
