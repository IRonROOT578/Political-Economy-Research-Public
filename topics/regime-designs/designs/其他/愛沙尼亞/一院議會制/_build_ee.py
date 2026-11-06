"""愛沙尼亞 2023 國會（Riigikogu）逐投票所名單票 → 資料/rk-2023.csv。

    python _build_ee.py <parish 目錄> <POLLING_STATION_LOCATIONS_en.csv> <ehak.csv> <RESULTS.xml> 資料/rk-2023.csv

- 來源：國家選舉委員會開放資料 opendata.valimised.ee/api/RK_2023/ 的 VOTING_RESULT_IN_PARISH_<EHAK>.xml
  （每個市鎮／塔林市區一檔；欄位 K＝合計、P＝紙本、E＝網路、J<n>＝第 n 號投票所的紙本票）。
- **網路票只公布到市鎮層級**：每黨在該市鎮的網路票，依該黨在各投票所的紙本票比例分回投票所
  （該黨在市鎮內紙本 0 票時，依投票所紙本總票比例）。投票所的票＝紙本＋分回的網路票（推估）。
- 市鎮檔合計比官方選區合計少約 4%（不歸屬市鎮的票：海外、外地提前投票等）：每黨在每個選區的差額
  （官方＝RESULTS.xml 候選人得票依選區加總）依該黨在選區內各投票所的票比例補上；選區×政黨總數與官方一致。
- 選區：投票所位置檔的「Municipality or city district → Electoral district」。座標：Wikidata EHAK 代碼（P1140）。
"""
import csv
import glob
import os
import re
import sys

PDIR, LOC, GEO, RES, OUT = sys.argv[1:6]
sys.stdout.reconfigure(encoding="utf-8")
PARTY = {"REF": "RE", "EKRE": "EKRE", "KESK": "KESK", "EE200": "E200", "SDE": "SDE", "IE": "IE",
         "PP": "PP", "ROH": "EER", "EÜVP": "EÜVP"}
DIST = {1: "塔林一", 2: "塔林二", 3: "塔林三", 4: "哈留－拉普拉", 5: "三島", 6: "西維魯", 7: "東維魯",
        8: "耶爾瓦－維爾揚迪", 9: "約蓋瓦－塔爾圖縣", 10: "塔爾圖市", 11: "東南", 12: "派爾努"}
dist_of = {}
for r in csv.DictReader(open(LOC, encoding="utf-8-sig"), delimiter=";"):
    m = re.search(r"nr (\d+)", r["Electoral district"])
    dist_of[r["Municipality or city district"]] = int(m.group(1))
geo = {}
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m:
        geo[r["e"]] = (float(m.group(1)), float(m.group(2)))
# 2017 年合併後 EHAK 碼變動、Wikidata 未更新的 4 個市鎮：以名稱查 Wikidata 的座標
BYNAME = {"Antsla vald": (26.5333, 57.8333), "Põhja-Pärnumaa vald": (24.8333, 58.6667), "Tori vald": (24.8242, 58.4789),
          "Valga vald": (26.2, 57.8)}
rows, tot, miss, codes = [], {}, [], set()
for fn in sorted(glob.glob(os.path.join(PDIR, "VOTING_RESULT_IN_PARISH_*.xml"))):
    t = open(fn, encoding="utf-8").read()
    name = re.search(r"<adminUnitName>(.*?)</adminUnitName>", t).group(1)
    ehak = re.search(r"<ehakCode>(.*?)</ehakCode>", t).group(1)
    if name not in dist_of:
        miss.append(name)
        continue
    party = {}
    for blk in re.findall(r"<party>(.*?)</party>", t, re.S):
        code = re.search(r"<partyCode>(.*?)</partyCode>", blk).group(1)
        codes.add(code)
        k = PARTY.get(code, "其他")
        d = party.setdefault(k, {})
        own = re.sub(r"<candidates>.*?</candidates>", "", blk, flags=re.S)   # 只取政黨列，不加候選人列
        for nm, v in re.findall(r"<name>(\w+)</name>\s*<value>(\d+)</value>", own):
            d[nm] = d.get(nm, 0) + int(v)
    stations = sorted({c for d in party.values() for c in d if c.startswith("J")}, key=lambda c: int(c[1:]))
    paper_tot = {s: sum(d.get(s, 0) for d in party.values()) for s in stations}
    ptot = sum(paper_tot.values())
    x, y = geo.get(ehak) or BYNAME.get(name, (0.0, 0.0))
    if (x, y) == (0.0, 0.0):
        miss.append("座標 " + name)
    cols = sorted(set(PARTY.values())) + ["其他"]
    for s in stations:
        v = {}
        for k in cols:
            d = party.get(k, {})
            paper = d.get(s, 0)
            e = d.get("E", 0)
            p_all = sum(d.get(z, 0) for z in stations)
            share = paper / p_all if p_all else (paper_tot[s] / ptot if ptot else 0)
            v[k] = paper + e * share
        for k, n in v.items():
            tot[k] = tot.get(k, 0) + n
        rows.append([DIST[dist_of[name]], name, int(s[1:]), f"{x:.4f}", f"{y:.4f}", round(sum(v.values()))] + [round(v[k]) for k in cols])
# 補上不歸屬市鎮的票：選區×政黨 對齊官方
r = open(RES, encoding="utf-8").read()
code_of = {}
off = {}
for blk in re.findall(r"<party>(.*?)</party>", r[:r.find("</votesAndMandates>")], re.S):
    k = PARTY.get(re.search(r"<code>(.*?)</code>", blk).group(1), "其他")
    for v, dn in re.findall(r"<votes>(\d+)</votes>.*?<districtNumber>(\d+)</districtNumber>", re.sub(r"^.*?<candidates>", "", blk, flags=re.S), re.S):
        off[(DIST[int(dn)], k)] = off.get((DIST[int(dn)], k), 0) + int(v)
cols = sorted(set(PARTY.values())) + ["其他"]
mine = {}
for row in rows:
    for k, v in zip(cols, row[6:]):
        mine[(row[0], k)] = mine.get((row[0], k), 0) + v
for row in rows:
    for i, k in enumerate(cols):
        m = mine.get((row[0], k), 0)
        if m:
            row[6 + i] = round(row[6 + i] * off.get((row[0], k), m) / m)
    row[5] = sum(row[6:])
tot = {}
for row in rows:
    for k, v in zip(cols, row[6:]):
        tot[k] = tot.get(k, 0) + v
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "市鎮", "投票所", "經度", "緯度", "有效票"] + cols)
    w.writerows(rows)
s = sum(tot.values())
print(len(rows), "投票所；有效票", round(s), "；黨代碼", sorted(codes))
print({k: round(v * 100 / s, 2) for k, v in sorted(tot.items(), key=lambda x: -x[1])})
print("對不上：", miss)
print("官方：", re.findall(r"<code>(\w+)</code>\s*<votes>(\d+)</votes>", r[:r.find("</votesAndMandates>")]))
