"""土耳其一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2023-05、2018-06 議會選舉；2023 總統第一輪版；2024-03 地方選舉代理
    python 生態模型.py --sweep      # 敏感度

得票：最高選舉委員會（YSK）開放資料的**逐縣**結果（約 970 縣），彙整成 資料/mv2023.csv 等；國外與海關票不含。
聯盟票（只蓋聯盟章的票）歸聯盟最大黨。2023 年在 CHP 名單上參選的 DEVA、未來黨、幸福黨、民主黨併入 CHP。
單一 270：依 2023 選舉人分到 16 區（最大餘數），區內依縣中心座標的 Hilbert 序連續切成選舉人相近的選區（可跨省界）；
選舉人超過一席半數的縣先等分成數塊（同一組成）。top-3 孔多賽，循環 Ranked Pairs，平手以排第一者多為先。
複數 180：16 區（伊斯坦堡拆三），依選舉人最大餘數，聖拉古，無法定門檻，M∈[8,16]。
偏好：四維空間（宗教保守：世俗 −1 … 宗教 +1；民族：庫德 −1 … 土耳其民族主義 +1；經濟：左 −1 … 右 +1；
陣營：反對 −1 … 執政 +1）。每黨選民分四型。行政首長：全院 450 記名排名投票；須 ≥226 排在「維持空缺」之上。
"""
import csv
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (宗教保守, 民族, 經濟, 陣營)
POS = {
    "AKP": (0.7, 0.5, 0.3, 1.0), "MHP": (0.4, 1.0, 0.1, 0.8), "BBP": (0.7, 1.0, 0.1, 0.7), "YRP": (1.0, 0.4, -0.2, 0.3),
    "SP": (0.9, 0.2, -0.3, -0.5), "CHP": (-0.7, 0.2, -0.4, -1.0), "İYİ": (-0.2, 0.8, 0.3, -0.7),
    "Zafer": (-0.5, 1.0, 0.2, -0.4), "Memleket": (-0.4, 0.5, 0.0, -0.3), "DEM": (-0.3, -1.0, -0.7, -1.0),
    "TİP": (-0.9, -0.4, -1.0, -0.9),
}
# 陣營軸依當屆的聯盟：2023 新福利黨在人民聯盟內；2024 它與好黨都單獨參選
OVERRIDE = {
    "mv2023": {"YRP": (1.0, 0.4, -0.2, 0.6)},
    "bm2024": {"YRP": (1.0, 0.4, -0.2, -0.2), "İYİ": (-0.2, 0.8, 0.3, -0.4)},
    # 2015：MHP 在野、不與 CHP 結盟（陣營軸居中）
    "mv2015k": {"MHP": (0.4, 1.0, 0.1, 0.0)},
    "mv2015h": {"MHP": (0.4, 1.0, 0.1, 0.0)},
}
CAMP = 1.0                          # 陣營軸的權重（12 §6 敏感度）
TYPES = [(0.25, 1.0, 0.5, 0.5, 0.5), (0.25, 0.5, 1.0, 0.5, 0.5), (0.25, 0.5, 0.5, 1.0, 0.5),
         (0.25, 0.5, 0.5, 0.5, 1.0)]
BALANCED = (0.8, 0.8, 0.8, 0.8)
CURRENT = ["mv2023"]
LIST_GROUPS = [   # (名稱, 省碼, 拆幾區)
    ("伊斯坦堡", (34,), 3),
    ("西馬爾馬拉＋布爾薩", (22, 39, 59, 17, 10, 16), 1),
    ("東馬爾馬拉", (41, 54, 81, 14, 11, 26, 77), 1),
    ("伊茲密爾", (35,), 1),
    ("愛琴海內陸", (9, 20, 48, 45, 3, 43, 64), 1),
    ("安卡拉", (6,), 1),
    ("中安納托利亞", (42, 70, 68, 51, 50, 40, 71, 38, 66, 58), 1),
    ("西地中海", (7, 32, 15, 33), 1),
    ("東地中海", (1, 31, 80, 46), 1),
    ("西黑海", (67, 78, 74, 37, 18, 57, 55, 60, 19, 5), 1),
    ("東黑海與東北", (61, 52, 28, 53, 8, 29, 25, 24, 69, 4, 36, 76, 75), 1),
    ("中東部", (44, 23, 12, 62, 65, 49, 13, 30), 1),
    ("東南西", (27, 2, 79, 63), 1),
    ("東南東", (21, 47, 72, 73, 56), 1),
]
ACTUAL = {
    "mv2023": {"AKP": 268, "CHP": 169, "DEM": 61, "MHP": 50, "İYİ": 43, "YRP": 5, "TİP": 4},
    "mv2018": {"AKP": 295, "CHP": 146, "DEM": 67, "MHP": 49, "İYİ": 43},
    "mv2015k": {"AKP": 317, "CHP": 134, "DEM": 59, "MHP": 40},
    "mv2015h": {"AKP": 258, "CHP": 132, "MHP": 80, "DEM": 80},
}
SMD_TOTAL, LIST_TOTAL, NEED = 270, 180, 226


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
    return [(int(r[1]), r[2], float(r[3]), float(r[4]), int(r[5]), {c: int(v) for c, v in zip(cols, r[7:])}, r[0])
            for r in rows[1:]]


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
    return [(p, t[0], rank_from(p, parties, t[1:4] + (t[4] * CAMP,))) for p in parties for t in types]


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


def split_big(units, quota):
    out = []
    for u in units:
        k = max(1, math.ceil(u[4] / (quota * 0.5)))
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
    """16 區（伊斯坦堡以 2023 的縣序切成三塊）；單一與複數都依 2023 選舉人在 16 區間分配。"""
    units = load("mv2023")
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
    assert all(8 <= v <= 16 for v in m.values()), m
    first = {}
    for name, provs, _ in LIST_GROUPS:
        for p in provs:
            first.setdefault(p, name if name in m else f"{name}一")
    return smd, m, names, region_of, first, sum(w.values()) / SMD_TOTAL


SMD_N, LIST_M, PROV_NAME, REGION_OF, FIRST_REGION, QUOTA = layout()


def region(u):
    return REGION_OF.get((u[0], u[1].split("#")[0]), FIRST_REGION[u[0]])


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    units = split_big(units, QUOTA)
    for reg, n in SMD_N.items():
        for part in cut(order([u for u in units if region(u) == reg]), n, shift):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    votes[c] = votes.get(c, 0) + v
            parties = sorted(p for p in votes if p in POS and votes[p] > 0)
            finals = sorted(parties, key=lambda p: (-votes[p], p))[:k]
            w, cyc, _ = pairwise_winner(finals, voter_groups(parties, types), lambda s: votes.get(s, 0))
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
    for u in units:
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
    w8 = BALANCED[:3] + (BALANCED[3] * CAMP,)
    groups = [(p, 1.0, rank_from(p, parties, w8)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min(P[(w, b)] for b in parties if b != w)
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def coalition(total, pm, need=NEED):
    w8 = BALANCED[:3] + (BALANCED[3] * CAMP,)
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(w8, pos(p), pos(pm))) ** 0.5
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
        print("實際 600：", fmt(ACTUAL[name]))
    print("單一 270：", fmt(smd), stats)
    print("複數 180：", fmt(lst))
    print("全院 450：", fmt(total))
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
    for p in ("DEM", "CHP", "AKP", "MHP", "İYİ", "YRP"):
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
    global CAMP
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if "--sweep" in sys.argv:
        cases = (("全部重宗教", [(1.0, 1.0, 0.5, 0.5, 0.5)]), ("全部重民族", [(1.0, 0.5, 1.0, 0.5, 0.5)]),
                 ("全部重經濟", [(1.0, 0.5, 0.5, 1.0, 0.5)]), ("全部重陣營", [(1.0, 0.5, 0.5, 0.5, 1.0)]),
                 ("全部均衡", [(1.0, 0.8, 0.8, 0.8, 0.8)]))
        for label, types in cases:
            for name in ("mv2023", "mv2018", "bm2024"):
                smd, _, total, _, _ = run(name, types)
                print(f"{label} {name}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for camp in (0.0, 0.5, 2.0):
            CAMP = camp
            for name in ("mv2023", "mv2018", "bm2024"):
                smd, _, total, _, _ = run(name)
                print(f"陣營軸權重 {camp} {name}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        CAMP = 1.0
        for name in ("mv2023", "mv2018", "bm2024"):
            a = run(name, shift=True)
            b = run(name, k=2)
            print(f"{name} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{name} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run("mv2023", units=swing(load("mv2023"), "AKP", pts))
            print(f"2023 AKP {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    print("單一 270 各區：", SMD_N)
    print("複數 180 各區 M：", LIST_M)
    print(f"每席選舉人（單一）：{QUOTA:.0f}")
    report("2023-05 議會選舉", "mv2023")
    report("2023-05 總統第一輪當第一偏好（複數照議會票）", "cb2023", list_from="mv2023")
    report("2018-06 議會選舉", "mv2018")
    report("2024-03 地方選舉（市議會票）代理", "bm2024")
    report("2015-11 議會選舉", "mv2015k")
    report("2015-06 議會選舉", "mv2015h")


if __name__ == "__main__":
    main()
