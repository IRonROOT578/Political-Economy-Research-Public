# -*- coding: utf-8 -*-
"""從 Statistikbanken API 拉 FV22TOTA／FV19TOTA 逐 opstillingskreds → 資料/ft-YYYY.csv。

單位：DST OMRÅDE 的**投票所（afstemningsområde，id ≥ 1000）**，約 1,300 個；DST 依提名區（id 20–111）列出其下的投票所，
CSV 的 id 是在 DST 清單中的順序（同一提名區的投票所相鄰），op 欄是所屬提名區。storkreds 10–19 → 本夾五區。
不入庫 API 原始 JSON；只留彙整 CSV。重跑：python _fetch_dst.py 2019 2022 2026
"""
from __future__ import annotations

import csv
import json
import os
import ssl
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
os.makedirs(DATA, exist_ok=True)
CTX = ssl._create_unverified_context()

# opstillingskreds id → storkreds
OP_STORK = {}
for i in range(20, 30):
    OP_STORK[str(i)] = "10"
for i in range(30, 40):
    OP_STORK[str(i)] = "11"
for i in range(40, 46):
    OP_STORK[str(i)] = "12"
for i in range(46, 48):
    OP_STORK[str(i)] = "13"
for i in range(48, 60):
    OP_STORK[str(i)] = "14"
for i in range(60, 68):
    OP_STORK[str(i)] = "15"
for i in range(68, 81):
    OP_STORK[str(i)] = "16"
for i in range(81, 92):
    OP_STORK[str(i)] = "17"
for i in range(92, 103):
    OP_STORK[str(i)] = "18"
for i in range(103, 112):
    OP_STORK[str(i)] = "19"

STORK_LAND = {
    "10": "Hovedstaden",
    "11": "Hovedstaden",
    "12": "Hovedstaden",
    "13": "Hovedstaden",
    "14": "Sjælland",
    "15": "Syddanmark",
    "16": "Syddanmark",
    "17": "Midtjylland",
    "18": "Midtjylland",
    "19": "Nordjylland",
}
STORK_NAME = {
    "10": "København",
    "11": "Københavns Omegn",
    "12": "Nordsjælland",
    "13": "Bornholm",
    "14": "Sjælland",
    "15": "Fyn",
    "16": "Sydjylland",
    "17": "Østjylland",
    "18": "Vestjylland",
    "19": "Nordjylland",
}

# VALRES id → short code（兩屆共用＋屆別專有）
PARTY_2022 = {
    "5891": "S",
    "5893": "RV",
    "5895": "C",
    "1675319": "NB",
    "5897": "SF",
    "5907": "LA",
    "5901": "KD",
    "1962293": "M",
    "5899": "DF",
    "5903": "V",
    "1968075": "DD",
    "5905": "EL",
    "1487618": "ALT",
    "1962272": "FG",
}
PARTY_2026 = {
    "5891": "S", "5893": "RV", "5895": "C", "5897": "SF", "2559203": "BP", "5907": "LA",
    "1962293": "M", "5899": "DF", "5903": "V", "1968075": "DD", "5905": "EL", "1487618": "ALT",
}
PARTY_2019 = {
    "5891": "S",
    "5893": "RV",
    "5895": "C",
    "1675319": "NB",
    "5897": "SF",
    "5907": "LA",
    "5901": "KD",
    "5899": "DF",
    "5903": "V",
    "5905": "EL",
    "1487618": "ALT",
    "1684467": "SK",  # Stram Kurs
    "1675339": "KRP",  # Klaus Riskær Pedersen
}


def api(path, payload=None):
    url = "https://api.statbank.dk/v1/" + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 regime-designs",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
        raw = r.read().decode("utf-8")
        if payload and str(payload.get("format", "")).upper() == "CSV":
            return raw
        return json.loads(raw)


def dump_info(table):
    info = api(f"tableinfo/{table}")
    path = os.path.join(DATA, f"_{table}_info.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print("info", path)
    return info


def fetch_opstilling(table, party_map):
    """POST 全 92 提名區 × 政黨＋GYLD_IALT；回傳 {op_id: {party: votes, '_valid': n, '_name': t}}。"""
    ops = sorted(OP_STORK.keys(), key=int)
    valres = list(party_map.keys()) + ["GYLD_IALT"]
    # 分批以免過大
    out = {}
    batch = 30
    for i in range(0, len(ops), batch):
        chunk = ops[i : i + batch]
        payload = {
            "table": table,
            "format": "JSONSTAT",
            "variables": [
                {"code": "OMRÅDE", "values": chunk},
                {"code": "VALRES", "values": valres},
            ],
        }
        data = api("data", payload)
        dim = data["dataset"]["dimension"]
        # keys may be OMRÅDE or garbled; find by label
        omr_key = next(k for k in dim if "omr" in k.lower() or k.upper().startswith("OMR"))
        val_key = next(k for k in dim if "val" in k.lower() or k.upper() == "VALRES")
        omr_idx = dim[omr_key]["category"]["index"]  # id → pos
        val_idx = dim[val_key]["category"]["index"]
        omr_lab = dim[omr_key]["category"]["label"]
        size = data["dataset"]["dimension"]["size"] if "size" in data["dataset"] else data["dataset"]["dimension"].get("size")
        # id order from dataset
        ids = data["dataset"]["dimension"]["id"]
        sizes = data["dataset"]["dimension"]["size"]
        values = data["dataset"]["value"]
        # stride
        # typically [VALRES, OMRÅDE, ContentsCode, Tid] or similar
        def pos(indices):
            # indices aligned to ids order
            p = 0
            for j, ix in enumerate(indices):
                stride = 1
                for s in sizes[j + 1 :]:
                    stride *= s
                p += ix * stride
            return p

        # build reverse: for each area, each party
        for oid, opos in omr_idx.items():
            name = omr_lab.get(oid, oid)
            row = {"_name": name, "_valid": 0}
            for vid, vpos in val_idx.items():
                indices = []
                for key in ids:
                    if key == val_key:
                        indices.append(vpos)
                    elif key == omr_key:
                        indices.append(opos)
                    else:
                        indices.append(0)
                val = values[pos(indices)]
                if val is None:
                    val = 0
                if vid == "GYLD_IALT":
                    row["_valid"] = int(val)
                elif vid in party_map:
                    row[party_map[vid]] = int(val)
            out[oid] = row
        print("  batch", chunk[0], "-", chunk[-1], "got", len(chunk))
    return out


def fetch_polling(table, party_map):
    """投票所層級：依 tableinfo 的清單順序，把每個 id ≥ 1000 的投票所歸到它前面最近的提名區。"""
    info = api(f"tableinfo/{table}")
    areas = next(v for v in info["variables"] if v["id"].upper().startswith("OMR"))["values"]
    order, op = [], None
    for a in areas:
        if a["id"] in OP_STORK:
            op = a["id"]
        elif int(a["id"]) >= 1000:
            order.append((a["id"], op))
    valres = list(party_map.keys()) + ["GYLD_IALT"]
    got = {}
    for i in range(0, len(order), 150):
        chunk = [a for a, _ in order[i:i + 150]]
        payload = {"table": table, "format": "JSONSTAT",
                   "variables": [{"code": "OMRÅDE", "values": chunk}, {"code": "VALRES", "values": valres}]}
        ds = api("data", payload)["dataset"]
        dim = ds["dimension"]
        ids, sizes, values = dim["id"], dim["size"], ds["value"]
        omr_key = next(k for k in ids if k.upper().startswith("OMR"))
        val_key = next(k for k in ids if k.upper() == "VALRES")
        strides = [1] * len(ids)
        for j in range(len(ids) - 2, -1, -1):
            strides[j] = strides[j + 1] * sizes[j + 1]
        jo, jv = ids.index(omr_key), ids.index(val_key)
        lab = dim[omr_key]["category"]["label"]
        for oid, opos in dim[omr_key]["category"]["index"].items():
            row = {"_name": lab.get(oid, oid), "_valid": 0}
            for vid, vpos in dim[val_key]["category"]["index"].items():
                x = values[opos * strides[jo] + vpos * strides[jv]] or 0
                if vid == "GYLD_IALT":
                    row["_valid"] = int(x)
                else:
                    row[party_map[vid]] = int(x)
            got[oid] = row
        print("  ", table, i + len(chunk), "/", len(order))
    return [(aid, op, got[aid]) for aid, op in order if got[aid]["_valid"] > 0]


def write_polling_csv(year, rows, party_cols):
    path = os.path.join(DATA, f"ft-{year}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "op", "land", "storkreds", "name", "valid"] + party_cols)
        for k, (aid, op, r) in enumerate(rows, 1):
            stork = OP_STORK[op]
            w.writerow([k, op, STORK_LAND[stork], STORK_NAME[stork], r["_name"], r["_valid"]] + [r.get(p, 0) for p in party_cols])
    nat = {p: sum(r.get(p, 0) for _, _, r in rows) for p in party_cols}
    print("wrote", path, "n=", len(rows), "valid=", sum(r["_valid"] for _, _, r in rows), nat)


COLS = {
    "2026": ("FV26TOTA", PARTY_2026, ["S", "V", "M", "SF", "DD", "LA", "C", "EL", "RV", "BP", "ALT", "DF"]),
    "2022": ("FV22TOTA", PARTY_2022, ["S", "V", "M", "SF", "DD", "LA", "C", "EL", "RV", "NB", "ALT", "DF", "KD", "FG"]),
    "2019": ("FV19TOTA", PARTY_2019, ["S", "V", "DF", "RV", "SF", "EL", "C", "ALT", "NB", "LA", "KD", "SK", "KRP"]),
}


def write_csv(year, rows_by_op, party_cols):
    path = os.path.join(DATA, f"ft-{year}.csv")
    fields = ["id", "land", "storkreds", "name", "valid"] + party_cols
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for oid in sorted(rows_by_op.keys(), key=int):
            r = rows_by_op[oid]
            stork = OP_STORK[oid]
            land = STORK_LAND[stork]
            w.writerow(
                [oid, land, STORK_NAME[stork], r["_name"], r["_valid"]]
                + [r.get(p, 0) for p in party_cols]
            )
    # sanity
    tot = sum(rows_by_op[o]["_valid"] for o in rows_by_op)
    print("wrote", path, "n=", len(rows_by_op), "valid_sum=", tot)
    return path


def main():
    years = [y for y in sys.argv[1:] if y in COLS]
    if years:
        for y in years:
            table, pm, cols = COLS[y]
            write_polling_csv(y, fetch_polling(table, pm), cols)
        return
    if "op2026" in sys.argv:   # 舊：提名區層級
        r26 = fetch_opstilling("FV26TOTA", PARTY_2026)
        cols26 = ["S", "V", "M", "SF", "DD", "LA", "C", "EL", "RV", "BP", "ALT", "DF"]
        write_csv(2026, r26, cols26)
        print("2026 national", {p: sum(r26[o].get(p, 0) for o in r26) for p in cols26})
        return
    dump_info("FV22TOTA")
    dump_info("FV19TOTA")
    print("fetch 2022…")
    r22 = fetch_opstilling("FV22TOTA", PARTY_2022)
    cols22 = ["S", "V", "M", "SF", "DD", "LA", "C", "EL", "RV", "NB", "ALT", "DF", "KD", "FG"]
    write_csv(2022, r22, cols22)
    # national check vs known
    nat = {p: sum(r22[o].get(p, 0) for o in r22) for p in cols22}
    print("2022 national", nat)

    print("fetch 2019…")
    r19 = fetch_opstilling("FV19TOTA", PARTY_2019)
    cols19 = ["S", "V", "DF", "RV", "SF", "EL", "C", "ALT", "NB", "LA", "KD", "SK", "KRP"]
    write_csv(2019, r19, cols19)
    nat19 = {p: sum(r19[o].get(p, 0) for o in r19) for p in cols19}
    print("2019 national", nat19)


if __name__ == "__main__":
    main()
