# -*- coding: utf-8 -*-
"""BMI xlsx → 資料/nr-YYYY.csv（市鎮；Briefwahl 按同政治區有效票比例併入）。"""
import csv
import os
import re
import sys
from collections import defaultdict
from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
LAND = {
    "1": "Burgenland", "2": "Kärnten", "3": "Niederösterreich", "4": "Oberösterreich",
    "5": "Salzburg", "6": "Steiermark", "7": "Tirol", "8": "Vorarlberg", "9": "Wien",
}


def build(year, xlsx_name, parties):
    path = os.path.join(DATA, xlsx_name)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    # find header row with GKZ
    header_i = next(i for i, r in enumerate(rows) if r and r[0] == "GKZ")
    header = list(rows[header_i])
    # find Gültige column: often index 5 after multi-row header
    # 2024: eligible=2, abgegeben=3, ungültige=4, gültige=5
    # 2019: row0 has Wahlberechtigte at 2; row1 has Abgegeb/Ungültige/Gültige at 3,4,5
    idx = {}
    for p in parties:
        if p in header:
            idx[p] = header.index(p)
    # locate gültige: look at first data row
    gems, wk = {}, defaultdict(lambda: {**{p: 0 for p in parties}, "valid": 0})
    for r in rows[header_i + 1:]:
        gkz = r[0]
        name = r[1] or ""
        if not isinstance(gkz, str) or not re.fullmatch(r"G\d{5}", gkz):
            continue
        # valid votes column: try 5, else scan
        valid = r[5]
        if valid is None and r[3] is not None:
            # sometimes structure differs
            valid = r[3]
        try:
            valid = int(valid or 0)
        except Exception:
            continue
        gem = int(gkz[4:6])
        bez = gkz[1:4]
        votes = {p: int(r[idx[p]] or 0) if p in idx else 0 for p in parties}
        if gem == 99 or "Wahlkarten" in str(name):
            for p in parties:
                wk[bez][p] += votes[p]
            wk[bez]["valid"] += valid
            continue
        if gem == 0:
            continue
        eligible = int(r[2] or 0) if r[2] is not None else 0
        gems[gkz] = {"land": LAND[gkz[1]], "name": name, "eligible": eligible, "valid": valid, "votes": votes, "bez": bez}

    bez_valid = defaultdict(int)
    for rec in gems.values():
        bez_valid[rec["bez"]] += rec["valid"]
    for gkz, rec in gems.items():
        bag = wk.get(rec["bez"])
        if not bag or bag["valid"] <= 0 or bez_valid[rec["bez"]] <= 0:
            continue
        share = rec["valid"] / bez_valid[rec["bez"]]
        for p in parties:
            rec["votes"][p] += bag[p] * share
        rec["valid"] += bag["valid"] * share

    out_path = os.path.join(DATA, f"nr-{year}.csv")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gkz", "land", "name", "eligible", "valid"] + parties)
        for gkz, rec in sorted(gems.items()):
            v = int(round(rec["valid"]))
            if v <= 0:
                continue
            votes = {p: int(round(rec["votes"][p])) for p in parties}
            w.writerow([gkz, rec["land"], rec["name"], rec["eligible"], v] + [votes[p] for p in parties])
    print(year, "units", len(gems), "->", out_path)


build(2024, "nr2024-bmi.xlsx",
      ["ÖVP", "SPÖ", "FPÖ", "GRÜNE", "NEOS", "BIER", "MFG", "BGE", "LMP", "GAZA", "KPÖ", "KEINE"])
build(2019, "nr2019-bmi.xlsx",
      ["ÖVP", "SPÖ", "FPÖ", "NEOS", "JETZT", "GRÜNE", "KPÖ", "WANDL", "BZÖ", "BIER", "CPÖ", "GILT", "SLP"])
