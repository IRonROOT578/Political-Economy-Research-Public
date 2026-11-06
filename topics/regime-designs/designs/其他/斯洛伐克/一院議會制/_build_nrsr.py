"""統計局 NRSR 逐投票區（tab03f：okrsok × 政黨）＋Wikidata LAU（P782）市鎮座標 → nrsr-YYYY.csv。
Usage: build.py TAB03F GEOCSV OUTCSV [YEAR]（政黨依官方編號對應，見 NUM）"""
import collections, csv, re, sys
SRC, GEO, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
KRAJ = {"Bratislavský kraj": "布拉提斯拉瓦", "Trnavský kraj": "特爾納瓦", "Trenčiansky kraj": "特倫欽", "Nitriansky kraj": "尼特拉",
        "Žilinský kraj": "日利納", "Banskobystrický kraj": "班斯卡比斯特里察", "Prešovský kraj": "普雷紹夫",
        "Košický kraj": "科希策", "Cudzina": "海外"}
NUM = {"2023": {3: "PS", 5: "OĽaNO", 12: "SaS", 13: "SmeRodina", 15: "SNS", 16: "Smer", 17: "Hlas", 18: "Aliancia",
                21: "ĽSNS", 22: "Demokrati", 23: "KDH", 25: "Republika"}}
YEAR = sys.argv[4] if len(sys.argv) > 4 else "2023"
def code(num):
    return NUM[YEAR].get(int(num), "其他")
geo = {}
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m:
        geo.setdefault(r["lau"][-6:], (float(m.group(1)), float(m.group(2))))
units = collections.OrderedDict()
names = {}
for x in list(csv.reader(open(SRC, encoding="utf-8-sig")))[1:]:
    k = (KRAJ[x[1]], x[6], x[8])
    v = units.setdefault(k, collections.Counter())
    c = code(x[9]); names[x[10]] = c
    v[c] += int(x[11])
cols = sorted({c for v in units.values() for c in v} - {"其他"}) + ["其他"]
rows, miss = [], set()
for (reg, obec, ok), v in units.items():
    xy = geo.get(obec)
    if not xy and reg != "海外":
        miss.add(obec)
    xy = xy or (0.0, 0.0)
    rows.append([reg, obec, ok, f"{xy[0]:.4f}", f"{xy[1]:.4f}", sum(v.values())] + [v.get(c, 0) for c in cols])
# 沒座標的市鎮：用同區平均
by = collections.defaultdict(list)
for r in rows:
    if r[3] != "0.0000":
        by[r[0]].append((float(r[3]), float(r[4])))
for r in rows:
    if r[0] != "海外" and r[1] in miss:
        p = by[r[0]]
        r[3], r[4] = f"{sum(a for a, _ in p) / len(p):.4f}", f"{sum(b for _, b in p) / len(p):.4f}"
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "市鎮碼", "投票區", "經度", "緯度", "有效票"] + cols)
    w.writerows(rows)
tot = collections.Counter()
reg = collections.Counter()
for r in rows:
    reg[r[0]] += r[5]
    for c, n in zip(cols, r[6:]):
        tot[c] += n
s = sum(tot.values())
print(len(rows), "投票區；無座標市鎮", len(miss), sorted(miss)[:8], "；有效票", s)
print({c: round(tot[c] * 100 / s, 2) for c in cols})
print(dict(reg))
