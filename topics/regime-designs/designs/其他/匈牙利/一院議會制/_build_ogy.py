"""NVI vtr 逐投票所名單票（SzavkorJkv）＋投票所中心座標 → ogy-YYYY.csv；海外郵寄票（ListasJkv 的 level_szavazat）另成一列。
Usage: build.py DIR OUTCSV [CENTRUM.json]（2022 沿用 2026 的投票所座標；NVI 市鎮代碼兩屆相同）"""
import collections, csv, glob, json, os, re, sys
D, OUT = sys.argv[1:3]
CEN = sys.argv[3] if len(sys.argv) > 3 else f"{D}/centrum.json"
sys.stdout.reconfigure(encoding="utf-8")
REGION = {"01": "布達佩斯", "14": "佩斯", "07": "中多瑙河外", "12": "中多瑙河外", "19": "中多瑙河外",
          "08": "西多瑙河外", "18": "西多瑙河外", "20": "西多瑙河外", "02": "南多瑙河外", "15": "南多瑙河外", "17": "南多瑙河外",
          "05": "北匈牙利", "10": "北匈牙利", "13": "北匈牙利", "09": "北大平原", "11": "北大平原", "16": "北大平原",
          "03": "南大平原", "04": "南大平原", "06": "南大平原"}
def code(name):
    n = name.upper()
    if "FIDESZ" in n: return "FIDESZ"
    if "TISZA" in n: return "TISZA"
    if "MI HAZÁNK" in n: return "MI"
    if "EGYSÉGBEN" in n or "DK-JOBBIK" in n or "JOBBIK" in n: return "EGYSÉG"
    if n.startswith("DK") or "DEMOKRATIKUS KOALÍCIÓ" in n: return "DK"
    if "MKKP" in n or "KUTYA" in n: return "MKKP"
    if n.startswith("MNOÖ") or "NÉMETEK" in n: return "德意志族"
    return "其他"
lists = json.load(open(f"{D}/ListakEsJeloltek.json", encoding="utf-8"))["list"]
tl = {x["tl_id"]: code(x["jlcs_nev"]) for x in lists}
names = {x["tl_id"]: x["jlcs_nev"] for x in lists}
cent = json.load(open(CEN, encoding="utf-8"))
cols = sorted(set(tl.values()) - {"其他"}, key=lambda c: ["TISZA", "FIDESZ", "EGYSÉG", "MI", "DK", "MKKP", "德意志族"].index(c)) + ["其他"]
rows, nocoord = [], 0
for f in sorted(glob.glob(f"{D}/szk/*.json")):
    for s in json.load(open(f, encoding="utf-8"))["list"]:
        lj = s.get("listas_jkv") or {}
        v = collections.Counter()
        for t in lj.get("tetelek", []):
            v[tl[t["tl_id"]]] += t["szavazat"]
        if not v:
            continue
        c = cent.get(f"{s['maz']}-{s['taz']}-{s['sorsz']}")
        if c:
            lat, lon = map(float, c.split())
        else:
            nocoord += 1
            lat = lon = None
        rows.append([REGION[s["maz"]], f"{s['maz']}-{s['taz']}-{s['sorsz']}", lon, lat, sum(v.values())] + [v.get(k, 0) for k in cols])
# 沒座標的投票所：用同市鎮其他投票所平均
cby = collections.defaultdict(list)   # 座標檔本身的市鎮平均（2022 用：投票所編號可能變了，市鎮不變）
for k, c in cent.items():
    if c:
        la, lo = map(float, c.split())
        cby[k[:6]].append((lo, la))
by = collections.defaultdict(list)
for r in rows:
    if r[2] is not None:
        by[r[1][:6]].append((r[2], r[3]))
for r in rows:
    if r[2] is None:
        pts = by.get(r[1][:6]) or cby.get(r[1][:6]) or [(19.0, 47.2)]
        r[2], r[3] = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
lv = collections.Counter()
for t in json.load(open(f"{D}/ListasJkv.json", encoding="utf-8"))["list"][0]["tetelek"]:
    lv[tl[t["tl_id"]]] += t.get("level_szavazat", 0) or 0
rows.append(["海外", "郵寄", 0.0, 0.0, sum(lv.values())] + [lv.get(k, 0) for k in cols])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "投票所", "經度", "緯度", "有效票"] + cols)
    for r in rows:
        w.writerow(r[:2] + [f"{r[2]:.4f}", f"{r[3]:.4f}"] + r[4:])
tot = collections.Counter()
for r in rows:
    for k, n in zip(cols, r[5:]):
        tot[k] += n
s = sum(tot.values())
print(len(rows) - 1, "投票所＋海外；無座標", nocoord, "；有效票", s)
print({k: round(tot[k] * 100 / s, 2) for k in cols})
print("lists:", {names[k]: v for k, v in tl.items()})
