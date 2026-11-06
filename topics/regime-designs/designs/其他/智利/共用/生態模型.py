"""智利（一院總統制、一院議會制兩夾共用）：得票 → 選制 → 席次 → 總統／行政首長。

偏好位置與選民類型是**假設**（見兩夾的 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2025、2017 國會重算；總統 top-3（2025、2021、2017）；議會制首長；制憲公投三案
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：SERVEL 逐投票桌眾議員票，合到投票所（local de votación）→ 資料/cl-2025.csv（2025 初步結果，3,496 所）、
cl-2017.csv（2017 TRICEL 確定結果，2,149 所）（_build_cl.py）。2021 年的國會逐桌檔在 SERVEL 網站上找不到，國會重算用 2017。
座標：Wikidata 智利市鎮（Q1840161）。區內依市鎮座標的 Hilbert 序連續切單一選區。
區：現行 28 個眾議員選區合成 6 區（見 01 §2）。海外選民照現行只投總統與公投，不設國會區。
國會 180＝單一 108（top-3 孔多賽）＋複數 72（聖拉古、無門檻）。
偏好：二維（經濟：國家、再分配 −1 … 市場 +1；價值：自由、進步 −1 … 保守、秩序 +1）。每黨選民分三型。
總統（總統制夾）：全國 top-3 孔多賽，候選人用自己的位置。首長（議會制夾）：全院 180 記名排名投票，須 ≥91。
校準：2017、2021、2025 三次決選的模型對決（見 12 §2）。
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 6, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402

POS = {
    "IZQ": (-1.0, -0.3),    # 平等黨、革命工人黨、愛國聯盟
    "PC": (-0.9, -0.2),     # 共產黨
    "FA": (-0.7, -0.7),     # 廣泛陣線（2017 民主革命、公民力量）
    "HUM": (-0.6, -0.5),    # 人道主義黨、人道主義行動
    "PEV": (-0.5, -0.7),    # 綠色生態黨、人民綠色聯盟
    "PRO": (-0.5, -0.3),    # 進步黨（Enríquez-Ominami）、PAIS
    "PS": (-0.5, -0.3),     # 社會黨
    "FRVS": (-0.4, -0.3),   # 綠色社會地方主義聯盟
    "PPD": (-0.35, -0.4),   # 爭取民主黨
    "PL": (-0.3, -0.6),     # 自由黨
    "PR": (-0.3, -0.2),     # 激進黨
    "PDC": (-0.1, 0.1),     # 基督教民主黨
    "DEM": (0.1, 0.1),      # 民主黨人（2017 公民、Amplitud）
    "AMA": (0.2, 0.0),      # 黃色運動
    "PDG": (0.1, 0.0),      # 人民黨（Parisi）：反建制、經濟居中；決選校準
    "EVO": (0.5, -0.2),     # Evópoli
    "RN": (0.4, 0.1),       # 國家革新（決選校準）
    "UDI": (0.65, 0.45),    # 獨立民主聯盟
    "REP": (0.8, 0.85),     # 共和黨（Kast）
    "PSC": (0.8, 1.0),      # 社會基督黨
    "PNL": (1.0, 0.8),      # 國家自由黨（Kaiser）
}
OVERRIDE = {}
# 選民三型：(比例, 經濟權重, 價值權重)
TYPES = [(0.5, 1.0, 0.6), (0.2, 0.6, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.0, 0.0)), (0.5, (-0.3, -0.2))]
BALANCED = (0.8, 0.8)
YEAR = [2025]

REGIONS = ["北部", "瓦爾帕萊索－奧希金斯", "聖地牙哥西北", "聖地牙哥東南", "中南部", "南部"]
DISTRICT_REGION = {**{d: "北部" for d in range(1, 6)}, **{d: "瓦爾帕萊索－奧希金斯" for d in (6, 7, 15, 16)},
                   **{d: "聖地牙哥西北" for d in (8, 9, 10)}, **{d: "聖地牙哥東南" for d in (11, 12, 13, 14)},
                   **{d: "中南部" for d in range(17, 22)}, **{d: "南部" for d in range(22, 29)}}
SMD_TOTAL, LIST_TOTAL, NEED = 108, 72, 91


def P(c):
    return OVERRIDE.get(YEAR[0], {}).get(c, POS[c])


# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {"IZQ": "左", "PC": "左", "FA": "左", "HUM": "左", "PEV": "左", "PRO": "左", "PS": "左", "FRVS": "左", "PPD": "左",
        "PL": "左", "PR": "左", "PDC": "左",
        "DEM": "右", "AMA": "右", "EVO": "右", "RN": "右", "UDI": "右", "REP": "右", "PSC": "右", "PNL": "右"}
BETA, SPREAD, ALPHA = 0.0, 0.0, {}


def prefs():
    return Prefs(POS, BLOC, BETA, SPREAD, ALPHA)


def largest_remainder(weights, seats):
    tot = sum(weights.values())
    q = {k: v * seats / tot for k, v in weights.items()}
    got = {k: int(v) for k, v in q.items()}
    for k in sorted(q, key=lambda k: q[k] - got[k], reverse=True)[:seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    keys = [k for k, w in weights.items() if w > 0]
    for _ in range(seats):
        k = max(keys, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def hilbert(x, y, n=1 << 10):
    d, t = 0, n >> 1
    while t:
        rx, ry = int(x & t > 0), int(y & t > 0)
        d += t * t * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = n - 1 - x, n - 1 - y
            x, y = y, x
        t >>= 1
    return d


_UNITS = {}


def units(year):
    """[(區, (市鎮, 投票所), 經度, 緯度, 國會有效票, {黨: 票})]，區內依 Hilbert 排序。只取有國會票的國內投票所。"""
    if year not in _UNITS:
        with open(os.path.join(HERE, "資料", f"cl-{year}.csv"), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        cc = [(k, c[2:]) for k, c in enumerate(rows[0]) if c.startswith("C_")]
        us = []
        for r in rows[1:]:
            d = re.sub(r"\D", "", r[1] or "")
            if not d:
                continue
            v = {c: int(r[k]) for k, c in cc}
            if sum(v.values()):
                us.append((DISTRICT_REGION[int(d)], (r[2], r[3]), float(r[4]), float(r[5]), sum(v.values()), v))
        out = []
        for reg in REGIONS:
            part = [u for u in us if u[0] == reg]
            # 智利南北狹長：經度放大 3 倍再排，避免 Hilbert 方格只沿緯度切
            xs, ys = [u[2] * 3 for u in part], [u[3] for u in part]
            x0, y0 = min(xs), min(ys)
            span = max(max(xs) - x0, max(ys) - y0) or 1.0
            part.sort(key=lambda u: (hilbert(int((u[2] * 3 - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1]))
            out += part
        _UNITS[year] = out
    return _UNITS[year]


def layout():
    """席次分配固定用 2025 國會有效票：單一 108、複數 72 都依 6 區。"""
    v = {}
    for u in units(2025):
        v[u[0]] = v.get(u[0], 0) + u[4]
    return largest_remainder(v, SMD_TOTAL), largest_remainder(v, LIST_TOTAL)


SMD_N, LIST_M = layout()


def rank_from(pos, cands, wx, wy, home=None):
    return prefs().rank(pos, home, cands, (wx, wy))


def voter_groups(parties, types=TYPES):
    return prefs().groups(parties, parties, types, OTHER_POS, BALANCED)


def pairwise_winner(cands, groups, weight):
    Pw = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        r = [c for c in order if c in cands]
        v = weight(src) * w
        for i, a in enumerate(r):
            for b in r[i + 1:]:
                Pw[(a, b)] += v
    for a in cands:
        if all(Pw[(a, b)] > Pw[(b, a)] for b in cands if b != a):
            return a, False, Pw
    wins = sorted(((Pw[(a, b)], a, b) for a in cands for b in cands if a != b and Pw[(a, b)] > Pw[(b, a)]), reverse=True)
    locked = set()

    def reach(x, y):
        st, seen = [x], set()
        while st:
            u = st.pop()
            if u == y:
                return True
            for (s, t) in locked:
                if s == u and t not in seen:
                    seen.add(t)
                    st.append(t)
        return False
    for _, a, b in wins:
        if not reach(b, a):
            locked.add((a, b))
    return next(c for c in cands if not any(t == c for _, t in locked)), True, Pw


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
    assert len(out) == n and all(out)
    return out


def single_seats(us, types=TYPES, shift=False):
    out, by = {}, {}
    st = {"循環": 0, "非第一偏好第一名當選": 0, "第一偏好過半": 0}
    first_share = []
    for reg in REGIONS:
        for part in cut([u for u in us if u[0] == reg], SMD_N[reg], shift):
            d = {}
            for u in part:
                for p, v in u[5].items():
                    d[p] = d.get(p, 0) + v
            cands = [p for p in d if p in POS and d[p] > 0]
            finals = sorted(cands, key=lambda p: (-d[p], p))[:3]
            w, cyc, _ = pairwise_winner(finals, voter_groups(cands, types), lambda s: d.get(s, 0))
            out[w] = out.get(w, 0) + 1
            by.setdefault(reg, {})
            by[reg][w] = by[reg].get(w, 0) + 1
            tot = sum(d.values())
            st["循環"] += cyc
            st["非第一偏好第一名當選"] += w != finals[0]
            st["第一偏好過半"] += d[w] > tot / 2
            first_share.append(d[w] / tot)
    first_share.sort()
    st["當選者第一偏好中位數"] = round(first_share[len(first_share) // 2] * 100, 1)
    return out, st, by


def list_seats(us):
    agg = {}
    for u in us:
        d = agg.setdefault(u[0], {})
        for p, v in u[5].items():
            d[p] = d.get(p, 0) + v
    out = {}
    for reg, m in LIST_M.items():
        d = dict(agg[reg])
        o = d.pop("其他", 0)
        for i in range(5):
            d[f"其他{i}"] = o / 5
        for p, n in sainte_lague(d, m).items():
            k = "其他" if p.startswith("其他") else p
            out[k] = out.get(k, 0) + n
    return out


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p in POS]
    pr = prefs()
    groups = [(p, 1.0, pr.rank(pr.pos[p], p, parties, BALANCED)) for p in parties]
    w, cyc, Pw = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    duel = {b: (round(Pw[(w, b)]), round(Pw[(b, w)])) for b in parties if b != w}
    return w, cyc, duel


def coalition(total, pm, need=NEED):
    return prefs().coalition(total, pm, need, BALANCED)


def national(us):
    t = {}
    for u in us:
        for p, v in u[5].items():
            t[p] = t.get(p, 0) + v
    s = sum(t.values())
    return {p: v / s for p, v in t.items()}


def scale(us, target):
    """target：{黨: 全國份額}；每黨在每個單位的票 ×（目標／實際）。"""
    base = national(us)
    return [(u[0], u[1], u[2], u[3], u[4], {p: v * target.get(p, 0) / base[p] if base.get(p) else 0 for p, v in u[5].items()})
            for u in us]


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def chamber(us, types=TYPES, shift=False):
    smd, st, by = single_seats(us, types, shift)
    lst = list_seats(us)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, st, by


ACTUAL = {
    2025: ("眾議院 155：REP 31、UDI 18、FA 17、PDG 14、RN 13、PS 11、PC 11、PPD 9、PDC 8、PNL 8 …；另參議院 50",
           "總統 Kast（REP）決選 58.2%"),
    2017: ("眾議院 155：RN 36、UDI 30、PS 19、PDC 14、RD 10、PPD 8、PC 8、PR 8、EVO 6 …；另參議院 50",
           "總統 Piñera（RN）決選 54.6%"),
}

# 總統第一輪（維基 Chilean general election 各年的 Election results 模板，引 SERVEL／TRICEL）：(候選人, 票, 位置)
PRES = {
    2025: [("Jara", 3483490, POS["PC"]), ("Kast", 3104458, POS["REP"]), ("Parisi", 2557737, POS["PDG"]),
           ("Kaiser", 1808434, POS["PNL"]), ("Matthei", 1617720, POS["UDI"]), ("Mayne-Nicholls", 163105, (0.0, -0.1)),
           ("Enríquez-Ominami", 154698, POS["PRO"]), ("Artés", 85392, POS["IZQ"])],
    2021: [("Kast", 1961779, POS["REP"]), ("Boric", 1815024, POS["FA"]), ("Parisi", 900064, POS["PDG"]),
           ("Sichel", 898635, (0.45, 0.0)), ("Provoste", 815563, POS["PDC"]), ("Enríquez-Ominami", 534383, POS["PRO"]),
           ("Artés", 102897, POS["IZQ"])],
    2017: [("Piñera", 2418540, POS["RN"]), ("Guillier", 1498040, (-0.6, -0.4)), ("Sánchez", 1338037, POS["FA"]),
           ("Kast", 523375, POS["REP"]), ("Goic", 387784, POS["PDC"]), ("Enríquez-Ominami", 376871, POS["PRO"]),
           ("Artés", 33665, POS["IZQ"]), ("Navarro", 23968, (-0.6, -0.2))],
}
CAND_PARTY = {"Jara": "PC", "Kast": "REP", "Parisi": "PDG", "Kaiser": "PNL", "Matthei": "UDI", "Enríquez-Ominami": "PRO",
              "Artés": "IZQ", "Boric": "FA", "Sichel": "EVO", "Provoste": "PDC", "Piñera": "RN", "Guillier": "PS",
              "Sánchez": "FA", "Goic": "PDC", "Navarro": "PRO"}
RUNOFF = {2025: ("Kast", "Jara", 58.2), 2021: ("Boric", "Kast", 55.9), 2017: ("Piñera", "Guillier", 54.6)}


def _cand_prefs(year):
    cs = PRES[year]
    where = {c: p for c, _, p in cs}
    return Prefs(where, {c: BLOC.get(CAND_PARTY.get(c)) for c, _, _ in cs}, BETA, SPREAD,
                 {c: ALPHA.get(CAND_PARTY.get(c), 0) for c, _, _ in cs})


def _rank(pos, cands, where, wx, wy, home=None):
    return Prefs(where, BLOC, BETA, 0.0, ALPHA).rank(pos, home, cands, (wx, wy))


def presidential(year, types=TYPES):
    """全國 top-3 孔多賽：第一輪前三名兩兩對決；各候選人的第一偏好選民依偏好引擎排序。"""
    cs = PRES[year]
    votes = {c: n for c, n, _ in cs}
    finals = [c for c, _, _ in sorted(cs, key=lambda x: -x[1])[:3]]
    groups = _cand_prefs(year).groups([c for c, _, _ in cs], finals, types)
    w, cyc, Pw = pairwise_winner(finals, groups, lambda s: votes[s])
    pct = {f"{a}>{b}": round(Pw[(a, b)] * 100 / (Pw[(a, b)] + Pw[(b, a)]), 1) for a in finals for b in finals if a < b}
    return finals, w, cyc, pct


def runoff_fit(year, types=TYPES):
    """實際決選兩人在模型裡的對決（校準用）。"""
    a, b, real = RUNOFF[year]
    cs = PRES[year]
    votes = {c: n for c, n, _ in cs}
    groups = _cand_prefs(year).groups([c for c, _, _ in cs], [a, b], types)
    _, _, Pw = pairwise_winner([a, b], groups, lambda s: votes[s])
    return round(Pw[(a, b)] * 100 / (Pw[(a, b)] + Pw[(b, a)]), 1), real


# 制憲公投三案（12 §4、14 §4）：2022 年草案（制憲會議，左派主導）、2023 年草案（憲法委員會，右派主導）、現行憲法。
# 選民用 2025 國會得票（2022 起恢復強制投票，兩次公投與 2025 的投票母體相近）。
CHARTER = {"2022 草案": (-0.7, -0.6), "2023 草案": (0.4, 0.2), "現行憲法": (0.2, 0.1)}   # 位置用兩次公投實際結果校準
CHARTER_REAL = {"2022 草案": 38.1, "2023 草案": 44.2}   # 實際「贊成」（2022-09-04：4,860,266 對 7,886,434；2023-12-17：5,470,025 對 6,894,287）


def charter_vote(types=TYPES):
    nat = national(units(2025))
    opts = list(CHARTER)
    pr = prefs()
    groups = []
    for p in nat:
        center = pr.pos[p] if p in pr.pos else (0.0, 0.0)
        for t in types:
            for pw, at in pr.points(center):
                groups.append((p, t[0] * pw, sorted(opts, key=lambda o: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(t[1:], CHARTER[o], at)), o))))
    w, cyc, Pw = pairwise_winner(opts, groups, lambda s: nat.get(s, 0))
    pct = {f"{a}>{b}": round(Pw[(a, b)] * 100 / (Pw[(a, b)] + Pw[(b, a)]), 1) for a in opts for b in opts if a != b and a < b}
    return w, cyc, pct


def projection():
    """第 3 屆（推測）：以 2025 地理；兩端（REP、PNL、PSC、PC、IZQ）各讓出 1/8 第一偏好給中間（RN、PS 各半）。"""
    us = units(2025)
    nat = national(us)
    t = dict(nat)
    moved = 0
    for p in ("REP", "PNL", "PSC", "PC", "IZQ"):
        t[p] = nat[p] * 7 / 8
        moved += nat[p] / 8
    t["RN"] += moved / 2
    t["PS"] += moved / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print("單一 108：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print("複數 72：", fmt(lst))
    print("全院 180：", fmt(total), "合計", sum(total.values()))
    print(f"［議會制夾］首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"［議會制夾］組閣聯盟（由近到遠）：{'＋'.join(seq)}＝{acc}")
    return total


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("單一 108：", SMD_N)
    print("複數 72：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重經濟", [(1.0, 1.0, 0.6)]), ("全部重價值", [(1.0, 0.6, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.8)])):
            cells = []
            for y in (2025, 2017):
                s_, _, t_, _, _ = chamber(units(y), types)
                cells.append(f"{fmt(s_)} ｜ 首長 {head_of_gov(t_)[0]}")
            pres = "、".join(f"{y} {presidential(y, types)[1]}" for y in (2025, 2021, 2017))
            print(f"| {label} | " + " | ".join(cells) + f" | 總統 {pres} | 憲法 {charter_vote(types)[0]} |")
        for shift in (False, True):
            print(f"| 切線{'位移半區' if shift else '基準'} | " + " | ".join(fmt(chamber(units(y), shift=shift)[0]) for y in (2025, 2017)) + " |")
        nat = national(units(2025))
        for d in (-6, -3, 3, 6):
            t = dict(nat)
            t["REP"] = nat["REP"] + d / 100
            t["FA"] = nat["FA"] - d / 100
            smd, _, total, _, _ = chamber(scale(units(2025), t))
            print(f"| REP {d:+d}／FA {-d:+d} 點 | {fmt(smd)} | {fmt(total)} | 首長 {head_of_gov(total)[0]} |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for y in (2025, 2017):
        print()
        print("實際：", ACTUAL[y][0], "；", ACTUAL[y][1])
        report(str(y), units(y))
    print()
    for y in (2025, 2021, 2017):
        finals, w, cyc, pct = presidential(y)
        print(f"［總統制夾］總統 {y} top-3（{'、'.join(finals)}）：{w}；循環 {cyc}；兩兩 {pct}；實際決選 {RUNOFF[y]}，模型同對決 {runoff_fit(y)[0]}")
    w, cyc, pct = charter_vote()
    print(f"制憲三案：{w}；循環 {cyc}；兩兩 {pct}；實際贊成 {CHARTER_REAL}")


if __name__ == "__main__":
    main()
