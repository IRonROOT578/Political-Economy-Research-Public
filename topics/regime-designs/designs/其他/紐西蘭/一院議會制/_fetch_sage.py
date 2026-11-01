# -*- coding: utf-8 -*-
"""從 sage-archive 拉紐西蘭投票所政黨票，對齊官方選區總票 → 資料/ge-YYYY.csv。

來源：
- 地理單位：GCS sage-archive parquet（Electoral Commission 投票所層）
- 校準：scgElectionsNZ party_votes.rda（官方選區政黨票）

官方 electionresults.govt.nz CSV 被 Cloudflare 擋；sage 為公開彙整。
重跑：python _fetch_sage.py
"""
from __future__ import annotations

import csv
import os
import ssl
import sys
import tempfile
import urllib.request

import pandas as pd
import pyreadr

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
os.makedirs(DATA, exist_ok=True)
CTX = ssl._create_unverified_context()
UA = {"User-Agent": "Mozilla/5.0 regime-designs"}

YEARS = (2023, 2020, 2017, 2014)

# sage party name → 本夾短名
PARTY_MAP = {
    "New Zealand National Party": "國家黨",
    "National Party": "國家黨",
    "New Zealand Labour Party": "工黨",
    "Labour Party": "工黨",
    "Green Party of Aotearoa New Zealand": "綠黨",
    "Green Party": "綠黨",
    "ACT New Zealand": "行動黨",
    "ACT Party": "行動黨",
    "New Zealand First": "紐西蘭優先",
    "NZ First": "紐西蘭優先",
    "Te Pāti Māori": "毛利黨",
    "Maori Party": "毛利黨",
    "Māori Party": "毛利黨",
    "The Opportunities Party": "機會黨",
    "The Opportunities Party (TOP)": "機會黨",
    "Conservative Party": "保守黨",
    "Conservative": "保守黨",
    "United Future": "聯合未來",
    "United Future New Zealand": "聯合未來",
    "Internet MANA": "網路MANA",
    "Internet Party": "網路MANA",
    "MANA Movement": "網路MANA",
    "Internet Party and Mana Movement": "網路MANA",
}

# 官方 rda 黨名 → 短名
RDA_MAP = {
    "National Party": "國家黨",
    "Labour Party": "工黨",
    "Green Party": "綠黨",
    "ACT Party": "行動黨",
    "NZ First": "紐西蘭優先",
    "Maori Party": "毛利黨",
    "The Opportunities Party (TOP)": "機會黨",
    "Conservative Party": "保守黨",
    "United Future": "聯合未來",
    "Internet Party": "網路MANA",
    "MANA": "網路MANA",
    "Internet MANA": "網路MANA",
}


def fold_name(s: str) -> str:
    """去掉長音符號，對齊 sage（有 macron）與 rda（無）。"""
    table = str.maketrans({
        "ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u",
        "Ā": "A", "Ē": "E", "Ī": "I", "Ō": "O", "Ū": "U",
    })
    return s.translate(table)

MAIN_COLS = ["國家黨", "工黨", "綠黨", "行動黨", "紐西蘭優先", "毛利黨", "機會黨", "保守黨", "聯合未來", "網路MANA"]

# 選區 → 四複數區（見 01）
AUCKLAND = {
    "Auckland Central", "Botany", "East Coast Bays", "Epsom", "Kelston", "Māngere",
    "Manurewa", "Maungakiekie", "Mt Albert", "Mt Roskill", "New Lynn", "North Shore",
    "Northcote", "Pakuranga", "Panmure-Ōtāhuhu", "Papakura", "Takanini", "Tāmaki",
    "Te Atatū", "Upper Harbour", "Whangaparāoa", "Kaipara ki Mahurangi", "Tāmaki Makaurau",
}
WELLINGTON_CENTRAL = {
    "Wellington Central", "Ōhāriu", "Rongotai", "Hutt South", "Remutaka", "Mana",
    "Ōtaki", "Palmerston North", "Wairarapa", "Rangitīkei", "Whanganui", "Napier",
    "Tukituki", "Ikaroa-Rāwhiti", "Te Tai Hauāuru",
}
SOUTH = {
    "Christchurch Central", "Christchurch East", "Ilam", "Wigram", "Banks Peninsula",
    "Selwyn", "Waimakariri", "Kaikōura", "Nelson", "West Coast-Tasman", "Waitaki",
    "Dunedin", "Taieri", "Invercargill", "Southland", "Rangitata", "Te Tai Tonga",
}


def region_of(electorate: str) -> str:
    if electorate in AUCKLAND:
        return "奧克蘭"
    if electorate in WELLINGTON_CENTRAL:
        return "威靈頓中央"
    if electorate in SOUTH:
        return "南島"
    return "北島其餘"


def download(url: str, path: str) -> None:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, context=CTX, timeout=300) as r:
        open(path, "wb").write(r.read())


def fetch_parquet(year: int, dest: str) -> str:
    # GCS key 字面含 %20
    url = (
        "https://storage.googleapis.com/sage-archive/parquet/"
        f"country=New%2520Zealand/year={year}/part-0.parquet"
    )
    path = os.path.join(dest, f"{year}.parquet")
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        print("download", year)
        download(url, path)
    return path


def fetch_rda(dest: str) -> pd.DataFrame:
    path = os.path.join(dest, "party_votes.rda")
    url = "https://raw.githubusercontent.com/sarahcgallLtd/scgElectionsNZ/master/data/party_votes.rda"
    if not os.path.exists(path):
        download(url, path)
    return list(pyreadr.read_r(path).values())[0]


def build_year(year: int, pq_path: str, official: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_parquet(pq_path)
    raw["party_zh"] = raw["party"].map(PARTY_MAP)
    raw = raw[raw["party_zh"].notna()].copy()
    # 合併提前＋當日同一地址
    place = (
        raw.groupby(["NAME1", "NAME3", "party_zh"], dropna=False)["votes"]
        .sum()
        .reset_index()
        .rename(columns={"NAME1": "electorate", "NAME3": "place", "votes": "votes"})
    )
    # 官方選區總票
    off = official[official["Election"] == float(year)].copy()
    off["party_zh"] = off["Party"].map(RDA_MAP)
    off = off[off["party_zh"].notna()]
    off["electorate_key"] = off["Electorate"].map(fold_name)
    off_tot = off.groupby(["electorate_key", "party_zh"])["Votes"].sum().reset_index()
    off_tot = off_tot.rename(columns={"Votes": "official"})

    place["electorate_key"] = place["electorate"].map(fold_name)
    place_tot = place.groupby(["electorate_key", "party_zh"])["votes"].sum().reset_index()
    merged = place_tot.merge(off_tot, on=["electorate_key", "party_zh"], how="left")
    # 縮放係數
    merged["scale"] = merged.apply(
        lambda r: (r["official"] / r["votes"]) if r["votes"] and pd.notna(r["official"]) else 1.0,
        axis=1,
    )
    scale = merged.set_index(["electorate_key", "party_zh"])["scale"]
    place["scale"] = place.set_index(["electorate_key", "party_zh"]).index.map(scale)
    place["scale"] = place["scale"].fillna(1.0)
    n_miss = int(merged["official"].isna().sum())
    if n_miss:
        print(f"  warn {year}: {n_miss} electorate×party missing official scale")
    place["votes"] = (place["votes"] * place["scale"]).round().astype(int)

    # 寬表
    wide = place.pivot_table(
        index=["electorate", "place"], columns="party_zh", values="votes", aggfunc="sum", fill_value=0
    ).reset_index()
    for c in MAIN_COLS:
        if c not in wide.columns:
            wide[c] = 0
    wide["land"] = wide["electorate"].map(region_of)
    wide["valid"] = wide[MAIN_COLS].sum(axis=1)
    wide = wide[wide["valid"] > 0].copy()
    wide.insert(0, "id", [f"{year}-{i:05d}" for i in range(1, len(wide) + 1)])
    cols = ["id", "land", "electorate", "place", "valid"] + MAIN_COLS
    return wide[cols]


def main():
    tmp = os.path.join(tempfile.gettempdir(), "sage_nz_fetch")
    os.makedirs(tmp, exist_ok=True)
    official = fetch_rda(tmp)
    for year in YEARS:
        pq = fetch_parquet(year, tmp)
        wide = build_year(year, pq, official)
        out = os.path.join(DATA, f"ge-{year}.csv")
        wide.to_csv(out, index=False, encoding="utf-8")
        # 全國校準檢查
        print(
            f"wrote {out} n={len(wide)} valid={wide['valid'].sum()} "
            f"by land={wide.groupby('land')['valid'].sum().to_dict()}"
        )
        nat = {c: int(wide[c].sum()) for c in MAIN_COLS if wide[c].sum()}
        print("  national", nat)


if __name__ == "__main__":
    main()
