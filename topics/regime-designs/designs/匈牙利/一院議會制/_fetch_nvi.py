"""NVI vtr 逐投票所（SzavkorJkv-縣-市鎮.json）批次下載。Usage: fetch.py YEAR OUTDIR"""
import json, os, sys, time, urllib.request
Y, OUT = sys.argv[1:3]
BASE = f"https://vtr.valasztas.hu/ogy{Y}/data"
def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "Mozilla/5.0 regime-designs-research"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()
cfg = json.loads(get("config.json"))
os.makedirs(f"{OUT}/szk", exist_ok=True)
for f in ("Telepulesek", "ListakEsJeloltek", "Szervezetek", "EgyeniJeloltek"):
    open(f"{OUT}/{f}.json", "wb").write(get(f"{cfg['ver']}/ver/{f}.json"))
for f in ("ListasJkv", "OevkJkv", "LevelJkv"):
    try:
        open(f"{OUT}/{f}.json", "wb").write(get(f"{cfg['szavossz']}/szavossz/{f}.json"))
    except Exception as e:
        print("skip", f, e)
tel = json.load(open(f"{OUT}/Telepulesek.json", encoding="utf-8"))["list"]
n = 0
for t in tel:
    L = t.get("leiro", t)
    m, z = L["maz"], L["taz"]
    dst = f"{OUT}/szk/{m}-{z}.json"
    if os.path.exists(dst):
        continue
    for k in range(3):
        try:
            open(dst, "wb").write(get(f"{cfg['szavossz']}/szavossz/{m}/SzavkorJkv-{m}-{z}.json"))
            break
        except Exception as e:
            time.sleep(2)
    n += 1
    time.sleep(0.05)
print(Y, "done", n, "files; config", cfg)
