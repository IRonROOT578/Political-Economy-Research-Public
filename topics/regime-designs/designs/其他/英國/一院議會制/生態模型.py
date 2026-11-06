"""英國一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2024-07、2019-12 大選重算（當時得票）
    python 生態模型.py --sincere    # 同上，但「調回誠實偏好」（§2.3）
    python 生態模型.py --sweep      # 敏感度

得票：650 個現行選區的逐區得票（Wikipedia「Results of the YYYY United Kingdom general election」，
引選舉委員會與北愛選舉辦公室），彙整成 資料/ge-YYYY.csv；選區中心座標取自 ONS。
2024 年缺議長選區（Chorley）與 North Norfolk（表格解析失敗）。
單一 240：依 2024 有效票分到 9 個英格蘭大區＋蘇格蘭、威爾斯、北愛（最大餘數），區內沿選區中心的
希爾伯特曲線把相鄰的現行選區合併（約 2.7 個併 1 個）；top-3 孔多賽，循環 Ranked Pairs，平手以排第一者多為先。
複數 160：15 區，聖拉古，無法定門檻，M∈[8,16]。
偏好：三維空間（經濟：左 −1 … 右 +1；文化與脫歐：留歐、開放 −1 … 脫歐、限移民 +1；
聯合：獨立、統一愛爾蘭 −1 … 聯合派 +1）。每黨選民分三型。
行政首長：全院 400 記名排名投票；須 ≥201 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

POS = {
    "Lab": (-0.4, -0.4, 0.5), "Con": (0.6, 0.4, 0.9), "Reform": (0.6, 1.0, 0.9), "LD": (0.0, -0.8, 0.6),
    "Green": (-0.8, -0.8, 0.2), "SNP": (-0.4, -0.7, -1.0), "PC": (-0.5, -0.6, -0.8),
    "SF": (-0.5, -0.5, -1.0), "SDLP": (-0.4, -0.6, -0.7), "Alliance": (0.0, -0.7, 0.0),
    "UUP": (0.3, 0.2, 1.0), "DUP": (0.3, 0.7, 1.0), "TUV": (0.4, 1.0, 1.0),
}
OVERRIDE = {2019: {"Lab": (-0.8, -0.3, 0.5), "Reform": (0.5, 1.0, 0.9)},   # 2019：Corbyn 的工黨；Reform 欄＝脫歐黨
            2017: {"Lab": (-0.8, -0.3, 0.5), "Reform": (0.4, 1.0, 0.9)}}   # 2017：Corbyn 的工黨；Reform 欄＝UKIP
TYPES = [(0.30, 1.0, 0.6, 0.6), (0.30, 0.6, 1.0, 0.6), (0.40, 0.8, 0.8, 0.8)]
BALANCED = (0.8, 0.8, 0.8)
CURRENT = [2024]
LIST_GROUPS = [
    ("東南", ("SE",), 2), ("倫敦", ("LND",), 2), ("西北", ("NW",), 2), ("東英格蘭", ("E",), 1),
    ("西南", ("SW",), 1), ("威爾斯–西密德蘭", ("Wales", "WM"), 2), ("蘇格蘭–北愛", ("Scotland", "Northern Ireland"), 2),
    ("約克郡–東北", ("YTH", "NE"), 2), ("東密德蘭", ("EM",), 1),
]
ACTUAL = {
    2024: {"Lab": 411, "Con": 121, "LD": 72, "SNP": 9, "SF": 7, "Reform": 5, "DUP": 5, "Green": 4, "PC": 4, "其他": 12},
    2019: {"Con": 365, "Lab": 202, "SNP": 48, "LD": 11, "DUP": 8, "SF": 7, "PC": 4, "SDLP": 2, "Green": 1, "Alliance": 1, "其他": 1},
    2017: {"Con": 317, "Lab": 262, "SNP": 35, "LD": 12, "DUP": 10, "SF": 7, "PC": 4, "Green": 1, "其他": 2},
}
GB = ("Lab", "Con", "Reform", "LD", "Green", "SNP", "PC")


def pos(p):
    return OVERRIDE.get(CURRENT[0], {}).get(p, POS[p])


def load(year):
    with open(os.path.join(HERE, "資料", f"ge-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][5:]
    return [(r[0], hilbert(float(r[2]), float(r[3])), 0, r[1], int(r[4]), {c: int(v) for c, v in zip(cols, r[5:])})
            for r in rows[1:]]


def load_ep2019():
    """2019-05 歐洲議會選舉得票（估計到 2010–19 年國會選區；北愛爾蘭沿用 2019 國會選舉）。格式同 load()。"""
    with open(os.path.join(HERE, "資料", "ep-2019.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][5:]
    return [(r[0], hilbert(float(r[2]), float(r[3])), 0, r[1], int(r[4]), {c: int(v) for c, v in zip(cols, r[5:])})
            for r in rows[1:]]


def hilbert(lon, lat, order=12):
    """經緯度 → 希爾伯特曲線序號（英國框 −9…2、49…61）。"""
    n = 1 << order
    xi = min(n - 1, max(0, int((lon + 9) / 12 * n)))
    yi = min(n - 1, max(0, int((lat - 49) / 12 * n)))
    d, s = 0, n >> 1
    while s:
        rx, ry = int(xi & s > 0), int(yi & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                xi, yi = s - 1 - xi, s - 1 - yi
            xi, yi = yi, xi
        s >>= 1
    return d


def sincere(units, squeeze=0.10):
    """「調回誠實偏好」：每區前 2 名各讓出 squeeze 的票，按全國（大不列顛）其餘政黨的得票比例分給其餘政黨。
    粗略模擬一輪相對多數下的策略投票被解除。北愛不調。"""
    nat = {}
    for u in units:
        for c, v in u[5].items():
            nat[c] = nat.get(c, 0) + v
    out = []
    for u in units:
        if u[0] == "Northern Ireland":
            out.append(u)
            continue
        d = dict(u[5])
        top2 = sorted((c for c in d if c in GB), key=lambda c: -d[c])[:2]
        pool = sum(d[c] for c in top2) * squeeze
        rest = [c for c in d if c in GB and c not in top2 and (c not in ("SNP",) or u[0] == "Scotland")
                and (c != "PC" or u[0] == "Wales")]
        w = sum(nat[c] for c in rest)
        for c in top2:
            d[c] *= 1 - squeeze
        for c in rest:
            d[c] += pool * nat[c] / w if w else 0
        out.append(u[:5] + (d,))
    return out


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
    top = [c for c in cands if not any(t == c for _, t in locked)] or list(cands)
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
    while not out[-1] and len(out) > 1 and len(out[-2]) > 1:
        out[-1].append(out[-2].pop())
    assert len(out) == n and all(out)
    return out


def order(units):
    return sorted(units, key=lambda u: (u[1], u[3]))


def layout():
    units = load(2024)
    by = {}
    for u in units:
        by[u[0]] = by.get(u[0], 0) + u[4]
    smd = largest_remainder(by, 240, floor=1)
    regions = []
    for name, regs, k in LIST_GROUPS:
        rows = order([u for u in units if u[0] in regs])
        parts = cut(rows, k) if k > 1 else [rows]
        for i, part in enumerate(parts):
            regions.append((name if k == 1 else f"{name}{'一二'[i]}", regs, sum(u[4] for u in part)))
    m = largest_remainder({r[0]: r[2] for r in regions}, 160)
    return smd, [(r[0], r[1], m[r[0]]) for r in regions]


SMD_N, LIST_REGIONS = layout()
LIST_M = {r[0]: r[2] for r in LIST_REGIONS}


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for reg, n in sorted(SMD_N.items()):
        for part in cut(order([u for u in units if u[0] == reg]), n, shift):
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
            detail.append((reg, part[0][3], len(part), w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, tiny=6):
    out, acc, done = {}, {}, set()
    for name, regs, m in LIST_REGIONS:
        if regs in done:
            continue
        done.add(regs)
        parts = [r for r in LIST_REGIONS if r[1] == regs]
        rows = order([u for u in units if u[0] in regs])
        chunks = cut(rows, len(parts)) if len(parts) > 1 else [rows]
        for (pname, _, _), chunk in zip(parts, chunks):
            acc[pname] = {}
            for u in chunk:
                for c, v in u[5].items():
                    acc[pname][c] = acc[pname].get(c, 0) + v
    for name, _, m in LIST_REGIONS:
        d = dict(acc[name])
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


def coalition(total, pm, need=201):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, pos(p), pos(pm))) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(year, types=TYPES, k=3, shift=False, units=None):
    CURRENT[0] = year
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


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
    print("實際 650：", fmt(ACTUAL[year]))
    print("單一 240：", fmt(smd), stats)
    print("複數 160：", fmt(lst))
    print("全院 400：", fmt(total))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥201 {worst >= 201}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣陣營（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by = {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
    print("    各區單一：", "；".join(f"{r}（{SMD_N[r]}）{fmt(c)}" for r, c in sorted(by.items())))
    combos = {}
    for d in detail:
        key = "／".join(sorted(d[4]))
        combos[key] = combos.get(key, 0) + 1
    print("    決選三人：", sorted(combos.items(), key=lambda x: -x[1])[:6])
    sh = sorted(d[5] for d in detail)
    print(f"    當選者第一偏好：中位 {sh[len(sh) // 2]:.0%}、最低 {sh[0]:.0%}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if "--sweep" in sys.argv:
        for name, types in (("全部重經濟", [(1.0, 1.0, 0.6, 0.6)]), ("全部重文化", [(1.0, 0.6, 1.0, 0.6)]),
                            ("全部均衡", [(1.0, 0.8, 0.8, 0.8)])):
            for year in (2024, 2019):
                smd, _, total, _, _ = run(year, types)
                print(f"{name} {year}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for year in (2024, 2019):
            a = run(year, shift=True)
            b = run(year, k=2)
            print(f"{year} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{year} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for sq in (0.05, 0.10, 0.20):
            smd, lst, total, _, _ = run(2024, units=sincere(load(2024), sq))
            print(f"2024 誠實偏好（前 2 名讓出 {sq:.0%}）：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    print("單一 240 各區：", SMD_N)
    print("複數 160 各區 M：", LIST_M)
    for year in (2024, 2019, 2017):
        units = load(year)
        if "--sincere" in sys.argv:
            report(f"{year}（誠實偏好，前 2 名讓出 10%）", year, sincere(units))
        else:
            report(f"{year}", year, units)
    if "--sincere" not in sys.argv:
        # 2019-05 歐洲議會選舉：大不列顛唯一的全國比例代表政黨票，估計到國會選區（資料/ep-2019.csv，_build_ep2019.py）
        report("2019-05 歐洲議會名單票當第一偏好", 2019, load_ep2019())


if __name__ == "__main__":
    main()
