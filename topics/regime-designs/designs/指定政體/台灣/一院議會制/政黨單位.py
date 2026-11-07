"""台灣單一選區多黨孔多賽共用模組（一院議會制、一院總統制-測試、兩院議會制三夾共用）。

將村里政黨票的「綠系小黨／地方型／其他」依各區實際政黨名單得票（名單-YYYY.csv）拆回各真實政黨，
讓所有實際參選且具明確政治座標的政黨皆可作為單一選區候選人進入 top-k／全候選人孔多賽對決。
"""
import os

CAND_PARTIES = [
    "台灣基進", "台聯", "時代力量", "綠黨", "綠黨社會民主黨聯盟", "綠黨與環境團體聯盟",
    "小民參政歐巴桑聯盟", "民進黨", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨",
]
G_MOD = ["綠黨", "綠黨與環境團體聯盟", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟"]

NORM = {
    "民主進步黨": "民進黨", "中國國民黨": "國民黨", "台灣民眾黨": "民眾黨",
    "台灣團結聯盟": "台聯", "台灣綠黨": "綠黨",
}
GREEN_RAW = {
    "時代力量", "台灣團結聯盟", "綠黨", "台灣綠黨", "綠黨社會民主黨聯盟",
    "自由台灣黨", "社會民主黨", "台灣基進", "一邊一國行動黨", "喜樂島聯盟",
    "台澎黨", "台灣獨立黨", "樹黨",
}


def tw_orders(q):
    """各政黨選民的完整排序分布（參數 q 對齊 生態模型.py 的三黨偏好比例）。"""
    qd, qk, qt = q["民進黨"], q["國民黨"], q["民眾黨"]
    return {
        "民進黨": [
            (qd, ["民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"]),
            (1 - qd, ["民進黨", "台聯", "台灣基進"] + G_MOD + ["時代力量", "國民黨", "無黨籍／地方", "親民黨", "民眾黨", "新黨"]),
        ],
        "國民黨": [
            (qk * 0.55, ["國民黨", "無黨籍／地方", "親民黨", "新黨", "民眾黨", "民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"]),
            (qk * 0.45, ["國民黨", "民眾黨", "無黨籍／地方", "親民黨", "新黨", "民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"]),
            (1 - qk, ["國民黨", "無黨籍／地方", "新黨", "民進黨", "民眾黨", "親民黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"]),
        ],
        "民眾黨": [
            (qt, ["民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨", "時代力量"] + G_MOD + ["民進黨", "台聯", "台灣基進"]),
            (1 - qt, ["民眾黨", "時代力量"] + G_MOD + ["民進黨", "親民黨", "無黨籍／地方", "國民黨", "台聯", "台灣基進", "新黨"]),
        ],
        "親民黨": [
            (qt, ["親民黨", "無黨籍／地方", "國民黨", "民眾黨", "新黨", "時代力量"] + G_MOD + ["民進黨", "台聯", "台灣基進"]),
            (1 - qt, ["親民黨", "民眾黨", "無黨籍／地方", "時代力量"] + G_MOD + ["民進黨", "國民黨", "新黨", "台聯", "台灣基進"]),
        ],
        "無黨籍／地方": [
            (1.0, ["無黨籍／地方", "國民黨", "親民黨", "民眾黨", "新黨", "民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"]),
        ],
        "時代力量": [
            (1.0, ["時代力量"] + G_MOD + ["民進黨", "台灣基進", "台聯", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"]),
        ],
        "綠黨": [(1.0, G_MOD + ["時代力量", "民進黨", "台灣基進", "台聯", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "綠黨社會民主黨聯盟": [(1.0, G_MOD + ["時代力量", "民進黨", "台灣基進", "台聯", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "綠黨與環境團體聯盟": [(1.0, G_MOD + ["時代力量", "民進黨", "台灣基進", "台聯", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "小民參政歐巴桑聯盟": [(1.0, ["小民參政歐巴桑聯盟"] + G_MOD[:3] + ["時代力量", "民進黨", "台灣基進", "台聯", "民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "台灣基進": [(1.0, ["台灣基進", "台聯", "民進黨", "時代力量"] + G_MOD + ["民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "台聯": [(1.0, ["台聯", "台灣基進", "民進黨", "時代力量"] + G_MOD + ["民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "新黨": [(1.0, ["新黨", "國民黨", "親民黨", "無黨籍／地方", "民眾黨", "民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"])],
        "綠系其他": [(1.0, ["台灣基進", "台聯", "民進黨", "時代力量"] + G_MOD + ["民眾黨", "親民黨", "無黨籍／地方", "國民黨", "新黨"])],
        "地方其他": [(1.0, ["無黨籍／地方", "國民黨", "親民黨", "新黨", "民眾黨", "民進黨"] + G_MOD + ["時代力量", "台聯", "台灣基進"])],
    }


def condorcet_multi(fp, q, k=3):
    """對選區第一偏好字典 fp 取前 k 名（得票 > 0）跑孔多賽完成法（循環時 Ranked Pairs）。
    回傳 (勝者, 是否循環, 兩兩對決表, 決選名單, 第一偏好第一名)。"""
    ords = tw_orders(q)
    cands = [p for p in CAND_PARTIES if fp.get(p, 0) > 0]
    fin = sorted(cands, key=lambda p: (-fp[p], p))[:k]
    P = {(a, b): 0.0 for a in fin for b in fin if a != b}
    for g, val in fp.items():
        if val <= 0 or g not in ords:
            continue
        for w, od in ords[g]:
            rr = [x for x in dict.fromkeys(od) if x in fin]
            for i, a in enumerate(rr):
                for b in rr[i + 1:]:
                    P[(a, b)] += val * w
    win = next((a for a in fin if all(P[(a, b)] > P[(b, a)] for b in fin if b != a)), None)
    cyc = win is None
    if cyc:
        wins = sorted(((P[(a, b)], a, b) for a in fin for b in fin if a != b and P[(a, b)] > P[(b, a)]), reverse=True)
        locked = set()

        def reach(x, y):
            st, seen = [x], set()
            while st:
                u = st.pop()
                if u == y:
                    return True
                seen.add(u)
                st += [c2 for a2, c2 in locked if a2 == u and c2 not in seen]
            return False

        for _, a, b in wins:
            if not reach(b, a):
                locked.add((a, b))
        win = next(a for a in fin if not any(c2 == a for _, c2 in locked))
    return win, cyc, P, fin, fin[0]


def region_minor_shares(lmap, year, regions):
    """由 名單-YYYY.csv 算出各區的綠系小黨內部占比與非綠小黨內部占比。"""
    reg_green, reg_non_green = {}, {}
    for reg in list(regions) + ["澎金馬"]:
        src_reg = "其餘縣市與離島" if (reg == "澎金馬" and not sum(lmap.get("澎金馬", {}).values())) else reg
        lr = lmap[src_reg]
        g_dict, ng_dict = {}, {}
        for raw_p, v in lr.items():
            if v <= 0 or raw_p in ("民主進步黨", "中國國民黨", "台灣民眾黨"):
                continue
            if year < 2020 and raw_p == "親民黨":
                continue
            p = NORM.get(raw_p, raw_p)
            if raw_p in GREEN_RAW:
                key = p if p in CAND_PARTIES else "綠系其他"
                g_dict[key] = g_dict.get(key, 0) + v
            else:
                key = p if p in CAND_PARTIES else "地方其他"
                ng_dict[key] = ng_dict.get(key, 0) + v
        gs, ngs = sum(g_dict.values()) or 1, sum(ng_dict.values()) or 1
        reg_green[reg] = {p: v / gs for p, v in g_dict.items()}
        reg_non_green[reg] = {p: v / ngs for p, v in ng_dict.items()}
    return reg_green, reg_non_green


def village_party_prefs(villages, reg, year, mode, reg_green=None, reg_non_green=None):
    """一選區村里列表 → 各真實政黨第一偏好份額字典。"""
    if mode == "總統":
        mid = "親民黨" if year < 2020 else "民眾黨"
        t = {
            "民進黨": sum(int(r["總統_民進黨"]) for r in villages),
            "國民黨": sum(int(r["總統_國民黨"]) for r in villages),
            mid: sum(int(r["總統_民眾黨"]) for r in villages),
        }
        s = sum(t.values()) or 1
        return {k: v / s for k, v in t.items() if v > 0}

    mid = "親民黨" if year < 2020 else "民眾黨"
    d = {
        "民進黨": float(sum(int(r["民進黨"]) for r in villages)),
        "國民黨": float(sum(int(r["國民黨"]) for r in villages)),
        mid: float(sum(int(r["民眾黨"]) for r in villages)),
    }
    gv = sum(int(r["綠系小黨"]) for r in villages)
    ngv = sum(int(r["地方型"]) + int(r.get("其他", 0) or 0) for r in villages)
    if gv > 0 and reg_green and reg in reg_green:
        for p, sh in reg_green[reg].items():
            d[p] = d.get(p, 0.0) + gv * sh
    elif gv > 0:
        d["綠系其他"] = gv
    if ngv > 0 and reg_non_green and reg in reg_non_green:
        for p, sh in reg_non_green[reg].items():
            d[p] = d.get(p, 0.0) + ngv * sh
    elif ngv > 0:
        d["地方其他"] = ngv
    s = sum(d.values()) or 1.0
    return {k: v / s for k, v in d.items() if v > 0}


def decompose_term_prefs(fp, lst=None):
    """把生態模型 TERMS 的「綠系小黨／地方型」拆回真實政黨候選人。"""
    d = {k: v for k, v in fp.items() if k not in ("綠系小黨", "地方型")}
    g = fp.get("綠系小黨", 0.0)
    l = fp.get("地方型", 0.0)
    if g > 0:
        w_npp = lst.get("時代力量", 5) if lst else 5
        w_grn = lst.get("綠黨與環境團體聯盟", 4) if lst else 4
        w_tsp = lst.get("台灣基進", 3) if lst else 3
        gt = w_npp + w_grn + w_tsp
        d["時代力量"] = g * w_npp / gt
        d["綠黨與環境團體聯盟"] = g * w_grn / gt
        d["台灣基進"] = g * w_tsp / gt
    if l > 0:
        d["無黨籍／地方"] = l
    return d
