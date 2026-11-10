"""SERVEL 逐投票桌（眾議員 DIPUTADOS_DISTRITO_*.xlsx；總統 PRESIDENTE_*.xlsx）→ cl-YYYY.csv（逐投票所 local de votación）。
座標：Wikidata 智利市鎮（Q1840161）西文名稱對應。
Usage: build.py YEAR DIP_GLOB PRES_CHILE PRES_EXT GEO_CSV OUT_CSV"""
import collections, csv, glob, re, sys, unicodedata, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _xlsx as xlsx
Y, DG, PC, PE, GEO, OUT = sys.argv[1:7]
sys.stdout.reconfigure(encoding="utf-8")
norm = lambda s: re.sub(r" +", " ", re.sub(r"[^A-Z ]", " ", unicodedata.normalize("NFKD", (s or "").upper()).encode("ascii", "ignore").decode())).strip()
ALIAS = {"SAN VICENTE": "SAN VICENTE DE TAGUA TAGUA", "CABO DE HORNOS EX NAVARINO": "CABO DE HORNOS", "TREHUACO": "TREGUACO",
         "CALERA": "LA CALERA", "CAMARONES": "COMUNA DE CAMARONES", "AISEN": "AYSEN"}
CORE = {"COMUNISTA DE CHILE": "PC", "FRENTE AMPLIO": "FA", "REVOLUCION DEMOCRATICA": "FA", "CONVERGENCIA SOCIAL": "FA", "COMUNES": "FA",
        "PODER": "FA", "IGUALDAD": "IZQ", "DE TRABAJADORES REVOLUCIONARIOS": "IZQ", "UNION PATRIOTICA": "IZQ",
        "HUMANISTA": "HUM", "ACCION HUMANISTA": "HUM", "ECOLOGISTA VERDE": "PEV", "ALIANZA VERDE POPULAR": "PEV",
        "SOCIALISTA DE CHILE": "PS", "POR LA DEMOCRACIA": "PPD", "LIBERAL DE CHILE": "PL", "RADICAL DE CHILE": "PR",
        "RADICAL SOCIALDEMOCRATA": "PR", "DEMOCRATA CRISTIANO": "PDC", "PROGRESISTA": "PRO", "PAIS": "PRO",
        "FEDERACION REGIONALISTA VERDE SOCIAL": "FRVS", "DEMOCRATAS CHILE": "DEM", "CIUDADANOS": "DEM", "AMPLITUD": "DEM",
        "MOVIMIENTO AMARILLOS POR CHILE": "AMA", "DE LA GENTE": "PDG", "EVOLUCION POLITICA": "EVO", "RENOVACION NACIONAL": "RN",
        "UNION DEMOCRATA INDEPENDIENTE": "UDI", "REPUBLICANO DE CHILE": "REP", "REPUBLICANO": "REP", "SOCIAL CRISTIANO": "PSC",
        "CONSERVADOR CRISTIANO": "PSC", "NACIONAL LIBERTARIO": "PNL"}


def party_code(name):
    n = norm(name)
    if n.startswith("INDEPENDIENTE "):
        n = n[len("INDEPENDIENTE "):]
    if n.startswith("PARTIDO "):
        n = n[len("PARTIDO "):]
    return CORE.get(n, "其他")


CAND = {"JEANNETTE JARA": "PC", "JOSE ANTONIO KAST": "REP", "FRANCO PARISI": "PDG", "JOHANNES KAISER": "PNL", "EVELYN MATTHEI": "UDI",
        "MARCO ANTONIO ENRIQUEZ": "MEO", "HAROLD MAYNE": "HMN", "EDUARDO ARTES": "IZQ",
        # 2021
        "GABRIEL BORIC": "FA", "SEBASTIAN SICHEL": "RN", "YASNA PROVOSTE": "PDC", "MARCO ENRIQUEZ": "MEO"}
TOTALS = ("Total", "Votos Nulos", "Votos en Blanco", "Votos Nulos ", "Votos en Blanco ")
def cand_code(n):
    n = norm(n)
    for k, c in CAND.items():
        if norm(k) in n:
            return c
    return "其他"
def is_total(name):
    return name is None or str(name).startswith(("Total", "Votos", "VOTOS", "TOTAL"))
geo = {}
for r in csv.DictReader(open(GEO, encoding="utf-8")):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["coord"])
    if m:
        geo.setdefault(norm(r["l"]), (float(m.group(1)), float(m.group(2))))
units = collections.OrderedDict()
RAW = collections.Counter()
def key(region, comuna, local):
    return (region, comuna, str(local))
for f in sorted(glob.glob(DG)):
    rows, _ = xlsx.read(f, 1)
    h = [unicodedata.normalize("NFKD", str(c or "")).encode("ascii", "ignore").decode().strip().lower() for c in rows[0]]
    ix = {c: i for i, c in enumerate(h)}
    vcol = ix.get("votos_preliminares", ix.get("votos tricel", ix.get("votos")))
    if vcol is None: raise SystemExit(f"no vote column in {f}: {h}")
    for r in rows[1:]:
        if not r or len(r) <= vcol: continue
        name = r[ix.get("nombre_candidato", ix.get("candidato", 0))]
        if is_total(name): continue
        k = key(r[ix["region"]], r[ix["comuna"]], r[ix.get("cod_local_votacion", ix.get("local", 0))])
        u = units.setdefault(k, {"C": collections.Counter(), "P": collections.Counter(), "dist": r[ix["distrito"]]})
        RAW[(r[ix["partido"]] or "").strip()] += int(float(r[vcol] or 0))
        p = (r[ix["partido"]] or "").strip()
        u["C"][party_code(p)] += int(float(r[vcol] or 0))
for f in (PC, PE):
    if not f or f == "-": continue
    rows, _ = xlsx.read(f, 1)
    h = [unicodedata.normalize("NFKD", str(c or "")).encode("ascii", "ignore").decode().strip().lower() for c in rows[0]]
    ix = {c: i for i, c in enumerate(h)}
    vcol = ix.get("votos_preliminares", ix.get("votos tricel", ix.get("votos")))
    if vcol is None: raise SystemExit(f"no vote column in {f}: {h}")
    ext = "continente" in ix
    for r in rows[1:]:
        if not r or len(r) <= vcol: continue
        name = r[ix.get("nombre_candidato", ix.get("candidato", 0))]
        if is_total(name): continue
        if ext:
            k = ("海外", r[ix["pais"]], r[ix["cod_local_votacion"]])
        else:
            k = key(r[ix["region"]], r[ix["comuna"]], r[ix.get("cod_local_votacion", ix.get("local", 0))])
        u = units.setdefault(k, {"C": collections.Counter(), "P": collections.Counter(), "dist": r[ix["distrito"]] if "distrito" in ix else ""})
        u["P"][cand_code(name)] += int(float(r[vcol] or 0))
CC = sorted({c for u in units.values() for c in u["C"]} - {"其他"}) + ["其他"]
PCo = sorted({c for u in units.values() for c in u["P"]} - {"其他"}) + ["其他"]
rows, miss = [], set()
for (reg, com, loc), u in units.items():
    if reg == "海外":
        xy = (0.0, 0.0)
    else:
        n = norm(com); n = ALIAS.get(n, n)
        xy = geo.get(n)
        if not xy:
            miss.add(com); xy = (0.0, 0.0)
    rows.append([reg, u["dist"], com, loc, f"{xy[0]:.4f}", f"{xy[1]:.4f}", sum(u["C"].values())] + [u["C"].get(c, 0) for c in CC]
                + [sum(u["P"].values())] + [u["P"].get(c, 0) for c in PCo])
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["大區", "眾議員選區", "市鎮", "投票所", "經度", "緯度", "國會有效票"] + ["C_" + c for c in CC] + ["總統有效票"] + ["P_" + c for c in PCo])
    w.writerows(rows)
tc, tp = collections.Counter(), collections.Counter()
for u in units.values():
    tc.update(u["C"]); tp.update(u["P"])
sc, sp = sum(tc.values()), sum(tp.values())
print(Y, len(rows), "投票所；無座標市鎮", sorted(miss))
if "--raw" in sys.argv:
    for k, v in RAW.most_common(): print(v, k, "->", party_code(k))
print("國會", {c: round(tc[c] * 100 / sc, 2) for c, _ in tc.most_common()}, sc)
print("總統", {c: round(tp[c] * 100 / sp, 2) for c, _ in tp.most_common()}, sp)
