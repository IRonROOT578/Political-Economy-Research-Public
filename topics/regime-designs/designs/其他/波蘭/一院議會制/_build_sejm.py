"""PKW 眾議院 逐投票所（wyniki_gl_na_listy_po_obwodach_sejm）→ sejm-YYYY.csv。
區＝本夾 12 個國內區＋海外；座標＝Wikidata P1653（TERYT 7 碼）前 6 碼平均。
Usage: build.py YEAR CSV GEOCSV OUTCSV"""
import collections, csv, re, sys
Y, SRC, GEO, OUT = sys.argv[1:5]
sys.stdout.reconfigure(encoding="utf-8")
STOL = {"Warszawa", "m. st. Warszawa", "grodziski", "legionowski", "miński", "nowodworski", "otwocki", "piaseczyński", "pruszkowski",
        "warszawski zachodni", "wołomiński"}
REG = {"śląskie": "西里西亞", "wielkopolskie": "大波蘭", "małopolskie": "小波蘭", "łódzkie": "羅茲", "pomorskie": "波美拉尼亞",
       "dolnośląskie": "下西里西亞－奧波萊", "opolskie": "下西里西亞－奧波萊", "lubelskie": "盧布林－波德拉謝", "podlaskie": "盧布林－波德拉謝",
       "podkarpackie": "喀爾巴阡－聖十字", "świętokrzyskie": "喀爾巴阡－聖十字", "kujawsko-pomorskie": "庫亞維－瓦爾米亞",
       "warmińsko-mazurskie": "庫亞維－瓦爾米亞", "zachodniopomorskie": "西波美拉尼亞－盧布斯卡", "lubuskie": "西波美拉尼亞－盧布斯卡"}
PARTY = [("PRAWO I SPRAWIEDLIWO", "PiS"), ("KOALICJA OBYWATELSKA", "KO"), ("TRZECIA DROGA", "TD"), ("LEWICA", "Lewica"),
         ("KONFEDERACJA", "Konf"), ("BEZPARTYJNI", "BS"), ("MNIEJSZO", "MN"), ("POLSKIE STRONNICTWO LUDOWE", "PSL")]
COLS = {"2023": ["PiS", "KO", "TD", "Lewica", "Konf", "BS", "MN", "其他"], "2019": ["PiS", "KO", "Lewica", "PSL", "Konf", "BS", "MN", "其他"]}[Y]
geo = collections.defaultdict(list)
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m and len(r["code"]) == 7:
        geo[r["code"][:6]].append((float(m.group(1)), float(m.group(2))))
geo4 = collections.defaultdict(list)
for k, v in geo.items():
    geo4[k[:4]] += v
avg = lambda v: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
geo = {k: avg(v) for k, v in geo.items()}
geo4 = {k: avg(v) for k, v in geo4.items()}   # 縣（powiat）平均：TERYT 對不上的鄉鎮用
r = csv.reader(open(SRC, encoding="utf-8-sig"), delimiter=";")
h = next(r)
ix = lambda *names: next(i for i, c in enumerate(h) if c in names)
iT, iW, iP, iV = ix("TERYT Gminy", "Kod TERYT"), ix("Województwo"), ix("Powiat"), ix("Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów")
iN = ix("Nr komisji", "Numer")
pcol = {}
for i, c in enumerate(h[iV + 1:], iV + 1):
    code = next((p for k, p in PARTY if k in c), "其他")
    if code == "Lewica" and "SOJUSZ LEWICY DEMOKRATYCZNEJ" not in c and Y == "2019":
        code = "其他"
    if Y == "2019" and "SOJUSZ LEWICY DEMOKRATYCZNEJ" in c:
        code = "Lewica"
    pcol[i] = code if code in COLS else "其他"
out, miss = [], collections.Counter()
for row in r:
    if not row or not row[iV].strip():
        continue
    t = row[iT].strip().zfill(6) if row[iT].strip() else ""
    w, pw = row[iW].strip(), row[iP].strip()
    if not t or not w or t[:4] in ("1498", "1499"):   # 1499 海外、1498 船上
        reg, xy = "海外", (0.0, 0.0)
    else:
        reg = ("首都" if pw in STOL else "馬佐夫舍") if w == "mazowieckie" else REG[w]
        xy = geo.get(t) or geo4.get(t[:4])
        if not xy:
            miss[t] += 1
            xy = (0.0, 0.0)
    v = collections.Counter()
    for i, c in pcol.items():
        x = row[i].strip()
        v[c] += int(x) if x.isdigit() else 0
    out.append([reg, t, row[iN], f"{xy[0]:.4f}", f"{xy[1]:.4f}", sum(v.values())] + [v.get(c, 0) for c in COLS])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "TERYT", "投票所", "經度", "緯度", "有效票"] + COLS)
    w.writerows(out)
tot = collections.Counter()
for o in out:
    for c, n in zip(COLS, o[6:]):
        tot[c] += n
s = sum(tot.values())
print(Y, len(out), "投票所；無座標 TERYT", len(miss), list(miss)[:8])
print({c: round(tot[c] * 100 / s, 2) for c in COLS}, "有效票", s, "valid col", sum(o[5] for o in out))
print(collections.Counter(o[0] for o in out))
