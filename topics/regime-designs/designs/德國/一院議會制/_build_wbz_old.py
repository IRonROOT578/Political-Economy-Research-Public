"""Bundeswahlleiterin Wahlbezirksstatistik 2013、2017 舊格式（Zweitstimmen 單獨一檔、無市鎮名稱欄）→ wbz-YYYY.csv。
做法同 _build_wbz.py：郵寄投票區（Bezirksart 5）按同池實體投票區的 A2（已領郵寄選票）比例分回；投票區號 //100 合併。
Usage: build_old.py ZWEITCSV ENCODING LANDREF OUTCSV"""
import collections, csv, sys
W, ENC, REF, OUT = sys.argv[1:5]
sys.stdout.reconfigure(encoding="utf-8")
MAIN = {"SPD": "SPD", "CDU": "CDU", "GRÜNE": "GRÜNE", "FDP": "FDP", "AfD": "AfD", "CSU": "CSU", "DIE LINKE": "LINKE",
        "FREIE WÄHLER": "FW"}
COLS = ["SPD", "CDU", "GRÜNE", "FDP", "AfD", "CSU", "LINKE", "BSW", "FW", "SSW", "其他"]
land = {r["land_code"]: r["land"] for r in csv.DictReader(open(REF, encoding="utf-8"))}
L = open(W, encoding=ENC).read().splitlines()
i = next(k for k, l in enumerate(L) if l.startswith('"Wahlkreis"'))
rows = list(csv.reader(L[i:], delimiter=";"))
h, rows = rows[0], [r for r in rows[1:] if r and r[0].strip()]
ix = {c: j for j, c in enumerate(h)}
g = ix.get("Gültige", ix.get("Gültig"))
end = ix.get("Ungekürzte Wahlbezirksbezeichnung", len(h))
pcols = {j: MAIN.get(h[j], "其他") for j in range(g + 1, end)}
a2, art, wbz = ix["Wahlberechtigte mit Sperrvermerk (A2)"], ix["Bezirksart"], ix["Wahlbezirk"]
num = lambda x: int(x) if x.strip().lstrip("-").isdigit() else 0
def votes(r):
    v = collections.Counter()
    for j, p in pcols.items():
        v[p] += num(r[j])
    return v
urn, pools = [], collections.defaultdict(collections.Counter)
for r in rows:
    if r[art] == "5":
        pools[tuple(r[0:6])].update(votes(r))
    else:
        urn.append(r)
members = collections.defaultdict(list)
for r in urn:
    for lvl, k in enumerate([tuple(r[0:6]), tuple(r[0:5]), tuple(r[0:4]), (r[0],)]):
        members[(lvl, k)].append(r)
alloc = collections.defaultdict(collections.Counter)
lost = 0
for pk, pv in pools.items():
    tgt = next((members[(lvl, k)] for lvl, k in enumerate([pk, pk[:5], pk[:4], pk[:1]]) if members.get((lvl, k))), None)
    if not tgt:
        lost += sum(pv.values()); continue
    w = [max(num(r[a2]), 0) for r in tgt]
    if not sum(w):
        w = [1] * len(tgt)
    s = sum(w)
    for r, x in zip(tgt, w):
        for p, n in pv.items():
            alloc[id(r)][p] += n * x / s
units = collections.OrderedDict()
for r in urn:
    k = (r[0], r[1], r[2], r[3], r[4], r[5], num("".join(ch for ch in r[wbz] if ch.isdigit()) or "0") // 100)
    u = units.setdefault(k, collections.Counter())
    u.update(votes(r))
    u.update(alloc[id(r)])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["land_code", "land", "wk_nr", "unit", "name", "valid"] + COLS)
    for n, (k, v) in enumerate(units.items()):
        vals = [round(v.get(c, 0)) for c in COLS]
        w.writerow([k[1], land[k[1]], k[0], f"{k[0]}-{n:06d}", f"{k[1]}{k[2]}{k[3]}{k[4]}{k[5]}", sum(vals)] + vals)
tot = collections.Counter()
for v in units.values():
    tot.update(v)
s = sum(tot.values())
print(len(units), "units；郵寄池", len(pools), "；無承接", lost, "；valid", round(s))
print({c: round(tot[c] * 100 / s, 2) for c in COLS})
