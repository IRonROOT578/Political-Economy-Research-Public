"""西班牙一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2023-07、2019-11 眾議院選舉
    python 生態模型.py --sweep      # 敏感度

得票：內政部 infoelectoral 的**逐市鎮**結果（約 8,100 市鎮），彙整成 資料/congreso-YYYY.csv；國外選民（CERA）不含。
各地同一政治空間的名單合成一格：PSOE（含 PSC 等）、SUMAR（2019 年為 Podemos 系、En Comú、Más País、Compromís）、
UPN（2019 年為 Navarra Suma）、地方（PRC、Teruel Existe、UPL、Existe）。
單一 210：依選舉人分到 13 區（最大餘數），區內依市鎮座標的 Hilbert 序連續切成選舉人相近的選區（可跨省界）；
選舉人超過一席半數的市鎮先等分成數塊（同一組成）。top-3 孔多賽，循環 Ranked Pairs，平手以排第一者多為先。
複數 140：13 區（安達魯西亞、馬德里、加泰隆尼亞＋巴利亞利、瓦倫西亞＋穆爾西亞各拆二），依選舉人最大餘數，聖拉古，
無法定門檻，M∈[8,16]（加那利群島例外）。
偏好：三維空間（經濟：左 −1 … 右 +1；領土：地方民族主義 −1 … 中央集權 +1；社會：進步 −1 … 保守 +1）。
每黨選民分三型＋均衡型。行政首長：全院 350 記名排名投票；須 ≥176 排在「維持空缺」之上。
"""
import csv
import io
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# (經濟, 領土, 社會)
POS = {
    "PSOE": (-0.4, 0.0, -0.5), "PP": (0.5, 0.6, 0.4), "VOX": (0.6, 1.0, 1.0), "SUMAR": (-0.8, -0.3, -0.9),
    "Cs": (0.4, 0.7, -0.2), "ERC": (-0.5, -1.0, -0.6), "JUNTS": (0.3, -1.0, 0.0), "PNV": (0.2, -0.8, 0.0),
    "BILDU": (-0.8, -1.0, -0.7), "BNG": (-0.7, -0.9, -0.6), "CC": (0.2, -0.5, 0.0), "UPN": (0.5, 0.8, 0.5),
    "CUP": (-1.0, -1.0, -1.0), "地方": (0.0, -0.3, 0.1),
}
OVERRIDE = {}
TYPES = [(0.25, 1.0, 0.5, 0.5), (0.25, 0.5, 1.0, 0.5), (0.25, 0.5, 0.5, 1.0), (0.25, 0.8, 0.8, 0.8)]
BALANCED = (0.8, 0.8, 0.8)
CURRENT = ["congreso-2023"]
PROVS = {1: "阿拉瓦", 2: "阿爾瓦塞特", 3: "阿利坎特", 4: "阿爾梅里亞", 5: "阿維拉", 6: "巴達霍斯", 7: "巴利亞利", 8: "巴塞隆納",
         9: "布哥斯", 10: "卡塞雷斯", 11: "加的斯", 12: "卡斯特利翁", 13: "雷阿爾城", 14: "哥多華", 15: "拉科魯尼亞", 16: "昆卡",
         17: "赫羅納", 18: "格拉納達", 19: "瓜達拉哈拉", 20: "吉普斯夸", 21: "韋爾瓦", 22: "韋斯卡", 23: "哈恩", 24: "萊昂",
         25: "萊里達", 26: "拉里奧哈", 27: "盧戈", 28: "馬德里", 29: "馬拉加", 30: "穆爾西亞", 31: "納瓦拉", 32: "奧倫塞",
         33: "阿斯圖里亞斯", 34: "帕倫西亞", 35: "拉斯帕爾馬斯", 36: "龐特韋德拉", 37: "薩拉曼卡", 38: "聖克魯斯-德特內里費",
         39: "坎塔布里亞", 40: "塞哥維亞", 41: "塞維亞", 42: "索里亞", 43: "塔拉戈納", 44: "特魯埃爾", 45: "托雷多",
         46: "瓦倫西亞", 47: "瓦拉多利德", 48: "比斯開", 49: "薩莫拉", 50: "薩拉戈薩", 51: "休達", 52: "梅利利亞"}
LIST_GROUPS = [   # (名稱, 省碼, 拆幾區)
    ("安達魯西亞", (4, 11, 14, 18, 21, 23, 29, 41, 51, 52), 2),
    ("馬德里", (28,), 2),
    ("加泰隆尼亞＋巴利亞利", (8, 17, 25, 43, 7), 2),
    ("瓦倫西亞＋穆爾西亞", (3, 12, 46, 30), 2),
    ("加利西亞＋阿斯圖里亞斯", (15, 27, 32, 36, 33), 1),
    ("卡斯提亞-萊昂＋坎塔布里亞＋埃斯特雷馬杜拉", (5, 9, 24, 34, 37, 40, 42, 47, 49, 39, 6, 10), 1),
    ("巴斯克＋納瓦拉＋拉里奧哈", (1, 20, 48, 31, 26), 1),
    ("卡斯提亞-拉曼查＋亞拉岡", (2, 13, 16, 19, 45, 22, 44, 50), 1),
    ("加那利", (35, 38), 1),
]
ISLAND = "加那利"
ACTUAL = {
    "congreso-2023": {"PP": 137, "PSOE": 121, "VOX": 33, "SUMAR": 31, "ERC": 7, "JUNTS": 7, "BILDU": 6, "PNV": 5, "BNG": 1,
                      "CC": 1, "UPN": 1},
    "congreso-2019": {"PSOE": 120, "PP": 89, "VOX": 52, "SUMAR": 38, "ERC": 13, "Cs": 10, "JUNTS": 8, "PNV": 6, "BILDU": 5,
                      "CUP": 2, "CC": 2, "UPN": 2, "地方": 2, "BNG": 1},
    "congreso-201904": {"PSOE": 123, "PP": 66, "Cs": 57, "SUMAR": 43, "VOX": 24, "ERC": 15, "JUNTS": 7, "PNV": 6, "BILDU": 4,
                        "CC": 2, "UPN": 2, "地方": 1},
    "congreso-201606": {"PP": 137, "PSOE": 85, "SUMAR": 71, "Cs": 32, "ERC": 9, "JUNTS": 8, "PNV": 5, "BILDU": 2, "CC": 1},
    "congreso-201512": {"PP": 123, "PSOE": 90, "SUMAR": 71, "Cs": 40, "ERC": 9, "JUNTS": 8, "PNV": 6, "BILDU": 2, "CC": 1},
}
SMD_TOTAL, LIST_TOTAL, NEED = 210, 140, 176


def pos(p):
    return OVERRIDE.get(CURRENT[0], {}).get(p, POS[p])


def hilbert(x, y, n=1 << 10):
    d, s = 0, n >> 1
    while s:
        rx, ry = int(x & s > 0), int(y & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        s >>= 1
    return d


def load(name):
    with open(os.path.join(HERE, "資料", f"{name}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][7:]
    return [(int(r[0]), r[2], float(r[4]), float(r[5]), int(r[6]), {c: int(v) for c, v in zip(cols, r[7:])},
             PROVS[int(r[0])]) for r in rows[1:]]


def largest_remainder(weights, seats, floor=0):
    got = {k: floor for k in weights}
    rest = seats - floor * len(weights)
    tot = sum(weights.values())
    q = {k: v * rest / tot for k, v in weights.items()}
    for k in q:
        got[k] += int(q[k])
    for k in sorted(q, key=lambda k: q[k] - int(q[k]), reverse=True)[:seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def rank_from(me, cands, w):
    a = pos(me)
    return sorted(cands, key=lambda c: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, pos(c), a)), c))


def voter_groups(parties, types):
    return [(p, t[0], rank_from(p, parties, t[1:])) for p in parties for t in types]


def pairwise_winner(cands, groups, weight):
    cands = sorted(cands)
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        v = weight(src) * w
        if not v:
            continue
        r = [c for c in order if c in cands]
        for i, a in enumerate(r):
            for b in r[i + 1:]:
                P[(a, b)] += v
    for a in cands:
        if all(P[(a, b)] > P[(b, a)] for b in cands if b != a):
            return a, False, P
    wins = sorted(((P[(a, b)], a, b) for a in cands for b in cands if a != b and P[(a, b)] > P[(b, a)]), reverse=True)
    locked = set()

    def reach(x, y):
        st, seen = [x], set()
        while st:
            u = st.pop()
            if u == y:
                return True
            for s, t in locked:
                if s == u and t not in seen:
                    seen.add(t)
                    st.append(t)
        return False
    for _, a, b in wins:
        if not reach(b, a):
            locked.add((a, b))
    top = [c for c in cands if not any(t == c for _, t in locked)] or list(cands)
    if len(top) > 1:                     # 平手：把他排第一的票較多者為先
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


def split_big(units, quota, kmap=None):
    """選舉人超過半席的市鎮等分成 k 塊；k 以 2023 年為準（kmap），各年一致。"""
    out = []
    for u in units:
        k = (kmap or {}).get((u[0], u[1])) or max(1, math.ceil(u[4] / (quota * 0.5)))
        if k == 1:
            out.append(u)
        else:
            out += [(u[0], f"{u[1]}#{i + 1}", u[2], u[3], u[4] / k, {c: v / k for c, v in u[5].items()}, u[6])
                    for i in range(k)]
    return out


def order(units):
    if not units:
        return units
    xs, ys = [u[2] for u in units], [u[3] for u in units]
    x0, y0 = min(xs), min(ys)
    span = max(max(xs) - x0, max(ys) - y0) or 1.0
    key = lambda u: (hilbert(int((u[2] - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1])
    return sorted(units, key=key)


def cut(rows, n, shift=False):
    target = sum(u[4] for u in rows) / n
    if shift and n > 1:
        acc, k = 0, 0
        while acc < target / 2:
            acc += rows[k][4]
            k += 1
        rows = rows[k:] + rows[:k]
    out, cur, acc = [], [], 0
    for u in rows:
        cur.append(u)
        acc += u[4]
        if acc >= target * (len(out) + 1) - u[4] / 2 and len(out) < n - 1:
            out.append(cur)
            cur = []
    out.append(cur)
    while not out[-1] and len(out) > 1 and len(out[-2]) > 1:
        out[-1].append(out[-2].pop())
    assert len(out) == n and all(out)
    return out


def layout():
    """13 區（四個大區以 2023 的市鎮序各切成兩塊）；單一與複數都依 2023 選舉人在 13 區間分配。"""
    units = load("congreso-2023")
    quota = sum(u[4] for u in units) / SMD_TOTAL
    kmap = {(u[0], u[1]): max(1, math.ceil(u[4] / (quota * 0.5))) for u in units}
    units = split_big(units, quota, kmap)
    names, region_of, regions = {}, {}, []
    for u in units:
        names[u[0]] = u[6]
    for name, provs, k in LIST_GROUPS:
        rows = order([u for u in units if u[0] in provs])
        parts = cut(rows, k) if k > 1 else [rows]
        for i, part in enumerate(parts):
            rname = name if k == 1 else f"{name}{'一二三'[i]}"
            regions.append((rname, sum(u[4] for u in part)))
            for u in part:
                region_of[(u[0], u[1])] = rname
    assert sorted(p for _, provs, _ in LIST_GROUPS for p in provs) == sorted(names)
    w = dict(regions)
    m = largest_remainder(w, LIST_TOTAL)
    smd = largest_remainder(w, SMD_TOTAL)
    assert all(8 <= v <= 16 for k, v in m.items() if k != ISLAND), m
    first = {}
    for name, provs, _ in LIST_GROUPS:
        for p in provs:
            first.setdefault(p, name if name in m else f"{name}一")
    return smd, m, names, region_of, first, quota, kmap


SMD_N, LIST_M, PROV_NAME, REGION_OF, FIRST_REGION, QUOTA, SPLIT_K = layout()


def region(u):
    return REGION_OF.get((u[0], u[1])) or REGION_OF.get((u[0], u[1].split("#")[0])) or FIRST_REGION[u[0]]


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    units = split_big(units, QUOTA, SPLIT_K)
    for reg, n in SMD_N.items():
        for part in cut(order([u for u in units if region(u) == reg]), n, shift):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    votes[c] = votes.get(c, 0) + v
            parties = sorted(p for p in votes if p in POS and votes[p] > 0)
            _g = voter_groups(parties, types)
            _w = lambda s: votes.get(s, 0)
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
            finals = _finals_for({p: votes[p] for p in parties}, k, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, _g, _w)[0], POS)
            w, cyc, _ = pairwise_winner(finals, _g, _w)
            out[w] = out.get(w, 0) + 1
            tot = sum(votes.values())
            stats["循環"] += cyc
            stats["第一偏好過半"] += votes[w] > tot / 2
            stats["非第一偏好第一名當選"] += w != finals[0]
            pv = {}
            for u in part:
                pv[u[6]] = pv.get(u[6], 0) + u[4]
            detail.append((reg, max(pv, key=pv.get), len(part), w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, tiny=6):
    out, acc = {}, {}
    for u in split_big(units, QUOTA, SPLIT_K):
        d = acc.setdefault(region(u), {})
        for c, v in u[5].items():
            d[c] = d.get(c, 0) + v
    for name, m in LIST_M.items():
        d = {c: v for c, v in acc[name].items() if v}
        o = d.pop("其他", 0)
        for i in range(tiny):
            d[f"其他{i}"] = o / tiny
        for p, n in sainte_lague(d, m).items():
            if n:
                key = "其他" if p.startswith("其他") else p
                out[key] = out.get(key, 0) + n
    return out


def head_of_gov(total):
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min(P[(w, b)] for b in parties if b != w)
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def coalition(total, pm, need=NEED):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, pos(p), pos(pm))) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(name, types=TYPES, k=3, shift=False, units=None, list_from=None):
    CURRENT[0] = name
    units = units or load(name)
    smd, stats, detail = single_seats(units, types, k, shift)
    lst = list_seats(load(list_from) if list_from else units)
    total = {p: smd.get(p, 0) + lst.get(p, 0) for p in set(smd) | set(lst)}
    return smd, lst, total, stats, detail


def national(units):
    t = {}
    for u in units:
        for c, v in u[5].items():
            t[c] = t.get(c, 0) + v
    s = sum(t.values())
    return {c: v * 100 / s for c, v in t.items() if v}


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def report(label, name, list_from=None):
    units = load(name)
    smd, lst, total, stats, detail = run(name, units=units, list_from=list_from)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
    if name in ACTUAL:
        print("實際 350：", fmt(ACTUAL[name]))
    print("單一 210：", fmt(smd), stats)
    print("複數 140：", fmt(lst))
    print("全院 350：", fmt(total))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥{NEED} {worst >= NEED}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣陣營（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by, bp = {}, {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
        bp.setdefault(d[1], {}).setdefault(d[3], 0)
        bp[d[1]][d[3]] += 1
    print("    各區單一：", "；".join(f"{r}（{SMD_N[r]}）{fmt(c)}" for r, c in by.items()))
    big = sorted(bp.items(), key=lambda x: -sum(x[1].values()))
    for p in ("PSOE", "PP", "VOX", "SUMAR", "PNV", "JUNTS", "ERC", "BILDU", "BNG", "CC"):
        provs = [f"{r}{c[p]}" for r, c in big if c.get(p)]
        print(f"    {p} 單一所在（以選區多數省計）：", "、".join(provs[:40]))
    combos = {}
    for d in detail:
        key = "／".join(sorted(d[4]))
        combos[key] = combos.get(key, 0) + 1
    print("    決選三人：", sorted(combos.items(), key=lambda x: -x[1])[:6])
    sh = sorted(d[5] for d in detail)
    print(f"    當選者第一偏好：中位 {sh[len(sh) // 2]:.0%}、最低 {sh[0]:.0%}")


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        out.append(u[:5] + ({c: (nv if c == party else x * (t - nv) / rest if rest else x) for c, x in u[5].items()},) + u[6:])
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    years = ("congreso-2023", "congreso-2019")
    if "--sweep" in sys.argv:
        cases = (("全部重經濟", [(1.0, 1.0, 0.5, 0.5)]), ("全部重領土", [(1.0, 0.5, 1.0, 0.5)]),
                 ("全部重社會", [(1.0, 0.5, 0.5, 1.0)]), ("全部均衡", [(1.0, 0.8, 0.8, 0.8)]))
        for label, types in cases:
            for name in years:
                smd, _, total, _, _ = run(name, types)
                w = head_of_gov(total)[0]
                print(f"{label} {name}：單一 {fmt(smd)}；首長 {w}；組閣 {coalition(total, w)}")
        for name in years:
            a = run(name, shift=True)
            b = run(name, k=2)
            print(f"{name} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{name} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for party in ("PP", "PSOE"):
            for pts in (-3, 3):
                smd, lst, total, _, _ = run("congreso-2023", units=swing(load("congreso-2023"), party, pts))
                w = head_of_gov(total)[0]
                print(f"2023 {party} {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {w}；組閣 {coalition(total, w)}")
        return
    print("單一 210 各區：", SMD_N)
    print("複數 140 各區 M：", LIST_M)
    print(f"每席選舉人（單一）：{QUOTA:.0f}")
    report("2023-07 眾議院選舉", "congreso-2023")
    report("2019-11 眾議院選舉", "congreso-2019")
    report("2019-04 眾議院選舉", "congreso-201904")
    report("2016-06 眾議院選舉", "congreso-201606")
    report("2015-12 眾議院選舉", "congreso-201512")


if __name__ == "__main__":
    main()
