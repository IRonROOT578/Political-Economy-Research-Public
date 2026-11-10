"""由 DINE 2023 大選逐投票桌暫定開票（ResultadoElectorales_2023_Generales.csv）彙整國會眾議員票到「選區（circuito）」。

    python -I _build_circ.py <ResultadoElectorales_2023_Generales.csv>   # 輸出 circ-2023.csv

來源：datos.gob.ar「Resultados provisionales de las Elecciones 2023」（Dirección Nacional Electoral），
2023_generales_1.zip。只取 cargo＝DIPUTADO NACIONAL、votos_tipo＝POSITIVO（有效票）。
各省的聯盟改名（例：CAMBIA MENDOZA＝變革聯盟在門多薩的名單）併回全國聯盟；
省級政黨保留原名（只在本省出現），零星名單併入「其他」。
"""
import csv
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

PROV = {
    "Buenos Aires": "布宜諾斯艾利斯省", "Ciudad Autónoma de Buenos Aires": "布宜諾斯艾利斯自治市", "Córdoba": "科多瓦",
    "Santa Fe": "聖大非", "Mendoza": "門多薩", "Tucumán": "圖庫曼", "Salta": "薩爾塔", "Entre Ríos": "恩特雷里奧斯",
    "Misiones": "米西奧內斯", "Corrientes": "科連特斯", "Chaco": "查科", "Santiago del Estero": "聖地亞哥-德埃斯特羅",
    "San Juan": "聖胡安", "Jujuy": "胡胡伊", "Río Negro": "里奧內格羅", "Neuquén": "內烏肯", "Formosa": "福莫薩",
    "Chubut": "丘布特", "San Luis": "聖路易斯", "Catamarca": "卡塔馬卡", "La Rioja": "拉里奥哈", "La Pampa": "拉潘帕",
    "Santa Cruz": "聖克魯斯", "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "火地島",
}
BLOC = {
    "UNION POR LA PATRIA": "祖國聯盟", "FRENTE CIVICO POR SANTIAGO": "祖國聯盟", "MAS PARA ENTRE RIOS": "祖國聯盟",
    "LA LIBERTAD AVANZA": "自由前進",
    "JUNTOS POR EL CAMBIO": "變革聯盟", "CAMBIA MENDOZA": "變革聯盟", "JUNTOS POR ENTRE RIOS": "變革聯盟",
    "ENCUENTRO POR CORRIENTES - ECO+VAMOS CORRIENTES": "變革聯盟", "CAMBIA JUJUY": "變革聯盟",
    "JUNTOS POR EL CAMBIO CHUBUT": "變革聯盟", "JUNTOS POR EL CAMBIO LA PAMPA": "變革聯盟",
    "JUNTOS POR EL CAMBIO TDF": "變革聯盟", "CAMBIA SANTA CRUZ": "變革聯盟",
    "HACEMOS POR NUESTRO PAIS": "為我國做事", "HACEMOS POR NUESTRO PAÍS": "為我國做事",
    "FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD": "工人左翼",
}
LOCAL_MIN = 0.05   # 省級政黨：本省得票 ≥5% 才保留原名，否則併入「其他」


def main(src):
    agg = defaultdict(Counter)
    prov_tot = defaultdict(Counter)
    with open(src, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["cargo_nombre"] != "DIPUTADO NACIONAL" or row["votos_tipo"] != "POSITIVO":
                continue
            p = PROV[row["distrito_nombre"]]
            k = (p, int(row["seccion_id"] or 0), row["seccion_nombre"], row["circuito_id"])
            v = int(row["votos_cantidad"] or 0)
            agg[k][row["agrupacion_nombre"]] += v
            prov_tot[p][row["agrupacion_nombre"]] += v

    def label(prov, name):
        if name in BLOC:
            return BLOC[name]
        s = sum(prov_tot[prov].values()) or 1
        short = name.split(" - ")[0].replace("FRENTE ", "").title()
        return f"地方:{short}" if prov_tot[prov][name] / s >= LOCAL_MIN else "其他"

    rows, cols = [], Counter()
    for (p, sid, sname, cid), c in sorted(agg.items()):
        d = Counter()
        for n, v in c.items():
            d[label(p, n)] += v
        cols.update(d)
        rows.append((p, sid, sname, cid, d))
    names = [n for n, _ in cols.most_common()]
    with open(os.path.join(HERE, "circ-2023.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["province", "seccion_id", "seccion", "circuito"] + names)
        for p, sid, sname, cid, d in rows:
            w.writerow([p, sid, sname, cid] + [d.get(n, 0) for n in names])
    tot = sum(cols.values())
    sys.stdout.reconfigure(encoding="utf-8")
    print("選區數", len(rows), "有效票", tot)
    for n, v in cols.most_common():
        print(f"{100 * v / tot:6.2f} {n}")


if __name__ == "__main__":
    main(sys.argv[1])
