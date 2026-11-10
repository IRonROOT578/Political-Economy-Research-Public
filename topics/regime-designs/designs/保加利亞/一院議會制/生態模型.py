"""保加利亞一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
所有輸入都是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py            # 歷史重算（2024-10、2026-04）與推估屆次
    python 生態模型.py --sweep    # 敏感度

偏好：二維空間（地緣：親西方 −1 … 親俄 +1；體制：反寡頭改革 −1 … 寡頭網絡 +1）＋族群軸
（土耳其裔／穆斯林政黨 1，其餘 0）。每黨選民分三型（重地緣、重體制、均衡），依加權距離排序其他政黨。
單一席次 100：top-3 孔多賽（第一輪取第一偏好前 3 名，第二輪孔多賽完成法；循環時 Ranked Pairs）。
複數席次 80：7 區，聖拉古，無法定門檻。
行政首長：全院 180 記名排名投票（議員依黨的均衡型排序），孔多賽完成法；須 ≥91 排在「維持空缺」之上。
"""
import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

# 政黨系：(地緣 x, 體制 y, 族群 e)。位置是假設（12 §2.1）。
POS = {
    "進步保加利亞": (0.3, -0.4, 0),
    "GERB": (-0.5, 0.7, 0),
    "PP–DB": (-0.9, -0.8, 0),
    "DPS": (-0.3, 1.0, 1),      # 2024 年為「DPS–新開始」（Peevski）
    "APS": (0.0, 0.5, 1),       # Dogan 派
    "復興": (0.9, -0.5, 0),
    "社會黨": (0.5, 0.2, 0),
    "ITN": (0.0, 0.1, 0),
    "MECh": (0.4, -0.7, 0),
    "Velichie": (0.6, -0.3, 0),
}
ETHNIC = ("DPS", "APS")
# 選民三型：(比例, 地緣權重, 體制權重, 族群權重)
TYPES = [(0.35, 1.0, 0.4, 1.5), (0.35, 0.4, 1.0, 1.5), (0.30, 0.7, 0.7, 1.5)]
# 「其他」選民（抗議小黨、藍色保加利亞等）的位置與比例
OTHER_POS = [(0.5, (0.5, -0.5, 0)), (0.25, (-0.6, -0.3, 0)), (0.25, (0.0, 0.3, 0))]

# 7 個複數選區（NUTS-2 規劃區，索非亞市單獨；人口萬，2021 普查約數）
REGIONS = ["索非亞市", "西南", "南中", "東南", "東北", "北中", "西北"]
POP = {"索非亞市": 125, "西南": 81, "南中": 136, "東南": 98, "東北": 91, "北中": 75, "西北": 72}
# 區域偏移（百分點，示意）
OFFSET = {
    "索非亞市": {"PP–DB": +12, "進步保加利亞": -4, "GERB": -2, "復興": -3, "社會黨": -1},
    "西南": {"GERB": +4, "PP–DB": -3},
    "南中": {"GERB": +1, "PP–DB": -4},
    "東南": {"復興": +1, "PP–DB": -4},
    "東北": {"復興": +3, "PP–DB": -3},
    "北中": {"社會黨": +2, "進步保加利亞": +3, "PP–DB": -5},
    "西北": {"社會黨": +4, "進步保加利亞": +5, "PP–DB": -6, "GERB": -1},
}
# 族群政黨得票對全國的倍數：名單層（全區）、單一選區（非集中區）
ETH_LIST = {"索非亞市": 0.15, "西南": 0.8, "南中": 1.8, "東南": 1.0, "東北": 2.0, "北中": 1.6, "西北": 0.4}
ETH_SMD = {"索非亞市": 0.15, "西南": 0.5, "南中": 0.7, "東南": 0.7, "東北": 1.2, "北中": 0.9, "西北": 0.4}
# 族群集中的單一選區：(名稱, 所在區, 倍數)，上限 80%
ETH_SEATS = [("卡爾賈利一", "南中", 6.0), ("卡爾賈利二", "南中", 5.5), ("斯莫梁", "南中", 1.6),
             ("拉兹格勒", "北中", 3.2), ("錫利斯特拉—圖特拉坎", "北中", 2.0),
             ("舍門", "東北", 2.2), ("特爾戈維什泰", "東北", 2.4),
             ("布爾加斯西北", "東南", 2.6), ("布拉戈耶夫格勒南", "西南", 2.0)]


def largest_remainder(weights, seats):
    tot = sum(weights.values())
    q = {k: v * seats / tot for k, v in weights.items()}
    got = {k: int(v) for k, v in q.items()}
    for k in sorted(q, key=lambda k: q[k] - got[k], reverse=True)[:seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


SMD_N = largest_remainder(POP, 100)
LIST_M = largest_remainder(POP, 80)


def rank_from(pos, cands, wx, wy, we):
    d = lambda c: (wx * (POS[c][0] - pos[0])) ** 2 + (wy * (POS[c][1] - pos[1])) ** 2 + (we * (POS[c][2] - pos[2])) ** 2
    return sorted(cands, key=d)


def voter_groups(parties, types=TYPES):
    """回傳 [(得票來源, 比例, 排序)]：每黨選民三型＋「其他」三類。"""
    out = []
    for p in parties:
        for w, wx, wy, we in types:
            out.append((p, w, rank_from(POS[p], parties, wx, wy, we)))
    for w, pos in OTHER_POS:
        out.append(("其他", w, rank_from(pos, parties, 0.7, 0.7, 1.5)))
    return out


def local(fp, region, eth_mult, rng=None, sd=0.0):
    d = {k: v for k, v in fp.items()}
    for k, v in OFFSET[region].items():
        if k in d:
            d[k] = max(0.5, d[k] + v)
    if rng:
        for k in d:
            if k != "其他" and k not in ETHNIC:
                d[k] = max(0.3, d[k] + rng.gauss(0, sd))
    eth = sum(d.get(k, 0) for k in ETHNIC)
    if eth:
        target = min(80.0, sum(fp.get(k, 0) for k in ETHNIC) * eth_mult)
        rest = 100 - eth
        for k in d:
            d[k] = d[k] * target / eth if k in ETHNIC else d[k] * (100 - target) / rest
    t = sum(d.values())
    return {k: v * 100 / t for k, v in d.items()}


def pairwise_winner(cands, groups, weight):
    """groups: [(來源, 比例, 排序)]；weight(來源) 給該來源的總量。回傳 (勝者, 是否循環)。"""
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        r = [c for c in order if c in cands]
        v = weight(src) * w
        for i, a in enumerate(r):
            for b in r[i + 1:]:
                P[(a, b)] += v
    for a in cands:
        if all(P[(a, b)] > P[(b, a)] for b in cands if b != a):
            return a, False, P
    # Ranked Pairs
    wins = sorted(((P[(a, b)], a, b) for a in cands for b in cands if a != b and P[(a, b)] > P[(b, a)]), reverse=True)
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
    return next(c for c in cands if not any(t == c for _, t in locked)), True, P


def single_seats(fp, types=TYPES, seed=7):
    rng = random.Random(seed)
    parties = [p for p in fp if p != "其他"]
    groups = voter_groups(parties, types)
    out = {p: 0 for p in parties}
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    eth_won = []
    for region in REGIONS:
        special = [s for s in ETH_SEATS if s[1] == region]
        seats = [(s[0], s[2]) for s in special] + [(None, ETH_SMD[region])] * (SMD_N[region] - len(special))
        for name, mult in seats:
            d = local(fp, region, mult, rng, 3.0)
            _w = lambda s: d.get(s, 0)
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
            finals = _finals_for({p: d[p] for p in parties}, 3, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, groups, _w)[0], POS)
            w, cyc, _ = pairwise_winner(finals, groups, _w)
            out[w] += 1
            stats["循環"] += cyc
            stats["第一偏好過半"] += d[w] > 50
            stats["非第一偏好第一名當選"] += w != finals[0]
            if name:
                eth_won.append(f"{name}:{w}")
    return out, stats, eth_won


def list_seats(fp):
    parties = [p for p in fp if p != "其他"]
    out = {p: 0 for p in parties}
    out["其他"] = 0
    for region in REGIONS:
        d = local(fp, region, ETH_LIST[region])
        o = d.pop("其他", 0)
        for i in range(5):  # 「其他」視為 5 個小黨
            d[f"其他{i}"] = o / 5
        for p, n in sainte_lague(d, LIST_M[region]).items():
            out["其他" if p.startswith("其他") else p] += n
    return out


def head_of_gov(total):
    """全院 180 以議員所屬政黨的均衡型排序投票。回傳 (勝者, 循環, 勝者對每個對手的最少票)。"""
    parties = [p for p, n in total.items() if n and p != "其他"]
    groups = [(p, 1.0, rank_from(POS[p], parties, 0.7, 0.7, 1.5)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min((P[(w, b)] for b in parties if b != w), default=total[w])
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


SCENARIOS = {
    # 實際得票（%，「都不支持」與 0.5% 以下小黨併入其他；Siyanie 併入其他）
    "2024-10 大選": {"GERB": 25.52, "PP–DB": 13.75, "復興": 12.92, "DPS": 11.13, "社會黨": 7.32, "APS": 7.24,
                    "ITN": 6.56, "MECh": 4.45, "Velichie": 3.87, "其他": 7.24},
    "2026-04 大選": {"進步保加利亞": 43.91, "GERB": 13.18, "PP–DB": 12.42, "DPS": 7.01, "復興": 4.19,
                    "MECh": 3.18, "Velichie": 3.06, "社會黨": 2.97, "APS": 1.54, "ITN": 0.73, "其他": 7.81},
    # 推估：新制下第 3 屆，進步保加利亞浪潮退去（12 §2.2）
    "推估 第 3 屆": {"進步保加利亞": 26, "GERB": 18, "PP–DB": 17, "DPS": 6, "APS": 2, "復興": 10, "社會黨": 5,
                   "MECh": 3, "Velichie": 3, "其他": 10},
}


def run(name, types=TYPES):
    fp = SCENARIOS[name]
    smd, stats, eth = single_seats(fp, types)
    lst = list_seats(fp)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, stats, eth


def main():
    if "--sweep" in sys.argv:
        print("| 進步保加利亞第一偏好（第 3 屆其餘按比例） | 單一席次 | 全院 | 行政首長 |")
        print("|:--:|---|---|---|")
        for pb in (12, 16, 20, 26, 32):
            fp = dict(SCENARIOS["推估 第 3 屆"])
            rest = 100 - fp["進步保加利亞"]
            fp = {k: (v * (100 - pb) / rest if k != "進步保加利亞" else pb) for k, v in fp.items()}
            SCENARIOS["_s"] = fp
            smd, lst, total, _, _ = run("_s")
            w, _, worst = head_of_gov(total)
            f = lambda d: "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)
            print(f"| {pb}% | {f(smd)} | {f(total)} | {w}（最弱對決 {worst:.0f}） |")
        print()
        print("| 選民類型 | 2024-10 單一席次 | 2026-04 單一席次 |")
        print("|---|---|---|")
        for label, types in (("基準（三型各約 1/3）", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4, 1.5)]),
                             ("全部重體制", [(1.0, 0.4, 1.0, 1.5)])):
            a = run("2024-10 大選", types)[0]
            b = run("2026-04 大選", types)[0]
            f = lambda d: "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)
            print(f"| {label} | {f(a)} | {f(b)} |")
        return
    print("單一選區數：", SMD_N, "；複數選區 M：", LIST_M)
    for name in SCENARIOS:
        smd, lst, total, stats, eth = run(name)
        w, cyc, worst = head_of_gov(total)
        f = lambda d: "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)
        print(f"\n## {name}")
        print("單一 100：", f(smd), stats)
        print("族群選區：", "；".join(eth))
        print("複數 80：", f(lst))
        print("全院 180：", f(total))
        print(f"行政首長（全院排名投票）：{w}；循環 {cyc}；勝者在最弱一場對決得 {worst:.0f} 票")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者單獨：全院 {total[w]}（≥91 {total[w] >= 91}；≥108 {total[w] >= 108}；≥120 {total[w] >= 120}）"
              f"；複數 {lst.get(w, 0)}（≥48 {lst.get(w, 0) >= 48}）")
        # 參考：只限單一席次 100 選首長時
        w2, _, worst2 = head_of_gov({k: v for k, v in smd.items()})
        print(f"參考：若只由單一席次 100 選：{w2}（最弱 {worst2:.0f}）")


if __name__ == "__main__":
    main()
