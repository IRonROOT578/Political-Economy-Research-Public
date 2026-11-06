"""2019-05 歐洲議會選舉（大不列顛 11 區、比例代表名單票）估計到 2010–2019 年的 632 個國會選區 → 資料/ep-2019.csv。

    python _build_ep2019.py <維基原始碼> 資料/ge-2019.csv 資料/ep-2019.csv

- 來源：維基「Results of the 2019 European Parliament election in the United Kingdom by Westminster constituency」
  （原始碼 action=raw；計票區得票估計到國會選區）。英國選舉委員會網站對自動存取回 403，未繞過。
- 欄位與 ge-2019.csv 相同（地區、選區、經度、緯度、有效票、各黨）；選區名稱、座標、地區取自 ge-2019.csv。
- 政黨：Brexit Party→Reform（同一黨，2021 年改名）；Change UK、UKIP、其他→其他；北愛爾蘭（表中沒有）沿用 2019 國會選舉得票。
- 用途：英國沒有全國政黨名單票；歐洲議會選舉是唯一的全國比例代表政黨票，當作「第一偏好＝政黨票」的對照版。
"""
import csv
import re
import sys
import unicodedata

WIKI, GE, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
PARTIES = ["Brexit", "ChangeUK", "Con", "Green", "Lab", "LD", "Other", "PC", "SNP", "UKIP"]
MAP = {"Brexit": "Reform", "ChangeUK": "其他", "Con": "Con", "Green": "Green", "Lab": "Lab", "LD": "LD", "Other": "其他",
       "PC": "PC", "SNP": "SNP", "UKIP": "其他"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and").replace(" st ", " saint ").replace("st. ", "saint ")
    return re.sub(r"[^a-z]", "", s)


t = open(WIKI, encoding="utf-8").read()
i = t.index('{| class="wikitable sortable')
body = t[i:t.index("\n|}", i)]
rows = {}
for blk in body.split("\n|-")[1:]:
    cells = [c for c in blk.split("\n") if c.startswith("|") and not c.startswith("|}")]
    if not cells:
        continue
    sn = re.search(r"\{\{sortname\|([^|]*)\|\s*([^|}]*)", cells[0])   # {{sortname|The| Cotswolds|…}}
    m = re.search(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", cells[0])
    if sn:
        name = f"{sn.group(1).strip()} {sn.group(2).strip()}"
    elif m:
        name = m.group(1).strip()
    else:
        continue
    vals = []
    for c in cells[3:]:
        x = re.sub(r"style=\"[^\"]*\"\|", "", c[1:]).replace("'", "").strip()
        vals.append(x)
    votes = {}
    for k, p in enumerate(PARTIES):
        v = vals[2 * k] if 2 * k < len(vals) else ""
        v = v.replace(",", "")
        votes[p] = int(v) if v.isdigit() else 0
    rows[norm(name)] = (name, votes)
ge = list(csv.reader(open(GE, encoding="utf-8")))
hdr = ge[0]
cols = hdr[5:]
out, miss = [hdr], []
ALIAS = {norm("Carmarthen West and South Pembrokeshire"): norm("Carmarthen West and Pembrokeshire South")}
for r in ge[1:]:
    key = ALIAS.get(norm(r[1]), norm(r[1]))
    if key in rows:
        _, v = rows[key]
        d = {c: 0 for c in cols}
        for p, n in v.items():
            d[MAP[p]] = d.get(MAP[p], 0) + n
        out.append(r[:4] + [sum(d.values())] + [d[c] for c in cols])
    else:
        if r[0] != "Northern Ireland":
            miss.append(r[1])
        out.append(r)
csv.writer(open(OUT, "w", newline="", encoding="utf-8")).writerows(out)
tot = {}
for r in out[1:]:
    for c, v in zip(cols, r[5:]):
        tot[c] = tot.get(c, 0) + int(v)
s = sum(tot.values())
print(f"維基表 {len(rows)} 選區；對不上的大不列顛選區 {len(miss)}：{miss[:8]}")
print("全英得票%：", {c: round(v * 100 / s, 1) for c, v in sorted(tot.items(), key=lambda x: -x[1]) if v})
