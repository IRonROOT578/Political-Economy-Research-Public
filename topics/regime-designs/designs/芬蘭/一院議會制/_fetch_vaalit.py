# -*- coding: utf-8 -*-
"""從正義部 tulospalvelu 抓國會選舉市鎮×黨 → `資料/fi-YYYY.csv`。

    python _fetch_vaalit.py 2023
    python _fetch_vaalit.py 2019
    python _fetch_vaalit.py 2015

2019 以後：https://tulospalvelu.vaalit.fi/EKV-{YYYY}/ekv-{YYYY}_puo_maa.csv.zip
2015：https://tulospalvelu.vaalit.fi/E-2015/e-2015_puo_maa.csv.zip
（同一檔含投票區 A、市鎮 K、選區 V 三層，只取市鎮 K。）
`district`＝vaalipiiri 碼（01–13；05＝奧蘭）。八區 remap 在 `生態模型.py`。
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
OUT = HERE / "資料"

PARTY_MAP = {
    "SDP": "社民黨",
    "KESK": "中間黨",
    "KOK": "聯合黨",
    "PS": "芬人黨",
    "VIHR": "綠黨",
    "VAS": "左翼聯盟",
    "RKP": "瑞典人民黨",
    "SFP": "瑞典人民黨",
    "KD": "基民黨",
    "LIIK": "現在運動",
}
MAIN = list(dict.fromkeys(PARTY_MAP.values()))


def fetch_zip(year: int) -> bytes:
    if year <= 2015:
        url = f"https://tulospalvelu.vaalit.fi/E-{year}/e-{year}_puo_maa.csv.zip"
    else:
        url = f"https://tulospalvelu.vaalit.fi/EKV-{year}/ekv-{year}_puo_maa.csv.zip"
    with urlopen(url, timeout=120) as r:
        return r.read()


def parse_2015(raw: bytes) -> list[dict]:
    """2015 固定欄位檔。第 4 欄 A/K/V 是投票區、市鎮、選區三層，只留市鎮 K。

    欄：1 選區、2 市鎮碼、10 黨簡稱、13 市鎮名、40 總票。
    全國中間黨 626,218，與正義部公布一致，用來確認沒有把三層加在一起。
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(name).decode("latin-1")
    agg: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    names: dict[tuple[str, str], str] = {}
    for row in csv.reader(io.StringIO(text), delimiter=";"):
        if len(row) < 41 or row[3].strip() != "K":
            continue
        vp = row[1].strip()
        if not vp.isdigit():
            continue
        mid = row[2].strip()
        party_raw = row[10].strip().upper()
        party = PARTY_MAP.get(party_raw)
        votes = int(row[40].strip() or 0)
        if votes <= 0:
            continue
        key = (vp, mid)
        names[key] = row[13].strip()
        if party in MAIN:
            agg[key][party] += votes
        else:
            agg[key]["其他"] += votes
        agg[key]["valid"] += votes
    rows = []
    for (vp, mid), d in sorted(agg.items()):
        r = {"id": f"2015-{mid}", "land": "", "district": vp, "name": names[(vp, mid)],
             "valid": d.get("valid", 0), "其他": d.get("其他", 0)}
        for p in MAIN:
            r[p] = d.get(p, 0)
        rows.append(r)
    kesk = sum(r["中間黨"] for r in rows)
    if kesk != 626218:
        raise SystemExit(f"2015 中間黨票 {kesk}，不是正義部公布的 626218，沒有寫檔")
    return rows


def parse(raw: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        text = zf.read(name).decode("utf-8-sig", errors="replace")
    delim = ";" if text[:4000].count(";") > text[:4000].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    fields = reader.fieldnames or []

    def pick(*cands):
        low = {f.lower(): f for f in fields}
        for c in cands:
            if c.lower() in low:
                return low[c.lower()]
        for f in fields:
            fl = f.lower()
            for c in cands:
                if c.lower() in fl:
                    return f
        return None

    f_muni = pick("kunta", "alue_koodi", "kuntanumero")
    f_name = pick("kunta_nimi", "alue_nimi", "nimi", "name")
    f_vp = pick("vaalipiiri", "vaalipiiri_numero")
    f_party = pick("puolue", "lyhenne", "party")
    f_votes = pick("äänet", "aanet", "votes", "lkm")
    if not (f_muni and f_party and f_votes):
        raise SystemExit(f"無法辨識欄位 fields={fields[:20]}")

    agg: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    names: dict[str, str] = {}
    for row in reader:
        mid = (row.get(f_muni) or "").strip()
        if not mid or mid.startswith("*"):
            continue
        vp = (row.get(f_vp) or "").strip().zfill(2)[-2:]
        party_raw = (row.get(f_party) or "").strip().upper()
        party = PARTY_MAP.get(party_raw)
        if party is None:
            pr = party_raw.lower()
            for key, zh in (
                ("sosialidemokra", "社民黨"),
                ("keskusta", "中間黨"),
                ("kokoomus", "聯合黨"),
                ("perussuomal", "芬人黨"),
                ("vihre", "綠黨"),
                ("vasemmisto", "左翼聯盟"),
                ("ruotsalainen", "瑞典人民黨"),
                ("kristillis", "基民黨"),
                ("liike nyt", "現在運動"),
                ("liikenyt", "現在運動"),
            ):
                if key in pr:
                    party = zh
                    break
        try:
            votes = int(float((row.get(f_votes) or "0").replace(" ", "").replace(",", ".")))
        except ValueError:
            votes = 0
        if votes <= 0:
            continue
        key = (vp, mid)
        if party in MAIN:
            agg[key][party] += votes
        else:
            agg[key]["其他"] += votes
        agg[key]["valid"] += votes
        if f_name and row.get(f_name):
            names[mid] = row[f_name].strip()

    rows = []
    for (vp, mid), d in sorted(agg.items()):
        r = {"id": mid, "land": "", "district": vp, "name": names.get(mid, mid), "valid": d.get("valid", 0), "其他": d.get("其他", 0)}
        for p in MAIN:
            r[p] = d.get(p, 0)
        rows.append(r)
    return rows


def main() -> None:
    years = [int(a) for a in sys.argv[1:]] or [2023, 2019]
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["id", "land", "district", "name", "valid"] + MAIN + ["其他"]
    for year in years:
        print(f"fetch {year}…")
        raw = fetch_zip(year)
        rows = parse_2015(raw) if year <= 2015 else parse(raw)
        path = OUT / f"fi-{year}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, 0) for k in fields})
        print(f"  → {path.name}: {len(rows)} 市鎮, valid={sum(r['valid'] for r in rows):,}")


if __name__ == "__main__":
    main()
