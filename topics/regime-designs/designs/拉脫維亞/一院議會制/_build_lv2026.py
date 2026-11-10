"""拉脫維亞 2026 國會（15. Saeima）→ 資料/lv-2026.csv（**推估**）。

    python _build_lv2026.py <latest.json> 資料/lv-2022.csv 資料/lv-2026.csv

- 中央選舉委員會（cvk.lv/data/rezultati/latest.json，2026-10-16 最終）只公布 5 個選區的政黨得票，沒有逐投票所。
- 做法：以 2022 逐投票所為地理基礎；每個 2026 政黨沿用 2022 母黨（CODE）在該選區內的投票所分布，
  縮放到該黨 2026 年的選區得票（選區總數與官方完全一致；選區內分布是推估）。海外票併入里加（同官方）。
"""
import csv
import json
import sys

LATEST, BASE, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
# 2026 簡稱 → (本模型代碼, 2022 母黨代碼)
CODE = {"AS": ("AS", "AS"), "LP": ("LPV", "LPV"), "SV": ("SV", "SV"), "NA": ("NA", "NA"), "PR": ("PRO", "PRO"),
        "JV": ("JV", "JV"), "ZU": ("ZZS", "ZZS"), "MM": ("MMN", "其他"), "LA": ("AP", "AP"), "ST": ("S!", "S!"),
        "AS12": ("ASL", "其他"), "GS": ("GS", "KuK"), "PP": ("SDPS", "SDPS"), "JJ": ("K", "K")}
DIST = {"riga": "里加", "vidzeme": "維澤梅", "latgale": "拉特加萊", "kurzeme": "庫爾澤梅", "zemgale": "澤姆加萊"}
d = json.load(open(LATEST, encoding="utf-8"))
v26 = {DIST[x["id"]]: {CODE[p["short"]][0]: p["votes"] for p in x["parties"]} for x in d["districts"]}
parent = {c: q for c, q in CODE.values()}
rows = list(csv.reader(open(BASE, encoding="utf-8")))
hdr, rows = rows[0], rows[1:]
cols = hdr[6:]
dist_of = lambda r: "里加" if r[0] == "海外" else r[0]
base = {}
for r in rows:
    for c, v in zip(cols, r[6:]):
        base.setdefault(dist_of(r), {}).setdefault(c, 0)
        base[dist_of(r)][c] += int(v)
newcols = sorted(parent)
out = []
for r in rows:
    dd = dist_of(r)
    v = dict(zip(cols, map(int, r[6:])))
    tot_u = sum(v.values())
    tot_d = sum(base[dd].values())
    new = {}
    for c in newcols:
        q = parent[c]
        target = v26[dd].get(c, 0)
        # 同一母黨被多個 2026 政黨共用時（其他），各自用母黨分布縮放
        new[c] = target * (v.get(q, 0) / base[dd][q] if base[dd].get(q) else tot_u / tot_d)
    out.append(r[:5] + [round(sum(new.values()))] + [round(new[c]) for c in newcols])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(hdr[:6] + newcols)
    w.writerows(out)
chk = {}
for r in out:
    for c, x in zip(newcols, r[6:]):
        chk[c] = chk.get(c, 0) + int(x)
s = sum(chk.values())
print("2026 推估：有效票", s, {c: round(v * 100 / s, 2) for c, v in sorted(chk.items(), key=lambda x: -x[1])})
