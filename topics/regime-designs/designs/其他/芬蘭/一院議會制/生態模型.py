# -*- coding: utf-8 -*-
"""芬蘭一院議會制：市鎮得票 → 並立選制 → 席次 → 行政首長。

計劃：`notes/sdd/芬蘭-計劃.md`（使用者「去做」：全部照建議）。
200＝單一 120（本土 119＋奧蘭 1）＋複數 80（8 區聖拉古、無門檻）。**不是**現行 d'Hondt 開放名單。

    python 生態模型.py
    python 生態模型.py --projection

得票：正義部 tulospalvelu 市鎮×黨 → `資料/fi-YYYY.csv`（見 `_fetch_vaalit.py`／`資料/README.md`）。
新地西／東：市鎮清單見 `UUSIMAA_WEST`（埃斯波岸 vs 萬塔／東岸）。
奧蘭：源檔政黨列為「其他」→ 單一席記「奧蘭」。
偏好：二維（經濟左−右；文化開放−限移民）。假設見 12。
首長：全院 ≥101；候選黨 ≥5 席。
"""
from __future__ import annotations

import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 6, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402

SMD, PR, TOTAL, NEED = 120, 80, 200, 101

# 經濟左−1…右+1；文化開放−1…保守／限移民+1
POS = {
    "左翼聯盟": (-0.85, -0.55),
    "綠黨": (-0.55, -0.75),
    "社民黨": (-0.35, -0.15),
    "瑞典人民黨": (0.05, -0.35),
    "奧蘭": (0.0, -0.2),  # 地方自治／瑞典語；排序用近 RKP
    "中間黨": (0.1, 0.25),
    "現在運動": (0.2, 0.05),
    "聯合黨": (0.45, 0.2),
    "基民黨": (0.35, 0.55),
    "芬人黨": (0.15, 0.9),
}
TYPES = [(0.30, 1.0, 0.5), (0.40, 0.5, 1.0), (0.30, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
BLOC = {
    "左翼聯盟": "中左",
    "綠黨": "中左",
    "社民黨": "中左",
    "瑞典人民黨": "中間",
    "奧蘭": "中間",
    "中間黨": "中間",
    "現在運動": "中右",
    "聯合黨": "中右",
    "基民黨": "中右",
    "芬人黨": "民粹右",
}
BETA, SPREAD, ALPHA = 0.0, 0.0, {}

# 計劃 §3.1 固定配額
LIST_M = {
    "赫爾辛基": 9,
    "新地西": 8,
    "新地東": 8,
    "西南": 10,
    "海梅皮爾卡": 14,
    "東南薩沃": 12,
    "瓦薩中芬": 10,
    "北部": 9,
}
SMD_N = {
    "赫爾辛基": 14,
    "新地西": 11,
    "新地東": 11,
    "西南": 15,
    "海梅皮爾卡": 20,
    "東南薩沃": 18,
    "瓦薩中芬": 16,
    "北部": 14,
    "奧蘭": 1,
}
assert sum(LIST_M.values()) == PR
assert sum(SMD_N.values()) == SMD
REGIONS = list(SMD_N.keys())
LIST_REGIONS = list(LIST_M.keys())

# 新地西＝埃斯波／西岸；其餘 02 區市鎮＝新地東
UUSIMAA_WEST = {
    "Espoo",
    "Kauniainen",
    "Kirkkonummi",
    "Siuntio",
    "Inkoo",
    "Lohja",
    "Vihti",
    "Karkkila",
    "Hanko",
    "Raasepori",
}

DISTRICT_TO_LAND = {
    "01": "赫爾辛基",
    "03": "西南",
    "04": "西南",
    "05": "奧蘭",
    "06": "海梅皮爾卡",
    "07": "海梅皮爾卡",
    "08": "東南薩沃",
    "09": "東南薩沃",
    "10": "瓦薩中芬",
    "11": "瓦薩中芬",
    "12": "北部",
    "13": "北部",
}

ELECTIONS = {
    "2023-04": {
        "file": "fi-2023.csv",
        "actual": {
            "聯合黨": 48,
            "芬人黨": 46,
            "社民黨": 43,
            "中間黨": 23,
            "綠黨": 13,
            "左翼聯盟": 11,
            "瑞典人民黨": 9,
            "基民黨": 5,
            "現在運動": 1,
            "奧蘭": 1,
        },
        "cabinet": ("Orpo（聯合黨）", ("聯合黨", "芬人黨", "瑞典人民黨", "基民黨"), 108),
    },
    "2019-04": {
        "file": "fi-2019.csv",
        "actual": {
            "社民黨": 40,
            "芬人黨": 39,
            "聯合黨": 38,
            "中間黨": 31,
            "綠黨": 20,
            "左翼聯盟": 16,
            "瑞典人民黨": 9,
            "基民黨": 5,
            "現在運動": 1,
            "奧蘭": 1,
        },
        "cabinet": ("Rinne／Marin（社民黨）", ("社民黨", "中間黨", "綠黨", "左翼聯盟", "瑞典人民黨"), 117),
    },
}


def prefs():
    return Prefs(POS, BLOC, BETA, SPREAD, ALPHA)


def land_of(district: str, name: str) -> str:
    if district == "02":
        return "新地西" if name in UUSIMAA_WEST else "新地東"
    return DISTRICT_TO_LAND[district]


def load(label):
    path = os.path.join(HERE, "資料", ELECTIONS[label]["file"])
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        land = land_of(r["district"], r["name"])
        votes = {p: int(r.get(p, 0) or 0) for p in POS if p != "奧蘭"}
        other = int(r.get("其他", 0) or 0)
        if land == "奧蘭":
            # 源檔奧蘭政黨列在「其他」
            votes = {"奧蘭": other + sum(votes.values())}
            other = 0
        if other:
            votes["其他"] = other
        valid = int(r["valid"])
        out.append((land, r["id"], r["name"], valid, valid, votes))
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


def voter_groups(parties, types=TYPES):
    return prefs().groups(parties, parties, types)


def pairwise_winner(cands, groups, weight):
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


def cut(rows, n, shift=False):
    import math
    rows = list(rows)
    target = sum(u[4] for u in rows) / n if n else 0
    expanded = []
    for u in rows:
        if target > 0 and u[4] > target * 0.55:
            parts = max(2, int(math.ceil(u[4] / (target * 0.5))))
            is_float = any(isinstance(v, float) for v in u[5].values())
            if is_float:
                v_part = {c: v / parts for c, v in u[5].items()}
                w_part = sum(v_part.values())
                for p_i in range(parts):
                    expanded.append((u[0], f"{u[1]}-{p_i+1:02d}", f"{u[2]}-{p_i+1}", w_part, w_part, dict(v_part)))
            else:
                rem = {c: int(v) for c, v in u[5].items()}
                for p_i in range(parts):
                    left = parts - p_i
                    v_part = {c: rem[c] // left for c in rem}
                    for c in rem:
                        rem[c] -= v_part[c]
                    w_part = sum(v_part.values())
                    expanded.append((u[0], f"{u[1]}-{p_i+1:02d}", f"{u[2]}-{p_i+1}", w_part, w_part, v_part))
        else:
            expanded.append(u)
    rows = expanded
    if shift and n > 1 and rows:
        acc, k_idx = 0.0, 0
        while k_idx < len(rows) and acc < target / 2:
            acc += rows[k_idx][4]
            k_idx += 1
        rows = rows[k_idx:] + rows[:k_idx]
    out, cur, acc = [], [], 0.0
    for i, u in enumerate(rows):
        cur.append(u)
        acc += u[4]
        rem_units = len(rows) - 1 - i
        rem_buckets = n - 1 - len(out)
        if rem_buckets > 0 and (acc >= target * (len(out) + 1) - u[4] / 2 or rem_units == rem_buckets):
            out.append(cur)
            cur = []
    if cur:
        if len(out) < n:
            out.append(cur)
        else:
            out[-1].extend(cur)
    assert len(out) == n and all(out), (len(out), n)
    return out


def single_seats(units, types=TYPES, k=3, shift=False):
    out, by = {}, {}
    stats = {"循環": 0, "非第一偏好第一名當選": 0, "第一偏好過半": 0}
    first_share = []
    awarded = 0
    for land, n in SMD_N.items():
        part = sorted([u for u in units if u[0] == land], key=lambda u: u[1])
        assert part, land
        for block in cut(part, n, shift=shift):
            votes = {}
            for u in block:
                for c, v in u[5].items():
                    if c in POS:
                        votes[c] = votes.get(c, 0) + v
            parties = [p for p in votes if votes[p] > 0]
            assert parties, (land, block)
            finals = sorted(parties, key=lambda p: (-votes[p], p))[:k]
            if len(finals) == 1:
                w, cyc = finals[0], False
            else:
                w, cyc, _ = pairwise_winner(
                    finals, voter_groups(parties, types), lambda s: votes.get(s, 0)
                )
            out[w] = out.get(w, 0) + 1
            by.setdefault(land, {})
            by[land][w] = by[land].get(w, 0) + 1
            awarded += 1
            tot_v = sum(votes.values())
            stats["循環"] += int(cyc)
            stats["非第一偏好第一名當選"] += int(w != finals[0])
            stats["第一偏好過半"] += int(votes[w] > tot_v / 2)
            first_share.append(votes[w] / tot_v)
    assert awarded == SMD
    first_share.sort()
    stats["當選者第一偏好中位數"] = round(first_share[len(first_share) // 2] * 100, 1)
    stats["by"] = by
    return out, stats


def list_seats(units):
    out = {}
    for land, m in LIST_M.items():
        d = {}
        for u in units:
            if u[0] != land:
                continue
            for c, v in u[5].items():
                if c in POS and c != "奧蘭":
                    d[c] = d.get(c, 0) + v
        for p, n in sainte_lague(d, m).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out


def head_of_gov(total, min_seats=5):
    cands = sorted(p for p, n in total.items() if n >= min_seats and p in POS and p != "奧蘭")
    if not cands:
        cands = sorted(p for p, n in total.items() if n and p in POS and p != "奧蘭")
    voters = [p for p, n in total.items() if n and p in POS]
    pr = prefs()
    groups = [(p, 1.0, pr.rank(pr.pos[p], p, cands, BALANCED)) for p in voters]
    w, cyc, P = pairwise_winner(cands, groups, lambda s: total.get(s, 0))
    duel = {b: (int(P[(w, b)]), int(P[(b, w)])) for b in cands if b != w}
    return w, cyc, duel


def coalition(total, pm, need=NEED):
    return prefs().coalition(total, pm, need, BALANCED)


def run(label, units=None):
    units = units if units is not None else load(label)
    smd, stats = single_seats(units)
    lst = list_seats(units)
    assert sum(lst.values()) == PR
    total = {}
    for d in (smd, lst):
        for p, n in d.items():
            total[p] = total.get(p, 0) + n
    assert sum(total.values()) == TOTAL, (sum(total.values()), total)
    return smd, lst, total, stats


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def projection():
    units = load("2023-04")
    base = {}
    for u in units:
        for p, v in u[5].items():
            if p in POS:
                base[p] = base.get(p, 0) + v
    tot = sum(base.values())
    shift = {
        "芬人黨": -1.2,
        "左翼聯盟": -0.4,
        "綠黨": -0.3,
        "聯合黨": 0.8,
        "社民黨": 0.7,
        "中間黨": 0.4,
    }
    mult = {}
    for p, pts in shift.items():
        if base.get(p):
            mult[p] = max(0.05, 1.0 + (pts / 100 * tot) / base[p])
    new = []
    for u in units:
        nv = {p: max(0, int(v * mult[p])) if p in mult else v for p, v in u[5].items()}
        new.append((u[0], u[1], u[2], u[3], sum(nv.values()), nv))
    return new


def projection_term3():
    return run("2023-04", units=projection())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"本夾 {TOTAL}＝單一 {SMD}＋複數 {PR}；過半 ≥{NEED}")
    print("單一配額", SMD_N)
    print("複數 M", LIST_M)
    if "--sweep" in sys.argv:
        u23, u19 = load("2023-04"), load("2019-04")
        lst23, lst19 = list_seats(u23), list_seats(u19)
        for label, types in (
            ("基準", TYPES),
            ("全部重經濟", [(1.0, 1.0, 0.4)]),
            ("全部重文化", [(1.0, 0.4, 1.0)]),
            ("全部均衡", [(1.0, 0.8, 0.8)]),
        ):
            s23, _ = single_seats(u23, types=types)
            s19, _ = single_seats(u19, types=types)
            t23 = {p: s23.get(p, 0) + lst23.get(p, 0) for p in set(s23) | set(lst23)}
            t19 = {p: s19.get(p, 0) + lst19.get(p, 0) for p in set(s19) | set(lst19)}
            print(f"| {label} | {fmt(s23)} | 首長 {head_of_gov(t23)[0]} | {fmt(s19)} | 首長 {head_of_gov(t19)[0]} |")
        s23_sh, _ = single_seats(u23, shift=True)
        s19_sh, _ = single_seats(u19, shift=True)
        t23_sh = {p: s23_sh.get(p, 0) + lst23.get(p, 0) for p in set(s23_sh) | set(lst23)}
        t19_sh = {p: s19_sh.get(p, 0) + lst19.get(p, 0) for p in set(s19_sh) | set(lst19)}
        print(f"| 切線位移半區 | {fmt(s23_sh)} | 首長 {head_of_gov(t23_sh)[0]} | {fmt(s19_sh)} | 首長 {head_of_gov(t19_sh)[0]} |")
        return
    if "--projection" in sys.argv:
        smd, lst, total, stats = projection_term3()
        pm, _, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        print("\n## 推估第 3 屆")
        print(f"單一 {SMD}：", fmt(smd))
        print(f"複數 {PR}：", fmt(lst))
        print(f"全院 {TOTAL}：", fmt(total))
        print(f"行政首長：{pm}；對決 {duel}")
        print(f"組閣：{'＋'.join(seq)}＝{acc}")
        print("stats", {k: v for k, v in stats.items() if k != "by"})
        return
    for label in ("2023-04", "2019-04"):
        smd, lst, total, stats = run(label)
        pm, _, duel = head_of_gov(total)
        seq, acc = coalition(total, pm)
        ev = ELECTIONS[label]
        by = stats.get("by", {})
        print(f"\n## {label}")
        print("實際", fmt(ev["actual"]))
        print(f"單一 {SMD}：", fmt(smd))
        print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
        print(f"複數 {PR}：", fmt(lst))
        print(f"全院 {TOTAL}：", fmt(total))
        print(
            "循環", stats["循環"],
            "；非第一偏好最多者當選", stats["非第一偏好第一名當選"],
            "；第一偏好過半", stats["第一偏好過半"],
            "；中位數", stats["當選者第一偏好中位數"],
        )
        print(f"行政首長：{pm}；對決 {duel}")
        print(f"組閣：{'＋'.join(seq)}＝{acc}")
        print("對照", ev["cabinet"])


if __name__ == "__main__":
    main()
