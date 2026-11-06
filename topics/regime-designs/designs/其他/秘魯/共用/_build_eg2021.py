"""ONPE 2021 逐投票桌（datosabiertos.gob.pe：EG2021_Congresal.csv、Resultados por mesa EG2021.csv）→ eg-2021.csv。
單位＝同一區（UBIGEO，RENIEC 碼）內依投票桌號每 25 桌合併；座標＝ubigeo_distrito.csv（jmcastagnetto/ubigeo-peru-aumentado，reniec 欄）。
國會名單票（C_ 欄）與總統第一輪票（P_ 欄）放在同一列。只計已計入的投票桌（CONTABILIZADA、COMPUTADA RESUELTA、ACTA RESUELTA）。
Usage: build.py CONG_CSV PRES_CSV GEO_CSV OUT_CSV"""
import collections, csv, sys
CONG, PRES, GEO, OUT = sys.argv[1:5]
sys.stdout.reconfigure(encoding="utf-8")
OK = {"CONTABILIZADA", "COMPUTADA RESUELTA", "ACTA RESUELTA", "ACTA ELECTORAL NORMAL", "ACTA ELECTORAL RESUELTA"}
PARTY = {"PARTIDO POLITICO NACIONAL PERU LIBRE": "PL", "FUERZA POPULAR": "FP", "RENOVACION POPULAR": "RP", "ACCION POPULAR": "AP",
         "ALIANZA PARA EL PROGRESO": "APP", "AVANZA PAIS - PARTIDO DE INTEGRACION SOCIAL": "AvP", "JUNTOS POR EL PERU": "JP",
         "PARTIDO DEMOCRATICO SOMOS PERU": "SP", "PODEMOS PERU": "Pod", "PARTIDO MORADO": "PM", "VICTORIA NACIONAL": "VN",
         "FRENTE POPULAR AGRICOLA FIA DEL PERU - FREPAP": "FREPAP", "UNION POR EL PERU": "UPP", "PARTIDO POPULAR CRISTIANO - PPC": "PPC",
         "PARTIDO NACIONALISTA PERUANO": "PNP", "EL FRENTE AMPLIO POR JUSTICIA, VIDA Y LIBERTAD": "FA"}
PRES_COL = ["PNP", "FA", "PM", "其他", "VN", "AP", "AvP", "Pod", "JP", "PPC", "FP", "UPP", "RP", "其他", "SP", "PL", "其他", "APP"]
NORTE_ESTE = {"ANCON", "CARABAYLLO", "COMAS", "INDEPENDENCIA", "LOS OLIVOS", "PUENTE PIEDRA", "SAN MARTIN DE PORRES", "SANTA ROSA",
              "ATE", "CHACLACAYO", "CIENEGUILLA", "EL AGUSTINO", "LURIGANCHO", "SAN JUAN DE LURIGANCHO", "SANTA ANITA", "LA MOLINA"}
REG = {}
for d in ("TUMBES", "PIURA", "LAMBAYEQUE", "LA LIBERTAD", "CAJAMARCA", "AMAZONAS", "SAN MARTIN"): REG[d] = "北部"
for d in ("ANCASH", "HUANUCO", "PASCO", "JUNIN", "HUANCAVELICA", "ICA", "LORETO", "UCAYALI"): REG[d] = "中部與亞馬遜"
for d in ("AREQUIPA", "MOQUEGUA", "TACNA", "PUNO", "CUSCO", "APURIMAC", "AYACUCHO", "MADRE DE DIOS"): REG[d] = "南部"
def region(dep, prov, dist, ub):
    if ub.startswith("9"): return "海外"
    if dep == "CALLAO": return "利馬北東－卡亞俄"
    if dep == "LIMA":
        if prov != "LIMA": return "中部與亞馬遜"
        return "利馬北東－卡亞俄" if dist in NORTE_ESTE else "利馬中南"
    return REG[dep]
geo = {r["reniec"]: (float(r["longitude"]), float(r["latitude"])) for r in csv.DictReader(open(GEO, encoding="utf-8")) if r["latitude"] not in ("", "NA")}
meta, cong, pres = {}, collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
for r in csv.reader(open(CONG, encoding="latin1"), delimiter=";"):
    if r[0] == "UBIGEO" or r[6] not in OK:
        continue
    k = (r[0], r[5]); meta[k] = (r[1], r[2], r[3])
    nm = r[10]
    if nm in ("VOTOS NULOS", "VOTOS EN BLANCO", "VOTOS IMPUGNADOS"):
        continue
    cong[k][PARTY.get(nm, "其他")] += int(r[11] or 0)
for r in csv.reader(open(PRES, encoding="latin1"), delimiter=";"):
    if r[0] == "UBIGEO" or r[6].strip() not in OK:
        continue
    k = (r[0], r[5]); meta.setdefault(k, (r[1], r[2], r[3]))
    for j, p in enumerate(PRES_COL):
        x = r[10 + j].strip()
        pres[k][p] += int(x) if x.isdigit() else 0
by = collections.defaultdict(list)
for k in meta:
    by[k[0]].append(k[1])
CC = sorted(set(PARTY.values())) + ["其他"]
PC = sorted(set(PRES_COL) - {"其他"}) + ["其他"]
rows, miss = [], set()
for ub in sorted(by):
    ms = sorted(by[ub])
    dep, prov, dist = meta[(ub, ms[0])]
    reg = region(dep, prov, dist, ub)
    xy = geo.get(ub)
    if not xy and reg != "海外":
        miss.add(ub)
    xy = xy or (0.0, 0.0)
    for b in range(0, len(ms), 25):
        c, p = collections.Counter(), collections.Counter()
        for m in ms[b:b + 25]:
            c.update(cong.get((ub, m), {})); p.update(pres.get((ub, m), {}))
        if not sum(c.values()) and not sum(p.values()):
            continue
        rows.append([reg, dep, ub, b // 25, f"{xy[0]:.4f}", f"{xy[1]:.4f}", sum(c.values())] + [c.get(x, 0) for x in CC] + [sum(p.values())] + [p.get(x, 0) for x in PC])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["區", "省", "UBIGEO", "塊", "經度", "緯度", "國會有效票"] + ["C_" + x for x in CC] + ["總統有效票"] + ["P_" + x for x in PC])
    w.writerows(rows)
tc, tp, rg = collections.Counter(), collections.Counter(), collections.Counter()
for r in rows:
    rg[r[0]] += r[6]
    for x, n in zip(CC, r[7:7 + len(CC)]): tc[x] += n
    for x, n in zip(PC, r[8 + len(CC):]): tp[x] += n
sc, sp = sum(tc.values()), sum(tp.values())
print(len(rows), "單位；無座標區", len(miss), sorted(miss)[:5])
print("國會", {x: round(tc[x] * 100 / sc, 2) for x, _ in tc.most_common()}, sc)
print("總統", {x: round(tp[x] * 100 / sp, 2) for x, _ in tp.most_common()}, sp)
print(dict(rg))
