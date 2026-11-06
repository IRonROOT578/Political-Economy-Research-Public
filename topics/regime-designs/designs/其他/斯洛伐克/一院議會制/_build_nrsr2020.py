"""統計局 NRSR 2020 tab03f（OBEC|OKRSOK|PS|P_HL_PS…，直線分隔）→ nrsr-2020.csv。
州與座標沿用 2023 檔的市鎮碼對應（同一套市鎮碼）；對不上的市鎮列為海外。
Usage: build2020.py TAB03F NRSR2023CSV OUTCSV"""
import collections, csv, sys
SRC, REF, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
NUM = {11: "OĽaNO", 19: "Smer", 4: "SmeRodina", 24: "ĽSNS", 12: "PS", 3: "SaS", 6: "ZaĽudí", 15: "KDH",
       22: "Aliancia", 9: "SNS", 2: "DobráVoľba", 17: "Vlasť", 18: "MostHid"}
ref = {}
for r in list(csv.reader(open(REF, encoding="utf-8")))[1:]:
    ref.setdefault(r[1], (r[0], r[3], r[4]))
units = collections.OrderedDict()
for l in open(SRC, encoding="utf-8-sig").read().splitlines()[1:]:
    f = l.split("|")
    units.setdefault((f[0], int(f[1])), collections.Counter())[NUM.get(int(f[2]), "其他")] += int(f[3])
cols = sorted({c for v in units.values() for c in v} - {"其他"}) + ["其他"]
rows, abroad = [], set()
for (obec, ok), v in units.items():
    reg, x, y = ref.get(obec, ("海外", "0.0000", "0.0000"))
    if obec not in ref:
        abroad.add(obec)
    rows.append([reg, obec, ok, x, y, sum(v.values())] + [v.get(c, 0) for c in cols])
with open(OUT, "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo)
    w.writerow(["區", "市鎮碼", "投票區", "經度", "緯度", "有效票"] + cols)
    w.writerows(rows)
tot = collections.Counter()
reg = collections.Counter()
for r in rows:
    reg[r[0]] += r[5]
    for c, n in zip(cols, r[6:]):
        tot[c] += n
s = sum(tot.values())
print(len(rows), "投票區；對不上 2023 市鎮（列為海外）", len(abroad), sorted(abroad)[:10], "；有效票", s)
print({c: round(tot[c] * 100 / s, 2) for c in cols})
print(dict(reg))
