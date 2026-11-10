"""拉脫維亞 2022 國會（14. Saeima）逐投票所名單票 → 資料/lv-2022.csv。

    python _build_lv.py <departments.json> <departmentresults.json> <muni.csv> 資料/lv-2022.csv

- 來源：data.gov.lv 開放資料「14. Saeimas vēlēšanas sv2022」（中央選舉委員會 CVK）；1,055 個投票所＋海外（Ārzemes）。
- 座標：Wikidata 市鎮／直轄市中心點（以拉脫維亞文名稱對應）；同一市鎮內依投票所編號排序。
- 黨代碼見 PARTY；其餘併入「其他」。
"""
import csv
import json
import re
import sys

DEP, RES, GEO, OUT = sys.argv[1:5]
sys.stdout.reconfigure(encoding="utf-8")
PARTY = {"jauna-vienotiba": "JV", "zalo-un-zemnieku-savieniba": "ZZS", "apvienotais-saraksts": "AS",
         "nacionala-apvieniba": "NA", "stabilitatei": "S!", "latvija-pirmaja-vieta": "LPV", "progresivie": "PRO",
         "attistibai-par": "AP", "saskana": "SDPS", "katram-un-katrai": "KuK", "latvijas-krievu-savieniba": "LKS",
         "suverena-vara": "SV", "republika": "Rep", "mes-mainam-noteikumus": "MMN"}
REGION = {"riga": "里加", "vidzeme": "維澤梅", "latgale": "拉特加萊", "kurzeme": "庫爾澤梅", "zemgale": "澤姆加萊"}
dep = {d["Id"]: d for d in json.load(open(DEP, encoding="utf-8-sig"))}
geo = {}
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m:
        geo[r["l"]] = (float(m.group(1)), float(m.group(2)))


def code(lid):
    lid = re.sub(r"^politiska-partija-", "", lid)
    for k, v in PARTY.items():
        if lid.startswith(k):
            return v
    return {"konservativie": "K"}.get(lid, "其他")


cols = sorted(set(PARTY.values()) | {"K"}) + ["其他"]
rows, tot, unknown = [], {}, {}
for r in json.load(open(RES, encoding="utf-8-sig")):
    d = r["Department"]
    if d["Type"] != 3:
        continue
    muni = dep[d["ParentId"]]
    reg = "海外" if muni["Id"] == "arzemes" else REGION[muni["ParentId"]]
    x, y = geo.get(muni["Name"], (0.0, 0.0))
    v = {c: 0 for c in cols}
    for c in r["CandidateLists"]:
        k = code(c["Id"])
        if k == "其他":
            unknown[c["Id"]] = unknown.get(c["Id"], 0) + c["ValidMarkCount"]["Count"]
        v[k] += c["ValidMarkCount"]["Count"]
    for k, n in v.items():
        tot[k] = tot.get(k, 0) + n
    rows.append([reg, muni["Name"], d["Number"], f"{x:.4f}", f"{y:.4f}", sum(v.values())] + [v[c] for c in cols])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "市鎮", "投票所", "經度", "緯度", "有效票"] + cols)
    w.writerows(rows)
s = sum(tot.values())
print(len(rows), "投票所；有效票", s)
print({k: round(v * 100 / s, 2) for k, v in sorted(tot.items(), key=lambda x: -x[1])})
print("併入其他：", {k: v for k, v in sorted(unknown.items(), key=lambda x: -x[1])})
