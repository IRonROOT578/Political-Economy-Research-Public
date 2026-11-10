# -*- coding: utf-8 -*-
"""澳洲一院議會制：眾議院選區第一偏好 → 並立選制 → 席次 → 行政首長。

正式規則是 **top-4** 孔多賽（使用者「澳洲用 top4 直接正式」），不是其他夾的 top-3，也不是 top4 測試頁。
300＝單一 180＋複數 120。平行、聖拉古、無法定門檻。首長全院 ≥151。

    python 生態模型.py
    python 生態模型.py --shift
    python 生態模型.py --乙       # 敏感度：自由黨也在國家黨獨占的選區參選（coalition_variant）

得票：AEC Tally Room 選區×候選人第一偏好（資料/raw-2025.csv 事件 31496、raw-2022.csv 事件 27966）。
第二偏好沒有逐票檔，用二維距離（經濟左右；文化開放−限制）。
"""
from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402
from 參選判定 import finalists as _finalists  # noqa: E402

SMD, PR, TOTAL, NEED = 180, 120, 300, 151
K = 4

# 經濟左−1…右+1；文化開放−1…限制+1
POS = {
    "維多利亞社會黨": (-0.9, -0.7),
    "綠黨": (-0.55, -0.8),
    "動物正義": (-0.4, -0.6),
    "工黨": (-0.35, -0.15),
    "合法大麻": (-0.15, -0.45),
    "獨立": (-0.05, -0.4),
    "中間聯盟": (0.05, 0.0),
    "蘭比": (0.05, 0.55),
    "一國黨": (0.1, 0.92),
    "卡特黨": (0.15, 0.65),
    "家庭第一": (0.2, 0.75),
    "喇叭愛國者": (0.25, 0.8),
    "聯合澳洲": (0.25, 0.8),
    "澳洲基督徒": (0.25, 0.8),
    "射手漁農": (0.2, 0.6),
    "國家黨": (0.3, 0.55),
    "倫尼克": (0.35, 0.7),
    "鄉村自由黨": (0.4, 0.5),
    "自由黨": (0.5, 0.35),
    "自由國家黨": (0.5, 0.45),
    "自由意志": (0.7, 0.15),
    "自由民主": (0.7, 0.15),
}
TYPES = [(0.35, 1.0, 0.45), (0.35, 0.45, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
BLOC = {
    "維多利亞社會黨": "左",
    "綠黨": "中左",
    "動物正義": "中左",
    "工黨": "中左",
    "合法大麻": "中左",
    "獨立": "中間",
    "中間聯盟": "中間",
    "蘭比": "中間",
    "自由民主": "自由右",
    "自由意志": "自由右",
    "國家黨": "聯盟",
    "鄉村自由黨": "聯盟",
    "自由黨": "聯盟",
    "自由國家黨": "聯盟",
    "卡特黨": "地方右",
    "射手漁農": "地方右",
    "家庭第一": "社會右",
    "澳洲基督徒": "社會右",
    "一國黨": "民粹右",
    "喇叭愛國者": "民粹右",
    "聯合澳洲": "民粹右",
    "倫尼克": "民粹右",
}
BETA, SPREAD, ALPHA = 0.0, 0.0, {}
VARIANT = ["乙" if "--乙" in sys.argv else "甲"]   # 聯盟參選：甲＝現實（主版）、乙＝自由黨也進國家黨選區

PARTY = {
    "ALP": "工黨",
    "LP": "自由黨",
    "LNP": "自由國家黨",
    "NP": "國家黨",
    "CLP": "鄉村自由黨",
    "GRN": "綠黨",
    "ON": "一國黨",
    "CYA": "喇叭愛國者",
    "UAPP": "聯合澳洲",
    "FFP": "家庭第一",
    "LTP": "自由意志",
    "LDP": "自由民主",
    "HMP": "合法大麻",
    "KAP": "卡特黨",
    "XEN": "中間聯盟",
    "AJP": "動物正義",
    "AUC": "澳洲基督徒",
    "ASP": "射手漁農",
    "VNS": "維多利亞社會黨",
    "GRPF": "倫尼克",
    "JLN": "蘭比",
}

# 2026-03-31 人口、最大餘數。見計劃 D3。
SMD_N = {
    "NSW": 56,
    "VIC": 46,
    "QLD": 37,
    "WA": 20,
    "SA": 12,
    "TAS": 4,
    "ACT": 3,
    "NT": 2,
}
assert sum(SMD_N.values()) == SMD

# 名單區席次固定；選區怎麼切進區，見 assign_regions。
LIST_M = {
    "新南威爾斯甲": 13,
    "新南威爾斯乙": 13,
    "新南威爾斯丙": 13,
    "維多利亞甲": 10,
    "維多利亞乙": 10,
    "維多利亞丙": 11,
    "昆士蘭甲": 12,
    "昆士蘭乙": 13,
    "西澳與北領地": 14,
    "南澳與塔斯馬尼亞": 11,
}
assert sum(LIST_M.values()) == PR

LIST_POOL = {
    "新南威爾斯甲": ("NSW", "ACT"),
    "新南威爾斯乙": ("NSW", "ACT"),
    "新南威爾斯丙": ("NSW", "ACT"),
    "維多利亞甲": ("VIC",),
    "維多利亞乙": ("VIC",),
    "維多利亞丙": ("VIC",),
    "昆士蘭甲": ("QLD",),
    "昆士蘭乙": ("QLD",),
    "西澳與北領地": ("WA", "NT"),
    "南澳與塔斯馬尼亞": ("SA", "TAS"),
}

ELECTIONS = {
    "2025-05": {
        "file": "raw-2025.csv",
        "actual": {
            "工黨": 94,
            "自由黨": 18,
            "自由國家黨": 16,
            "國家黨": 9,
            "綠黨": 1,
            "中間聯盟": 1,
            "卡特黨": 1,
            "獨立": 10,
        },
        "cabinet": "工黨單獨 94／150",
    },
    "2022-05": {
        "file": "raw-2022.csv",
        "actual": {
            "工黨": 77,
            "自由黨": 27,
            "自由國家黨": 21,
            "國家黨": 10,
            "綠黨": 4,
            "中間聯盟": 1,
            "卡特黨": 1,
            "獨立": 10,
        },
        "cabinet": "工黨 77／151，未過半",
    },
}


def prefs():
    return Prefs(POS, BLOC, BETA, SPREAD, ALPHA)


def _header(rows):
    for i, r in enumerate(rows):
        if r and r[0] == "StateAb":
            return i, r
    raise ValueError("no header")


def load(label):
    path = os.path.join(HERE, "資料", ELECTIONS[label]["file"])
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


def coalition_variant(units):
    """版本乙（敏感度）：聯盟協議鬆動，自由黨也在國家黨獨占的選區參選。

    主版（甲）保留現實的參選：澳洲眾議院是偏好排序投票，分票本來就不會害到盟友，自由黨與國家黨仍大多不互推，
    所以這是聯盟協議的選擇，不是相對多數制造成的；新制下的誘因和現在相同。
    乙：國家黨獨占的選區補上自由黨，比例＝當屆所有三角選區（兩黨都參選）中自由黨占聯盟票的比例；從國家黨扣回。
    國家黨是地方性政黨（只有鄉村組織），不補進自由黨獨占的選區。"""
    lib = nat = 0
    for u in units:
        if u[5].get("自由黨") and u[5].get("國家黨"):
            lib += u[5]["自由黨"]
            nat += u[5]["國家黨"]
    share = lib / (lib + nat)
    out = []
    for u in units:
        v = dict(u[5])
        if v.get("國家黨") and not v.get("自由黨"):
            c = v["國家黨"]
            v["自由黨"] = round(c * share)
            v["國家黨"] = c - v["自由黨"]
        out.append(u[:5] + (v,) + u[6:])
    coalition_variant.share = share
    return out


def assign_regions(units):
    """把選區切進 10 個名單區。同池的選區依選區編號排序，按得票累計切成等額段。"""
    by_state = {}
    for u in units:
        by_state.setdefault(u[0], []).append(u)
    out = []
    pools = {}
    for uname, states in LIST_POOL.items():
        if uname not in pools:
            chunk = []
            for s in states:
                chunk.extend(by_state.get(s, []))
            chunk.sort(key=lambda u: int(u[1]))
            names = [n for n, st in LIST_POOL.items() if st == states]
            seats = [LIST_M[n] for n in names]
            cuts = _chunks(chunk, seats)
            for name, block in zip(names, cuts):
                pools[name] = block
    for u in units:
        region = next(name for name, block in pools.items() if any(x[1] == u[1] and x[2] == u[2] for x in block))
        out.append((u[0], u[1], u[2], u[3], u[4], u[5], region))
    return out


def _chunks(units, seats):
    weights = [u[4] for u in units]
    total = sum(weights) or 1
    targets = []
    acc = 0.0
    running = 0
    seat_sum = sum(seats)
    for i, m in enumerate(seats):
        running += m
        edge = round(total * running / seat_sum)
        targets.append(edge)
        acc = edge
    blocks, cur, got = [], [], 0
    ti = 0
    for u in units:
        cur.append(u)
        got += u[4]
        if ti < len(targets) - 1 and got >= targets[ti]:
            blocks.append(cur)
            cur = []
            ti += 1
    blocks.append(cur)
    if len(blocks) != len(seats) or any(not b for b in blocks):
        # 得票剛好卡在邊界時退回平均切段
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
    """選區少於席次時，從最大塊對半切開，直到塊數等於席次；多於席次時把相鄰塊併成 n 段。"""
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
    cands = sorted(cands)
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        v = weight(src) * w
        if not v:
            continue
        r = [c for c in order if c in cands]
        for i, a in enumerate(r):
            for b in r[i + 1 :]:
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
            # 低得票獨立沒有可核對的位置。距離模型若把他們放在兩大黨正中間，進了前四就會贏走所有兩兩。
            # 只把該區第一偏好 ≥20% 的獨立送進候選人；這是模型限制，不是法律門檻。
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


def list_seats(units):
    out = {}
    seen = {name: [] for name in LIST_M}
    for u in units:
        seen[u[6]].append(u)
    for name, m in LIST_M.items():
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


def run(label, shift=False, variant=None):
    units, residual = load(label)
    if (variant or VARIANT[0]) == "乙":
        units = coalition_variant(units)
    if shift:
        # 每個州把編號排序旋轉一席再切，看切線敏不敏感
        rotated = []
        for state in SMD_N:
            part = [u for u in units if u[0] == state]
            if part:
                part = part[1:] + part[:1]
            rotated.extend(part)
        units = rotated
    units = assign_regions(units)
    smd, stats = single_seats(units, rotate=1 if shift else 0)
    lst = list_seats(units)
    assert sum(lst.values()) == PR, sum(lst.values())
    total = {}
    for d in (smd, lst):
        for p, n in d.items():
            total[p] = total.get(p, 0) + n
    assert sum(total.values()) == TOTAL, (sum(total.values()), total)
    stats["未入模型的小黨票"] = residual
    return smd, lst, total, stats


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"本夾 {TOTAL}＝單一 {SMD}＋複數 {PR}；過半 ≥{NEED}；單一 top-{K}")
    shift = "--shift" in sys.argv
    for label in ("2025-05", "2022-05"):
        smd, lst, total, stats = run(label, shift=shift)
        pm, cyc, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        ev = ELECTIONS[label]
        print(f"\n## {label}{' 切線旋轉' if shift else ''}")
        print("現行", fmt(ev["actual"]), ev["cabinet"])
        print(f"單一 {SMD}：", fmt(smd))
        print("  州：", "；".join(f"{s} {fmt(stats['by'].get(s, {}))}" for s in SMD_N))
        print(f"複數 {PR}：", fmt(lst))
        print(f"全院 {TOTAL}：", fmt(total))
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


if __name__ == "__main__":
    main()
