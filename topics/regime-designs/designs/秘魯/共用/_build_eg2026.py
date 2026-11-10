"""秘魯 2026：ONPE 結果網站擋自動存取，只有維基的全國眾議院得票與各省總統第一輪。
推估逐單位國會票：每個 2026 政黨沿用 2021 年「母黨」的單位分布（省內差異），
用 2026 各省總統第一輪調整省級總量（有省別資料的 7 黨），最後縮放到 2026 全國眾議院得票。
Usage: build2026.py EG2021_CSV WIKI OUT_CSV"""
import collections, csv, re, sys
SRC, WIKI, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
# 2026 眾議院全國得票（維基 Chamber of Deputies 模板）
NAT = {"FP": 2114389, "RP": 1593041, "JP": 1553154, "PBG": 1509987, "AN": 1224556, "OBRAS": 1199888, "PPT": 838901,
       "PLG": 434740, "APP": 401468, "Pod": 379812, "SP": 308218, "FREPAP": 272759, "APRA": 268803}
_t = open(WIKI, encoding="utf-8").read()
_s = _t.index("==== Chamber of Deputies ====")
OTHER = sum(int(x) for x in re.findall(r"\|votes\d+=(\d+)", _t[_s:_t.index("|invalid", _s)])) - sum(NAT.values())  # 其餘 24 黨合計
PARENT = {"FP": ["FP"], "RP": ["RP"], "JP": ["JP", "PL"], "PBG": ["PM", "AP"], "AN": ["PL"], "OBRAS": ["Pod"], "PPT": ["SP"],
          "PLG": ["PM"], "APP": ["APP"], "Pod": ["Pod"], "SP": ["SP"], "FREPAP": ["FREPAP"], "APRA": ["其他"], "其他": ["其他", "UPP", "PNP", "FA", "PPC", "VN", "AvP"]}
DEPT_COLS = ["FP", "JP", "RP", "PBG", "OBRAS", "PPT", "AN", "其他"]
t = open(WIKI, encoding="utf-8").read()
i = t.index("==== By department ===="); j = t.index("|}", i)
dept = {}
for blk in t[i:j].split("\n|-")[1:]:
    m = re.search(r"scope=\"row\" \| \[\[(?:[^|\]]*\|)?([^\]]+)\]\]", blk)
    if not m: continue
    name = m.group(1).upper().replace("Á", "A").replace("Í", "I").replace("Ú", "U").replace("Ó", "O").replace("É", "E")
    nums = [int(x.replace(",", "")) for x in re.findall(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?![\d.%])", blk.split("\n", 1)[1]) ]
    vals = []
    for line in blk.split("\n")[1:]:
        v = re.findall(r"'''([\d,]+)'''|^\|\s*([\d,]+)\s*$", line.strip())
        mm = re.search(r"([\d,]+)'''?\}?\}?\s*$", line.strip())
        if "%" in line: continue
        x = re.sub(r"[^\d,]", "", line.split("|")[-1]) if "|" in line else ""
        if x.replace(",", "").isdigit():
            vals.append(int(x.replace(",", "")))
    dept[name] = dict(zip(DEPT_COLS, vals[:8]))
rows = list(csv.reader(open(SRC, encoding="utf-8")))
h, rows = rows[0], rows[1:]
ci = {c[2:]: k for k, c in enumerate(h) if c.startswith("C_")}
def dep_key(d):
    return {"LIMA": "LIMA"}.get(d, d)
# 省級：每黨 2026 各省總統票 ／ 母黨 2021 該省國會票
par = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    for p, ps in PARENT.items():
        par[r[1]][p] += sum(int(r[ci[q]]) for q in ps if q in ci)
miss = set()
units = []
for r in rows:
    d = r[1]
    v = {}
    for p, ps in PARENT.items():
        base = sum(int(r[ci[q]]) for q in ps if q in ci)
        f = 1.0
        if p in DEPT_COLS and r[0] != "海外":
            dd = dept.get(d) or dept.get(d.replace(" ", ""))
            if dd and par[d][p]:
                f = dd.get(p, 0) / par[d][p]
            elif not dd:
                miss.add(d)
        v[p] = base * f
    units.append((r, v))
tot = collections.Counter()
for _, v in units:
    tot.update(v)
NAT["其他"] = OTHER
k = {p: NAT[p] / tot[p] if tot[p] else 0 for p in NAT}
cols = list(NAT)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(h[:6] + ["國會有效票"] + ["C_" + c for c in cols])
    for r, v in units:
        vals = [round(v[c] * k[c]) for c in cols]
        w.writerow(r[:6] + [sum(vals)] + vals)
print("depts parsed", len(dept), "missing", sorted(miss)); print(list(dept.items())[:2])
