"""義大利一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2022-09、2018-03 眾議院重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：內政部逐市鎮×單一選區（collegio uninominale）的眾議院名單得票，彙整成 資料/camera-YYYY.csv；
大城市跨多個現行單一選區者，每個現行選區一個單位。海外選區、2022 年的瓦萊達奧斯塔（另檔，約 0.1%）不計；
瓦萊達奧斯塔併入皮埃蒙特計算。
單一 240：依 2022 有效票分到各大區（最大餘數），大區內依「現行選區 → 現行單一選區編號 → 市鎮」的順序
連續切成有效票相近的選區（現行單一選區在地理上連續）；top-3 孔多賽，循環 Ranked Pairs，平手以排第一者多為先。
複數 160：13 區（大區合併或拆分），聖拉古，無法定門檻，M∈[8,16]。
偏好：三維空間（經濟：左 −1 … 右 +1；主權：親歐、自由派 −1 … 主權派、民族保守 +1；建制：反建制 −1 … 建制 +1）。
每黨選民分四型（重經濟、重主權、重建制、均衡）。
行政首長：全院 400 記名排名投票；須 ≥201 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (經濟, 主權, 建制)。建制軸：反建制 −1 … 建制 +1（五星的位置靠這一軸區分，不是「左右中間」）。
POS = {
    "激左": (-1.0, -0.1, -0.6), "AVS": (-0.8, -0.5, 0.0), "PD": (-0.4, -0.6, 0.7), "中左小黨": (-0.2, -0.6, 0.5),
    "+Europa": (0.2, -1.0, 0.5), "第三極": (0.3, -0.7, 0.5), "M5S": (-0.4, 0.2, -0.6), "SVP": (0.2, -0.3, 0.6),
    "溫和派": (0.4, 0.0, 0.6), "FI": (0.6, -0.1, 0.6), "Lega": (0.5, 0.8, -0.2), "FdI": (0.4, 0.7, 0.0),
    "主權派": (-0.1, 1.0, -0.9), "極右": (0.3, 1.0, -0.7),
}
OVERRIDE = {2018: {"M5S": (-0.2, 0.4, -0.8), "Lega": (0.5, 0.8, -0.4), "FdI": (0.4, 0.7, -0.2)}}
# 敏感度用：五星在建制軸上的位置（12 §6）
M5S_EST = (-1.0, -0.6, -0.2)
# 選民四型：(比例, 經濟, 主權, 建制)
TYPES = [(0.25, 1.0, 0.5, 0.5), (0.25, 0.5, 1.0, 0.5), (0.25, 0.5, 0.5, 1.0), (0.25, 0.8, 0.8, 0.8)]
BALANCED = (0.8, 0.8, 0.8)
MERGE_REGION = {"VALLE D'AOSTA": "PIEMONTE"}
LIST_GROUPS = [
    ("西北", ("PIEMONTE", "LIGURIA"), 1),
    ("倫巴底", ("LOMBARDIA",), 2),
    ("東北", ("VENETO", "TRENTINO-ALTO ADIGE", "FRIULI-VENEZIA GIULIA"), 2),
    ("艾米利亞–羅馬涅", ("EMILIA-ROMAGNA",), 1),
    ("托斯卡尼–薩丁尼亞", ("TOSCANA", "SARDEGNA"), 1),
    ("中部", ("MARCHE", "UMBRIA", "ABRUZZO", "MOLISE"), 1),
    ("拉齊奧", ("LAZIO",), 1),
    ("坎帕尼亞", ("CAMPANIA",), 1),
    ("普利亞–巴西利卡塔", ("PUGLIA", "BASILICATA"), 1),
    ("西西里–卡拉布里亞", ("SICILIA", "CALABRIA"), 2),
]
# 實際席次（陣營層級）
ACTUAL = {
    2022: {"中右（FdI 119、Lega 66、FI 45、溫和派 7）": 237, "中左（PD 69、AVS 12 等）": 85, "M5S": 52, "第三極": 21, "其他": 5},
    2018: {"中右（Lega 125、FI 104、FdI 32、溫和派 4）": 265, "M5S": 227, "中左（PD 112 等）": 122, "LeU": 14, "其他": 2},
}
CABINET = {2022: ("Meloni（FdI）", "FdI＋Lega＋FI＋溫和派"),
           2018: ("Conte I → Conte II → Draghi", "M5S＋Lega → M5S＋PD → 大聯合")}
CURRENT = [2022]


def load(year):
    with open(os.path.join(HERE, "資料", f"camera-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][6:]
    return [(MERGE_REGION.get(r[0], r[0]), int(r[4]), 0, r[3], int(r[5]), {c: int(v) for c, v in zip(cols, r[6:])})
            for r in rows[1:]]


def pos(p):
    return OVERRIDE.get(CURRENT[0], {}).get(p, POS[p])


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
    while not out[-1] and len(out) > 1 and len(out[-2]) > 1:   # 平移後最後一段可能是空的
        out[-1].append(out[-2].pop())
    assert len(out) == n and all(out)
    return out


def order(units):
    return sorted(units, key=lambda u: (u[1], u[2]))


def layout():
    """單一 240 的大區配額；複數 160 的區（大區合併或拆分）與 M。固定用 2022 有效票。"""
    units = load(2022)
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
    """拆成兩區的大區組，依同樣的順序切成兩半（2018 年用同一套切法）。"""
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
    """從首長的黨由近到遠加入，直到過半。"""
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


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        out.append(u[:5] + ({c: (nv if c == party else x * (t - nv) / rest if rest else x) for c, x in u[5].items()},))
    return out


# 推估第 3 屆（12 §2.3）：2022 的地理與得票。
PROJECTION = 2022


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
    if year in ACTUAL and label.startswith(str(year)):
        print("實際：", ACTUAL[year], "；實際內閣", CABINET[year])
    print("單一 240：", fmt(smd), stats)
    print("複數 160：", fmt(lst))
    print("全院 400：", fmt(total), "；中右", sum(total.get(p, 0) for p in ("FdI", "Lega", "FI", "溫和派")), "中左", sum(total.get(p, 0) for p in ("PD", "AVS", "+Europa", "中左小黨", "激左")))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥201 {worst >= 201}）")
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
        for name, types in (("全部重經濟", [(1.0, 1.0, 0.5, 0.5)]), ("全部重主權", [(1.0, 0.5, 1.0, 0.5)]), ("全部重建制", [(1.0, 0.5, 0.5, 1.0)]), ("全部均衡", [(1.0, 0.8, 0.8, 0.8)])):
            for year in (2022, 2018):
                smd, _, total, _, _ = run(year, types)
                print(f"{name} {year}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for year in (2022, 2018):
            a = run(year, shift=True)
            b = run(year, k=2)
            print(f"{year} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{year} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for e in M5S_EST:
            for yr in (2022, 2018):
                POS["M5S"] = (POS["M5S"][0], POS["M5S"][1], e)
                OVERRIDE[2018]["M5S"] = (OVERRIDE[2018]["M5S"][0], OVERRIDE[2018]["M5S"][1], e)
                smd, _, total, _, _ = run(yr)
                print(f"五星建制軸 {e:+.1f}（{yr}）：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        POS["M5S"] = (-0.4, 0.2, -0.6)
        OVERRIDE[2018]["M5S"] = (-0.2, 0.4, -0.8)
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run(2022, units=swing(load(2022), "FdI", pts))
            print(f"2022 FdI {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    print("單一 240 各大區：", SMD_N)
    print("複數 160 各區 M：", LIST_M)
    if "--projection" in sys.argv:
        report("推估第 3 屆", PROJECTION, load(PROJECTION))
        return
    for year in (2022, 2018):
        report(f"{year}", year, load(year))


if __name__ == "__main__":
    main()
