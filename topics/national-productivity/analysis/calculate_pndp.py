#!/usr/bin/env python3
"""生產性國內淨產值（PNDP）：17 國（屬地）2024 年核算。

    python calculate_pndp.py          # 印出表格、寫出 pndp_2024.json

定義（見 outputs/國家生產力指標（PNDP）….md §2）：
    NDP   ＝ GDP − 固定資本消耗（全體）
    地租  ＝（不動產業淨營業盈餘 ＋ 不動產業其他生產稅淨額）× λ
           λ ＝ 土地 ／（土地 ＋ 住宅 ＋ 其他建物與構造物）（國家資產負債表，淨值）
    PNDP-A ＝ NDP − 地租（只扣不動產地租；建物的淨報酬保留）
    PNDP-B ＝ PNDP-A − 天然資源租（世界銀行 NY.GDP.TOTL.RT.ZS，最新 2021 年占 GDP 比 × 2024 GDP）

資料（analysis/資料/，皆 2024 年；下載日 2026-11-10）：
- OECD SDMX：DSD_NAMAIN10@DF_TABLE1_EXPENDITURE（GDP）、DF_TABLE6（各業 B1G、P51C、B2A3N、D29X39；實體部門＝A 農林漁、B 礦、C 製造、D 電力燃氣、E 用水廢棄物、F 營造）、
  DF_TABLE3（人口）、DF_TABLE4（匯率、PPP）；DSD_NASEC10@DF_TABLE9B（土地 N211N、住宅 N111N、其他建物 N112N）。
- 台灣：主計總處《國民所得統計年報 113 年》表 4（2024 年各業生產毛額與要素所得）；
  國富統計 2024 年底（國富毛額 330.11 兆元；土地 40.63%、房屋及營建工程 23.17%）。
- 官方未公布土地價值者（美、波、匈、義、西、紐、丹）：λ 為估計，見 LAMBDA_EST 與文件 §3.3。
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "資料")
Y = "2024"
ORDER = [("台美日韓", ["TWN", "USA", "JPN", "KOR"]), ("英法德荷", ["GBR", "FRA", "DEU", "NLD"]), ("波匈捷", ["POL", "HUN", "CZE"]),
         ("斯洛伐克", ["SVK"]), ("義西", ["ITA", "ESP"]), ("澳紐", ["AUS", "NZL"]), ("丹麥", ["DNK"])]
NAME = {"TWN": "台灣", "USA": "美國", "JPN": "日本", "KOR": "南韓", "GBR": "英國", "FRA": "法國", "DEU": "德國", "NLD": "荷蘭",
        "POL": "波蘭", "HUN": "匈牙利", "CZE": "捷克", "SVK": "斯洛伐克", "ITA": "義大利", "ESP": "西班牙", "AUS": "澳洲", "NZL": "紐西蘭", "DNK": "丹麥"}
CUR = {"TWN": "TWD", "USA": "USD", "JPN": "JPY", "KOR": "KRW", "GBR": "GBP", "FRA": "EUR", "DEU": "EUR", "NLD": "EUR", "POL": "PLN",
       "HUN": "HUF", "CZE": "CZK", "SVK": "EUR", "ITA": "EUR", "ESP": "EUR", "AUS": "AUD", "NZL": "NZD", "DNK": "DKK"}
# 官方沒有土地價值的國家：λ 估計值（中值, 下限, 上限, 依據）
LAMBDA_EST = {
    "USA": (0.40, 0.35, 0.45, "FHFA（Davis, Larson, Oliner, Shui）：住宅土地占房價 2022 年 39.9%"),
    "POL": (0.27, 0.20, 0.35, "同區捷克 0.29、斯洛伐克 0.24 的平均"),
    "HUN": (0.27, 0.20, 0.35, "同區捷克 0.29、斯洛伐克 0.24 的平均"),
    "ITA": (0.45, 0.35, 0.55, "介於法國 0.50 與德國 0.35；義大利央行研究指戰後房價上漲多來自土地"),
    "ESP": (0.44, 0.35, 0.55, "西班牙研究：2010 年土地占房價約 44%"),
    "NZL": (0.60, 0.50, 0.70, "澳洲 0.58；紐西蘭住宅價值以土地為主"),
    "DNK": (0.40, 0.30, 0.50, "介於德國 0.35 與荷蘭 0.49"),
}
# 台灣 2024（新臺幣百萬元）：主計總處《國民所得統計年報 113 年》表 4；國富統計 2024 年底（百萬元）
TWN = dict(gdp=25_737_088, cfc=4_313_370, nos_L=1_423_531, tax_L=74_389, va_L=1_962_109, cfc_L=339_513,
           va_imp=1_716_498 - 227_875, va_agri=373_949, cfc_agri=29_548, va_ind=10_365_317, cfc_ind=2_380_398,
           land=0.4063 * 330.11e6, struct=0.2317 * 330.11e6, pop=23.40e6, fx=32.11, ppp=None)

def rows(f):
    with open(os.path.join(D, f), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))

def pick(rs, **kw):
    out = {}
    for x in rs:
        if x["OBS_VALUE"] and all(x[k] == v for k, v in kw.items()):
            out[x["REF_AREA"]] = float(x["OBS_VALUE"]) * 10 ** int(x["UNIT_MULT"] or 0)
    return out

def load():
    t6, t6r, t1, t3, t4, t9 = (rows(f) for f in ("oecd_table6_L_total.csv", "oecd_table6_real_sectors.csv", "oecd_table1_gdp.csv",
                                                 "oecd_table3_pop.csv", "oecd_table4_fx_ppp.csv", "oecd_table9b_balance.csv"))

    def g(rs, y=Y, **kw):
        return pick(rs, TIME_PERIOD=y, **kw)

    data = {"gdp": g(t1, TRANSACTION="B1GQ"), "cfc": g(t6, TRANSACTION="P51C", ACTIVITY="_T"),
            "nos_L": g(t6, TRANSACTION="B2A3N", ACTIVITY="L"), "tax_L": g(t6, TRANSACTION="D29X39", ACTIVITY="L"),
            "va_L": g(t6, TRANSACTION="B1G", ACTIVITY="L"), "cfc_L": g(t6, TRANSACTION="P51C", ACTIVITY="L"),
            "va_imp": g(t6, TRANSACTION="B1G", ACTIVITY="L68A"), "pop": g(t3, TRANSACTION="POP"),
            "fx": g(t4, TRANSACTION="EXC_A"), "ppp": g(t4, TRANSACTION="PPP_B1GQ")}
    for k, acts in (("agri", "A"), ("ind", "BCDE"), ("con", "F")):
        for tr, pre in (("B1G", "va_"), ("P51C", "cfc_")):
            tot = {}
            for a in acts:
                for c, val in g(t6r, TRANSACTION=tr, ACTIVITY=a).items():
                    tot[c] = tot.get(c, 0) + val
            data[pre + k] = tot
    filled = []
    # 紐西蘭等 2024 年缺項：以 2023 年占 GDP 比例推 2024（標註）
    gdp23 = g(t1, "2023", TRANSACTION="B1GQ")
    for k, tr, act in (("cfc", "P51C", "_T"), ("nos_L", "B2A3N", "L"), ("tax_L", "D29X39", "L"), ("va_L", "B1G", "L"), ("cfc_L", "P51C", "L")):
        v23 = g(t6, "2023", TRANSACTION=tr, ACTIVITY=act)
        for c in v23:
            if c not in data[k] and c in data["gdp"] and c in gdp23:
                data[k][c] = v23[c] * data["gdp"][c] / gdp23[c]
                filled.append(f"{NAME[c]} {k}（2023 年占 GDP 比例推 2024）")
    # 資產負債表：取 ≤2024 的最近一年
    bal = {}
    for x in t9:
        a = x["INSTR_ASSET"]
        if a in ("N211N", "N111N", "N112N") and x["OBS_VALUE"] and x["SECTOR"] == "S1" and x["TIME_PERIOD"] <= Y:
            key = (a, x["REF_AREA"])
            if key not in bal or x["TIME_PERIOD"] > bal[key][0]:
                bal[key] = (x["TIME_PERIOD"], float(x["OBS_VALUE"]) * 10 ** int(x["UNIT_MULT"] or 0))
    for k, acts in (("agri", "A"), ("ind", "BCDE"), ("con", "F")):
        for tr, pre in (("B1G", "va_"), ("P51C", "cfc_")):
            for c in gdp23:
                if c in data[pre + k] or c not in data["gdp"]:
                    continue
                v23 = sum(g(t6r, "2023", TRANSACTION=tr, ACTIVITY=a).get(c, 0) for a in acts)
                if v23:
                    data[pre + k][c] = v23 * data["gdp"][c] / gdp23[c]
                    filled.append(f"{NAME[c]} {pre + k}（2023 年占 GDP 比例推 2024）")
    with open(os.path.join(D, "worldbank_resource_rents.json"), encoding="utf-8") as fh:
        wb = json.load(fh)[1]
    rent = {}
    for x in wb:
        if x["value"] is not None:
            c = x["countryiso3code"]
            if c not in rent or x["date"] > rent[c][0]:
                rent[c] = (x["date"], x["value"] / 100)
    return data, bal, rent, filled

def compute():
    data, bal, rent, filled = load()
    out = {}
    for grp, cs in ORDER:
        for c in cs:
            if c == "TWN":
                v = {k: (x * 1e6 if k not in ("pop", "fx", "ppp", "land", "struct") and x is not None else x) for k, x in TWN.items()}
                v["va_con"] = v["cfc_con"] = 0.0          # 台灣「工業」已含營造業
                lam = TWN["land"] / (TWN["land"] + TWN["struct"])
                lam_lo = lam_hi = None
                lam_src, lam_y = "國富統計 2024 年底：土地／（土地＋房屋及營建工程）", "2024"
                res = ("—", 0.0)
            else:
                v = {k: data[k].get(c) for k in data}
                land, dw, ob = (bal.get((a, c)) for a in ("N211N", "N111N", "N112N"))
                if land and dw and ob:
                    lam = land[1] / (land[1] + dw[1] + ob[1])
                    lam_lo = lam_hi = None
                    lam_src, lam_y = "OECD 國家資產負債表：土地／（土地＋住宅＋其他建物與構造物）", land[0]
                else:
                    lam, lam_lo, lam_hi, lam_src = LAMBDA_EST[c]
                    lam_y = "估計"
                res = rent.get(c, ("—", 0.0))
            ndp = v["gdp"] - v["cfc"]
            base = v["nos_L"] + (v["tax_L"] or 0)
            lr = base * lam
            pndp_a = ndp - lr
            rr = v["gdp"] * res[1]
            pndp_b = pndp_a - rr
            real = sum((v.get("va_" + s) or 0) - (v.get("cfc_" + s) or 0) for s in ("agri", "ind", "con"))
            fx, ppp, pop = v["fx"], v.get("ppp"), v["pop"]
            r = dict(name=NAME[c], group=grp, cur=CUR[c], gdp=v["gdp"], cfc=v["cfc"], ndp=ndp, re_va=v["va_L"], re_base=base,
                     imp=v.get("va_imp"), lam=lam, lam_lo=lam_lo, lam_hi=lam_hi, lam_src=lam_src, lam_year=lam_y,
                     land_rent=lr, res_rent=rr, res_year=res[0], pndp_a=pndp_a, pndp_b=pndp_b, real_nva=real,
                     pop=pop, fx=fx, ppp=ppp,
                     ndp_usd=ndp / fx / 1e9, pndp_a_usd=pndp_a / fx / 1e9, pndp_b_usd=pndp_b / fx / 1e9,
                     ndp_pc_usd=ndp / fx / pop, pndp_a_pc_usd=pndp_a / fx / pop, pndp_b_pc_usd=pndp_b / fx / pop,
                     pndp_a_pc_ppp=(pndp_a / ppp / pop) if ppp else None,
                     gap=lr / ndp, gap_b=(lr + rr) / ndp, re_share=v["va_L"] / v["gdp"], real_share=real / ndp,
                     land_gdp=None)
            if lam_lo is not None:
                r["gap_lo"], r["gap_hi"] = base * lam_lo / ndp, base * lam_hi / ndp
            out[c] = r
    return out, filled

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    out, filled = compute()
    print("| 國 | λ | 不動產業占 GDP | 地租／NDP | ＋資源租／NDP | PNDP-A（十億美元） | 人均 NDP | 人均 PNDP-A | 人均 PNDP-A（PPP） | 實體部門／NDP |")
    for c, r in out.items():
        ppp = f"{r['pndp_a_pc_ppp']:,.0f}" if r["pndp_a_pc_ppp"] else "—"
        rng = f"（{r['gap_lo']*100:.1f}–{r['gap_hi']*100:.1f}）" if "gap_lo" in r else ""
        print(f"| {r['name']} | {r['lam']:.2f}{'*' if r['lam_lo'] is not None else ''} | {r['re_share']*100:.1f}% | {r['gap']*100:.1f}%{rng} | "
              f"{r['gap_b']*100:.1f}% | {r['pndp_a_usd']:,.0f} | {r['ndp_pc_usd']:,.0f} | {r['pndp_a_pc_usd']:,.0f} | {ppp} | {r['real_share']*100:.1f}% |")
    print("補值：", filled)
    with open(os.path.join(HERE, "pndp_2024.json"), "w", encoding="utf-8") as fh:
        json.dump({"countries": out, "filled": filled}, fh, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
