# -*- coding: utf-8 -*-
"""紐西蘭一院議會制：投票所得票 → 並立選制 → 席次 → 行政首長。

得票：Electoral Commission 投票所政黨票（sage-archive）校準至官方選區總票
→ 資料/ge-YYYY.csv（`_fetch_sage.py`）。120＝單一 72＋複數 48；**不是 MMP**。
偏好排序是假設（見 12）。廢毛利平行選區：毛利選區投票所併入四區地理切開。

    python 生態模型.py
"""
from __future__ import annotations

import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

SMD, PR, TOTAL, MAJORITY = 72, 48, 120, 61

POS = {
    "綠黨": (-0.7, -0.8),
    "工黨": (-0.4, -0.3),
    "機會黨": (-0.2, -0.4),
    "毛利黨": (-0.6, -0.9),   # 經濟上比工黨更左（財富稅、公共住宅）
    "紐西蘭優先": (0.2, 0.6),
    "國家黨": (0.4, 0.3),
    "行動黨": (0.8, 0.5),
    "保守黨": (0.7, 0.7),
    "聯合未來": (0.1, 0.0),
    "網路MANA": (-0.6, -0.7),
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)

REGIONS = ["奧克蘭", "北島其餘", "威靈頓中央", "南島"]
LIST_M = {"奧克蘭": 14, "北島其餘": 14, "威靈頓中央": 10, "南島": 10}
assert sum(LIST_M.values()) == PR

ELECTIONS = {
    "2023-10": {
        "file": "ge-2023.csv",
        "actual_mmp": {"國家黨": 48, "工黨": 34, "綠黨": 15, "行動黨": 11, "紐西蘭優先": 8, "毛利黨": 6},
        "actual_total": 122,
    },
    "2020-10": {
        "file": "ge-2020.csv",
        "actual_mmp": {"工黨": 65, "國家黨": 33, "綠黨": 10, "行動黨": 10, "毛利黨": 2},
        "actual_total": 120,
    },
    "2017-09": {
        "file": "ge-2017.csv",
        "actual_mmp": {"國家黨": 56, "工黨": 46, "紐西蘭優先": 9, "綠黨": 8, "行動黨": 1},
        "actual_total": 120,
    },
    "2014-09": {
        "file": "ge-2014.csv",
        "actual_mmp": {
            "國家黨": 60, "工黨": 32, "綠黨": 14, "紐西蘭優先": 11,
            "毛利黨": 2, "行動黨": 1, "聯合未來": 1,
        },
        "actual_total": 121,
    },
}


def load(label):
    path = os.path.join(HERE, "資料", ELECTIONS[label]["file"])
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        votes = {p: int(r.get(p, 0) or 0) for p in POS}
        other = 0
        for k, v in r.items():
            if k in ("id", "land", "electorate", "place", "valid") or k in POS:
                continue
            other += int(v or 0)
        if other:
            votes["其他"] = other
        valid = int(r["valid"])
        out.append((r["land"], r["id"], r["place"], valid, valid, votes))
    return out


def hare_smd(units):
    """四區依有效票 Hare 配 72 單一席。"""
    tot = {reg: sum(u[4] for u in units if u[0] == reg) for reg in REGIONS}
    grand = sum(tot.values()) or 1
    raw = {reg: SMD * tot[reg] / grand for reg in REGIONS}
    base = {reg: int(raw[reg]) for reg in REGIONS}
    rem = SMD - sum(base.values())
    order = sorted(REGIONS, key=lambda r: (-(raw[r] - base[r]), r))
    for i in range(rem):
        base[order[i % len(order)]] += 1
    assert sum(base.values()) == SMD
    return base


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
    while len(rows) < n and guard < 5000:
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
        if len(out[i]) < 2:
            u0 = out[i][0]
            v1 = {c: int(v) // 2 for c, v in u0[5].items()}
            v2 = {c: int(u0[5][c]) - v1[c] for c in u0[5]}
            out[i:i + 1] = [
                [(u0[0], u0[1] + "a", u0[2] + "-A", sum(v1.values()), sum(v1.values()), v1)],
                [(u0[0], u0[1] + "b", u0[2] + "-B", sum(v2.values()), sum(v2.values()), v2)],
            ]
            continue
        mid = max(1, len(out[i]) // 2)
        out[i:i + 1] = [out[i][:mid], out[i][mid:]]
    while len(out) > n:
        best = min(range(len(out) - 1), key=lambda j: sum(x[4] for x in out[j]) + sum(x[4] for x in out[j + 1]))
        out[best:best + 2] = [out[best] + out[best + 1]]
    assert len(out) == n, (len(out), n)
    return out


def single_seats(units, smd_n, types=TYPES, k=3):
    out, detail = {}, []
    stats = {"循環": 0, "非第一偏好第一名當選": 0}
    awarded = 0
    for land, n in smd_n.items():
        part_units = sorted([u for u in units if u[0] == land], key=lambda u: u[1])
        assert part_units, land
        for part in cut(part_units, n):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    if c in POS:
                        votes[c] = votes.get(c, 0) + v
            parties = [p for p in votes if votes[p] > 0]
            if not parties:
                w, cyc, finals = "國家黨", False, ["國家黨"]
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
    assert awarded == SMD, awarded
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


def head_of_gov(total):
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    duel = {b: (int(P[(w, b)]), int(P[(b, w)])) for b in parties if b != w}
    return w, cyc, duel


def coalition(total, pm, need=MAJORITY):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[p], POS[pm])) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(label):
    units = load(label)
    smd_n = hare_smd(units)
    smd, stats, detail = single_seats(units, smd_n)
    lst = list_seats(units)
    assert sum(lst.values()) == PR, sum(lst.values())
    total = {}
    for d in (smd, lst):
        for p, n in d.items():
            total[p] = total.get(p, 0) + n
    assert sum(total.values()) == TOTAL
    return smd, lst, total, stats, smd_n


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(f"本夾 {TOTAL}＝單一 {SMD}＋複數 {PR}；過半 ≥{MAJORITY}")
    print("複數各區 M", LIST_M)
    for label in ("2023-10", "2020-10", "2017-09", "2014-09"):
        smd, lst, total, stats, smd_n = run(label)
        pm, _, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        ev = ELECTIONS[label]
        print(f"\n## {label}")
        print("單一配額", smd_n)
        print("實際 MMP", fmt(ev["actual_mmp"]), f"/ {ev['actual_total']}")
        print("單一", fmt(smd), "計", sum(smd.values()))
        print("複數", fmt(lst), "計", sum(lst.values()))
        print("全院", fmt(total), "計", sum(total.values()))
        print("循環區", stats["循環"], "；非第一偏好最多者當選", stats["非第一偏好第一名當選"])
        print("首長", pm, "；組閣", "＋".join(seq), "=", acc)


if __name__ == "__main__":
    main()
