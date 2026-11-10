# -*- coding: utf-8 -*-
"""奧地利一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2024-09 Nationalrat 重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆（＝2024 地理常態假設）

得票：BMI 終局 Gemeinde／區結果彙整為 資料/nr-2024.csv（政治區級，含 Briefwahl）。
單一 108：依人口配額固定到九邦（見 SMD_N），邦內依 GKZ 序切有效票相近選區；top-3 孔多賽。
複數 72：九邦名單區，聖拉古，無全國門檻，M 見 LIST_M（小邦底限 4）。
偏好：二維（經濟：左 −1 … 右 +1；文化：開放 −1 … 保守、限移民 +1）。
行政首長：全院 180 記名排名；須 ≥91 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

POS = {
    "KPÖ": (-0.9, -0.3), "SPÖ": (-0.5, -0.2), "GRÜNE": (-0.4, -0.8), "JETZT": (-0.35, -0.55),
    "NEOS": (0.3, -0.7), "BIER": (0.0, 0.1), "ÖVP": (0.4, 0.3), "FPÖ": (-0.1, 1.0),
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
# 計劃 §2.3 方案 A
SMD_N = {
    "Wien": 24, "Niederösterreich": 20, "Oberösterreich": 18, "Steiermark": 15,
    "Tirol": 9, "Salzburg": 7, "Kärnten": 7, "Vorarlberg": 5, "Burgenland": 3,
}
LIST_M = {
    "Wien": 14, "Niederösterreich": 13, "Oberösterreich": 12, "Steiermark": 10,
    "Tirol": 6, "Salzburg": 5, "Kärnten": 4, "Vorarlberg": 4, "Burgenland": 4,
}
ACTUAL = {
    2024: {"FPÖ": 57, "ÖVP": 51, "SPÖ": 41, "NEOS": 18, "GRÜNE": 16},
    2019: {"ÖVP": 71, "SPÖ": 40, "FPÖ": 31, "GRÜNE": 26, "NEOS": 15},
}
CABINET = {
    2024: ("Stocker（ÖVP）", ("ÖVP", "SPÖ", "NEOS"), 155),
    2019: ("Kurz（ÖVP）", ("ÖVP", "GRÜNE"), 0),
}
SMD_TOTAL, LIST_TOTAL, NEED = 108, 72, 91
MAIN = ["ÖVP", "SPÖ", "FPÖ", "GRÜNE", "NEOS", "KPÖ", "BIER", "JETZT"]


def load(year=2024):
    with open(os.path.join(HERE, "資料", f"nr-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][5:]
    out = []
    for r in rows[1:]:
        votes = {c: int(v) for c, v in zip(cols, r[5:])}
        # 合併小黨到「其他」供名單，但孔多賽只對有 POS 的黨
        merged = {p: votes.get(p, 0) for p in MAIN}
        other = sum(v for c, v in votes.items() if c not in MAIN)
        merged["其他"] = other
        out.append((r[1], r[0], r[2], int(r[3]), int(r[4]), merged))
    return out


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    keys = [k for k, w in weights.items() if w > 0]
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
    """單位數少於應切選區數時（如 Wien 23 區要 24 席），對半拆最大單位。"""
    rows = list(rows)
    guard = 0
    while len(rows) < n and guard < 1000:
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
    # 若累加切點過少：把最大塊再拆
    while len(out) < n:
        i = max(range(len(out)), key=lambda j: sum(x[4] for x in out[j]))
        block = out[i]
        if len(block) < 2:
            block = split_until(block, 2)
        mid = max(1, len(block) // 2)
        out[i:i + 1] = [block[:mid], block[mid:]]
    while len(out) > n:
        # 合併最小兩相鄰
        best = min(range(len(out) - 1), key=lambda j: sum(x[4] for x in out[j]) + sum(x[4] for x in out[j + 1]))
        out[best:best + 2] = [out[best] + out[best + 1]]
    assert len(out) == n, (len(out), n, len(rows))
    return out


def order(units):
    return sorted(units, key=lambda u: u[1])  # GKZ


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


def run(year=2024, types=TYPES, units=None):
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
    """依全國目標得票%縮放各單位（地理形狀保留）。targets 加總應≈100。"""
    nat = national(units)
    # 只縮放有目標的黨；其餘併入「其他」後再按比例
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


# Unique Research / Heute，田野 2026-09-28..10-01（PolitPro）
POLL_UNIQUE = {"FPÖ": 38.0, "ÖVP": 20.0, "SPÖ": 15.0, "GRÜNE": 12.0, "NEOS": 10.0, "KPÖ": 4.0, "BIER": 1.0}

# 推估第 3 屆（12 §2.3）：2024 地理形狀＋新制誘因下的全國得票；FPÖ 文化軸軟化見 POS_TERM3。
# 論據：兩屆後「只靠第一偏好、決選全滅」的代價顯現 → 部分抗議票回 ÖVP；FPÖ 為搶第二偏好收斂文化軸。
TERM3 = {"FPÖ": 24.0, "ÖVP": 28.0, "SPÖ": 21.0, "NEOS": 10.0, "GRÜNE": 9.0, "KPÖ": 3.5, "BIER": 0.5}
POS_TERM3 = {"FPÖ": (0.15, 0.55)}  # 仍偏右，但已能在部分農村三人決選贏 ÖVP／SPÖ


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1]) if k != "其他"))
    if year in ACTUAL and str(year) in label:
        print("實際 183：", fmt(ACTUAL[year]), "；實際內閣", CABINET[year])
    print("單一 108：", fmt(smd), stats)
    print("複數 72：", fmt(lst))
    print("全院 180：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥91 {worst >= 91}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣聯盟／多數派政府（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by = {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
    print("    各邦單一：", "；".join(f"{p}（{SMD_N[p]}）{fmt(c)}" for p, c in sorted(by.items())))


def main():
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("單一 108：", SMD_N, "合計", sum(SMD_N.values()))
    print("複數 72：", LIST_M, "合計", sum(LIST_M.values()))
    units24 = load(2024)
    print("2024 單位", len(units24), "有效票", sum(u[4] for u in units24))
    if "--sweep" in sys.argv:
        for name, types in (("全部重經濟", [(1.0, 1.0, 0.5)]), ("全部重文化", [(1.0, 0.5, 1.0)]), ("全部均衡", [(1.0, 0.8, 0.8)])):
            smd, _, total, _, _ = run(2024, types, units=units24)
            print(f"{name}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run(2024, units=swing(units24, "FPÖ", pts))
            print(f"FPÖ {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    if "--projection" in sys.argv:
        old = {k: POS[k] for k in POS_TERM3}
        POS.update(POS_TERM3)
        try:
            report("推估第 3 屆", 2024, scale_to_poll(units24, TERM3))
        finally:
            POS.update(old)
        return
    if "--poll" in sys.argv:
        report("民調 Unique Research 2026-10-01", 2024, scale_to_poll(units24, POLL_UNIQUE))
        return
    for year in (2024, 2019):
        u = units24 if year == 2024 else load(year)
        print(f"{year} 單位", len(u), "有效票", sum(x[4] for x in u))
        report(f"{year}-09", year, u)


if __name__ == "__main__":
    main()
