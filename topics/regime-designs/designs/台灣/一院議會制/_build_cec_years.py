# -*- coding: utf-8 -*-
"""從 votedata.zip 建 村里-YYYY.csv、名單-YYYY.csv（2016、2012）。

中間第三黨：當時無民眾黨 → 政黨票把「親民黨」寫進「民眾黨」欄（供 top-3 孔多賽中位槽）；
總統票「民眾黨」欄＝宋楚瑜。名單檔仍用真實黨名（親民黨另列）。
"""
import csv
import os
import re
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料")
Z = os.path.join(DATA, "raw", "votedata.zip")

COUNTY_TO_REGION = {
    "臺北市": "臺北市", "新北市": "新北市", "臺中市": "臺中＋彰化", "彰化縣": "臺中＋彰化",
    "桃園市": "桃園＋新竹縣市", "桃園縣": "桃園＋新竹縣市", "新竹市": "桃園＋新竹縣市", "新竹縣": "桃園＋新竹縣市",
    "臺南市": "雲嘉南", "臺南縣": "雲嘉南", "嘉義市": "雲嘉南", "嘉義縣": "雲嘉南", "雲林縣": "雲嘉南",
    "高雄市": "高屏", "高雄縣": "高屏", "屏東縣": "高屏",
    "基隆市": "其餘縣市與離島", "宜蘭縣": "其餘縣市與離島", "苗栗縣": "其餘縣市與離島",
    "南投縣": "其餘縣市與離島", "花蓮縣": "其餘縣市與離島", "臺東縣": "其餘縣市與離島",
    "澎湖縣": "澎金馬", "金門縣": "澎金馬", "連江縣": "澎金馬",
}

# 政黨票歸群（親民 → 民眾黨欄，見檔頭說明）
GREEN = {"時代力量", "台灣團結聯盟", "綠黨", "綠黨社會民主黨聯盟", "自由台灣黨", "社會民主黨", "台灣基進"}
LOCAL = {
    "新黨", "無黨團結聯盟", "民國黨", "中華統一促進黨", "信心希望聯盟", "軍公教聯盟黨",
    "和平鴿聯盟黨", "大愛憲改聯盟", "健保免費連線", "正黨", "台灣工黨", "人民民主陣線",
    "台灣國民會議", "人民最大黨", "台灣主義黨", "中華台商愛國黨", "中華民國臺灣基本法連線",
    "台灣進步黨", "中華民主向心力黨",
}


def dec(n):
    try:
        return n.encode("cp437").decode("big5")
    except Exception:
        return n


def clean(s):
    return s.strip().strip("'").strip('"')


def load_crosswalk():
    """2024 風格縣市碼（如 63000、10004）+ 鄉鎮 + 村里 → (區,縣市,現行選區)。"""
    path = os.path.join(DATA, "村里-2024.csv")
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["縣市碼"], r["鄉鎮碼"], r["村里碼"])] = (r["區"], r["縣市"], r["現行選區"])
    return out


def norm_city_code(cty, sub):
    """把各年 elctks 的（省市碼, 縣市子碼）收成 2024 五碼縣市碼（能對上才對；對不上就回 None）。"""
    # 2016／2020／2024 直轄市：63–68 → 63000…
    if cty in ("63", "64", "65", "66", "67", "68"):
        return cty + "000"
    # 2016 臺灣省／金馬：10+004→10004；09+020→09020
    if cty in ("09", "10") and sub and sub != "000":
        return cty + sub
    return None


def build_county_map(elbase_rows):
    """(省市碼, 縣市子碼) → 縣市名。直轄市子碼為 000；省／金馬用第二欄區分。"""
    out = {}
    for r in elbase_rows:
        cty, sub, dist, town, vill, name = r[0], r[1], r[2], r[3], r[4], r[5]
        if town != "000" or vill != "0000" or dist not in ("00", "000"):
            continue
        if name in ("全國",):
            continue
        out[(cty, sub)] = name
        # 直轄市也收 (cty, "000")
        if sub == "000":
            out[(cty, "000")] = name
    return out


def county_name(city_map, cty, sub):
    if (cty, sub) in city_map:
        return city_map[(cty, sub)]
    if (cty, "000") in city_map:
        return city_map[(cty, "000")]
    return cty


def open_member(zf, mapping, must_substrs, filename):
    """must_substrs 皆需出現；檔名須精確結尾；排除 /old/。"""
    hits = []
    for d, raw in mapping.items():
        dd = d.replace("\\", "/")
        if "/old/" in dd:
            continue
        if not dd.endswith("/" + filename):
            continue
        if all(s in dd for s in must_substrs):
            hits.append((dd, raw))
    if not hits:
        raise FileNotFoundError((must_substrs, filename))
    # 偏好路徑較短／較精確者（避免「總統及立委」誤配到「…/總統/」以外）
    hits.sort(key=lambda x: (0 if "/總統/" in x[0] and "總統" in must_substrs else 1, len(x[0])))
    if "總統" in must_substrs:
        hits = [h for h in hits if "/總統/" in h[0]] or hits
    if "不分區" in "".join(must_substrs):
        hits = [h for h in hits if "不分區" in h[0]] or hits
    return zf.open(hits[0][1])


def read_csv_rows(zf, mapping, must_substrs, filename):
    with open_member(zf, mapping, must_substrs, filename) as f:
        text = f.read().decode("utf-8-sig", errors="replace")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        rows.append([clean(c) for c in next(csv.reader([line]))])
    return rows


def party_no_to_name(elcand_rows):
    """名單號 → 黨名（不分區：候選人列的黨名欄）。"""
    out = {}
    for r in elcand_rows:
        # 欄：省市,縣市,選區,鄉鎮,村里,名單號,姓名或黨名,政黨碼,...
        no = r[5]
        name = r[6]
        out[no] = name
    return out


def group_party(name):
    if name in ("民主進步黨",):
        return "民進黨"
    if name in ("中國國民黨",):
        return "國民黨"
    if name in ("親民黨", "台灣民眾黨"):
        return "民眾黨"  # 2012/2016：親民進中位槽
    if name in GREEN:
        return "綠系小黨"
    if name in LOCAL:
        return "地方型"
    return "其他"


def build_year(year, party_dir_parts, pres_dir_parts, party_ctks, party_cand, party_base, party_paty,
               pres_ctks, pres_cand):
    cw = load_crosswalk()
    with zipfile.ZipFile(Z) as zf:
        mapping = {dec(n): n for n in zf.namelist()}
        elcand = read_csv_rows(zf, mapping, party_dir_parts, party_cand)
        elctks = read_csv_rows(zf, mapping, party_dir_parts, party_ctks)
        elbase = read_csv_rows(zf, mapping, party_dir_parts, party_base)
        pcand = read_csv_rows(zf, mapping, pres_dir_parts, pres_cand)
        pctks = read_csv_rows(zf, mapping, pres_dir_parts, pres_ctks)

    no2party = party_no_to_name(elcand)
    # 總統：名單號 → 陣營
    # 2016: 1朱=國民 2蔡=民進 3宋=中間；2012: 1蔡=民進 2馬=國民 3宋=中間
    pres_map = {}
    for r in pcand:
        no, name, pcode = r[5], r[6], r[7]
        if name in ("蔡英文",):
            pres_map[no] = "民進黨"
        elif name in ("馬英九", "朱立倫", "韓國瑜", "侯友宜"):
            pres_map[no] = "國民黨"
        elif name in ("宋楚瑜", "柯文哲"):
            pres_map[no] = "民眾黨"

    city_map = build_county_map(elbase)
    # key = (cty, sub, town, vill)；省／金馬必須帶 sub，否則鄉鎮碼會撞
    vill_name = {}
    for r in elbase:
        cty, sub, town, vill, name = r[0], r[1], r[3], r[4], r[5]
        if vill != "0000" and town != "000":
            vill_name[(cty, sub, town, vill)] = name

    # elctks: 省市, 縣市子碼, 選區, 鄉鎮, 村里, 投開票所, 候選人, 得票, …
    party_v = defaultdict(lambda: defaultdict(int))
    party_dist = {}  # key → 現行選區號（取自 elctks 選區欄）

    def is_poll(station):
        # station 0／0000＝村里加總列，與各投開票所並列時會双計
        return station not in ("0", "00", "000", "0000")

    for r in elctks:
        cty, sub, dist_no, town, vill, station, cand = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        votes = int(r[7] or 0)
        if vill == "0000" or town == "000" or not is_poll(station):
            continue
        key = (cty, sub, town, vill)
        g = group_party(no2party.get(cand, "其他"))
        party_v[key][g] += votes
        party_v[key]["_raw_" + no2party.get(cand, cand)] += votes
        party_dist[key] = dist_no.lstrip("0") or "1"

    # 若某村里略過加總列後完全沒有投開票所列，改用 station 0 加總
    seen = set(party_v)
    for r in elctks:
        cty, sub, dist_no, town, vill, station, cand = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        votes = int(r[7] or 0)
        if vill == "0000" or town == "000":
            continue
        key = (cty, sub, town, vill)
        if key in seen:
            continue
        if station in ("0", "00", "000", "0000"):
            g = group_party(no2party.get(cand, "其他"))
            party_v[key][g] += votes
            party_v[key]["_raw_" + no2party.get(cand, cand)] += votes
            party_dist[key] = dist_no.lstrip("0") or "1"

    pres_v = defaultdict(lambda: defaultdict(int))
    for r in pctks:
        cty, sub, town, vill, station, cand = r[0], r[1], r[3], r[4], r[5], r[6]
        votes = int(r[7] or 0)
        if vill == "0000" or town == "000" or not is_poll(station):
            continue
        camp = pres_map.get(cand)
        if camp:
            pres_v[(cty, sub, town, vill)][camp] += votes
    seen_p = set(pres_v)
    for r in pctks:
        cty, sub, town, vill, station, cand = r[0], r[1], r[3], r[4], r[5], r[6]
        votes = int(r[7] or 0)
        if vill == "0000" or town == "000":
            continue
        key = (cty, sub, town, vill)
        if key in seen_p:
            continue
        if station in ("0", "00", "000", "0000"):
            camp = pres_map.get(cand)
            if camp:
                pres_v[key][camp] += votes

    RENAME = {"桃園縣": "桃園市", "臺南縣": "臺南市", "高雄縣": "高雄市", "臺中縣": "臺中市"}

    # 寫村里
    rows_out = []
    list_by_region = defaultdict(lambda: defaultdict(int))
    for key, gv in party_v.items():
        cty, sub, town, vill = key
        code24 = norm_city_code(cty, sub)
        hit = cw.get((code24, town, vill)) if code24 else None
        if hit:
            region, county, dist_no = hit
        else:
            cname = county_name(city_map, cty, sub)
            cname = RENAME.get(cname, cname)
            region = COUNTY_TO_REGION.get(cname, "其餘縣市與離島")
            county = cname
            dist_no = party_dist.get(key, "1")
        # 縣市碼欄：能對 2024 就寫五碼，否則保留「省市+子碼」
        city_code_out = code24 or (cty + (sub if sub != "000" else ""))
        name = vill_name.get(key, vill)
        dpp = gv.get("民進黨", 0)
        kmt = gv.get("國民黨", 0)
        tpp = gv.get("民眾黨", 0)  # 親民
        gre = gv.get("綠系小黨", 0)
        loc = gv.get("地方型", 0)
        oth = gv.get("其他", 0)
        total = dpp + kmt + tpp + gre + loc + oth
        pd = pres_v.get(key, {})
        rows_out.append({
            "區": region, "縣市": county, "現行選區": dist_no,
            "縣市碼": city_code_out, "鄉鎮碼": town, "村里碼": vill, "村里": name,
            "政黨票": total, "民進黨": dpp, "國民黨": kmt, "民眾黨": tpp,
            "綠系小黨": gre, "地方型": loc, "其他": oth,
            "總統_民進黨": pd.get("民進黨", 0), "總統_國民黨": pd.get("國民黨", 0),
            "總統_民眾黨": pd.get("民眾黨", 0),
        })
        for raw_k, v in gv.items():
            if raw_k.startswith("_raw_"):
                list_by_region[region][raw_k[5:]] += v

    rows_out.sort(key=lambda r: (r["區"], r["縣市碼"], int(r["現行選區"] or 0), r["鄉鎮碼"], r["村里碼"]))
    vill_path = os.path.join(DATA, f"村里-{year}.csv")
    fields = ["區", "縣市", "現行選區", "縣市碼", "鄉鎮碼", "村里碼", "村里", "政黨票",
              "民進黨", "國民黨", "民眾黨", "綠系小黨", "地方型", "其他",
              "總統_民進黨", "總統_國民黨", "總統_民眾黨"]
    with open(vill_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)

    # 名單：各區真實黨名
    parties = sorted({p for d in list_by_region.values() for p in d})
    list_path = os.path.join(DATA, f"名單-{year}.csv")
    with open(list_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["區"] + parties)
        for reg in ["臺北市", "新北市", "桃園＋新竹縣市", "臺中＋彰化", "雲嘉南", "高屏", "其餘縣市與離島", "澎金馬"]:
            w.writerow([reg] + [list_by_region[reg].get(p, 0) for p in parties])

    tot = sum(r["政黨票"] for r in rows_out)
    print(year, "villages", len(rows_out), "party_votes", tot,
          "dpp", sum(r["民進黨"] for r in rows_out),
          "kmt", sum(r["國民黨"] for r in rows_out),
          "mid", sum(r["民眾黨"] for r in rows_out))


def main():
    build_year(
        2016,
        ("2016總統立委", "不分區政黨"),
        ("2016總統立委", "總統"),
        "elctks_T4.csv", "elcand_T4.csv", "elbase_T4.csv", "elpaty.csv",
        "elctks_P1.csv", "elcand_P1.csv",
    )
    build_year(
        2012,
        ("20120114-總統及立委", "不分區政黨"),
        ("20120114-總統及立委", "總統"),
        "elctks.csv", "elcand.csv", "elbase.csv", "elpaty.csv",
        "elctks.csv", "elcand.csv",
    )


if __name__ == "__main__":
    main()
