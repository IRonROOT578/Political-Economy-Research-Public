"""荷蘭一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2025-10、2023-11 下議院重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：選舉委員會（Kiesraad）逐投票所結果，彙整成 資料/tk-YYYY.csv 的「單位」＝市鎮 × 4 位數郵遞區。
海外選民與加勒比荷蘭（約 0.9%）無法定位，單一與複數席次都不計。
單一 90：依 2025 有效票分到 12 省（最大餘數），省內依郵遞區號連續切成有效票相近的選區
（荷蘭的 4 位數郵遞區號在地理上連續編排）；top-3 孔多賽，循環用 Ranked Pairs，平手以排第一者多為先。
複數 60：5 區，聖拉古，無法定門檻，M∈[8,16]。
偏好：二維空間（經濟：左 −1 … 右 +1；文化：開放、親歐 −1 … 保守、限移民 +1）。每黨選民分三型。
行政首長：全院 150 記名排名投票，議員依所屬政黨的均衡型排序；須 ≥76 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

POS = {
    "GL-PvdA": (-0.8, -0.7), "SP": (-0.9, 0.1), "PvdD": (-0.6, -0.6), "DENK": (-0.6, -0.3), "Volt": (-0.2, -0.9),
    "D66": (0.0, -0.7), "CU": (-0.1, 0.3), "50PLUS": (-0.3, 0.3), "NSC": (0.0, 0.3), "CDA": (0.2, 0.2),
    "VVD": (0.7, 0.1), "BBB": (0.3, 0.6), "SGP": (0.4, 0.8), "JA21": (0.7, 0.7), "PVV": (-0.1, 1.0), "FvD": (0.5, 1.0),
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
LIST_GROUPS = [
    ("北部", ("Groningen", "Fryslân", "Drenthe", "Overijssel")),
    ("中東部", ("Gelderland", "Utrecht", "Flevoland")),
    ("北荷蘭", ("Noord-Holland",)),
    ("南荷蘭–澤蘭", ("Zuid-Holland", "Zeeland")),
    ("南部", ("Noord-Brabant", "Limburg")),
]
ACTUAL = {
    2025: {"D66": 26, "PVV": 26, "VVD": 22, "GL-PvdA": 20, "CDA": 18, "JA21": 9, "FvD": 7, "BBB": 4, "CU": 3, "DENK": 3,
           "PvdD": 3, "SP": 3, "SGP": 3, "50PLUS": 2, "Volt": 1},
    2023: {"PVV": 37, "GL-PvdA": 25, "VVD": 24, "NSC": 20, "D66": 9, "BBB": 7, "CDA": 5, "SP": 5, "DENK": 3, "PvdD": 3,
           "FvD": 3, "SGP": 3, "CU": 3, "Volt": 2, "JA21": 1},
}
# 實際組閣
CABINET = {2025: ("Jetten（D66）", ("D66", "VVD", "CDA"), 117), 2023: ("Schoof（無黨籍）", ("PVV", "VVD", "NSC", "BBB"), 223)}


def load(year):
    with open(os.path.join(HERE, "資料", f"tk-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][5:]
    return [(r[0], int(r[3]), int(r[1]), r[2], int(r[4]), {c: int(v) for c, v in zip(cols, r[5:])}) for r in rows[2:]]


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
    a = POS[me]
    return sorted(cands, key=lambda c: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, POS[c], a)), c))


def voter_groups(parties, types=TYPES):
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
    top = [c for c in cands if not any(t == c for _, t in locked)]
    if len(top) > 1:                     # 平手：把他排第一的票較多者為先
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


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
    assert len(out) == n
    return out


def order(units):
    return sorted(units, key=lambda u: (u[1], u[2]))


def layout():
    units = load(2025)
    by = {}
    for u in units:
        by[u[0]] = by.get(u[0], 0) + u[4]
    smd = largest_remainder(by, 90, floor=1)
    m = largest_remainder({name: sum(by[p] for p in ps) for name, ps in LIST_GROUPS}, 60)
    return smd, m


SMD_N, LIST_M = layout()


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for prov, n in sorted(SMD_N.items()):
        for part in cut(order([u for u in units if u[0] == prov]), n, shift):
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
            detail.append((prov, part[0][3], part[0][1], w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, tiny=6):
    out = {}
    for name, provs in LIST_GROUPS:
        d = {}
        for u in units:
            if u[0] in provs:
                for c, v in u[5].items():
                    d[c] = d.get(c, 0) + v
        o = d.pop("其他", 0)
        for i in range(tiny):
            d[f"其他{i}"] = o / tiny
        for p, n in sainte_lague(d, LIST_M[name]).items():
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


def coalition(total, pm, need=76):
    """從首長的黨由近到遠加入，直到過半。"""
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[p], POS[pm])) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(year, types=TYPES, k=3, shift=False, units=None):
    units = units or load(year)
    smd, stats, detail = single_seats(units, types, k, shift)
    lst = list_seats(units)
    total = {p: smd.get(p, 0) + lst.get(p, 0) for p in set(smd) | set(lst)}
    return smd, lst, total, stats, detail


def national(units):
    t = {}
    for u in units:
        for c, v in u[5].items():
            t[c] = t.get(c, 0) + v
    s = sum(t.values())
    return {c: v * 100 / s for c, v in t.items()}


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        out.append(u[:5] + ({c: (nv if c == party else x * (t - nv) / rest if rest else x) for c, x in u[5].items()},))
    return out


# 推估第 3 屆（12 §2.3）：2025 的地理與得票；NSC 已於 2025 年幾近消失，不另外假設新黨。
PROJECTION = 2025


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
    if year in ACTUAL and label.startswith(str(year)):
        print("實際 150：", fmt(ACTUAL[year]), "；實際內閣", CABINET[year])
    print("單一 90：", fmt(smd), stats)
    print("複數 60：", fmt(lst))
    print("全院 150：", fmt(total))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥76 {worst >= 76}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣陣營（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by = {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
    print("    各省單一：", "；".join(f"{p}（{SMD_N[p]}）{fmt(c)}" for p, c in sorted(by.items())))
    combos = {}
    for d in detail:
        k = "／".join(sorted(d[4]))
        combos[k] = combos.get(k, 0) + 1
    print("    決選三人：", sorted(combos.items(), key=lambda x: -x[1])[:6])
    sh = sorted(d[5] for d in detail)
    print(f"    當選者第一偏好：中位 {sh[len(sh) // 2]:.0%}、最低 {sh[0]:.0%}")
    if "-v" in sys.argv:
        for d in detail:
            print("     ", d[0], d[1], d[2], d[3], "／".join(d[4]), f"{d[5]:.0%}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if "--sweep" in sys.argv:
        for name, types in (("全部重經濟", [(1.0, 1.0, 0.5)]), ("全部重文化", [(1.0, 0.5, 1.0)]), ("全部均衡", [(1.0, 0.8, 0.8)])):
            for year in (2025, 2023):
                smd, _, total, _, _ = run(year, types)
                print(f"{name} {year}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for year in (2025, 2023):
            a = run(year, shift=True)
            b = run(year, k=2)
            print(f"{year} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{year} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run(2025, units=swing(load(2025), "PVV", pts))
            print(f"2025 PVV {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    print("單一 90 各省：", SMD_N)
    print("複數 60 各區 M：", LIST_M)
    if "--projection" in sys.argv:
        report("推估第 3 屆", PROJECTION, load(PROJECTION))
        return
    for year in (2025, 2023):
        report(f"{year}", year, load(year))


if __name__ == "__main__":
    main()
