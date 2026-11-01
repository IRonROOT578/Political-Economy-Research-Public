"""羅馬尼亞一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
所有輸入都是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2024-12 國會重算、推估屆次、2024／2025 總統 top-3
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --validate   # 地區底子對照

地區底子：找不到 2024 國會的分縣得票，改用 2024-11-24 總統初選的分縣得票當「各黨在哪裡強」的形狀
（PSD←Ciolacu、AUR←Simion、PNL←Ciucă、USR←Lasconi、SOS 與 POT←Georgescu、UDMR←Kelemen），
再用迭代比例調整把全國加總拉回國會的實際得票。驗證見 14 §1.2。

偏好：二維空間（地緣：親歐盟 −1 … 主權派 +1；體制：反建制改革 −1 … 建制恩庇 +1）＋族群軸
（匈牙利族政黨 1，其餘 0）。每黨選民分三型（重地緣、重體制、均衡）。
單一席次 180：依人口分到 41 縣＋布加勒斯特；top-3 孔多賽；循環用 Ranked Pairs。
複數席次 120：10 個國內區＋海外 1 區，聖拉古，無法定門檻。
行政首長：全院 300 記名排名投票（議員依黨的均衡型排序），孔多賽完成法；須 ≥151。
"""
import random
import sys

POS = {
    "PSD": (0.3, 0.8, 0),      # 選民社會保守、偏農村：地緣上比黨中央更靠主權側（校準見 14 §1.3）
    "PNL": (-0.5, 0.6, 0),
    "USR": (-0.9, -0.4, 0),
    "AUR": (0.7, -0.3, 0),
    "SOS": (1.0, -0.6, 0),
    "POT": (0.9, -0.8, 0),
    "UDMR": (-0.4, 0.7, 1),
}
ETHNIC = ("UDMR",)
# 選民三型：(比例, 地緣權重, 體制權重, 族群權重)。2024–25 年地緣是主軸，重地緣型占一半（校準見 14 §1.3）
TYPES = [(0.5, 1.0, 0.4, 1.5), (0.2, 0.4, 1.0, 1.5), (0.3, 0.8, 0.5, 1.5)]
# 「其他」選民（REPER、SENS、DREPT、PMP、少數族群組織、獨立候選人等）
OTHER_POS = [(0.4, (-0.6, -0.3, 0)), (0.3, (0.0, 0.3, 0)), (0.3, (0.7, -0.5, 0))]

# 縣：(發展區, 2021 普查人口, 2024 總統初選有效票, 初選得票 %：
#       Georgescu, Lasconi, Ciolacu, Simion, Ciucă, Geoană, Kelemen)
COUNTY = {
    "Bucharest": ("布加勒斯特—伊爾福夫", 1716983, 912352, (14.54, 35.82, 14.83, 9.97, 6.62, 10.36, 0.46)),
    "Ilfov": ("布加勒斯特—伊爾福夫", 542686, 262712, (23.56, 25.59, 12.93, 12.47, 11.51, 8.36, 0.28)),
    "Alba": ("中部", 325941, 153263, (21.88, 14.14, 15.77, 15.97, 18.39, 5.36, 2.82)),
    "Brașov": ("中部", 546615, 265847, (20.71, 26.41, 14.77, 11.76, 7.33, 8.55, 3.72)),
    "Covasna": ("中部", 200042, 76171, (7.26, 6.21, 6.4, 5.5, 2.32, 1.86, 68.39)),
    "Harghita": ("中部", 291950, 117880, (3.49, 3.56, 3.69, 2.7, 1.35, 1.25, 82.65)),
    "Mureș": ("中部", 518193, 212252, (14.7, 13.7, 12.89, 12.43, 6.95, 4.92, 30.6)),
    "Sibiu": ("中部", 388325, 181359, (26.34, 23.58, 11.94, 11.65, 10.73, 7.04, 1.27)),
    "Bacău": ("東北", 601387, 236638, (23.35, 16.53, 24.85, 15.79, 6.4, 6.66, 0.93)),
    "Botoșani": ("東北", 392821, 144656, (25.75, 10.24, 27.69, 16.17, 8.87, 6.41, 0.26)),
    "Iași": ("東北", 760774, 342821, (22.01, 24.63, 18.46, 12.79, 8.59, 7.78, 0.24)),
    "Neamț": ("東北", 454203, 185912, (24.24, 15.43, 23.55, 16.54, 8.28, 5.92, 0.46)),
    "Suceava": ("東北", 642551, 255539, (28.47, 11.27, 22.83, 17.48, 8.71, 5.48, 0.33)),
    "Vaslui": ("東北", 374700, 140295, (23.06, 13.29, 30.3, 16.72, 6.31, 5.18, 0.33)),
    "Bihor": ("西北", 551297, 242647, (16.81, 12.47, 16.8, 11.66, 15.14, 4.15, 18.12)),
    "Bistrița-Năsăud": ("西北", 295988, 111686, (25.44, 13.12, 22.81, 13.76, 10.21, 6.07, 3.48)),
    "Cluj": ("西北", 679141, 348053, (15.36, 30.38, 10.55, 10.82, 9.55, 8.05, 9.0)),
    "Maramureș": ("西北", 452475, 164198, (22.63, 16.94, 18.97, 15.94, 9.52, 5.81, 4.53)),
    "Satu Mare": ("西北", 330668, 117515, (13.28, 10.9, 14.93, 10.85, 8.96, 3.86, 33.73)),
    "Sălaj": ("西北", 212224, 92907, (16.48, 12.53, 15.68, 11.64, 13.8, 4.72, 19.99)),
    "Brăila": ("東南", 281452, 122902, (26.33, 11.67, 27.57, 15.06, 8.45, 5.49, 0.35)),
    "Buzău": ("東南", 404979, 180081, (22.31, 10.45, 40.49, 12.9, 5.48, 4.41, 0.17)),
    "Constanța": ("東南", 655997, 297068, (26.5, 19.44, 16.74, 14.55, 8.39, 7.66, 0.27)),
    "Galați": ("東南", 496892, 215626, (22.11, 15.09, 26.87, 16.07, 7.32, 6.54, 0.29)),
    "Tulcea": ("東南", 193355, 78784, (26.89, 13.63, 20.99, 19.73, 7.26, 5.74, 0.27)),
    "Vrancea": ("東南", 335312, 134744, (20.34, 11.94, 25.87, 19.67, 11.88, 5.27, 0.15)),
    "Argeș": ("南蒙特尼亞", 569932, 267689, (24.84, 18.03, 24.74, 14.54, 7.58, 5.59, 0.15)),
    "Călărași": ("南蒙特尼亞", 283458, 107756, (26.16, 11.09, 25.96, 16.58, 11.26, 4.57, 0.34)),
    "Dâmbovița": ("南蒙特尼亞", 479404, 205463, (26.03, 13.6, 27.59, 15.12, 7.67, 5.31, 0.17)),
    "Giurgiu": ("南蒙特尼亞", 262066, 115198, (22.97, 9.27, 20.42, 13.41, 26.54, 4.08, 0.15)),
    "Ialomița": ("南蒙特尼亞", 250816, 93019, (27.06, 12.58, 27.59, 17.55, 5.45, 5.16, 0.35)),
    "Prahova": ("南蒙特尼亞", 695117, 316051, (26.03, 18.19, 19.52, 14.51, 8.36, 6.95, 0.24)),
    "Teleorman": ("南蒙特尼亞", 323544, 138919, (18.6, 8.13, 38.46, 14.57, 12.86, 3.89, 0.11)),
    "Dolj": ("西南奧爾特尼亞", 599442, 268549, (17.92, 13.2, 30.42, 15.93, 12.02, 6.81, 0.14)),
    "Gorj": ("西南奧爾特尼亞", 314684, 140704, (23.44, 10.63, 26.18, 22.18, 8.67, 4.83, 0.4)),
    "Mehedinți": ("西南奧爾特尼亞", 234339, 113117, (15.43, 7.11, 35.79, 16.38, 18.62, 3.54, 0.23)),
    "Olt": ("西南奧爾特尼亞", 383280, 136907, (21.79, 8.57, 38.88, 14.85, 8.48, 4.27, 0.11)),
    "Vâlcea": ("西南奧爾特尼亞", 341861, 151511, (22.76, 12.34, 26.01, 18.49, 9.78, 5.78, 0.26)),
    "Arad": ("西部", 410143, 171490, (23.29, 14.58, 14.88, 17.24, 13.23, 5.18, 4.97)),
    "Caraș-Severin": ("西部", 246588, 100905, (22.1, 12.55, 26.87, 17.13, 10.27, 4.82, 0.83)),
    "Hunedoara": ("西部", 361657, 166146, (22.34, 14.61, 22.09, 18.64, 8.2, 5.97, 2.0)),
    "Timiș": ("西部", 650533, 308919, (21.37, 28.4, 13.87, 13.9, 6.8, 7.44, 1.81)),
}
DIASPORA = (797982, (43.35, 26.82, 2.87, 12.07, 4.63, 4.88, 0.59))
# 政黨 → 地區形狀用的總統候選人欄位
SHAPE = {"PSD": 2, "AUR": 3, "PNL": 4, "USR": 1, "SOS": 0, "POT": 0, "UDMR": 6}

# 複數選區：8 個發展區，東北、南蒙特尼亞各拆成兩區，讓 M 落在 [8,16]
LIST_DIST = {
    "布加勒斯特—伊爾福夫": ["Bucharest", "Ilfov"],
    "中部": ["Alba", "Brașov", "Covasna", "Harghita", "Mureș", "Sibiu"],
    "東北一": ["Suceava", "Botoșani", "Iași"],
    "東北二": ["Neamț", "Bacău", "Vaslui"],
    "西北": ["Bihor", "Bistrița-Năsăud", "Cluj", "Maramureș", "Satu Mare", "Sălaj"],
    "東南": ["Brăila", "Buzău", "Constanța", "Galați", "Tulcea", "Vrancea"],
    "南蒙特尼亞西": ["Argeș", "Dâmbovița", "Teleorman"],
    "南蒙特尼亞東": ["Prahova", "Ialomița", "Călărași", "Giurgiu"],
    "西南奧爾特尼亞": ["Dolj", "Gorj", "Mehedinți", "Olt", "Vâlcea"],
    "西部": ["Arad", "Caraș-Severin", "Hunedoara", "Timiș"],
}
SMD_TOTAL, LIST_TOTAL = 180, 120


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


SMD_N = largest_remainder({c: v[1] for c, v in COUNTY.items()}, SMD_TOTAL)
# 海外 M：上一次全國選舉的海外有效票占比 × 120，限 [4,12]
_votes_all = sum(v[2] for v in COUNTY.values()) + DIASPORA[0]
DIASPORA_M = max(4, min(12, round(DIASPORA[0] / _votes_all * LIST_TOTAL)))
LIST_M = largest_remainder({d: sum(COUNTY[c][1] for c in cs) for d, cs in LIST_DIST.items()},
                           LIST_TOTAL - DIASPORA_M)
LIST_M["海外"] = DIASPORA_M


def county_shares(fp):
    """各縣（含海外）的政黨得票 %：總統初選形狀 × 迭代比例調整到全國 fp。"""
    units = {c: (v[2], v[3]) for c, v in COUNTY.items()}
    units["海外"] = DIASPORA
    parties = [p for p in fp if p != "其他"]
    sh = {}
    for u, (_, pres) in units.items():
        sh[u] = {p: max(0.05, pres[SHAPE[p]]) for p in parties}
        sh[u]["其他"] = 1.0
    for _ in range(60):
        for p in fp:
            nat = sum(units[u][0] * sh[u][p] for u in units) / _votes_all
            for u in sh:
                sh[u][p] *= fp[p] / nat
        for u in sh:
            t = sum(sh[u].values())
            sh[u] = {p: v * 100 / t for p, v in sh[u].items()}
    return sh


def rank_from(pos, cands, wx, wy, we, where=POS):
    d = lambda c: (wx * (where[c][0] - pos[0])) ** 2 + (wy * (where[c][1] - pos[1])) ** 2 + (we * (where[c][2] - pos[2])) ** 2
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


def smd_local(base, i, n, rng, sd):
    """縣內第 i 個（共 n 個）單一選區：城鄉梯度、匈牙利族集中梯度、隨機擾動。"""
    d = dict(base)
    if n >= 3:  # i=0 最城市
        u = 1 - 2 * i / (n - 1)
        for p, k in (("USR", 0.35), ("PNL", 0.05), ("PSD", -0.2), ("AUR", -0.1), ("SOS", -0.1), ("POT", -0.1)):
            if p in d:
                d[p] *= 1 + k * u
    if n >= 2 and 3 < d.get("UDMR", 0) < 60:  # 混居縣：匈牙利族集中在部分選區，順序和城鄉梯度錯開
        order = sorted(range(n), key=lambda j: (j * 7) % n)
        d["UDMR"] = min(85.0, d["UDMR"] * (2.0 - 1.9 * order.index(i) / (n - 1)))
    for p in d:
        if p != "其他" and p not in ETHNIC:
            d[p] = max(0.3, d[p] + rng.gauss(0, sd))
    t = sum(d.values())
    return {p: v * 100 / t for p, v in d.items()}


def single_seats(fp, types=TYPES, seed=7, sd=2.5):
    rng = random.Random(seed)
    sh = county_shares(fp)
    parties = [p for p in fp if p != "其他"]
    groups = voter_groups(parties, types)
    out = {p: 0 for p in parties}
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    by_county = {}
    for c, n in SMD_N.items():
        for i in range(n):
            d = smd_local(sh[c], i, n, rng, sd)
            finals = sorted(parties, key=lambda p: d[p], reverse=True)[:3]
            w, cyc, _ = pairwise_winner(finals, groups, lambda s: d.get(s, 0))
            out[w] += 1
            by_county.setdefault(c, []).append(w)
            stats["循環"] += cyc
            stats["第一偏好過半"] += d[w] > 50
            stats["非第一偏好第一名當選"] += w != finals[0]
    return out, stats, by_county


def list_seats(fp):
    sh = county_shares(fp)
    parties = [p for p in fp if p != "其他"]
    out = {p: 0 for p in parties}
    out["其他"] = 0
    dists = dict(LIST_DIST)
    dists["海外"] = ["海外"]
    w = {c: v[2] for c, v in COUNTY.items()}
    w["海外"] = DIASPORA[0]
    for dname, cs in dists.items():
        tot = sum(w[c] for c in cs)
        d = {p: sum(w[c] * sh[c][p] for c in cs) / tot for p in fp}
        o = d.pop("其他", 0)
        for i in range(5):  # 「其他」視為 5 個小黨
            d[f"其他{i}"] = o / 5
        for p, n in sainte_lague(d, LIST_M[dname]).items():
            out["其他" if p.startswith("其他") else p] += n
    return out


def head_of_gov(total):
    """全院 300 以議員所屬政黨的均衡型排序投票。回傳 (勝者, 循環, 勝者對每個對手的最少票)。"""
    parties = [p for p, n in total.items() if n and p != "其他"]
    groups = [(p, 1.0, rank_from(POS[p], parties, 0.8, 0.5, 1.5)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min((P[(w, b)] for b in parties if b != w), default=total[w])
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


SCENARIOS = {
    # 2024-12-01 眾議院實際得票（%）；其他＝未過門檻各黨＋少數族群組織＋獨立
    "2024-12 大選": {"PSD": 21.96, "AUR": 18.01, "PNL": 13.20, "USR": 12.40, "SOS": 7.36, "POT": 6.46,
                    "UDMR": 6.33, "其他": 14.28},
    # 2026-10 民調（PolitPro 加權平均，10-27）；其他含 SENS 2.4
    "2026-10 民調": {"PSD": 22.9, "AUR": 35.8, "PNL": 16.9, "USR": 8.2, "SOS": 2.9, "POT": 2.3, "UDMR": 5.1, "其他": 5.9},
}

# 總統 top-3：候選人位置（同一空間），以及各候選人第一偏好選民的位置
PRES = {
    "2024-11": {
        "cands": {"Georgescu": (1.0, -0.9, 0), "Lasconi": (-0.9, -0.4, 0), "Ciolacu": POS["PSD"]},
        "voters": [("Georgescu", 22.94, (1.0, -0.9, 0)), ("Lasconi", 19.18, POS["USR"]),
                   ("Ciolacu", 19.15, POS["PSD"]), ("Simion", 13.86, POS["AUR"]), ("Ciucă", 8.79, POS["PNL"]),
                   ("Geoană", 6.32, (-0.6, 0.2, 0)), ("Kelemen", 4.50, (-0.4, 0.7, 0)), ("其他", 5.26, (0.0, -0.2, 0))],
    },
    # 只算第一輪選民，不含第二輪新增的動員（實際決選投票率 64.7%，有效票比第一輪多約 200 萬）
    "2025-05": {
        "cands": {"Simion": (0.8, -0.5, 0), "Dan": (-0.7, -0.6, 0), "Antonescu": (-0.4, 0.7, 0)},
        "voters": [("Simion", 40.96, (0.8, -0.5, 0)), ("Dan", 20.99, (-0.7, -0.6, 0)),
                   ("Antonescu", 20.07, (-0.4, 0.7, 0)), ("Ponta", 13.04, (0.4, 0.5, 0)),
                   ("Lasconi", 2.68, POS["USR"]), ("其他", 2.26, (0.3, -0.2, 0))],
    },
}


def presidential(key, types=TYPES):
    c = PRES[key]["cands"]
    groups = []
    for name, share, pos in PRES[key]["voters"]:
        for w, wx, wy, we in types:
            groups.append((name, w, rank_from(pos, list(c), wx, wy, we, where=c)))
    shares = {n: s for n, s, _ in PRES[key]["voters"]}
    return pairwise_winner(list(c), groups, lambda s: shares[s])


def run(name, types=TYPES):
    fp = SCENARIOS[name]
    smd, stats, byc = single_seats(fp, types)
    lst = list_seats(fp)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, stats, byc


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def main():
    if "--validate" in sys.argv:
        sh = county_shares(SCENARIOS["2024-12 大選"])
        for c in ("Iași", "Ilfov", "Bucharest", "Harghita", "Cluj", "海外"):
            print(c, {p: round(v, 1) for p, v in sh[c].items()})
        win = {}
        for c in COUNTY:
            p = max((p for p in sh[c] if p != "其他"), key=lambda p: sh[c][p])
            win.setdefault(p, []).append(c)
        for p, cs in win.items():
            print(p, len(cs), cs)
        return
    if "--sweep" in sys.argv:
        print("| 選民類型 | 2024-12 單一 180 | 全院 300 | 首長 |")
        print("|---|---|---|---|")
        for label, types in (("基準（重地緣型占一半）", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4, 1.5)]),
                             ("全部重體制", [(1.0, 0.4, 1.0, 1.5)])):
            smd, lst, total, _, _ = run("2024-12 大選", types)
            w, _, worst = head_of_gov(total)
            print(f"| {label} | {fmt(smd)} | {fmt(total)} | {w}（最弱 {worst:.0f}） |")
        print()
        print("| 擾動 sd | 種子 | 單一 180 |")
        print("|---|---|---|")
        for sd in (0, 2.5, 5):
            for seed in (1, 7):
                print(f"| {sd} | {seed} | {fmt(single_seats(SCENARIOS['2024-12 大選'], TYPES, seed, sd)[0])} |")
        print()
        for party, grid in (("AUR", (18, 24, 30, 36)), ("PSD", (14, 18, 22, 26, 30))):
            print(f"| {party} 第一偏好（其餘按比例） | 單一 180 | 全院 300 | 首長 |")
            print("|:--:|---|---|---|")
            for x in grid:
                fp = dict(SCENARIOS["2024-12 大選"])
                rest = 100 - fp[party]
                SCENARIOS["_s"] = {k: (v * (100 - x) / rest if k != party else x) for k, v in fp.items()}
                smd, lst, total, _, _ = run("_s")
                w, _, worst = head_of_gov(total)
                print(f"| {x}% | {fmt(smd)} | {fmt(total)} | {w}（最弱 {worst:.0f}） |")
            print()
        print()
        for key in PRES:
            for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4, 1.5)]),
                                 ("全部重體制", [(1.0, 0.4, 1.0, 1.5)])):
                w, cyc, P = presidential(key, types)
                print(f"總統 {key} {label}：{w}（循環 {cyc}）",
                      "、".join(f"{a}>{b} {v:.1f}" for (a, b), v in P.items() if v > P[(b, a)]))
        return
    print("單一選區數：", SMD_N)
    print("複數選區 M：", LIST_M)
    for name in SCENARIOS:
        smd, lst, total, stats, byc = run(name)
        w, cyc, worst = head_of_gov(total)
        print(f"\n## {name}")
        print("單一 180：", fmt(smd), stats)
        print("匈牙利族縣：", {c: byc[c] for c in ("Harghita", "Covasna", "Mureș", "Satu Mare", "Bihor", "Sălaj")})
        print("布加勒斯特：", fmt({p: byc["Bucharest"].count(p) for p in set(byc["Bucharest"])}))
        print("複數 120：", fmt(lst))
        print("全院 300：", fmt(total))
        print(f"行政首長（全院排名投票）：{w}；循環 {cyc}；勝者在最弱一場對決得 {worst:.0f} 票")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者單獨：全院 {total[w]}（≥151 {total[w] >= 151}；≥180 {total[w] >= 180}）"
              f"；複數 {lst.get(w, 0)}（≥72 {lst.get(w, 0) >= 72}）")
        w2, _, worst2 = head_of_gov(dict(smd))
        print(f"參考：若只由單一席次 180 選：{w2}（最弱 {worst2:.0f}）")
    for key in PRES:
        w, cyc, P = presidential(key)
        print(f"\n## 總統 {key} top-3：{w}（循環 {cyc}）")
        print("    ", "、".join(f"{a}>{b} {v:.1f}" for (a, b), v in P.items() if v > P[(b, a)]))


if __name__ == "__main__":
    main()
