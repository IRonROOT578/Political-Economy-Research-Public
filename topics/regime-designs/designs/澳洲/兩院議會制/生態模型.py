# -*- coding: utf-8 -*-
"""澳洲兩院議會制：眾議院選區第一偏好 → 眾議院並立 ＋ 參議院比例。

正式規則是 **top-4** 孔多賽。眾議院 180＝單一 120＋複數 60，首長與供給只在眾議院全院 ≥91。
參議院 120 沿用一院複數的十區，不管信任、不管供給。

    python 生態模型.py
    python 生態模型.py --shift
    python 生態模型.py --乙       # 敏感度：自由黨也在國家黨獨占的選區參選（一院夾 coalition_variant）

得票：讀一院夾的 AEC 選區×候選人第一偏好，不另存一份。
第二偏好用與一院相同的二維距離。
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNI = os.path.normpath(os.path.join(HERE, "..", "一院議會制"))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
_spec = importlib.util.spec_from_file_location("au_uni", os.path.join(UNI, "生態模型.py"))
uni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uni)

from 偏好模型 import Prefs  # noqa: E402
from 參選判定 import finalists as _finalists  # noqa: E402

SMD, HOUSE_PR, HOUSE, NEED = 120, 60, 180, 91
SENATE = 120
K = 4

POS = uni.POS
BLOC = uni.BLOC
TYPES = uni.TYPES
BALANCED = uni.BALANCED
PARTY = uni.PARTY
BETA, SPREAD, ALPHA = uni.BETA, uni.SPREAD, uni.ALPHA

# 2026-03-31 八州領地人口、最大餘數（不含海外領地 5,047 人）。見 01。
SMD_N = {
    "NSW": 37,
    "VIC": 31,
    "QLD": 25,
    "WA": 13,
    "SA": 8,
    "TAS": 3,
    "ACT": 2,
    "NT": 1,
}
assert sum(SMD_N.values()) == SMD

# 州配額 NSW19＋ACT1、VIC15＋SA4＋TAS1、QLD12、WA7＋NT1，再切成 M∈[8,12]。
HOUSE_M = {
    "新南威爾斯甲": 10,
    "新南威爾斯乙": 10,
    "維多利亞甲": 10,
    "維多利亞乙": 10,
    "昆士蘭": 12,
    "西澳與北領地": 8,
}
assert sum(HOUSE_M.values()) == HOUSE_PR
HOUSE_POOL = {
    "新南威爾斯甲": ("NSW", "ACT"),
    "新南威爾斯乙": ("NSW", "ACT"),
    "維多利亞甲": ("VIC", "SA", "TAS"),
    "維多利亞乙": ("VIC", "SA", "TAS"),
    "昆士蘭": ("QLD",),
    "西澳與北領地": ("WA", "NT"),
}

# 與一院複數十區相同，兩版比例席才能對看。
SENATE_M = dict(uni.LIST_M)
SENATE_POOL = dict(uni.LIST_POOL)
assert sum(SENATE_M.values()) == SENATE

ELECTIONS = uni.ELECTIONS


def prefs():
    return Prefs(POS, BLOC, BETA, SPREAD, ALPHA)


def _header(rows):
    for i, r in enumerate(rows):
        if r and r[0] == "StateAb":
            return i, r
    raise ValueError("no header")


def load(label):
    path = os.path.join(UNI, "資料", ELECTIONS[label]["file"])
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    start, hdr = _header(rows)
    idx = {n: i for i, n in enumerate(hdr)}
    acc = {}
    residual = 0
    for r in rows[start + 1 :]:
        if len(r) < len(hdr):
            continue
        code = r[idx["PartyAb"]]
        if not code:
            continue
        votes = int(r[idx["TotalVotes"]] or 0)
        if votes <= 0:
            continue
        state = r[idx["StateAb"]]
        div = r[idx["DivisionNm"]]
        key = (state, div, r[idx["DivisionID"]])
        box = acc.setdefault(key, {})
        if code == "IND":
            name = f"獨立·{div}·{r[idx['Surname']]}"
            box[name] = box.get(name, 0) + votes
        elif code in PARTY:
            name = PARTY[code]
            box[name] = box.get(name, 0) + votes
        else:
            residual += votes
    units = []
    for (state, div, did), votes in sorted(acc.items(), key=lambda kv: (kv[0][0], int(kv[0][2]))):
        total = sum(votes.values())
        units.append((state, did, div, total, total, votes, None))
    return units, residual


def assign_regions(units, pool, seats_map):
    by_state = {}
    for u in units:
        by_state.setdefault(u[0], []).append(u)
    pools = {}
    for uname, states in pool.items():
        if uname in pools:
            continue
        chunk = []
        for s in states:
            chunk.extend(by_state.get(s, []))
        chunk.sort(key=lambda u: int(u[1]))
        names = [n for n, st in pool.items() if st == states]
        seats = [seats_map[n] for n in names]
        for name, block in zip(names, _chunks(chunk, seats)):
            pools[name] = block
    out = []
    for u in units:
        region = next(name for name, block in pools.items() if any(x[1] == u[1] and x[2] == u[2] for x in block))
        out.append((u[0], u[1], u[2], u[3], u[4], u[5], region))
    return out


def _chunks(units, seats):
    weights = [u[4] for u in units]
    total = sum(weights) or 1
    running = 0
    seat_sum = sum(seats)
    targets = []
    for m in seats:
        running += m
        targets.append(round(total * running / seat_sum))
    blocks, cur, got, ti = [], [], 0, 0
    for u in units:
        cur.append(u)
        got += u[4]
        if ti < len(targets) - 1 and got >= targets[ti]:
            blocks.append(cur)
            cur = []
            ti += 1
    blocks.append(cur)
    if len(blocks) != len(seats) or any(not b for b in blocks):
        n = len(seats)
        size = len(units) / n
        blocks = [units[int(i * size) : int((i + 1) * size)] for i in range(n)]
    assert len(blocks) == len(seats) and all(blocks), (len(blocks), [len(b) for b in blocks])
    return blocks


def split_half(u):
    a, b = {}, {}
    for c, v in u[5].items():
        left = v // 2
        a[c] = left
        b[c] = v - left

    def pack(votes, suffix):
        vv = {c: n for c, n in votes.items() if n}
        w = sum(vv.values())
        return (u[0], f"{u[1]}{suffix}", f"{u[2]}{suffix}", w, w, vv, u[6])

    return pack(a, "a"), pack(b, "b")


def seat_blocks(units, n, rotate=0):
    parts = list(units)
    guard = 0
    while len(parts) < n:
        i = max(range(len(parts)), key=lambda j: parts[j][4])
        a, b = split_half(parts.pop(i))
        parts.extend([a, b])
        guard += 1
        if guard > n * 4:
            raise RuntimeError("split did not converge")
    parts.sort(key=lambda u: (u[1], u[2]))
    if rotate and parts:
        r = rotate % len(parts)
        parts = parts[r:] + parts[:r]
    if len(parts) == n:
        return [[p] for p in parts]
    target = sum(p[4] for p in parts) / n
    out, cur, acc = [], [], 0.0
    for i, u in enumerate(parts):
        cur.append(u)
        acc += u[4]
        rem_units = len(parts) - 1 - i
        rem_buckets = n - 1 - len(out)
        if rem_buckets > 0 and (acc >= target * (len(out) + 1) - u[4] / 2 or rem_units == rem_buckets):
            out.append(cur)
            cur, acc = [], 0.0
    if cur:
        if len(out) < n:
            out.append(cur)
        else:
            out[-1].extend(cur)
    assert len(out) == n and all(out), (len(out), n, len(parts))
    return out


def voter_groups(parties, types, where):
    home = {p: "獨立" for p in parties if p.startswith("獨立")}
    return prefs().groups(parties, parties, types, where=where, home_of=home)


def pairwise_winner(cands, groups, weight, where):
    return uni.pairwise_winner(cands, groups, weight, where)


def label_of(name):
    return "獨立" if name.startswith("獨立") else name



def _dist(where, a, b):
    return sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, where[a], where[b])) ** 0.5

def single_seats(units, types=TYPES, k=K, rotate=0):
    out, by = {}, {}
    stats = {"循環": 0, "非第一偏好第一名當選": 0, "第一偏好過半": 0, "獨立當選": 0, "共同提名": 0}
    first_share = []
    awarded = 0
    for state, n in SMD_N.items():
        part = [u for u in units if u[0] == state]
        assert part, state
        for block in seat_blocks(part, n, rotate=rotate):
            votes = {}
            for u in block:
                for c, v in u[5].items():
                    votes[c] = votes.get(c, 0) + v
            tot_v = sum(votes.values()) or 1
            votes = {
                c: v for c, v in votes.items()
                if not str(c).startswith("獨立") or v >= 0.20 * tot_v
            }
            parties = [p for p, v in votes.items() if v > 0]
            assert parties, state
            where = dict(POS)
            for p in parties:
                if p.startswith("獨立"):
                    where[p] = POS["獨立"]
            groups = voter_groups(parties, types, where)
            wt = lambda s: votes.get(s, 0)
            win = lambda f: f[0] if len(f) == 1 else pairwise_winner(f, groups, wt, where)[0]
            # 策略層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py）；獨立候選人不在 universe，不整合
            finals, mlog = _finalists({p: votes[p] for p in parties}, k, win, lambda a, b: _dist(where, a, b),
                                      universe=POS, return_log=True, withdraw=True)
            stats["共同提名"] += bool(mlog)
            if len(finals) == 1:
                w, cyc = finals[0], False
            else:
                w, cyc, _ = pairwise_winner(finals, groups, wt, where)
            lab = label_of(w)
            out[lab] = out.get(lab, 0) + 1
            by.setdefault(state, {})
            by[state][lab] = by[state].get(lab, 0) + 1
            awarded += 1
            tot_v = sum(votes.values())
            stats["循環"] += int(cyc)
            stats["非第一偏好第一名當選"] += int(w != finals[0])
            stats["第一偏好過半"] += int(votes[w] > tot_v / 2)
            stats["獨立當選"] += int(lab == "獨立")
            first_share.append(votes[w] / tot_v)
    assert awarded == SMD, awarded
    first_share.sort()
    stats["當選者第一偏好中位數"] = round(first_share[len(first_share) // 2] * 100, 1)
    stats["by"] = by
    return out, stats


def list_seats(units, seats_map):
    out = {}
    seen = {name: [] for name in seats_map}
    for u in units:
        seen[u[6]].append(u)
    for name, m in seats_map.items():
        d = {}
        for u in seen[name]:
            for c, v in u[5].items():
                if c in POS:
                    d[c] = d.get(c, 0) + v
        for p, n in sainte_lague(d, m).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    keys = [k for k, w in weights.items() if w > 0]
    if not keys or seats <= 0:
        return got
    for _ in range(seats):
        k = max(keys, key=lambda x: (weights[x] / (2 * got[x] + 1), x))
        got[k] += 1
    return got


# 參選方層：自由黨、自由國家黨、國家黨、鄉村自由黨是正式聯盟（Coalition），選首長時共推一人，
# 由席次最多的成員出任；其餘政黨各自推人。
ALLIANCE = ("自由黨", "自由國家黨", "國家黨", "鄉村自由黨")


def head_of_gov(total, min_seats=5):
    mem = [p for p in ALLIANCE if total.get(p, 0)]
    rep = max(mem, key=lambda p: (total[p], p)) if mem else None
    # 成員各自投票、席次不併；只合併候選人；成員議員把聯盟人選排第一
    cands = sorted(p for p, n in total.items()
                   if (n >= min_seats or p == rep) and p in POS and p != "獨立" and (p == rep or p not in ALLIANCE))
    voters = [p for p, n in total.items() if n and p in POS]
    pr = prefs()
    groups = [(p, 1.0, ([rep] + [c for c in pr.rank(pr.pos[p], p, cands, BALANCED) if c != rep]) if (rep and p in ALLIANCE)
               else pr.rank(pr.pos[p], p, cands, BALANCED)) for p in voters]
    w, cyc, P = pairwise_winner(cands, groups, lambda s: total.get(s, 0), POS)
    duel = {b: (int(P[(w, b)]), int(P[(b, w)])) for b in cands if b != w}
    return w, cyc, duel


def coalition(total, pm, need=NEED):
    return prefs().coalition(total, pm, need, BALANCED)


def _rotate_states(units):
    rotated = []
    for state in SMD_N:
        part = [u for u in units if u[0] == state]
        if part:
            part = part[1:] + part[:1]
        rotated.extend(part)
    return rotated


def run(label, shift=False, variant=None):
    units, residual = load(label)
    if (variant or uni.VARIANT[0]) == "乙":
        units = uni.coalition_variant(units)
    if shift:
        units = _rotate_states(units)
    smd, stats = single_seats(units, rotate=1 if shift else 0)
    house_u = assign_regions(units, HOUSE_POOL, HOUSE_M)
    senate_u = assign_regions(units, SENATE_POOL, SENATE_M)
    lst = list_seats(house_u, HOUSE_M)
    senate = list_seats(senate_u, SENATE_M)
    assert sum(lst.values()) == HOUSE_PR, sum(lst.values())
    assert sum(senate.values()) == SENATE, sum(senate.values())
    total = {}
    for d in (smd, lst):
        for p, n in d.items():
            total[p] = total.get(p, 0) + n
    assert sum(total.values()) == HOUSE, (sum(total.values()), total)
    stats["未入模型的小黨票"] = residual
    return smd, lst, total, senate, stats


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"眾議院 {HOUSE}＝單一 {SMD}＋複數 {HOUSE_PR}；過半 ≥{NEED}；單一 top-{K}；參議院 {SENATE}")
    shift = "--shift" in sys.argv
    for label in ("2025-05", "2022-05"):
        smd, lst, total, senate, stats = run(label, shift=shift)
        pm, cyc, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        ev = ELECTIONS[label]
        print(f"\n## {label}{' 切線旋轉' if shift else ''}")
        print("現行", fmt(ev["actual"]), ev["cabinet"])
        print(f"單一 {SMD}：", fmt(smd))
        print("  州：", "；".join(f"{s} {fmt(stats['by'].get(s, {}))}" for s in SMD_N))
        print(f"複數 {HOUSE_PR}：", fmt(lst))
        print(f"全院 {HOUSE}：", fmt(total))
        print(f"參議院 {SENATE}：", fmt(senate))
        print(
            "循環", stats["循環"],
            "；非第一名當選", stats["非第一偏好第一名當選"],
            "；第一偏好過半", stats["第一偏好過半"],
            "；獨立", stats["獨立當選"],
            "；中位數", stats["當選者第一偏好中位數"],
            "；未入模型票", stats["未入模型的小黨票"],
        )
        print(f"行政首長：{pm} 循環={cyc}")
        print("對決", duel)
        print(f"組閣：{'＋'.join(seq)}＝{acc}")
        print(f"眾議院過半：{pm} {total.get(pm, 0)}／{HOUSE} {'過' if total.get(pm, 0) >= NEED else '未過'} {NEED}")


if __name__ == "__main__":
    main()
