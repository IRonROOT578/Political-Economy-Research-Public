# -*- coding: utf-8 -*-
"""從 btw25_kerg2.csv 抽出 Wahlkreis 級 Zweitstimme → 資料/bt-2025.csv

欄位：land_code,land,wk_nr,wk_name,valid,SPD,CDU,GRÜNE,FDP,AfD,CSU,LINKE,BSW,FW,SSW,其他
只用 Zweitstimme（Stimme=2）做本夾複數與縮放基底；單一孔多賽用同票當「第一偏好強度」。
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")

LAND = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Württemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}

# kerg2 Gruppenname → 本夾短名
MAP = {
    "SPD": "SPD",
    "CDU": "CDU",
    "GRÜNE": "GRÜNE",
    "FDP": "FDP",
    "AfD": "AfD",
    "CSU": "CSU",
    "Die Linke": "LINKE",
    "DIE LINKE": "LINKE",
    "BSW": "BSW",
    "FREIE WÄHLER": "FW",
    "SSW": "SSW",
}
MAIN = ["SPD", "CDU", "GRÜNE", "FDP", "AfD", "CSU", "LINKE", "BSW", "FW", "SSW"]


def open_kerg2(path):
    """跳過版權／說明列，從含 Gebietsart 的表頭起讀。"""
    f = open(path, encoding="utf-8-sig", newline="")
    while True:
        pos = f.tell()
        line = f.readline()
        if not line:
            break
        if line.startswith("Wahlart;") or ";Gebietsart;" in line:
            f.seek(pos)
            break
    return csv.DictReader(f, delimiter=";"), f


def main(src_name="btw25_kerg2.csv", out_name="bt-2025.csv"):
    path = os.path.join(DATA, src_name)
    # 每 WK：party -> votes；meta
    wks = {}
    r, fh = open_kerg2(path)
    with fh:
        for row in r:
            if row["Gebietsart"] != "Wahlkreis":
                continue
            if row["Stimme"] != "2":  # Zweitstimme
                continue
            if row["Gruppenart"] not in ("Partei", "System-Gruppe"):
                continue
            nr = row["Gebietsnummer"].zfill(3)
            if nr not in wks:
                land_nr = row["UegGebietsnummer"].zfill(2)
                wks[nr] = {
                    "land_code": land_nr,
                    "land": LAND.get(land_nr, land_nr),
                    "wk_nr": nr,
                    "wk_name": row["Gebietsname"],
                    "votes": defaultdict(int),
                    "valid": 0,
                }
            g = row["Gruppenname"]
            n = int(row["Anzahl"] or 0)
            if g == "Gültige":
                wks[nr]["valid"] = n
            elif row["Gruppenart"] == "Partei":
                short = MAP.get(g)
                if short:
                    wks[nr]["votes"][short] += n
                else:
                    wks[nr]["votes"]["其他"] += n

    out_path = os.path.join(DATA, out_name)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["land_code", "land", "wk_nr", "wk_name", "valid"] + MAIN + ["其他"])
        for nr in sorted(wks):
            u = wks[nr]
            row = [u["land_code"], u["land"], u["wk_nr"], u["wk_name"], u["valid"]]
            for p in MAIN:
                row.append(u["votes"].get(p, 0))
            known = sum(u["votes"].get(p, 0) for p in MAIN)
            other = u["votes"].get("其他", 0)
            if u["valid"] and known + other < u["valid"]:
                other = u["valid"] - known
            row.append(other)
            w.writerow(row)
    print("wrote", out_path, "rows", len(wks), "valid", sum(wks[n]["valid"] for n in wks))


if __name__ == "__main__":
    import zipfile
    import sys

    zpath = os.path.join(DATA, "btw_kerg.zip")
    if os.path.isfile(zpath):
        with zipfile.ZipFile(zpath) as zf:
            for member in ("btw2021_kerg2.csv",):
                if member in zf.namelist():
                    dest = os.path.join(DATA, member)
                    if not os.path.isfile(dest):
                        zf.extract(member, DATA)
                        print("extracted", dest)
    main("btw25_kerg2.csv", "bt-2025.csv")
    if os.path.isfile(os.path.join(DATA, "btw2021_kerg2.csv")):
        # 2021 無 BSW；MAP 仍適用
        main("btw2021_kerg2.csv", "bt-2021.csv")
    if "--only2025" in sys.argv:
        pass
