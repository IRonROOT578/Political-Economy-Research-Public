"""愛沙尼亞 2019 國會逐投票所名單票 → 資料/rk-2019.csv。

    python _build_ee2019.py <頁面目錄> <ehak.csv> 資料/rk-2019.csv

- 來源：國家選舉委員會 rk2019.valimised.ee 的「Detailne hääletamistulemus」網頁表格
  （district-<n>、county-<EHAK>、local-municipality-<EHAK>-voting-result.html；開放資料平台沒有 2019）。
- 2019 年網路票按選民所屬投票所（J<n>E）公布：投票所的票＝紙本 J<n>P＋網路 J<n>E，**不需推估**。
- 每黨用「Nimekiri kokku」（名單合計）列；選區由選區頁 → 縣頁 → 市鎮頁的連結決定。
"""
import csv
import glob
import html
import os
import re
import sys

PDIR, GEO, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
PARTY = {"Eesti Reformierakond": "RE", "Eesti Keskerakond": "KESK", "Eesti Konservatiivne Rahvaerakond": "EKRE",
         "Isamaa Erakond": "IE", "Sotsiaaldemokraatlik Erakond": "SDE", "Erakond Eesti 200": "E200",
         "Erakond Eestimaa Rohelised": "EER", "Eestimaa Ühendatud Vasakpartei": "EÜVP"}
DIST = {1: "塔林一", 2: "塔林二", 3: "塔林三", 4: "哈留－拉普拉", 5: "三島", 6: "西維魯", 7: "東維魯",
        8: "耶爾瓦－維爾揚迪", 9: "約蓋瓦－塔爾圖縣", 10: "塔爾圖市", 11: "東南", 12: "派爾努"}
BYNAME = {"Antsla vald": (26.5333, 57.8333), "Põhja-Pärnumaa vald": (24.8333, 58.6667), "Tori vald": (24.8242, 58.4789),
          "Valga vald": (26.2, 57.8), "Kiili vald": (24.84, 59.31), "Märjamaa vald": (24.42, 58.90),
          "Narva-Jõesuu linn": (28.04, 59.46), "Saku vald": (24.66, 59.30), "Saue vald": (24.55, 59.32), "Sillamäe linn": (27.76, 59.40)}
geo = {}
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m:
        geo[r["e"]] = (float(m.group(1)), float(m.group(2)))
read = lambda f: html.unescape(open(os.path.join(PDIR, f), encoding="utf-8").read())
links = lambda t, kind: re.findall(rf'href="({kind}-(\d+)-voting-result\.html)"', t)
dist_of = {}
for d in range(1, 13):
    t = read(f"district-{d}.html")
    for f, code in links(t, "local-municipality"):
        dist_of.setdefault(code, d)
    for f, code in links(t, "county"):
        if os.path.exists(os.path.join(PDIR, f)):
            for g, mc in links(read(f), "local-municipality"):
                dist_of.setdefault(mc, d)
cols = sorted(set(PARTY.values())) + ["其他"]
rows, tot, miss = [], {}, []
cell = lambda r: [re.sub(r"<[^>]+>|\s+", " ", x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
for fn in sorted(glob.glob(os.path.join(PDIR, "local-municipality-*-voting-result.html"))):
    code = re.search(r"local-municipality-(\d+)-", fn).group(1)
    t = html.unescape(open(fn, encoding="utf-8").read())
    name = re.findall(r"<h\d[^>]*>(.*?)</h\d>", t, re.S)[1].strip()
    trs = [cell(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
    hdr = next(r for r in trs if r and r[0] == "Reg nr")
    st = [h for h in hdr[5:] if re.fullmatch(r"J\d+P", h)]
    idx = {h: i - 1 for i, h in enumerate(hdr)}          # 「Nimekiri kokku」列少一欄（沒有姓名欄）
    v = {s: {c: 0 for c in cols} for s in st}
    cur = None
    for r in trs:
        if len(r) == 1 and r[0]:
            cur = PARTY.get(r[0], "其他")
        elif r and r[0] == "Nimekiri kokku" and cur:
            for s in st:
                p = r[idx[s]] if idx[s] < len(r) else ""
                e = r[idx[s] + 1] if idx[s] + 1 < len(r) else ""
                v[s][cur] += int(p or 0) + int(e or 0)
            cur = None
    if code not in dist_of:
        miss.append(name)
        continue
    x, y = geo.get(code) or BYNAME.get(name, (0.0, 0.0))
    if (x, y) == (0.0, 0.0):
        miss.append("座標 " + name)
    for s in st:
        for k, n in v[s].items():
            tot[k] = tot.get(k, 0) + n
        rows.append([DIST[dist_of[code]], name, int(s[1:-1]), f"{x:.4f}", f"{y:.4f}", sum(v[s].values())] + [v[s][c] for c in cols])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "市鎮", "投票所", "經度", "緯度", "有效票"] + cols)
    w.writerows(rows)
s = sum(tot.values())
print(len(rows), "投票所；有效票", s, {k: round(n * 100 / s, 2) for k, n in sorted(tot.items(), key=lambda x: -x[1])})
print("對不上：", miss)
