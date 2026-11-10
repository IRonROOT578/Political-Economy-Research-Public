"""新加坡一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
所有輸入都是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py            # 2025-05、2020-07 國會重算；2023 總統（2020 國會得票 × 參選方層）
    python 生態模型.py --sweep    # 敏感度

得票：各選區的實際得票（Wikipedia 的 Results 頁，引選舉局公報）。現行只有一個反對黨出戰的選區，
模型就只有那兩個黨；**沒出戰的黨在該選區的第一偏好當作 0**（見 12 §2.3）。
Marine Parade–Braddell Heights 2025 年不戰而勝，沒有得票，假設 PAP 60%、WP 40%、投票數 122,340。
偏好：二維空間（體制：建制 −1 … 改革、問責 +1；經濟：成長、市場 −1 … 再分配 +1）。
每黨選民分三型（重體制、重經濟、均衡）。
單一 60：依投票數分到現行選區（最大餘數）；集選區拆成數個單一選區，各加隨機擾動；top-3 孔多賽，循環用 Ranked Pairs。
複數 40：以社區發展理事會（CDC）為底，調成人口相近的 5 區，各 8 席；聖拉古，無法定門檻。
行政首長：全院 100 記名排名投票，孔多賽完成法；須 ≥51。
"""
import random
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 總統民意 import president as _president, fmt as _pfmt  # noqa: E402
from 參選判定 import finalists as _finalists  # noqa: E402

POS = {
    "PAP": (-0.7, -0.3),
    "WP": (0.2, 0.2),
    "PSP": (0.5, 0.4),
    "RDU": (0.5, 0.3),
    "SDP": (0.6, 0.7),
    "PAR": (0.8, 0.5),
    "SDA": (0.5, 0.3),
    "SPP": (0.4, 0.2),
    "SUP": (0.4, 0.3),
    "PPP": (0.7, 0.3),
    "NSP": (0.5, 0.3),
    "IND": (0.3, 0.2),
    "PV": (0.8, 0.4),
    "RP": (0.8, 0.5),
}
# 選民三型：(比例, 體制權重, 經濟權重)
TYPES = [(0.5, 1.0, 0.4), (0.2, 0.4, 1.0), (0.3, 0.8, 0.5)]

# 選區：(CDC, 現行席次, 投票數, {黨: 票})
GE2025 = {
    "Aljunied": ("東南", 5, 133451, {'WP': 78847, 'PAP': 53263}),
    "Ang Mo Kio": ("中區", 5, 150312, {'PAP': 115562, 'SUP': 15874, 'PPP': 14929}),
    "Bishan-Toa Payoh": ("中區", 4, 90020, {'PAP': 66455, 'SPP': 21944}),
    "Bukit Gombak": ("西南", 1, 23806, {'PAP': 17946, 'PSP': 5726}),
    "Bukit Panjang": ("西北", 1, 31481, {'PAP': 19152, 'SDP': 12051}),
    "Chua Chu Kang": ("西南", 4, 87677, {'PAP': 55140, 'PSP': 31562}),
    "East Coast": ("東南", 5, 137141, {'PAP': 80105, 'WP': 56288}),
    "Holland-Bukit Timah": ("西北", 4, 111632, {'PAP': 86936, 'RDU': 22762}),
    "Hougang": ("東南", 1, 27481, {'WP': 16900, 'PAP': 10285}),
    "Jalan Besar": ("中區", 4, 96862, {'PAP': 70602, 'PAR': 23267}),
    "Jalan Kayu": ("中區", 1, 27796, {'PAP': 14146, 'WP': 13337}),
    "Jurong Central": ("西南", 1, 27713, {'PAP': 21947, 'RDU': 5313}),
    "Jurong East-Bukit Batok": ("西南", 5, 132786, {'PAP': 99692, 'RDU': 30342}),
    "Kebun Baru": ("中區", 1, 20356, {'PAP': 13787, 'PSP': 6342}),
    "Marine Parade-Braddell Heights": ("東南", 5, 122340, {'PAP': 73404, 'WP': 48936}),  # 不戰而勝，假設
    "Marsiling-Yew Tee": ("西北", 4, 119559, {'PAP': 81143, 'SDP': 29281}),
    "Marymount": ("中區", 1, 21282, {'PAP': 14954, 'PSP': 6187}),
    "Mountbatten": ("東南", 1, 20063, {'PAP': 12602, 'IND': 7143}),
    "Nee Soon": ("西北", 5, 142286, {'PAP': 102974, 'RDU': 36538}),
    "Pasir Ris-Changi": ("東北", 4, 92479, {'PAP': 61168, 'SDA': 29213}),
    "Pioneer": ("西南", 1, 23656, {'PAP': 15360, 'PSP': 8110}),
    "Potong Pasir": ("中區", 1, 28275, {'PAP': 19288, 'SPP': 6261, 'PAR': 2323}),
    "Punggol": ("東北", 4, 116074, {'PAP': 63745, 'WP': 51789}),
    "Queenstown": ("中區", 1, 26468, {'PAP': 20990, 'PAR': 4883}),
    "Radin Mas": ("中區", 1, 23289, {'PAP': 15854, 'IND': 5394, 'PAR': 1689}),
    "Sembawang": ("西北", 5, 125746, {'PAP': 84159, 'SDP': 37157, 'NSP': 2878}),
    "Sembawang West": ("西北", 1, 22788, {'PAP': 11999, 'SDP': 10564}),
    "Sengkang": ("東北", 4, 118815, {'WP': 66383, 'PAP': 51505}),
    "Tampines": ("東北", 5, 138570, {'PAP': 71589, 'WP': 65197, 'PPP': 596, 'NSP': 249}),
    "Tampines Changkat": ("東北", 1, 22372, {'PAP': 12476, 'WP': 9741}),
    "Tanjong Pagar": ("中區", 5, 124774, {'PAP': 98924, 'PAR': 23169}),
    "West Coast-Jurong West": ("西南", 5, 148647, {'PAP': 88587, 'PSP': 59078}),
    "Yio Chu Kang": ("中區", 1, 23400, {'PAP': 18066, 'PAR': 4876}),
}
GE2020 = {
    "Bukit Batok": ("西南", 1, 29948, {'PAP': 15500, 'SDP': 12787}),
    "Bukit Panjang": ("西北", 1, 35437, {'PAP': 18085, 'SDP': 15576}),
    "Hong Kah North": ("西南", 1, 28046, {'PAP': 16347, 'PSP': 10457}),
    "Hougang": ("東北", 1, 26432, {'WP': 15451, 'PAP': 9791}),
    "Kebun Baru": ("中區", 1, 22623, {'PAP': 13309, 'PSP': 7842}),
    "MacPherson": ("東南", 1, 28513, {'PAP': 19009, 'PPP': 7489}),
    "Marymount": ("中區", 1, 23431, {'PAP': 12173, 'PSP': 9943}),
    "Mountbatten": ("東南", 1, 24246, {'PAP': 16285, 'PV': 5775}),
    "Pioneer": ("西南", 1, 24653, {'PAP': 14593, 'PSP': 8289, 'IND': 655}),
    "Potong Pasir": ("中區", 1, 19731, {'PAP': 11264, 'SPP': 7302}),
    "Punggol West": ("東北", 1, 26587, {'PAP': 15655, 'WP': 10017}),
    "Radin Mas": ("中區", 1, 24931, {'PAP': 16864, 'RP': 5922}),
    "Yio Chu Kang": ("中區", 1, 25962, {'PAP': 14775, 'PSP': 9519}),
    "Yuhua": ("西南", 1, 21351, {'PAP': 14131, 'SDP': 5901}),
    "Bishan-Toa Payoh": ("中區", 4, 101220, {'PAP': 62983, 'SPP': 30696}),
    "Chua Chu Kang": ("西南", 4, 106632, {'PAP': 59554, 'PSP': 42012}),
    "Holland-Bukit Timah": ("西北", 4, 114973, {'PAP': 71218, 'SDP': 36100}),
    "Jalan Besar": ("中區", 4, 107720, {'PAP': 64631, 'PV': 34261}),
    "Marsiling-Yew Tee": ("西北", 4, 117077, {'PAP': 69813, 'SDP': 40690}),
    "Sengkang": ("東北", 4, 120100, {'WP': 60217, 'PAP': 55319}),
    "Aljunied": ("東北", 5, 150821, {'WP': 85815, 'PAP': 57330}),
    "Ang Mo Kio": ("中區", 5, 185261, {'PAP': 124597, 'RP': 48677}),
    "East Coast": ("東南", 5, 121644, {'PAP': 61144, 'WP': 53375}),
    "Jurong": ("西南", 5, 131058, {'PAP': 91846, 'RDU': 31260}),
    "Marine Parade": ("東南", 5, 139622, {'PAP': 75203, 'WP': 55047}),
    "Nee Soon": ("西北", 5, 146902, {'PAP': 86308, 'PSP': 53131}),
    "Pasir Ris-Punggol": ("東北", 5, 166556, {'PAP': 100932, 'SDA': 37237, 'PV': 19147}),
    "Sembawang": ("西北", 5, 147786, {'PAP': 94176, 'NSP': 45778}),
    "Tampines": ("東北", 5, 151589, {'PAP': 94668, 'NSP': 47875}),
    "Tanjong Pagar": ("中區", 5, 134494, {'PAP': 78330, 'PSP': 45807}),
    "West Coast": ("西南", 5, 146089, {'PAP': 71658, 'PSP': 66996}),
}
DATA = {2025: GE2025, 2020: GE2020}
# 複數區：以 CDC 為底，把幾個選區移到鄰區，讓 5 區人口相近（01 §3.2）
LIST_MOVE = {
    2025: {"Ang Mo Kio": "東北", "Pasir Ris-Changi": "東南", "Bukit Panjang": "西南"},
    2020: {"Aljunied": "東南", "Hougang": "東南", "Yio Chu Kang": "東北", "Kebun Baru": "東北",
           "Potong Pasir": "東南", "Radin Mas": "西南"},
}
# 現行制度下的實際席次
ACTUAL = {2025: {"PAP": 87, "WP": 10}, 2020: {"PAP": 83, "WP": 10}}
SMD, LIST, LIST_M = 60, 40, 8


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


ALPHA = 0.25   # 反對黨陣營內校正的強度（假設；--sweep 0–0.75）


def opp_composition(year):
    """各複數區（地區）內、實際有出戰的反對黨的得票組成。只用該區出戰過的黨＝地方性政黨只在地盤內補值。"""
    comp = {}
    for c, (_, _, _, v) in DATA[year].items():
        k = district(year, c)
        for p, x in v.items():
            if p != "PAP":
                comp.setdefault(k, {})
                comp[k][p] = comp[k].get(p, 0) + x
    return {k: {p: x / sum(d.values()) for p, x in d.items()} for k, d in comp.items()}


def shares(year, swing=0.0, alpha=None):
    """{選區: {黨: %}}。swing：PAP 加減幾個百分點，反對黨按比例吸收。
    民意層（notes/算法/選舉結果計算方式.md 優先 4）：反對黨之間的協調（每區通常只有一個反對黨出戰）是相對多數制下避免分票的產物；
    新制下各反對黨在自己有組織的地區都有動機參選。每區反對黨總票不動，反對黨之間的比例往該地區反對黨組成拉近 alpha；PAP 不動。"""
    alpha = ALPHA if alpha is None else alpha
    comp = opp_composition(year)
    out = {}
    for c, (_, _, _, v) in DATA[year].items():
        t = sum(v.values())
        d = {p: x * 100 / t for p, x in v.items()}
        o = sum(x for p, x in d.items() if p != "PAP")
        if alpha and o:
            cm = comp[district(year, c)]
            own = {p: x / o for p, x in d.items() if p != "PAP"}
            d = {"PAP": d.get("PAP", 0), **{p: o * ((1 - alpha) * own.get(p, 0) + alpha * cm.get(p, 0)) for p in sorted(set(own) | set(cm))}}
            d = {p: x for p, x in d.items() if x > 0}
        if swing:
            pap = min(99.0, max(1.0, d["PAP"] + swing))
            rest = 100 - d["PAP"]
            d = {p: (pap if p == "PAP" else x * (100 - pap) / rest) for p, x in d.items()}
        out[c] = d
    return out


def district(year, c):
    return LIST_MOVE[year].get(c, DATA[year][c][0])


def weights(year):
    return {c: v[2] for c, v in DATA[year].items()}


def rank_from(pos, cands, wx, wy, where=POS):
    d = lambda c: (wx * (where[c][0] - pos[0])) ** 2 + (wy * (where[c][1] - pos[1])) ** 2
    return sorted(cands, key=d)


def voter_groups(parties, types=TYPES):
    return [(p, w, rank_from(POS[p], parties, wx, wy)) for p in parties for w, wx, wy in types]


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


def smd_seats(year, types=TYPES, seed=7, sd=2.5, swing=0.0):
    rng = random.Random(seed)
    sh = shares(year, swing)
    n_of = largest_remainder(weights(year), SMD)
    out, by = {}, {}
    stats = {"循環": 0, "非第一偏好第一名當選": 0, "共同提名": 0}
    for c, n in n_of.items():
        for _ in range(n):
            d = {p: max(0.3, v + rng.gauss(0, sd)) for p, v in sh[c].items()}
            groups = voter_groups(list(d), types)
            win = lambda f: pairwise_winner(f, groups, lambda s: d[s])[0]
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py）
            finals, mlog = _finalists(d, 3, win, lambda a, b: sum((x - y) ** 2 for x, y in zip(POS[a], POS[b])) ** 0.5,
                                      universe=list(POS), return_log=True)
            stats["共同提名"] += bool(mlog)
            w, cyc, _ = pairwise_winner(finals, groups, lambda s: d[s])
            out[w] = out.get(w, 0) + 1
            by.setdefault(c, []).append(w)
            stats["循環"] += cyc
            stats["非第一偏好第一名當選"] += w != finals[0]
    return out, stats, by, n_of


def list_votes(year, swing=0.0, mode="local"):
    """{區: {黨: 票}}。mode="local"：只有實際出戰的黨有票；"national"：各區反對票按全國反對黨組成分配。"""
    sh, w = shares(year, swing), weights(year)
    out = {}
    for c, d in sh.items():
        dist = out.setdefault(district(year, c), {})
        for p, v in d.items():
            dist[p] = dist.get(p, 0) + w[c] * v / 100
    if mode == "national":
        opp = {}
        for dist in out.values():
            for p, v in dist.items():
                if p != "PAP":
                    opp[p] = opp.get(p, 0) + v
        t = sum(opp.values())
        for k, dist in out.items():
            o = sum(v for p, v in dist.items() if p != "PAP")
            out[k] = {"PAP": dist["PAP"], **{p: o * v / t for p, v in opp.items()}}
    return out


def list_seats(year, swing=0.0, mode="local"):
    out = {}
    for dist in list_votes(year, swing, mode).values():
        d = dict(dist)
        ind = d.pop("IND", 0)
        for i in range(5):  # 無黨籍視為 5 張小名單
            d[f"IND{i}"] = ind / 5
        for p, n in sainte_lague(d, LIST_M).items():
            if n:
                k = "其他" if p.startswith("IND") else p
                out[k] = out.get(k, 0) + n
    return out


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p in POS]
    groups = [(p, 1.0, rank_from(POS[p], parties, 0.8, 0.5)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min((P[(w, b)] for b in parties if b != w), default=total[w])
    return w, cyc, worst


def national(year):
    tot = {}
    for v in DATA[year].values():
        for p, x in v[3].items():
            tot[p] = tot.get(p, 0) + x
    t = sum(tot.values())
    return {p: round(x * 100 / t, 2) for p, x in sorted(tot.items(), key=lambda x: -x[1])}


def chamber(year, types=TYPES, seed=7, sd=2.5, swing=0.0, mode="local"):
    smd, st, by, n_of = smd_seats(year, types, seed, sd, swing)
    lst = list_seats(year, swing, mode)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, st, by


def presidential_list(fp, types=TYPES):
    """總統主版（notes/算法/選舉結果計算方式.md）：民意層＝國會名單票（2023 總統選舉前最近一次：2020-07 國會選舉；新加坡沒有名單票，用各黨國會得票（選區票）），政黨層級，不用現實總統第一輪、
    不用個別候選人；參選方層＝每黨可推人，參選判定.finalists 決定相鄰政黨的共同提名；前 3 名孔多賽。"""
    fp = {p: v for p, v in fp.items() if p in POS and v > 0}
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(POS[a], POS[b])) ** 0.5
    return _president(fp, lambda parties, cands: voter_groups(parties, types), dist, POS)

def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def gates(total, lst):
    pap, papl = total.get("PAP", 0), lst.get("PAP", 0)
    return (f"PAP 全院 {pap}（≥51 {pap >= 51}；3/5 ≥60 {pap >= 60}；2/3 ≥67 {pap >= 67}）"
            f"；複數 {papl}（3/5 ≥24 {papl >= 24}）")


def main():
    if "--sweep" in sys.argv:
        print("| 選民類型 | 2025 單一 60 | 2020 單一 60 |")
        print("|---|---|---|")
        for label, types in (("基準", TYPES), ("全部重體制", [(1.0, 1.0, 0.4)]), ("全部重經濟", [(1.0, 0.4, 1.0)])):
            print(f"| {label} | {fmt(chamber(2025, types)[0])} | {fmt(chamber(2020, types)[0])} |")
        print()
        print("| 擾動 sd | 種子 | 2025 單一 60 | 2020 單一 60 |")
        print("|---|---|---|---|")
        for sd in (0, 2.5, 5):
            for seed in (1, 7, 11):
                print(f"| {sd} | {seed} | {fmt(chamber(2025, seed=seed, sd=sd)[0])} | {fmt(chamber(2020, seed=seed, sd=sd)[0])} |")
        print()
        print("| 複數票的假設 | 2025 複數 40 | 2020 複數 40 |")
        print("|---|---|---|")
        for mode, label in (("local", "只有實際出戰的黨有票（基準）"), ("national", "各區反對票按全國組成分配")):
            print(f"| {label} | {fmt(list_seats(2025, mode=mode))} | {fmt(list_seats(2020, mode=mode))} |")
        print()
        print("| PAP 全國（2025 形狀，均勻擺動） | 單一 60 | 複數 40 | 全院 100 | 首長 | 門檻 |")
        print("|:--:|---|---|---|---|---|")
        base = national(2025)["PAP"]
        for x in (45, 50, 55, 60, 65.6, 70):
            smd, lst, total, _, _ = chamber(2025, swing=x - base)
            w, _, _ = head_of_gov(total)
            print(f"| {x}% | {fmt(smd)} | {fmt(lst)} | {fmt(total)} | {w} | {gates(total, lst)} |")
        print()
        for label, types in (("基準", TYPES), ("全部重體制", [(1.0, 1.0, 0.4)]), ("全部重經濟", [(1.0, 0.4, 1.0)])):
            print(f"總統 2023（2020 國會得票）{label}：{_pfmt(presidential_list(national(2020), types), national(2020))}")
    for year in (2025, 2020):
        smd, lst, total, st, by = chamber(year)
        n_of = smd_seats(year)[3]
        w, cyc, worst = head_of_gov(total)
        print(f"\n## 國會 {year}")
        print("全國（實際，有競選的選區）：", national(year))
        dsz = {}
        for c, v in DATA[year].items():
            dsz[district(year, c)] = dsz.get(district(year, c), 0) + v[2]
        m = sum(dsz.values()) / 5
        print("複數區投票數：", {k: f"{v} ({(v / m - 1) * 100:+.0f}%)" for k, v in dsz.items()})
        print("單一選區數（依現行選區）：", {c: n for c, n in n_of.items() if n})
        print("單一 60：", fmt(smd), st)
        print("    非 PAP 當選：", {c: [x for x in v if x != "PAP"] for c, v in by.items() if any(x != "PAP" for x in v)})
        print("複數 40：", fmt(lst))
        for k, v in list_votes(year).items():
            t = sum(v.values())
            print(f"    {k}：", {p: round(x * 100 / t, 1) for p, x in sorted(v.items(), key=lambda x: -x[1])})
        print("全院 100：", fmt(total), "；現行實際：", ACTUAL[year])
        print(f"行政首長：{w}；循環 {cyc}；最弱一場對決 {worst:.0f} 票")
        print("    ", gates(total, lst))
    fp = national(2020)
    print(f"\n## 總統 2023（2020-07 國會得票 × 參選方層）：{_pfmt(presidential_list(fp), fp)}")


if __name__ == "__main__":
    main()
