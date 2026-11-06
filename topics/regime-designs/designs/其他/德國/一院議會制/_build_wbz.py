"""Bundeswahlleiterin Wahlbezirksstatistik（btwYY_wbz_ergebnisse.csv）→ 逐投票區 Zweitstimme CSV。
郵寄投票區（Bezirksart 5）的票，按同一池（同選區、同市鎮；找不到則同 Verbandsgemeinde、同 Kreis、同選區）
各實體投票區的「Wahlberechtigte mit Sperrvermerk (A2)」（已領郵寄選票者）比例分回。
實體投票區再依「投票區號 // 100」併成小單位（大城市約等於城區；小市鎮＝整個市鎮）。
Usage: build.py WBZCSV LANDREF OUTCSV"""
import collections, csv, sys
W, REF, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
MAIN = {"SPD": "SPD", "CDU": "CDU", "GRÜNE": "GRÜNE", "FDP": "FDP", "AfD": "AfD", "CSU": "CSU", "Die Linke": "LINKE",
        "DIE LINKE": "LINKE", "BSW": "BSW", "FREIE WÄHLER": "FW", "SSW": "SSW"}
COLS = ["SPD", "CDU", "GRÜNE", "FDP", "AfD", "CSU", "LINKE", "BSW", "FW", "SSW", "其他"]
land = {}
for r in csv.DictReader(open(REF, encoding="utf-8")):
    land[r["land_code"]] = r["land"]
L = open(W, encoding="utf-8-sig").read().splitlines()
i = next(k for k, l in enumerate(L) if l.startswith("Wahlkreis;"))
rows = list(csv.reader(L[i:], delimiter=";"))
h, rows = rows[0], [r for r in rows[1:] if r and r[0].strip()]
zc = {}
for j, c in enumerate(h):
    if c.endswith(" - Zweitstimmen"):
        zc[j] = c[:-len(" - Zweitstimmen")]
    elif c.startswith("Z_"):
        zc[j] = c[2:]
zc = {j: p for j, p in zc.items() if p not in ("Ungültige", "Gültige")}
a2 = h.index("Wahlberechtigte mit Sperrvermerk (A2)")
def votes(r):
    v = collections.Counter()
    for j, p in zc.items():
        v[MAIN.get(p, "其他")] += int(r[j] or 0)
    return v
keys = lambda r: [tuple(r[0:6]), tuple(r[0:5]), tuple(r[0:4]), (r[0],)]
urn, pools = [], collections.defaultdict(collections.Counter)
for r in rows:
    if r[10] == "5":
        pools[tuple(r[0:6])].update(votes(r))
    else:
        urn.append(r)
# 每個池找承接的實體投票區
weight = collections.defaultdict(float)
members = collections.defaultdict(list)
for r in urn:
    for lvl in range(4):
        members[(lvl, keys(r)[lvl])].append(r)
alloc = collections.defaultdict(collections.Counter)
lost = 0
for pk, pv in pools.items():
    tgt = None
    for lvl, k in enumerate([pk, pk[:5], pk[:4], pk[:1]]):
        if members.get((lvl, k)):
            tgt = members[(lvl, k)]
            break
    if not tgt:
        lost += sum(pv.values()); continue
    w = [max(int(r[a2] or 0), 0) for r in tgt]
    if not sum(w):
        w = [1] * len(tgt)
    s = sum(w)
    for r, x in zip(tgt, w):
        for p, n in pv.items():
            alloc[id(r)][p] += n * x / s
units = collections.OrderedDict()
for r in urn:
    k = (r[0], r[1], r[2], r[3], r[4], r[5], int("".join(ch for ch in r[9] if ch.isdigit()) or 0) // 100)
    u = units.setdefault(k, [r[8], collections.Counter()])
    u[1].update(votes(r))
    u[1].update(alloc[id(r)])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["land_code", "land", "wk_nr", "unit", "name", "valid"] + COLS)
    for n, (k, (name, v)) in enumerate(units.items()):
        vals = [round(v.get(c, 0)) for c in COLS]
        w.writerow([k[1], land[k[1]], k[0], f"{k[0]}-{n:06d}", name, sum(vals)] + vals)
tot = collections.Counter()
for _, v in units.values():
    tot.update(v)
s = sum(tot.values())
print(len(units), "units；郵寄池", len(pools), "；無承接", lost)
print({c: round(tot[c] * 100 / s, 2) for c in COLS}, "valid", round(s))
