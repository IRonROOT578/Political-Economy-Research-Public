# -*- coding: utf-8 -*-
"""丹麥一院議會制：得票 → 並立選制 → 席次 → 行政首長。

得票：DST Statistikbanken FV26TOTA／FV22TOTA／FV19TOTA 逐 **afstemningsområde**（投票所，約 1,300 個；依所屬提名區排序）
→ 資料/ft-2026.csv、ft-2022.csv、ft-2019.csv（`_fetch_dst.py`）。並立 180＝單一 106＋複數 70＋北大西洋 4；
**不是** 135＋40 補償。偏好排序是假設（見 12）。

    python 生態模型.py
    python 生態模型.py --projection
"""
from __future__ import annotations

import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

SMD_MAIN, LIST_MAIN, NA, TOTAL = 106, 70, 4, 180
NEED = 91

# 經濟左−1…右+1；文化開放−1…保守/限移民+1
POS = {
    "EL": (-0.9, -0.5),
    "SF": (-0.6, -0.55),
    "ALT": (-0.45, -0.85),
    "S": (-0.35, -0.05),
    "RV": (-0.15, -0.75),
    "M": (0.15, -0.25),
    "V": (0.55, 0.15),
    "C": (0.45, 0.35),
    "LA": (0.75, -0.2),
    "KD": (0.25, 0.55),
    "DF": (0.1, 0.85),
    "DD": (0.2, 0.9),
    "NB": (0.35, 0.95),
    "BP": (0.3, 0.9),   # Borgernes Parti（2026 新黨）：右翼民粹、限移民（假設）
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)

REGIONS = ["Hovedstaden", "Sjælland", "Syddanmark", "Midtjylland", "Nordjylland"]
SMD_N = {"Hovedstaden": 28, "Sjælland": 16, "Syddanmark": 22, "Midtjylland": 26, "Nordjylland": 14}
LIST_M = {"Hovedstaden": 18, "Sjælland": 11, "Syddanmark": 15, "Midtjylland": 17, "Nordjylland": 9}
assert sum(SMD_N.values()) == SMD_MAIN and sum(LIST_M.values()) == LIST_MAIN

MAIN = list(POS.keys())

ELECTIONS = {
    "2026-03": {
        "file": "ft-2026.csv",
        "actual": {
            "S": 38, "SF": 20, "V": 18, "DF": 16, "LA": 16, "M": 14, "C": 13,
            "EL": 11, "DD": 10, "RV": 10, "ALT": 5, "BP": 4,
        },
        "actual_total": 175,
        "na": {"IA": 1, "Naleraq": 1, "JF": 1, "SB": 1},
        "cabinet": ("（2026 組閣未入本夾）", (), 0),
    },
    "2022-11": {
        "file": "ft-2022.csv",
        "actual": {
            "S": 50, "V": 23, "M": 16, "SF": 15, "DD": 14, "LA": 14, "C": 10,
            "EL": 9, "RV": 7, "ALT": 6, "NB": 6, "DF": 5,
        },
        "actual_total": 175,
        "na": {"Siumut": 1, "IA": 1, "JF": 1, "SB": 1},
        "cabinet": ("Frederiksen（S）", ("S", "V", "M"), 42),
    },
    "2019-06": {
        "file": "ft-2019.csv",
        "actual": {
            "S": 48, "V": 43, "DF": 16, "RV": 16, "SF": 14, "EL": 13, "C": 12,
            "ALT": 5, "NB": 4, "LA": 4, "KD": 0,
        },
        "actual_total": 175,
        "na": {"Siumut": 1, "IA": 1, "JF": 1, "SB": 1},
        "cabinet": ("Frederiksen（S）", ("S",), 0),
    },
}


def load(label):
    """單位：(land, id, name, valid, valid, votes_dict)。小黨併入「其他」。"""
    path = os.path.join(HERE, "資料", ELECTIONS[label]["file"])
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        votes = {}
        other = 0
        for k, v in r.items():
            if k in ("id", "op", "land", "storkreds", "name", "valid", "eligible"):
                continue
            n = int(v or 0)
            if k in POS:
                votes[k] = n
            else:
                other += n
        if other:
            votes["其他"] = other
        valid = int(r["valid"])
        out.append((r["land"], r["id"], r["name"], valid, valid, votes))
    return out


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    keys = [k for k, w in weights.items() if w > 0]
    if not keys or seats <= 0:
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
    top = [c for c in cands if not any(t == c for _, t in locked)] or list(cands)
    if len(top) > 1:
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


def cut(rows, n):
    rows = list(rows)
    guard = 0
    while len(rows) < n and guard < 2000:
        guard += 1
        i = max(range(len(rows)), key=lambda j: rows[j][4])
        u = rows[i]
        if u[4] <= 1:
            break
        v1 = {c: int(v) // 2 for c, v in u[5].items()}
        v2 = {c: int(u[5][c]) - v1[c] for c in u[5]}
        a = (u[0], u[1] + "a", u[2] + "-A", sum(v1.values()), sum(v1.values()), v1)
        b = (u[0], u[1] + "b", u[2] + "-B", sum(v2.values()), sum(v2.values()), v2)
        rows[i:i + 1] = [a, b]
    target = sum(u[4] for u in rows) / n if n else 0
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
            u0 = out[i][0]
            v1 = {c: int(v) // 2 for c, v in u0[5].items()}
            v2 = {c: int(u0[5][c]) - v1[c] for c in u0[5]}
            out[i:i + 1] = [
                [(u0[0], u0[1] + "a", u0[2] + "-A", sum(v1.values()), sum(v1.values()), v1)],
                [(u0[0], u0[1] + "b", u0[2] + "-B", sum(v2.values()), sum(v2.values()), v2)],
            ]
            continue
        mid = max(1, len(block) // 2)
        out[i:i + 1] = [block[:mid], block[mid:]]
    while len(out) > n:
        best = min(range(len(out) - 1), key=lambda j: sum(x[4] for x in out[j]) + sum(x[4] for x in out[j + 1]))
        out[best:best + 2] = [out[best] + out[best + 1]]
    assert len(out) == n, (len(out), n)
    return out


def single_seats(units, types=TYPES, k=3):
    out, detail = {}, []
    stats = {"循環": 0, "非第一偏好第一名當選": 0}
    awarded = 0
    for land, n in SMD_N.items():
        part_units = sorted([u for u in units if u[0] == land], key=lambda u: (int("".join(ch for ch in u[1] if ch.isdigit()) or 0), u[1]))
        assert part_units, land
        for part in cut(part_units, n):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    if c in POS:
                        votes[c] = votes.get(c, 0) + v
            parties = [p for p in votes if votes[p] > 0]
            if not parties:
                w, cyc, finals = "S", False, ["S"]
            else:
                _g = voter_groups(parties, types)
                _w = lambda s: votes.get(s, 0)
                # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
                finals = _finals_for({p: votes[p] for p in parties}, k, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, _g, _w)[0], POS)
                if len(finals) == 1:
                    w, cyc = finals[0], False
                else:
                    w, cyc, _ = pairwise_winner(finals, _g, _w)
            out[w] = out.get(w, 0) + 1
            awarded += 1
            stats["循環"] += int(cyc)
            stats["非第一偏好第一名當選"] += int(w != finals[0])
            detail.append((land, w, finals[0], cyc))
    assert awarded == SMD_MAIN, awarded
    return out, stats, detail


def list_seats(units):
    out = {}
    for land, m in LIST_M.items():
        d = {}
        for u in units:
            if u[0] != land:
                continue
            for c, v in u[5].items():
                if c in POS:
                    d[c] = d.get(c, 0) + v
        for p, n in sainte_lague(d, m).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out


def map_na(na_dict):
    m = {"Siumut": "S", "JF": "S", "IA": "EL", "SB": "V"}
    out = {}
    for k, n in na_dict.items():
        p = m.get(k, "M")
        out[p] = out.get(p, 0) + n
    return out


def head_of_gov(total):
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    duel = {b: (int(P[(w, b)]), int(P[(b, w)])) for b in parties if b != w}
    return w, cyc, duel


def coalition(total, pm, need=NEED):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[p], POS[pm])) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(label, units=None):
    units = units if units is not None else load(label)
    smd, stats, detail = single_seats(units)
    lst = list_seats(units)
    assert sum(lst.values()) == LIST_MAIN, sum(lst.values())
    na = map_na(ELECTIONS[label]["na"] if label in ELECTIONS else ELECTIONS["2022-11"]["na"])
    assert sum(na.values()) == NA, na
    total = {}
    for d in (smd, lst, na):
        for p, n in d.items():
            total[p] = total.get(p, 0) + n
    assert sum(smd.values()) == SMD_MAIN
    assert sum(total.values()) == TOTAL, (sum(total.values()), sum(smd.values()), sum(lst.values()), sum(na.values()))
    return smd, lst, na, total, stats, detail


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def projection_term3():
    """第 3 屆：以 2022 投票所地理，略減翼側、略增中位（誘因假設，非民調）。"""
    units = load("2022-11")
    # 全國份額調整係數
    base = {}
    for u in units:
        for p, v in u[5].items():
            if p in POS:
                base[p] = base.get(p, 0) + v
    tot = sum(base.values())
    # 目標：NB/DF/DD 各削、EL 削，給 M/RV/S
    target_shift = {"NB": -1.0, "DF": -0.8, "DD": -0.7, "EL": -0.5, "M": 1.2, "RV": 0.8, "S": 1.0}
    mult = {}
    for p, pts in target_shift.items():
        if p not in base or base[p] == 0:
            continue
        mult[p] = max(0.05, 1.0 + (pts / 100 * tot) / base[p])
    new_units = []
    for u in units:
        nv = {}
        for p, v in u[5].items():
            if p in mult:
                nv[p] = max(0, int(v * mult[p]))
            else:
                nv[p] = v
        new_units.append((u[0], u[1], u[2], u[3], sum(nv.values()), nv))
    return run("2022-11", units=new_units)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(f"本夾 {TOTAL}＝單一 {SMD_MAIN}＋複數 {LIST_MAIN}＋北大西洋 {NA}；過半 ≥{NEED}")
    print("單一各區", SMD_N)
    print("複數各區 M", LIST_M)
    if "--projection" in sys.argv:
        smd, lst, na, total, stats, _ = projection_term3()
        pm, _, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        print("\n## 推估第 3 屆")
        print("單一", fmt(smd), "；複數", fmt(lst), "；北大西洋→", fmt(na))
        print("全院", fmt(total))
        print("首長", pm, "對決", duel)
        print("組閣聯盟／多數派政府", "＋".join(seq), "=", acc)
        print("stats", stats)
        return
    for label in ("2026-03", "2022-11", "2019-06"):
        smd, lst, na, total, stats, _ = run(label)
        pm, _, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        ev = ELECTIONS[label]
        print(f"\n## {label}")
        print("實際（本土）", fmt(ev["actual"]), f"/ {ev['actual_total']}")
        print("單一", fmt(smd))
        print("複數", fmt(lst))
        print("北大西洋映射", fmt(na))
        print("全院", fmt(total), "計", sum(total.values()))
        print("循環區", stats["循環"], "；非第一偏好最多者當選", stats["非第一偏好第一名當選"])
        print("首長", pm, "；對決", duel)
        print("組閣聯盟／多數派政府", "＋".join(seq), "=", acc)
        print("對照現行組閣", ev["cabinet"])


if __name__ == "__main__":
    main()
