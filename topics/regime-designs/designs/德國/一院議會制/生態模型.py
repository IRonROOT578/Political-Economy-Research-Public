# -*- coding: utf-8 -*-
"""德國一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2025-02 Bundestag 重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆
    python 生態模型.py --poll       # 民調縮放

得票：Bundeswahlleiterin **Wahlbezirksstatistik**（逐投票區 Zweitstimme；郵寄票依各投票區已領郵寄選票人數 A2 分回）
→ 資料/wbz-2025.csv、wbz-2021.csv（_build_wbz.py）、wbz-2017.csv、wbz-2013.csv（_build_wbz_old.py；約 13,400–16,700 個單位＝投票區號 //100 合併）。
單一 252：依人口配額固定到十六邦（見 SMD_N），邦內依選區號、單位序切有效票相近選區；top-3 孔多賽。
複數 168：十六邦名單區，聖拉古，無全國門檻，M 見 LIST_M（純 Hare）。
偏好：二維（經濟：左 −1 … 右 +1；文化：開放 −1 … 保守、限移民 +1）。
行政首長：全院 420 記名排名；須 ≥211 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

POS = {
    "LINKE": (-0.85, -0.55),
    "BSW": (-0.55, 0.45),
    "SPD": (-0.35, -0.15),
    "GRÜNE": (-0.25, -0.85),
    "FDP": (0.55, -0.35),
    "CDU": (0.35, 0.25),
    "CSU": (0.45, 0.45),
    "FW": (0.25, 0.35),
    "SSW": (-0.15, -0.4),
    "AfD": (0.15, 1.0),
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
SMD_N = {
    "Nordrhein-Westfalen": 54, "Bayern": 40, "Baden-Württemberg": 34, "Niedersachsen": 24,
    "Hessen": 19, "Rheinland-Pfalz": 13, "Sachsen": 12, "Berlin": 11,
    "Schleswig-Holstein": 9, "Brandenburg": 8, "Sachsen-Anhalt": 6, "Thüringen": 6,
    "Hamburg": 6, "Mecklenburg-Vorpommern": 5, "Saarland": 3, "Bremen": 2,
}
LIST_M = {
    "Nordrhein-Westfalen": 36, "Bayern": 27, "Baden-Württemberg": 23, "Niedersachsen": 16,
    "Hessen": 13, "Rheinland-Pfalz": 8, "Sachsen": 8, "Berlin": 7,
    "Schleswig-Holstein": 6, "Brandenburg": 5, "Sachsen-Anhalt": 4, "Thüringen": 4,
    "Hamburg": 4, "Mecklenburg-Vorpommern": 3, "Saarland": 2, "Bremen": 2,
}
ACTUAL = {
    2025: {"CDU": 164, "AfD": 152, "SPD": 120, "GRÜNE": 85, "LINKE": 64, "CSU": 44, "SSW": 1},
    2021: {"SPD": 206, "CDU": 152, "GRÜNE": 118, "FDP": 91, "AfD": 83, "CSU": 45, "LINKE": 39, "SSW": 1},
    2017: {"CDU": 200, "SPD": 153, "AfD": 94, "FDP": 80, "LINKE": 69, "GRÜNE": 67, "CSU": 46},
    2013: {"CDU": 255, "SPD": 193, "LINKE": 64, "GRÜNE": 63, "CSU": 56},
}
CABINET = {
    2025: ("Merz（CDU）", ("CDU", "CSU", "SPD"), 0),
    2021: ("Scholz（SPD）", ("SPD", "GRÜNE", "FDP"), 0),
    2017: ("Merkel（CDU）", ("CDU", "CSU", "SPD"), 0),
    2013: ("Merkel（CDU）", ("CDU", "CSU", "SPD"), 0),
}
SMD_TOTAL, LIST_TOTAL, NEED = 252, 168, 211
MAIN = ["SPD", "CDU", "GRÜNE", "FDP", "AfD", "CSU", "LINKE", "BSW", "FW", "SSW"]


def load(year=2025):
    """逐投票區（資料/wbz-YYYY.csv，_build_wbz.py 產生）：(land, unit, name, valid, valid, votes)。"""
    with open(os.path.join(HERE, "資料", f"wbz-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][6:]
    out = []
    for r in rows[1:]:
        votes = {c: int(v) for c, v in zip(cols, r[6:])}
        merged = {p: votes.get(p, 0) for p in MAIN}
        other = votes.get("其他", 0)
        merged["其他"] = other
        # land, wk_nr, wk_name, valid, votes — land_code unused for cut
        out.append((r[1], r[3], r[4], int(r[5]), int(r[5]), merged))
    return out


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    keys = [k for k, w in weights.items() if w > 0]
    if not keys:
        return got
    for _ in range(seats):
        k = max(keys, key=lambda x: weights[x] / (2 * got[x] + 1))
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
    wins = sorted(
        ((P[(a, b)], a, b) for a in cands for b in cands if a != b and P[(a, b)] > P[(b, a)]),
        reverse=True,
    )
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
    if not top:
        top = list(cands)
    if len(top) > 1:
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


def split_until(rows, n):
    rows = list(rows)
    guard = 0
    while len(rows) < n and guard < 2000:
        guard += 1
        i = max(range(len(rows)), key=lambda j: rows[j][4])
        u = rows[i]
        half = u[4] // 2
        if half <= 0:
            break
        v1 = {c: int(v) // 2 for c, v in u[5].items()}
        v2 = {c: int(u[5][c]) - v1[c] for c in u[5]}
        a = (u[0], u[1] + "a", u[2] + "-A", u[3] // 2, half, v1)
        b = (u[0], u[1] + "b", u[2] + "-B", u[3] - u[3] // 2, u[4] - half, v2)
        rows[i:i + 1] = [a, b]
    return rows


def cut(rows, n):
    rows = split_until(rows, n)
    if len(rows) == n:
        return [[u] for u in rows]
    target = sum(u[4] for u in rows) / n
    out, cur, acc = [], [], 0
    for u in rows:
        cur.append(u)
        acc += u[4]
        if acc >= target * (len(out) + 1) - u[4] / 2 and len(out) < n - 1:
            out.append(cur)
            cur = []
    out.append(cur)
    while len(out) < n:
        i = max(range(len(out)), key=lambda j: sum(x[4] for x in out[j]))
        block = out[i]
        if len(block) < 2:
            block = split_until(block, 2)
        mid = max(1, len(block) // 2)
        out[i:i + 1] = [block[:mid], block[mid:]]
    while len(out) > n:
        best = min(
            range(len(out) - 1),
            key=lambda j: sum(x[4] for x in out[j]) + sum(x[4] for x in out[j + 1]),
        )
        out[best:best + 2] = [out[best] + out[best + 1]]
    assert len(out) == n, (len(out), n, len(rows))
    return out


def order(units):
    return sorted(units, key=lambda u: u[1])


def single_seats(units, types=TYPES, k=3):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for land, n in sorted(SMD_N.items()):
        part_units = order([u for u in units if u[0] == land])
        assert part_units, land
        for part in cut(part_units, n):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    if c in POS:
                        votes[c] = votes.get(c, 0) + v
            parties = sorted(p for p in votes if votes[p] > 0)
            if not parties:
                continue
            _g = voter_groups(parties, types)
            _w = lambda s: votes.get(s, 0)
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
            finals = _finals_for({p: votes[p] for p in parties}, k, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, _g, _w)[0], POS)
            if len(finals) == 1:
                w, cyc = finals[0], False
            else:
                w, cyc, _ = pairwise_winner(finals, _g, _w)
            out[w] = out.get(w, 0) + 1
            tot = sum(votes.values())
            stats["循環"] += cyc
            stats["第一偏好過半"] += votes[w] > tot / 2
            stats["非第一偏好第一名當選"] += w != finals[0]
            detail.append((land, part[0][2], part[0][1], w, finals, votes[w] / tot if tot else 0))
    return out, stats, detail


def list_seats(units):
    out = {}
    for land, m in LIST_M.items():
        d = {}
        for u in units:
            if u[0] != land:
                continue
            for c, v in u[5].items():
                if c == "其他":
                    continue
                d[c] = d.get(c, 0) + v
        for p, n in sainte_lague(d, m).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out


def head_of_gov(total):
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min(P[(w, b)] for b in parties if b != w)
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def coalition(total, pm, need=NEED):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[p], POS[pm])) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(year=2025, types=TYPES, units=None):
    units = units or load(year)
    smd, stats, detail = single_seats(units, types)
    lst = list_seats(units)
    total = {p: smd.get(p, 0) + lst.get(p, 0) for p in set(smd) | set(lst)}
    return smd, lst, total, stats, detail


def national(units):
    t = {}
    for u in units:
        for c, v in u[5].items():
            t[c] = t.get(c, 0) + v
    s = sum(t.values())
    return {c: v * 100 / s for c, v in t.items() if c != "其他" or v}


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        nvotes = {c: (nv if c == party else (x * (t - nv) / rest if rest else x)) for c, x in u[5].items()}
        out.append(u[:5] + (nvotes,))
    return out


def scale_to_poll(units, targets):
    nat = national(units)
    out = []
    for u in units:
        t = sum(u[5].values())
        if t <= 0:
            out.append(u)
            continue
        nv = {}
        for p, share in targets.items():
            base = nat.get(p, 0) or 0.01
            factor = share / base
            nv[p] = u[5].get(p, 0) * factor
        s = sum(nv.values())
        if s > 0:
            nv = {p: v * t / s for p, v in nv.items()}
        out.append(u[:5] + (nv,))
    return out


# Forsa / RTL（示意近期刊載；執行時可改）— 2026-10 下旬量級
POLL_FORSA = {
    "CDU": 24.0, "CSU": 6.0, "AfD": 26.0, "SPD": 14.0, "GRÜNE": 11.0,
    "LINKE": 10.0, "BSW": 4.0, "FDP": 3.0, "FW": 1.5, "SSW": 0.2,
}

# 推估第 3 屆：兩屆孔多賽後 AfD 部分軟化、中間黨回升
TERM3 = {
    "CDU": 26.0, "CSU": 6.5, "AfD": 18.0, "SPD": 17.0, "GRÜNE": 12.0,
    "LINKE": 9.0, "BSW": 5.0, "FDP": 4.0, "FW": 1.5, "SSW": 0.2,
}
POS_TERM3 = {"AfD": (0.2, 0.6)}  # 文化軸收斂以搶第二偏好


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1]) if k != "其他"))
    if year in ACTUAL and str(year) in label:
        print(f"實際 {sum(ACTUAL[year].values())}：", fmt(ACTUAL[year]), "；實際內閣", CABINET[year])
    print("單一 252：", fmt(smd), stats)
    print("複數 168：", fmt(lst))
    print("全院 420：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥211 {worst >= 211}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣聯盟／多數派政府（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by = {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
    print("    各邦單一：", "；".join(f"{p}（{SMD_N[p]}）{fmt(c)}" for p, c in sorted(by.items())))
    return smd, lst, total, w, seq, acc, stats, detail


def main():
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("單一 252：", SMD_N, "合計", sum(SMD_N.values()))
    print("複數 168：", LIST_M, "合計", sum(LIST_M.values()))
    units25 = load(2025)
    print("2025 單位", len(units25), "有效票", sum(u[4] for u in units25))
    if "--sweep" in sys.argv:
        for name, types in (
            ("全部重經濟", [(1.0, 1.0, 0.5)]),
            ("全部重文化", [(1.0, 0.5, 1.0)]),
            ("全部均衡", [(1.0, 0.8, 0.8)]),
        ):
            smd, _, total, _, _ = run(2025, types, units=units25)
            print(f"{name}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run(2025, units=swing(units25, "AfD", pts))
            print(f"AfD {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    if "--projection" in sys.argv:
        old = {k: POS[k] for k in POS_TERM3}
        POS.update(POS_TERM3)
        try:
            report("推估第 3 屆", 2025, scale_to_poll(units25, TERM3))
        finally:
            POS.update(old)
        return
    if "--poll" in sys.argv:
        report("民調 Forsa 示意 2026-10", 2025, scale_to_poll(units25, POLL_FORSA))
        return
    report("2025-02", 2025, units25)
    if os.path.isfile(os.path.join(HERE, "資料", "bt-2021.csv")):
        u21 = load(2021)
        print("2021 單位", len(u21), "有效票", sum(x[4] for x in u21))
        report("2021-09", 2021, u21)
    for y, lab in ((2017, "2017-09"), (2013, "2013-09")):
        if os.path.isfile(os.path.join(HERE, "資料", f"wbz-{y}.csv")):
            uy = load(y)
            print(f"{y} 單位", len(uy), "有效票", sum(x[4] for x in uy))
            report(lab, y, uy)


if __name__ == "__main__":
    main()
