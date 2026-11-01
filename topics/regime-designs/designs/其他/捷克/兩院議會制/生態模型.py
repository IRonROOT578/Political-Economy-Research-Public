"""捷克兩院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
所有輸入都是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py            # 2025-10、2021-10 眾議院重算；參議院；2023 總統 top-3
    python 生態模型.py --sweep    # 敏感度

地區：14 州的實際得票（Wikipedia 引 volby.cz）；州內單一選區加城鄉梯度與隨機擾動。
偏好：二維空間（地緣：西方整合 −1 … 主權派 +1；社經：自由市場、改革 −1 … 民粹、國家主義 +1）。
每黨選民分三型（重地緣、重社經、均衡）。
眾議院單一 110：依人口分到 14 州；top-3 孔多賽；循環用 Ranked Pairs。
眾議院複數 90：8 個 NUTS-2 區，聖拉古，無法定門檻；海外票照現行併入南摩拉維亞所在的區。
參議院 81：依人口分到 14 州；top-3 孔多賽（模型假設 81 席同時以同一次民意選出）。
行政首長：眾議院全院 200 記名排名投票，孔多賽完成法；須 ≥101。
"""
import random
import sys

POS = {
    # 2025
    "ANO": (0.1, 0.7),
    "SPOLU": (-0.7, -0.6),
    "STAN": (-0.6, -0.2),
    "Piráti": (-0.8, 0.1),
    "SPD": (0.9, 0.5),
    "AUTO": (0.6, -0.6),
    "Stačilo": (0.9, 0.9),
    # 2021
    "PirSTAN": (-0.7, -0.05),
    "Přísaha": (0.3, 0.2),
    "ČSSD": (-0.1, 0.8),
    "KSČM": (0.8, 0.9),
}
# 選民三型：(比例, 地緣權重, 社經權重)
TYPES = [(0.5, 1.0, 0.4), (0.2, 0.4, 1.0), (0.3, 0.8, 0.5)]
OTHER_POS = [(0.3, (-0.3, 0.0)), (0.4, (0.6, 0.3)), (0.3, (0.0, 0.4))]

P25 = ["ANO", "SPOLU", "STAN", "Piráti", "SPD", "AUTO", "Stačilo", "其他"]
P21 = ["SPOLU", "ANO", "PirSTAN", "SPD", "Přísaha", "ČSSD", "KSČM", "其他"]
# 州：(2026 人口, 複數區, 2025 得票 %（P25 順序）, 2025 投票率, 2021 得票 %（P21 順序）, 2021 投票率)
REGION = {
    "布拉格": (1407084, "布拉格", (19.83, 33.97, 13.40, 16.89, 5.23, 5.15, 2.75, 2.66), 71.44,
            (40.0, 17.5, 22.6, 4.6, 3.4, 4.0, 2.1, 5.8), 70.2),
    "中波希米亞": (1477134, "中波希米亞", (31.12, 24.32, 13.72, 9.09, 7.06, 7.76, 3.63, 3.19), 71.28,
              (28.7, 24.9, 19.5, 7.8, 4.6, 4.6, 3.5, 6.4), 68.0),
    "南波希米亞": (652896, "西南", (34.87, 23.61, 10.76, 7.59, 7.93, 7.04, 4.79, 3.28), 69.49,
              (29.1, 26.7, 13.5, 9.0, 4.5, 5.5, 4.5, 7.2), 66.3),
    "皮爾森": (614683, "西南", (37.31, 20.99, 10.62, 7.78, 8.88, 7.16, 4.26, 2.90), 68.26,
            (26.6, 29.0, 13.9, 10.0, 4.7, 5.0, 4.1, 6.7), 64.7),
    "卡羅維發利": (292027, "西北", (42.49, 15.40, 10.94, 6.49, 10.21, 7.28, 4.09, 2.98), 60.74,
              (20.2, 33.1, 14.2, 12.8, 4.9, 3.8, 3.4, 7.6), 57.1),
    "烏斯季": (805943, "西北", (44.85, 15.40, 9.61, 6.96, 9.13, 6.79, 4.32, 2.87), 61.96,
            (19.8, 35.6, 14.0, 11.9, 4.4, 3.2, 3.9, 7.2), 57.7),
    "利貝雷茨": (448610, "東北", (34.40, 18.06, 16.34, 8.20, 8.65, 7.35, 4.18, 2.74), 68.05,
             (22.8, 26.9, 21.4, 11.0, 4.3, 3.5, 3.0, 7.1), 64.6),
    "赫拉德茨-克拉洛韋": (554668, "東北", (33.63, 23.60, 12.21, 8.05, 7.75, 7.61, 4.21, 2.85), 70.56,
                  (28.6, 27.0, 15.1, 9.1, 4.7, 4.9, 3.4, 7.2), 67.9),
    "帕爾杜比采": (530950, "東北", (34.61, 23.62, 11.05, 7.71, 7.68, 7.76, 4.51, 2.98), 71.41,
              (28.5, 26.8, 14.1, 9.4, 5.0, 5.1, 3.8, 7.3), 67.9),
    "維索基納": (515953, "東南", (36.11, 23.28, 11.80, 7.07, 7.32, 6.80, 4.70, 2.83), 72.53,
             (28.0, 26.7, 13.5, 8.9, 5.2, 6.7, 4.7, 6.3), 68.9),
    "南摩拉維亞": (1230516, "東南", (32.29, 27.24, 9.63, 9.45, 7.54, 6.13, 4.42, 3.21), 70.07,
              (30.0, 25.4, 14.2, 9.4, 6.0, 4.4, 3.7, 6.9), 66.4),
    "奧洛穆克": (631480, "中摩拉維亞", (38.72, 20.14, 9.36, 7.33, 9.43, 6.64, 5.16, 3.12), 68.61,
             (24.5, 29.8, 12.4, 12.2, 4.7, 4.5, 4.0, 7.9), 64.7),
    "茲林": (577515, "中摩拉維亞", (34.87, 24.24, 10.20, 7.54, 8.74, 6.71, 4.65, 2.94), 69.76,
           (27.8, 27.0, 13.4, 11.4, 4.2, 4.9, 3.3, 8.0), 67.4),
    "摩拉維亞-西里西亞": (1176380, "摩拉維亞-西里西亞", (43.42, 17.98, 8.37, 7.18, 8.09, 6.42, 5.52, 2.91), 66.31,
                  (20.6, 33.7, 11.1, 12.8, 4.9, 5.4, 4.0, 7.5), 60.6),
}
# 海外（2025）：得票 %；有效票約 6 萬（假設），照現行併入南摩拉維亞所在的「東南」區
ABROAD25 = ((3.95, 39.26, 21.48, 28.24, 2.04, 2.32, 1.04, 1.56), 60000)
CH_SMD, CH_LIST, SENATE = 110, 90, 81


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


POP = {r: v[0] for r, v in REGION.items()}
SMD_N = largest_remainder(POP, CH_SMD)
SEN_N = largest_remainder(POP, SENATE)
DISTRICTS = {}
for r, v in REGION.items():
    DISTRICTS.setdefault(v[1], []).append(r)
LIST_M = largest_remainder({d: sum(POP[r] for r in rs) for d, rs in DISTRICTS.items()}, CH_LIST)


def shares(year):
    """回傳 (政黨清單, {州: {黨: %}}, {州: 權重})。"""
    parties = P25 if year == 2025 else P21
    si, ti = (2, 3) if year == 2025 else (4, 5)
    sh = {r: dict(zip(parties, v[si])) for r, v in REGION.items()}
    w = {r: v[0] * v[ti] / 100 for r, v in REGION.items()}
    return parties, sh, w


def rank_from(pos, cands, wx, wy, where=POS):
    d = lambda c: (wx * (where[c][0] - pos[0])) ** 2 + (wy * (where[c][1] - pos[1])) ** 2
    return sorted(cands, key=d)


def voter_groups(parties, types=TYPES):
    out = []
    for p in parties:
        for w, wx, wy in types:
            out.append((p, w, rank_from(POS[p], parties, wx, wy)))
    for w, pos in OTHER_POS:
        out.append(("其他", w, rank_from(pos, parties, 0.7, 0.7)))
    return out


def pairwise_winner(cands, groups, weight):
    """groups: [(來源, 比例, 排序)]；weight(來源) 給該來源的總量。回傳 (勝者, 是否循環, 兩兩票數)。"""
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


URBAN = {"SPOLU": 0.25, "Piráti": 0.35, "PirSTAN": 0.3, "STAN": 0.1, "ANO": -0.15, "SPD": -0.15,
         "Stačilo": -0.1, "KSČM": -0.1, "ČSSD": -0.05}


def smd_local(base, i, n, rng, sd):
    """州內第 i 個（共 n 個）單一選區：城鄉梯度（i=0 最城市）＋隨機擾動。"""
    d = dict(base)
    if n >= 3:
        u = 1 - 2 * i / (n - 1)
        for p, k in URBAN.items():
            if p in d:
                d[p] *= 1 + k * u
    for p in d:
        if p != "其他":
            d[p] = max(0.3, d[p] + rng.gauss(0, sd))
    t = sum(d.values())
    return {p: v * 100 / t for p, v in d.items()}


def smd_seats(year, counts, types=TYPES, seed=7, sd=2.5, override=None):
    rng = random.Random(seed)
    parties, sh, _ = shares(year)
    if override:
        sh = override
    cands = [p for p in parties if p != "其他"]
    groups = voter_groups(cands, types)
    out = {p: 0 for p in cands}
    stats = {"循環": 0, "非第一偏好第一名當選": 0}
    by = {}
    for r, n in counts.items():
        for i in range(n):
            d = smd_local(sh[r], i, n, rng, sd)
            finals = sorted(cands, key=lambda p: d[p], reverse=True)[:3]
            w, cyc, _ = pairwise_winner(finals, groups, lambda s: d.get(s, 0))
            out[w] += 1
            by.setdefault(r, []).append(w)
            stats["循環"] += cyc
            stats["非第一偏好第一名當選"] += w != finals[0]
    return out, stats, by


def list_seats(year, override=None):
    parties, sh, w = shares(year)
    if override:
        sh = override
    out = {p: 0 for p in parties}
    for dname, rs in DISTRICTS.items():
        tot = sum(w[r] for r in rs)
        d = {p: sum(w[r] * sh[r][p] for r in rs) for p in parties}
        if year == 2025 and dname == "東南":
            for p, v in zip(parties, ABROAD25[0]):
                d[p] += ABROAD25[1] * v
            tot += ABROAD25[1]
        d = {p: v / tot for p, v in d.items()}
        o = d.pop("其他", 0)
        for i in range(5):  # 「其他」視為 5 個小黨
            d[f"其他{i}"] = o / 5
        for p, n in sainte_lague(d, LIST_M[dname]).items():
            out["其他" if p.startswith("其他") else p] += n
    return out


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p != "其他"]
    groups = [(p, 1.0, rank_from(POS[p], parties, 0.8, 0.5)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min((P[(w, b)] for b in parties if b != w), default=total[w])
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def national(year):
    parties, sh, w = shares(year)
    tot = sum(w.values())
    return {p: sum(w[r] * sh[r][p] for r in sh) / tot for p in parties}


def scaled(year, party, x):
    """把某黨的全國第一偏好調到 x%，其餘按比例；各州維持相對形狀。"""
    parties, sh, _ = shares(year)
    nat = national(year)[party]
    out = {}
    for r, d in sh.items():
        k = d[party] * x / nat
        rest = 100 - d[party]
        out[r] = {p: (k if p == party else v * (100 - k) / rest) for p, v in d.items()}
    return out


# 總統 2023：top-3 候選人位置與第一輪各候選人選民的位置
PRES = {
    # Pavel、Nerudová 的位置以民調校準（14 §1.3）
    "cands": {"Pavel": (-0.6, -0.2), "Babiš": POS["ANO"], "Nerudová": (-0.4, -0.4)},
    "voters": [("Pavel", 35.40, (-0.6, -0.2)), ("Babiš", 34.99, POS["ANO"]), ("Nerudová", 13.92, (-0.4, -0.4)),
               ("Fischer", 6.75, (-0.5, -0.3)), ("Bašta", 4.45, POS["SPD"]), ("Hilšer", 2.56, (-0.7, -0.2)),
               ("Diviš", 1.35, (0.0, -0.2)), ("Zima", 0.55, (0.0, 0.3))],
}


def presidential(types=TYPES):
    c = PRES["cands"]
    groups = []
    for name, share, pos in PRES["voters"]:
        for w, wx, wy in types:
            groups.append((name, w, rank_from(pos, list(c), wx, wy, where=c)))
    shares_ = {n: s for n, s, _ in PRES["voters"]}
    return pairwise_winner(list(c), groups, lambda s: shares_[s])


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def chamber(year, types=TYPES, override=None, seed=7, sd=2.5):
    smd, st, by = smd_seats(year, SMD_N, types, seed, sd, override)
    lst = list_seats(year, override)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, st, by


def main():
    if "--sweep" in sys.argv:
        print("| 選民類型 | 2025 單一 110 | 2021 單一 110 |")
        print("|---|---|---|")
        for label, types in (("基準（重地緣型占一半）", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4)]),
                             ("全部重社經", [(1.0, 0.4, 1.0)])):
            print(f"| {label} | {fmt(chamber(2025, types)[0])} | {fmt(chamber(2021, types)[0])} |")
        print()
        print("| 擾動 sd | 種子 | 2025 單一 110 |")
        print("|---|---|---|")
        for sd in (0, 2.5, 5):
            for seed in (1, 7):
                print(f"| {sd} | {seed} | {fmt(chamber(2025, seed=seed, sd=sd)[0])} |")
        print()
        print("| ANO 第一偏好（2025 形狀，其餘按比例） | 單一 110 | 全院 200 | 首長 |")
        print("|:--:|---|---|---|")
        for x in (20, 25, 30, 34.5, 40):
            smd, lst, total, _, _ = chamber(2025, override=scaled(2025, "ANO", x))
            w, _, worst = head_of_gov(total)
            print(f"| {x}% | {fmt(smd)} | {fmt(total)} | {w}（最弱 {worst:.0f}） |")
        print()
        for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4)]), ("全部重社經", [(1.0, 0.4, 1.0)])):
            w, cyc, P = presidential(types)
            print(f"總統 2023 {label}：{w}（循環 {cyc}）",
                  "、".join(f"{a}>{b} {v:.1f}" for (a, b), v in P.items() if v > P[(b, a)]))
        return
    print("眾議院單一選區數：", SMD_N)
    print("參議院選區數：", SEN_N)
    print("複數選區 M：", LIST_M)
    for year in (2025, 2021):
        smd, lst, total, st, by = chamber(year)
        w, cyc, worst = head_of_gov(total)
        print(f"\n## 眾議院 {year}-10")
        print("全國（模型加權）：", {p: round(v, 1) for p, v in national(year).items()})
        print("單一 110：", fmt(smd), st)
        print("布拉格：", fmt({p: by["布拉格"].count(p) for p in set(by["布拉格"])}))
        print("複數 90：", fmt(lst))
        print("全院 200：", fmt(total))
        print(f"行政首長：{w}；循環 {cyc}；最弱一場對決 {worst:.0f} 票")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者單獨：全院 {total[w]}（≥101 {total[w] >= 101}；≥120 {total[w] >= 120}）"
              f"；複數 {lst.get(w, 0)}（≥54 {lst.get(w, 0) >= 54}）")
        sen, sst, _ = smd_seats(year, SEN_N)
        print("參議院 81（假設同一次民意全部改選）：", fmt(sen), sst)
    w, cyc, P = presidential()
    print(f"\n## 總統 2023 top-3：{w}（循環 {cyc}）")
    print("    ", "、".join(f"{a}>{b} {v:.1f}" for (a, b), v in P.items() if v > P[(b, a)]))


if __name__ == "__main__":
    main()
