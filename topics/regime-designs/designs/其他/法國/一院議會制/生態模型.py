"""法國一院議會制：預期政治生態的機械效應模型。

把 14-預期政治生態.md 的「得票 → 選制 → 席次」算出來。所有輸入都是**假設**（見 14 §2），
出發點是 2024 年國民議會選舉第一輪。改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 14 用的數字（政黨層級主算，見 政黨單位.py）
    python 生態模型.py --sweep    # 舊版四陣營模型的第二偏好敏感度（僅供對照）

主算（方案 A）：所有表用同一組 10 個政黨名稱；2024 實際地理逐黨縮放到各屆假設份額（PARTY_TERMS）。
單一席次 230：top-3 孔多賽（第一輪取第一偏好前 3 名，第二輪孔多賽完成法；循環時 Ranked Pairs）。
複數席次 170：14 區，聖拉古，無門檻。
行政首長：全院 400（單一＋複數）記名排名，須 ≥201。
下方 BLOCS／ORDERS／SPLIT 等四陣營定義只供 近期大選重算.py 的「2024 第一輪聯合推人原樣」對照與 --sweep 使用。
"""
import random
import sys

RN, G, C, LR, O = "國民聯盟系", "左翼陣營", "中間陣營", "共和黨系", "其他"
BLOCS = [RN, G, C, LR]

# 各陣營選民的完整排序（比例）。「其他」（各類右派、左派小黨、地方派）沒有自己的候選人進前 3。
ORDERS = {
    RN: [(0.7, [RN, LR, C, G]), (0.2, [RN, C, LR, G]), (0.1, [RN, G, C, LR])],
    G: [(0.8, [G, C, LR, RN]), (0.1, [G, C, RN, LR]), (0.1, [G, RN, C, LR])],
    C: [(0.5, [C, LR, G, RN]), (0.4, [C, G, LR, RN]), (0.1, [C, LR, RN, G])],
    LR: [(0.6, [LR, C, RN, G]), (0.4, [LR, RN, C, G])],
    O: [(0.4, [LR, C, RN, G]), (0.4, [G, C, LR, RN]), (0.2, [C, LR, G, RN])],
}

# 14 區：名稱、人口（萬，約）、陣營偏移（國民聯盟系、左翼，百分點，示意）
REGIONS = [
    ("法蘭西島－北", 410, -10, +12),
    ("法蘭西島－中", 410, -12, +8),
    ("法蘭西島－南", 450, -6, +4),
    ("奧弗涅－羅納－阿爾卑斯－北", 410, -2, 0),
    ("奧弗涅－羅納－阿爾卑斯－南", 410, +2, -2),
    ("新阿基坦", 610, 0, +2),
    ("奧克西塔尼", 610, +4, +3),
    ("上法蘭西", 600, +12, -2),
    ("大東部", 560, +8, -4),
    ("普羅旺斯－阿爾卑斯－蔚藍海岸＋科西嘉", 540, +12, -6),
    ("盧瓦爾河地區＋布列塔尼西", 560, -8, 0),
    ("諾曼第＋布列塔尼東", 520, +2, -2),
    ("中央－盧瓦爾河谷＋勃艮第－弗朗什孔泰", 540, +5, -3),
    ("海外省與海外領地", 220, -5, +10),
]
LIST_M = [10, 10, 11, 10, 10, 14, 14, 14, 14, 14, 14, 13, 14, 8]

# 陣營內部各黨在區域當選者中的比例（假設），與名單上的黨
SPLIT = {
    G: [("不屈法國系", 0.40), ("社會黨系", 0.40), ("生態派", 0.15), ("共產黨系", 0.05)],
    C: [("復興系（中間）", 0.75), ("民主運動", 0.25)],
    RN: [("國民聯盟系", 1.0)],
    LR: [("共和黨系", 1.0)],
}


def largest_remainder(weights, seats):
    tot = sum(weights.values())
    q = {k: v * seats / tot for k, v in weights.items()}
    got = {k: int(v) for k, v in q.items()}
    for k in sorted(q, key=lambda k: q[k] - got[k], reverse=True)[:seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def shifted(fp, rn, g):
    d = dict(fp)
    d[RN] = max(3.0, d[RN] + rn)
    d[G] = max(3.0, d[G] + g)
    t = sum(d.values())
    return {k: v * 100 / t for k, v in d.items()}


def condorcet(fp, orders=ORDERS):
    finals = sorted(BLOCS, key=lambda p: fp.get(p, 0), reverse=True)[:3]
    ballots = {}
    for grp, share in fp.items():
        for w, order in orders[grp]:
            r = tuple(p for p in order if p in finals)
            ballots[r] = ballots.get(r, 0) + share * w
    P = {(a, c): sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
         for a in finals for c in finals if a != c}
    for a in finals:
        if all(P[(a, c)] > P[(c, a)] for c in finals if c != a):
            majority = fp[a] > 50
            return a, False, majority
    wins = sorted(((P[(a, c)], a, c) for a in finals for c in finals
                   if a != c and P[(a, c)] > P[(c, a)]), reverse=True)
    losers = {c for _, _, c in wins[:2]}
    return next(a for a in finals if a not in losers), True, False


def single_seats(fp, orders=ORDERS, seed=5):
    rng = random.Random(seed)
    seats = largest_remainder({r[0]: r[1] for r in REGIONS}, 230)
    out = {b: 0 for b in BLOCS}
    cyc = safe = 0
    for name, _, rn, g in REGIONS:
        for _ in range(seats[name]):
            d = shifted(fp, rng.gauss(rn, 7.0), rng.gauss(g, 6.0))
            w, c, maj = condorcet(d, orders)
            out[w] += 1
            cyc += c
            safe += maj
    return out, cyc, safe


def by_party(bloc_seats):
    out = {}
    for b, n in bloc_seats.items():
        parts = largest_remainder({p: w for p, w in SPLIT[b]}, n) if n else {}
        for p, k in parts.items():
            out[p] = out.get(p, 0) + k
    return out


def list_seats(lst):
    shares = {p: v for p, v in lst.items() if p != O}
    for i in range(6):
        shares[f"其他{i}"] = lst[O] / 6
    out = {p: 0 for p in shares}
    for (name, _, rn, g), m in zip(REGIONS, LIST_M):
        d = dict(shares)
        d["國民聯盟系"] = max(1.0, d["國民聯盟系"] + rn)
        for p in ("不屈法國系", "社會黨系", "生態派", "共產黨系"):
            d[p] = max(0.5, d[p] * (1 + g / 30))
        for p, n in sainte_lague(d, m).items():
            out[p] += n
    other = sum(v for k, v in out.items() if k.startswith("其他"))
    out = {k: v for k, v in out.items() if not k.startswith("其他")}
    out["地方與無黨籍"] = other
    return out


TERMS = {
    # 屆: (區域陣營第一偏好, 名單政黨得票)
    3: ({RN: 33, G: 27, C: 22, LR: 9, O: 9},
        {"國民聯盟系": 31, "不屈法國系": 11, "社會黨系": 11, "生態派": 5, "共產黨系": 2,
         "復興系（中間）": 14, "民主運動": 5, "共和黨系": 9, O: 12}),
    6: ({RN: 35, G: 26, C: 20, LR: 10, O: 9},
        {"國民聯盟系": 33, "不屈法國系": 10, "社會黨系": 12, "生態派": 5, "共產黨系": 2,
         "復興系（中間）": 12, "民主運動": 5, "共和黨系": 10, O: 11}),
}


NEED = 201

# 主算用：各屆政黨份額假設（%）。復興系含 Ensemble 盟友民主運動、地平線。
PARTY_TERMS = {
    3: {"國民聯盟系": 29.0, "復興系": 18.0, "社會黨系": 15.0, "不屈法國系": 10.0, "共和黨系": 10.0, "生態派": 6.0,
        "收復黨": 4.5, "共產黨系": 2.5, "鄉村聯盟": 2.5, "各類極左": 0.5, "其他": 2.0},
    6: {"國民聯盟系": 31.0, "復興系": 16.0, "社會黨系": 15.0, "共和黨系": 11.0, "不屈法國系": 9.5, "生態派": 6.0,
        "收復黨": 4.0, "共產黨系": 2.5, "鄉村聯盟": 2.5, "各類極左": 0.5, "其他": 2.0},
}

# 名單政黨 → 陣營（供全院首長計票）
PARTY_BLOC = {
    "國民聯盟系": RN,
    "不屈法國系": G, "社會黨系": G, "生態派": G, "共產黨系": G,
    "復興系（中間）": C, "民主運動": C,
    "共和黨系": LR,
}


def full_chamber(single_blocs, list_by_party):
    """單一（陣營）＋複數（政黨映到陣營）→ 全院四陣營席次。"""
    ch = {b: single_blocs.get(b, 0) for b in BLOCS}
    for p, n in list_by_party.items():
        b = PARTY_BLOC.get(p)
        if b:
            ch[b] += n
    return ch


def premier(chamber):
    """全院記名排名選首長：各陣營議員照該陣營選民主要排序投；過半 NEED。"""
    if max(chamber.values()) >= NEED:
        w = max(chamber, key=chamber.get)
        return w, f"單獨過半（{chamber[w]}≥{NEED}）", None
    ballots = {}
    for b, n in chamber.items():
        if not n:
            continue
        order = tuple(ORDERS[b][0][1])
        ballots[order] = ballots.get(order, 0) + n
    finals = [b for b in BLOCS if chamber.get(b)]
    P = {(a, c): sum(v for r, v in ballots.items() if a in r and c in r and r.index(a) < r.index(c))
         for a in finals for c in finals if a != c}
    winners = [a for a in finals if all(P[(a, c)] > P[(c, a)] for c in finals if c != a)]
    if winners:
        w = winners[0]
        return w, "孔多賽", {c: (P[(w, c)], P[(c, w)]) for c in finals if c != w}
    w = max(finals, key=lambda b: chamber[b])
    return w, "無孔多賽→最大陣營", None


def run(t, orders=ORDERS):
    dfp, lst = TERMS[t]
    blocs, cyc, safe = single_seats(dfp, orders)
    return blocs, by_party(blocs), list_seats(lst), cyc, safe


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if "--sweep" in sys.argv:
        dfp = TERMS[3][0]
        print("| 國民聯盟系選民把中間排在左翼前（其餘排共和黨系） | 單一 國民聯盟／左翼／中間／共和黨 |")
        print("|:--:|:--:|")
        for share in (0.0, 0.1, 0.2, 0.3):
            o = dict(ORDERS)
            o[RN] = [(0.9 - share, [RN, LR, C, G]), (share, [RN, C, LR, G]), (0.1, [RN, G, C, LR])]
            b, _, _ = single_seats(dfp, o)
            print(f"| {share:.0%} | {b[RN]}／{b[G]}／{b[C]}／{b[LR]} |")
        print()
        print("| 左翼選民把國民聯盟系排在中間前 | 單一 國民聯盟／左翼／中間／共和黨 |")
        print("|:--:|:--:|")
        for share in (0.05, 0.1, 0.2, 0.3):
            o = dict(ORDERS)
            o[G] = [(0.9 - share, [G, C, LR, RN]), (0.1, [G, C, RN, LR]), (share, [G, RN, C, LR])]
            b, _, _ = single_seats(dfp, o)
            print(f"| {share:.0%} | {b[RN]}／{b[G]}／{b[C]}／{b[LR]} |")
        return
    # 主算（方案 A）：政黨層級。2024 實際地理（政黨單位.party_units_2024）逐黨縮放到各屆假設份額，
    # 同一張新選區圖、top-3 孔多賽；名單 14 區聖拉古；首長、組閣同 近期大選重算。
    import 政黨單位 as PU
    base = PU.party_units_2024()
    for t, shares in PARTY_TERMS.items():
        print("（假設份額：" + "、".join(f"{p} {v:g}%" for p, v in shares.items()) + "）")
        PU.report(f"第 {t} 屆（推估）", PU.scale_by_party(base, shares))


if __name__ == "__main__":
    main()
