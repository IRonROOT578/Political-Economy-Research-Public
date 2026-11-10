"""阿根廷一院議會制：得票 → 選制 → 席次 → 行政首長。

    python 生態模型.py              # 2025-10、2023-10 重算
    python 生態模型.py --projection # 推估第 3 屆
    python 生態模型.py --sweep      # 敏感度

民意層：2023 用 DINE **逐投票桌**眾議員有效票彙整到 5,752 個選區（circuito，資料/circ-2023.csv）；
2025 官方逐桌檔下載不到，用 2023 的選區地理 × 2025 各省總數（資料/votes-2025.csv，省級推估）縮放。
單一 150：各省依人口最大餘數（每省至少 1）；省內依選區編號（相鄰）連續切成等票數的選區；
參選方層（shared/tools/參選判定.py，含高票讓低票、單純退選）；top-3 孔多賽。
複數 100：10 區（布省切成 3 區、門多薩併入庫約），每區 M∈[6,14]，聖拉古，無門檻；「其他」拆成 5 份小名單。
偏好：二維（經濟左−1…右+1；文化開放−1…威權+1）；省級政黨只在本省參選。
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

SMD, PR, TOTAL, NEED, K = 150, 100, 250, 126, 3

# (經濟, 文化)
POS = {
    "工人左翼": (-0.95, -0.7),
    "祖國力量": (-0.55, -0.2),
    "祖國聯盟": (-0.55, -0.2),  # 2023 名
    "聯合省分": (0.05, 0.15),
    "為我國做事": (0.1, 0.2),  # 2023 名
    "變革聯盟": (0.25, 0.1),
    "聯邦革新": (0.15, 0.35),
    "自由前進": (0.85, 0.55),
    "其他": (0.0, 0.0),
}
TYPES = [(0.40, 1.0, 0.4), (0.25, 0.5, 1.0), (0.35, 0.8, 0.8)]
BALANCED = (0.85, 0.75)
BLOC = {
    "工人左翼": "左", "祖國力量": "庇隆", "祖國聯盟": "庇隆",
    "聯合省分": "中", "為我國做事": "中", "變革聯盟": "中右",
    "聯邦革新": "省", "自由前進": "自由", "其他": "中",
}
# 複數區：大省獨立，其餘合併
LIST_REGIONS = [
    ("布省", ["布宜諾斯艾利斯省"]),
    ("自治市", ["布宜諾斯艾利斯自治市"]),
    ("科多瓦", ["科多瓦"]),
    ("聖大非", ["聖大非"]),
    ("西北", ["圖庫曼", "薩爾塔", "聖地亞哥-德埃斯特羅", "胡胡伊", "卡塔馬卡", "拉里奥哈"]),
    ("東北", ["恩特雷里奧斯", "米西奧內斯", "科連特斯", "查科", "福莫薩"]),
    ("庫約", ["門多薩", "聖胡安", "聖路易斯", "拉潘帕"]),
    ("巴塔哥尼亞", ["里奧內格羅", "內烏肯", "丘布特", "聖克魯斯", "火地島"]),
]
ACTUAL = {
    2025: {"自由前進": 95, "祖國力量": 100, "聯合省分": 21, "工人左翼": 4, "其他": 37},  # 全院組成（維基敘述約數）
    2023: {"祖國聯盟": 108, "變革聯盟": 93, "自由前進": 39, "為我國做事": 8, "工人左翼": 5, "其他": 4},
}


LOCAL_POS = (0.15, 0.35)   # 省級政黨（各省執政黨或地方派系）：中間偏右、偏保守
# 立場明確的省級政黨（其餘用 LOCAL_POS；同省第二個以後的地方黨往外錯開，避免同座標時由黨名決勝）
LOCAL_KNOWN = {
    "地方:Partido Agrario Y Social": (-0.35, -0.05),   # 米西奧內斯，農民左翼
    "地方:Union Por San Luis": (-0.35, 0.05),           # 聖路易斯，庇隆派
    "地方:Fuerza Republicana": (0.7, 0.75),             # 圖庫曼，右翼
    "地方:Republicanos Unidos": (0.7, 0.3),             # 自由派右翼
}
# 2025 各黨在 2023 的地理來源（省內分布用 2023 選區票，省總數用 2025）
GEO_2025 = {"自由前進": ("自由前進", "變革聯盟"), "祖國力量": ("祖國聯盟",), "聯合省分": ("為我國做事", "變革聯盟"),
            "工人左翼": ("工人左翼",), "聯邦革新": ("地方",), "其他": ("其他",)}


def _provinces():
    with open(os.path.join(HERE, "資料", "provinces.csv"), encoding="utf-8") as f:
        return {r["province"]: int(r["pop"]) for r in csv.DictReader(f)}


def _circ2023():
    with open(os.path.join(HERE, "資料", "circ-2023.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    parties = [c for c in rows[0] if c not in ("province", "seccion_id", "seccion", "circuito")]
    out = []
    for r in rows:
        out.append({"province": r["province"], "key": (int(r["seccion_id"]), r["circuito"]),
                    "votes": {p: int(r[p]) for p in parties if int(r[p])}})
    return out


def load(year: int):
    """回傳選區清單 [{province, key, votes}]（依省、選區編號排序）與各省人口。"""
    pops = _provinces()
    circ = _circ2023()
    if year == 2023:
        units = circ
    else:
        with open(os.path.join(HERE, "資料", f"votes-{year}.csv"), encoding="utf-8") as f:
            ptot = {r["province"]: {p: int(v) for p, v in r.items() if p not in ("province", "pop", "lon", "lat", "region")}
                    for r in csv.DictReader(f)}
        units = []
        for prov in ptot:
            cs = [c for c in circ if c["province"] == prov]
            for party, total in ptot[prov].items():
                srcs = GEO_2025.get(party, (party,))
                w = [sum(v for p, v in c["votes"].items() if p in srcs or (p.startswith("地方:") and "地方" in srcs))
                     for c in cs]
                if sum(w) == 0:   # 2023 沒有對應名單：照有效票分布
                    w = [sum(c["votes"].values()) for c in cs]
                tw = sum(w) or 1
                for c, x in zip(cs, w):
                    c.setdefault("v25", Counter())[party] += total * x / tw
            for c in cs:
                units.append({"province": prov, "key": c["key"], "votes": {p: v for p, v in c.pop("v25", {}).items() if v > 0}})
    loc = Counter()
    prov_of = {}
    for u in units:
        for p, v in u["votes"].items():
            if p.startswith("地方:"):
                loc[(u["province"], p)] += v
    rank = {}
    for (prov, p), v in sorted(loc.items(), key=lambda x: (x[0][0], -x[1], x[0][1])):
        rank.setdefault(prov, []).append(p)
    for prov, ps in rank.items():
        for i, p in enumerate(ps):
            if p in POS:
                continue
            x, y = LOCAL_KNOWN.get(p, LOCAL_POS)
            if p not in LOCAL_KNOWN:
                x, y = x + 0.1 * i, y + 0.1 * i
            POS[p] = (x, y)
            BLOC[p] = "省"
    units.sort(key=lambda u: (u["province"], u["key"]))
    return units, pops


def chunks(units, n):
    """依序把選區切成 n 段，每段有效票約相等。"""
    tot = sum(sum(u["votes"].values()) for u in units)
    out, cur, acc = [], [], 0.0
    for u in units:
        v = sum(u["votes"].values())
        cur.append(u)
        acc += v
        if len(out) < n - 1 and acc >= tot * (len(out) + 1) / n:
            out.append(cur)
            cur = []
    out.append(cur)
    while len(out) < n:
        i = max(range(len(out)), key=lambda j: len(out[j]))
        b = out[i]
        out[i:i + 1] = [b[:len(b) // 2], b[len(b) // 2:]]
    return [c for c in out if c]


def sumv(units):
    t = Counter()
    for u in units:
        t.update(u["votes"])
    return t


def largest_remainder(weights, seats, floor=0):
    keys = list(weights)
    got = {k: floor for k in keys}
    rest = seats - floor * len(keys)
    tot = sum(weights[k] for k in keys) or 1
    q = {k: weights[k] * rest / tot for k in keys}
    for k in q:
        got[k] += int(q[k])
    rem = sorted(keys, key=lambda k: q[k] - int(q[k]), reverse=True)
    for k in rem[: seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1) if weights[x] else -1)
        got[k] += 1
    return got


def rank_from(me, cands, w):
    a = POS[me]
    return sorted(cands, key=lambda c: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, POS[c], a)), c))


def voter_groups(parties):
    return [(p, t[0], rank_from(p, parties, t[1:])) for p in parties for t in TYPES]


def pairwise_winner(cands, groups, weight_fn):
    cands = sorted(cands)
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        v = weight_fn(src) * w
        if not v:
            continue
        r = [c for c in order if c in cands]
        for i, a in enumerate(r):
            for b in r[i + 1 :]:
                P[(a, b)] += v
    for a in cands:
        if all(P[(a, b)] > P[(b, a)] for b in cands if b != a):
            return a, False
    # Ranked Pairs
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
    for a in cands:
        if all(reach(a, b) for b in cands if b != a):
            return a, True
    return cands[0], True


def topk_winner(votes, k=K):
    # 「其他」是殘餘桶，不當單一選區候選人
    parties = [p for p, v in votes.items() if v > 0 and p in POS and p != "其他"]
    if not parties:
        return max(votes, key=votes.get), False, {}
    fp = {p: votes[p] for p in parties}

    def win(fin):
        g = voter_groups(list(fin))
        a, _ = pairwise_winner(list(fin), g, lambda p: fp.get(p, 0))
        return a

    try:
        top = [p for p in _finals_for(fp, k, win, {p: POS[p] for p in parties}, withdraw=True) if p != "其他"]
    except Exception:
        top = sorted(parties, key=lambda p: (-fp[p], p))[:k]
    if len(top) < 2:
        top = sorted(parties, key=lambda p: (-fp[p], p))[:k]
    groups = voter_groups(top)
    w = pairwise_winner(top, groups, lambda p: fp.get(p, 0))
    return w[0], w[1], {p: fp.get(p, 0) for p in top}


def allocate_smd(units, pops):
    seats = largest_remainder(pops, SMD, floor=1)
    smd, by, cycles = Counter(), {}, 0
    for prov, n in seats.items():
        cs = [u for u in units if u["province"] == prov]
        by[prov] = Counter()
        for d in chunks(cs, n):
            w, cyc, _ = topk_winner(dict(sumv(d)))
            smd[w] += 1
            by[prov][w] += 1
            cycles += cyc
    return dict(smd), by, {"循環區數": cycles, "單一席次": SMD}


def list_districts(units, pops):
    """複數區：布省依選區編號切成 3 區，其餘照 LIST_REGIONS。回傳 [(區名, 選區清單, 人口)]。"""
    out = []
    for rname, members in LIST_REGIONS:
        cs = [u for u in units if u["province"] in members]
        pop = sum(pops[m] for m in members)
        if rname == "布省":
            parts = chunks(cs, 3)
            for i, p in enumerate(parts, 1):
                out.append((f"布省{i}", p, pop / 3))
        else:
            out.append((rname, cs, pop))
    return out


def allocate_list(units, pops):
    ds = list_districts(units, pops)
    m = largest_remainder({r: p for r, _, p in ds}, PR, floor=0)
    lst, by = Counter(), {}
    for r, cs, _ in ds:
        v = dict(sumv(cs))
        oth = v.pop("其他", 0)
        for i in range(5):                      # 零星名單：拆成 5 份小名單，不當一個黨
            v[f"其他{i}"] = oth / 5
        got = sainte_lague({p: x for p, x in v.items() if x > 0}, m[r])
        by[r] = {}
        for p, c in got.items():
            if c:
                k = "其他" if p.startswith("其他") else p
                lst[k] += c
                by[r][k] = by[r].get(k, 0) + c
    return dict(lst), by, m


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p in POS and p != "其他"]
    if not parties:
        return "—", {}
    groups = voter_groups(parties)
    # 席次加權兩兩
    def w(p):
        return total.get(p, 0)

    winner, _ = pairwise_winner(parties, groups, w)
    # 須有人把它排在「空缺」之上：簡化為席次 ≥ NEED 的聯盟存在時才就任
    return winner, {}


def coalition(total, pm, need=NEED):
    if pm not in total:
        return [], 0
    parties = [p for p, n in total.items() if n and p in POS and p != "其他"]
    order = rank_from(pm, [p for p in parties if p != pm], BALANCED)
    got = [pm]
    n = total[pm]
    for p in order:
        if n >= need:
            break
        got.append(p)
        n += total[p]
    return got, n


def fmt(d):
    order = [
        "工人左翼", "祖國力量", "祖國聯盟", "聯合省分", "為我國做事",
        "變革聯盟", "聯邦革新", "自由前進", "其他",
    ]
    rest = sorted((k for k in d if k not in order and d[k]), key=lambda k: -d[k])
    return "、".join(f"{k} {d[k]}" for k in order + rest if d.get(k))


def run(year):
    units, pops = load(year)
    parties = sorted({p for u in units for p in u["votes"]})
    smd, by_s, st = allocate_smd(units, pops)
    lst, by_l, m_seats = allocate_list(units, pops)
    total = Counter(smd) + Counter(lst)
    # 校正總席
    if sum(total.values()) != TOTAL:
        # 以複數吸收差額
        diff = TOTAL - sum(total.values())
        if diff and lst:
            top = max(lst, key=lst.get)
            total[top] += diff
            lst[top] = lst.get(top, 0) + diff
    pm, _ = head_of_gov(total)
    coal, cn = coalition(total, pm)
    return {
        "year": year, "smd": dict(smd), "lst": dict(lst), "total": dict(total),
        "by_s": by_s, "by_l": by_l, "m_seats": m_seats, "st": st,
        "pm": pm, "coal": coal, "cn": cn, "parties": parties,
    }


def report(r):
    y = r["year"]
    print(f"## {y}-10")
    print(f"單一 {SMD}： {fmt(r['smd'])}")
    print(f"複數 {PR}： {fmt(r['lst'])}")
    print(f"全院 {TOTAL}： {fmt(r['total'])}")
    print(f"各省單一：{'；'.join(f'{p} ' + fmt(dict(c)) for p, c in r['by_s'].items() if c)}")
    print(f"複數各區 M：{r['m_seats']}；循環區數 {r['st']['循環區數']}")
    print(f"行政首長：{r['pm']}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(r['coal'])}＝{r['cn']}")
    act = ACTUAL.get(y)
    if act:
        print(f"現行全院約： {fmt(act)}")
    print()


def projection():
    """以 2025 地理 × 全國均勢微移（自由前進 −3、祖國力量 +2、聯合省分 +1）。"""
    units, pops = load(2025)
    for u in units:
        v = u["votes"]
        move = int(v.get("自由前進", 0) * 0.03)
        v["自由前進"] = v.get("自由前進", 0) - move
        v["祖國力量"] = v.get("祖國力量", 0) + int(move * 2 / 3)
        v["聯合省分"] = v.get("聯合省分", 0) + (move - int(move * 2 / 3))
    smd, _, _ = allocate_smd(units, pops)
    lst, _, _ = allocate_list(units, pops)
    total = Counter(smd) + Counter(lst)
    pm, _ = head_of_gov(total)
    coal, cn = coalition(total, pm)
    print("## 推估第 3 屆")
    print(f"單一 {SMD}： {fmt(smd)}")
    print(f"複數 {PR}： {fmt(lst)}")
    print(f"全院 {TOTAL}： {fmt(total)}")
    print(f"行政首長：{pm}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(coal)}＝{cn}")


def sweep():
    r = run(2025)
    print("## --sweep 2025")
    print("基準", fmt(r["total"]), "首長", r["pm"])
    for label, delta in [("自由前進+5", {"自由前進": 1.05}), ("祖國力量+5", {"祖國力量": 1.05})]:
        units, pops = load(2025)
        for u in units:
            for p, f in delta.items():
                if p in u["votes"]:
                    u["votes"][p] = u["votes"][p] * f
        smd, _, _ = allocate_smd(units, pops)
        lst, _, _ = allocate_list(units, pops)
        total = Counter(smd) + Counter(lst)
        pm, _ = head_of_gov(total)
        print(label, fmt(total), "首長", pm)


def main(argv=None):
    argv = argv or sys.argv[1:]
    # 必要時重建票檔
    build = os.path.join(HERE, "資料", "_build_votes.py")
    if not os.path.exists(os.path.join(HERE, "資料", "votes-2025.csv")):
        os.system(f'python "{build}"')
    if "--projection" in argv:
        projection()
        return
    if "--sweep" in argv:
        sweep()
        return
    for y in (2025, 2023):
        report(run(y))


if __name__ == "__main__":
    main()
