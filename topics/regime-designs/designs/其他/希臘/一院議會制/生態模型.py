"""希臘一院議會制：得票 → 選制 → 席次 → 行政首長。

偏好位置與選民類型是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2023-06、2023-05 國會重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：**59 個選區**的名單得票率（維基 June／May 2023 Greek parliamentary election 的 By constituency 表），
以各選區 2021 普查法定居民加權（資料/gr-2023-06.csv、gr-2023-05.csv；_parse_wiki.py）。
內政部 ekloges.ypes.gr 擋自動存取（403），**拿不到逐投票所資料**：這是本夾最粗的地方，見 14 §1。
區：12 個國內區（REGIONS）。區內依選區順序（大致相鄰）按居民切成等大的新區，跨界的選區按比例拆分。
全院 220＝單一 132（top-3 孔多賽）＋複數 88（12 區、聖拉古、無門檻）。2023 年沒有海外投票，海外區不計。
偏好：二維（經濟、文化：左 −1 … 右 +1；體制：建制 −1 … 反體制 +1）。每黨選民分三型。
行政首長：全院 220 記名排名投票，孔多賽完成法；須 ≥111。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 6, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402

POS = {
    "ND": (0.5, -0.6),
    "SYRIZA": (-0.55, 0.0),
    "PASOK": (-0.25, -0.5),
    "KKE": (-1.0, 0.8),
    "Spartans": (1.0, 0.9),
    "EL": (0.9, 0.5),         # 希臘解決
    "Victory": (0.8, 0.4),    # 勝利（宗教保守）
    "PE": (-0.5, 1.0),        # 自由之航
    "MERA25": (-0.8, 0.7),
    # 2023 年後的新黨（民調用；地理沿用母黨，見 民調重算.py）
    "ELAS": (-0.55, 0.1),     # 希臘左翼聯盟（Tsipras）
    "DPK": (-0.35, 0.2),      # 民主運動（Kasselakis）
    "NA": (-0.8, 0.3),        # 新左翼
    "FL": (0.95, 0.7),        # 理性之聲
    "SE": (0.8, 0.3),         # 希臘人聯盟
    "ELPIDA": (0.0, 0.8),     # 民主希望
}
TYPES = [(0.5, 1.0, 0.5), (0.2, 0.5, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.3, 0.5)), (0.5, (-0.3, 0.5))]
BALANCED = (0.8, 0.8)

REGIONS = {
    "雅典中北": ["Athens A", "Athens B1"],
    "雅典西南": ["Athens B2", "Athens B3"],
    "比雷埃夫斯－西阿提卡": ["Piraeus A", "Piraeus B", "West Attica"],
    "東阿提卡－群島": ["East Attica", "Cyclades", "Dodecanese", "Samos", "Chios", "Lesbos"],
    "塞薩洛尼基": ["Thessaloniki A", "Thessaloniki B", "Chalkidiki"],
    "北希臘": ["Kilkis", "Serres", "Drama", "Kavala", "Xanthi", "Rhodope", "Evros"],
    "馬其頓西中": ["Pella", "Imathia", "Pieria", "Florina", "Kastoria", "Kozani", "Grevena"],
    "色薩利": ["Larissa", "Magnesia", "Trikala", "Karditsa"],
    "伊庇魯斯－西希臘－愛奧尼亞": ["Ioannina", "Thesprotia", "Preveza", "Arta", "Corfu", "Lefkada",
                          "Aetolia-Acarnania", "Cephalonia", "Zakynthos", "Achaea", "Elis"],
    "中希臘": ["Phthiotis", "Evrytania", "Phocis", "Boeotia", "Euboea"],
    "伯羅奔尼撒": ["Corinthia", "Argolis", "Arcadia", "Laconia", "Messenia"],
    "克里特": ["Chania", "Rethymno", "Heraklion", "Lasithi"],
}
SMD_TOTAL, LIST_TOTAL, NEED = 132, 88, 111


# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {"ND": "右", "EL": "右", "Victory": "右", "Spartans": "右", "FL": "右", "SE": "右",
        "SYRIZA": "左", "PASOK": "左", "KKE": "左", "MERA25": "左", "PE": "左", "ELAS": "左", "DPK": "左", "NA": "左"}
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


def load(label):
    """[(區, 選區, 居民, {黨: 加權票})]；票＝居民 × 得票率（投票率未知，以居民加權是近似）。"""
    with open(os.path.join(HERE, "資料", f"gr-{label}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][3:]
    reg_of = {c: r for r, cs in REGIONS.items() for c in cs}
    out = []
    for r in rows[1:]:
        res = int(r[1])
        pct = {c: float(v) for c, v in zip(cols, r[3:])}
        pct["其他"] = max(0.0, 100 - sum(pct.values()))
        out.append((reg_of[r[0]], r[0], res, {c: res * v / 100 for c, v in pct.items()}))
    order = {c: i for cs in REGIONS.values() for i, c in enumerate(cs)}
    return sorted(out, key=lambda u: (list(REGIONS).index(u[0]), order[u[1]]))


def layout():
    res = {}
    for u in load("2023-06"):
        res[u[0]] = res.get(u[0], 0) + u[2]
    return largest_remainder(res, SMD_TOTAL), largest_remainder(res, LIST_TOTAL)


SMD_N, LIST_M = layout()


def rank_from(pos, cands, wx, wy, home=None):
    return prefs().rank(pos, home, cands, (wx, wy))


def voter_groups(parties, types=TYPES):
    return prefs().groups(parties, parties, types, OTHER_POS, (0.8, 0.8))


def pairwise_winner(cands, groups, weight):
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


def merge(units, shift=False):
    """區內按居民切成 SMD_N[區] 個等大的新區；跨界的選區按比例拆。回傳 [(區, {黨: 票})]。"""
    out = []
    for reg in REGIONS:
        rows = [u for u in units if u[0] == reg]
        n = SMD_N[reg]
        size = sum(u[2] for u in rows) / n
        if shift and n > 1:
            k, acc = 0, 0
            while acc < size / 2:
                acc += rows[k][2]
                k += 1
            rows = rows[k:] + rows[:k]
        cur, room, made = {}, size, 0
        for u in rows:
            left = u[2]
            while left > 1e-6:
                take = min(left, room)
                for p, v in u[3].items():
                    cur[p] = cur.get(p, 0) + v * take / u[2]
                left -= take
                room -= take
                if room <= 1e-6 and made < n - 1:
                    out.append((reg, cur))
                    cur, room, made = {}, size, made + 1
        out.append((reg, cur))
    assert len(out) == SMD_TOTAL, len(out)
    return out


def single_seats(units, types=TYPES, shift=False):
    out, by = {}, {}
    st = {"循環": 0, "非第一偏好第一名當選": 0, "第一偏好過半": 0}
    shares = []
    for reg, d in merge(units, shift):
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
        shares.append(d[w] / tot)
    shares.sort()
    st["當選者第一偏好中位數"] = round(shares[len(shares) // 2] * 100, 1)
    return out, st, by


def list_seats(units):
    agg = {}
    for u in units:
        d = agg.setdefault(u[0], {})
        for p, v in u[3].items():
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


def national(units):
    t = {}
    for u in units:
        for p, v in u[3].items():
            t[p] = t.get(p, 0) + v
    s = sum(t.values())
    return {p: v / s for p, v in t.items()}


def scale(units, target):
    base = national(units)
    return [(u[0], u[1], u[2], {p: v * target.get(p, 0) / base[p] if base.get(p) else 0 for p, v in u[3].items()})
            for u in units]


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def chamber(units, types=TYPES, shift=False):
    smd, st, by = single_seats(units, types, shift)
    lst = list_seats(units)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, st, by


ACTUAL = {
    "2023-06": "ND 158、SYRIZA 47、PASOK 32、KKE 21、Spartans 12、EL 12、Victory 10、PE 8（300，含 ND 紅利 50）",
    "2023-05": "ND 146、SYRIZA 71、PASOK 41、KKE 26、EL 16（300，純比例；無人組閣，重選）",
}


def projection():
    """第 3 屆（推測）：2023-06 地理；兩翼（KKE、Spartans、EL、Victory、PE、MERA25）各讓出 1/8 第一偏好，
    一半給 ND、一半給 PASOK（中間）。"""
    us = load("2023-06")
    nat = national(us)
    t = dict(nat)
    moved = 0
    for p in ("KKE", "Spartans", "EL", "Victory", "PE", "MERA25"):
        t[p] = nat[p] * 7 / 8
        moved += nat[p] / 8
    t["ND"] += moved / 2
    t["PASOK"] += moved / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print("單一 132：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print("複數 88：", fmt(lst))
    print("全院 220：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(seq)}＝{acc}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("單一 132：", SMD_N)
    print("複數 88：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重左右", [(1.0, 1.0, 0.5)]), ("全部重體制", [(1.0, 0.5, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.8)])):
            s6, _, t6, _, _ = chamber(load("2023-06"), types)
            s5, _, t5, _, _ = chamber(load("2023-05"), types)
            print(f"| {label} | {fmt(s6)} | 首長 {head_of_gov(t6)[0]} | {fmt(s5)} | 首長 {head_of_gov(t5)[0]} |")
        for shift in (False, True):
            print(f"| 切線{'位移半區' if shift else '基準'} | {fmt(chamber(load('2023-06'), shift=shift)[0])} | | {fmt(chamber(load('2023-05'), shift=shift)[0])} |")
        nat = national(load("2023-06"))
        for d in (-8, -4, 4):
            t = dict(nat)
            t["ND"] = nat["ND"] + d / 100
            t["SYRIZA"] = nat["SYRIZA"] - d / 100
            smd, _, total, _, _ = chamber(scale(load("2023-06"), t))
            print(f"| ND {d:+d}／SYRIZA {-d:+d} 點 | {fmt(smd)} | {fmt(total)} | 首長 {head_of_gov(total)[0]} |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for label in ("2023-06", "2023-05"):
        print()
        print("實際：", ACTUAL[label])
        report(label, load(label))


if __name__ == "__main__":
    main()
