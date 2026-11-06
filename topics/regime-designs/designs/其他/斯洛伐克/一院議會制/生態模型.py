"""斯洛伐克一院議會制：得票 → 選制 → 席次 → 行政首長。

偏好位置與選民類型是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2023-09、2020-02 國會重算；2024 總統 top-3
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：統計局 volby.statistics.sk 逐投票區（okrsok）名單票 → 資料/nrsr-2023.csv、nrsr-2020.csv（_build_nrsr.py；2023 年 6,013 個＋海外）。
座標：Wikidata LAU 代碼（P782）末 6 碼＝市鎮碼；同市鎮的投票區依編號排序。
區：8 個州合成 5 個國內區＋海外。區內依座標 Hilbert 序連續切單一選區。
全院 150＝單一 90（top-3 孔多賽）＋複數 60（5 國內區＋海外、聖拉古、無門檻）。
偏好：二維（地緣：歐盟整合 −1 … 主權 +1；體制：自由、法治改革 −1 … 民族民粹 +1）。每黨選民分三型。
行政首長：全院 150 記名排名投票，孔多賽完成法；須 ≥76。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 6, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402

POS = {
    "Smer": (0.6, 0.7),
    "Hlas": (0.2, 0.35),
    "PS": (-0.9, -0.8),
    "OĽaNO": (-0.3, 0.1),     # 2023 名單 OĽaNO a priatelia；2020 OĽaNO
    "SaS": (-0.6, -0.5),
    "KDH": (-0.3, 0.2),
    "SNS": (0.8, 0.8),
    "Republika": (1.0, 0.9),
    "Aliancia": (-0.2, -0.1), # 匈牙利族（2020 MKS、Most-Híd 另計）
    "SmeRodina": (0.4, 0.5),
    "Demokrati": (-0.6, -0.4),
    "ĽSNS": (1.0, 1.0),
    "ZaĽudí": (-0.4, -0.3),   # 2020
    "Slovensko": (-0.3, 0.1), # 2023 後 Matovič 的 Slovensko（OĽaNO 拆出）
    "ZĽ": (-0.4, -0.3),       # Za ľudí（2023 在 OĽaNO 名單）
    "KÚ": (-0.1, 0.3),        # 基督教聯盟（2023 在 OĽaNO 名單）
    "MostHid": (-0.4, -0.3),  # 2020
    "DobráVoľba": (0.1, 0.3), # 2020（Drucker，自 Smer 分出）
    "Vlasť": (1.0, 0.9),      # 2020（Harabin）
}
TYPES = [(0.5, 1.0, 0.5), (0.2, 0.5, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.3, 0.3)), (0.5, (-0.3, -0.2))]
BALANCED = (0.8, 0.8)

KRAJ_TO = {"布拉提斯拉瓦": "布拉提斯拉瓦", "特爾納瓦": "特爾納瓦－尼特拉", "尼特拉": "特爾納瓦－尼特拉",
           "特倫欽": "特倫欽－日利納", "日利納": "特倫欽－日利納", "班斯卡比斯特里察": "班斯卡比斯特里察－科希策",
           "科希策": "班斯卡比斯特里察－科希策", "普雷紹夫": "普雷紹夫", "海外": "海外"}
REGIONS = ["布拉提斯拉瓦", "特爾納瓦－尼特拉", "特倫欽－日利納", "班斯卡比斯特里察－科希策", "普雷紹夫"]
ABROAD = "海外"
SMD_TOTAL, LIST_TOTAL, NEED = 90, 60, 76


# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {"Smer": "執政", "Hlas": "執政", "SNS": "執政", "Republika": "民族派", "ĽSNS": "民族派", "Vlasť": "民族派",
        "PS": "自由中右", "SaS": "自由中右", "KDH": "自由中右", "OĽaNO": "自由中右", "Slovensko": "自由中右", "ZĽ": "自由中右",
        "KÚ": "自由中右", "Demokrati": "自由中右", "ZaĽudí": "自由中右", "MostHid": "自由中右", "Aliancia": "自由中右"}
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
    """[(區, (市鎮碼, 投票區), 經度, 緯度, 有效票, {黨: 票})]，區內依 Hilbert 排序。"""
    if year not in _UNITS:
        with open(os.path.join(HERE, "資料", f"nrsr-{year}.csv"), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        cols = rows[0][6:]
        us = [(KRAJ_TO[r[0]], (r[1], int(r[2])), float(r[3]), float(r[4]), int(r[5]), {c: int(v) for c, v in zip(cols, r[6:])})
              for r in rows[1:]]
        out = []
        for reg in REGIONS:
            part = [u for u in us if u[0] == reg]
            xs, ys = [u[2] * 0.66 for u in part], [u[3] for u in part]
            x0, y0 = min(xs), min(ys)
            span = max(max(xs) - x0, max(ys) - y0) or 1.0
            part.sort(key=lambda u: (hilbert(int((u[2] * 0.66 - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1]))
            out += part
        out += [u for u in us if u[0] == ABROAD]
        _UNITS[year] = out
    return _UNITS[year]


def layout():
    """席次分配固定用 2023 有效票：單一 90 依國內 5 區；複數海外 [1,4]，其餘 5 區。"""
    v = {}
    for u in units(2023):
        v[u[0]] = v.get(u[0], 0) + u[4]
    dom = {r: v[r] for r in REGIONS}
    smd = largest_remainder(dom, SMD_TOTAL)
    abroad = min(4, max(1, round(v[ABROAD] * LIST_TOTAL / sum(v.values()))))
    lst = largest_remainder(dom, LIST_TOTAL - abroad)
    lst[ABROAD] = abroad
    return smd, lst


SMD_N, LIST_M = layout()


def rank_from(pos, cands, wx, wy, home=None):
    return prefs().rank(pos, home, cands, (wx, wy))


def voter_groups(parties, types=TYPES):
    return prefs().groups(parties, parties, types, OTHER_POS, (0.8, 0.6))


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
    """target：{黨: 全國份額}；每黨在每個投票所的票 ×（目標／實際）。"""
    base = national(us)
    return [(u[0], u[1], u[2], u[3], u[4], {p: v * target.get(p, 0) / base[p] if base.get(p) else 0 for p, v in u[5].items()})
            for u in us]


def split_party(us, parent, children):
    """把 parent 的票依比例拆成 children（同一地理），用於 2023 後分裂／合流的政黨。"""
    tot = sum(children.values())
    out = []
    for u in us:
        v = dict(u[5])
        x = v.pop(parent, 0)
        for c, s in children.items():
            v[c] = v.get(c, 0) + x * s / tot
        out.append((u[0], u[1], u[2], u[3], u[4], v))
    return out


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def chamber(us, types=TYPES, shift=False):
    smd, st, by = single_seats(us, types, shift)
    lst = list_seats(us)
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in set(smd) | set(lst)}
    return smd, lst, total, st, by


ACTUAL = {
    2023: ("Smer 42、PS 32、Hlas 27、OĽaNO 16、KDH 12、SaS 11、SNS 10（150）", "Fico（Smer）：Smer＋Hlas＋SNS 79"),
    2020: ("OĽaNO 53、Smer 38、Sme Rodina 17、ĽSNS 17、SaS 13、Za ľudí 12（150）", "Matovič（OĽaNO）：OĽaNO＋Sme Rodina＋SaS＋Za ľudí 95"),
}

# 2024 總統第一輪（維基 2024 Slovak presidential election 的 Election results 模板，引 volbysr.sk）。決選 Pellegrini 1,409,255：Korčok 1,243,709
# 候選人的位置借用最接近的政黨（Kubiš → KDH、Dubovský → Demokrati 是假設）。
PRES_2024 = [("Korčok", 958393, "PS"), ("Pellegrini", 834718, "Hlas"), ("Harabin", 264579, "Republika"),
             ("Forró", 65588, "Aliancia"), ("Matovič", 49201, "OĽaNO"), ("Kubiš", 45957, "KDH"),
             ("Dubovský", 16107, "Demokrati"), ("Kotleba", 12771, "ĽSNS"), ("其他", 6892, None)]


def presidential(types=TYPES):
    finals = ["Korčok", "Pellegrini", "Harabin"]
    cs = [(c, n, p) for c, n, p in PRES_2024 if n]
    where = {c: (POS[p] if p else (0.0, 0.0)) for c, _, p in cs}
    pr = Prefs(where, {c: BLOC.get(p) for c, _, p in cs if p}, BETA, SPREAD, {c: ALPHA.get(p, 0) for c, _, p in cs if p})
    groups = pr.groups([c for c, _, _ in cs], finals, types)
    votes = {c: n for c, n, _ in PRES_2024}
    w, cyc, P = pairwise_winner(finals, groups, lambda s: votes[s])
    return w, cyc, {f"{a}>{b}": round(P[(a, b)] * 100 / (P[(a, b)] + P[(b, a)]), 1) for a in finals for b in finals if a < b}, 0


def projection():
    """第 3 屆（推測）：以 2023 地理；兩翼（PS、Republika、SNS）各讓出 1/8 第一偏好給居中政黨（Hlas、KDH 各半）。"""
    us = units(2023)
    nat = national(us)
    t = dict(nat)
    moved = 0
    for p in ("PS", "Republika", "SNS"):
        t[p] = nat[p] * 7 / 8
        moved += nat[p] / 8
    t["Hlas"] += moved / 2
    t["KDH"] += moved / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print("單一 90：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print("複數 60：", fmt(lst))
    print("全院 150：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(seq)}＝{acc}")
    return total


YEARS = [y for y in (2023, 2020) if os.path.exists(os.path.join(HERE, "資料", f"nrsr-{y}.csv"))]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("單一 90：", SMD_N)
    print("複數 60：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4)]), ("全部重體制", [(1.0, 0.4, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.6)])):
            s23, _, t23, _, _ = chamber(units(2023), types)
            s19, _, t19, _, _ = chamber(units(YEARS[-1]), types)
            print(f"| {label} | {fmt(s23)} | 首長 {head_of_gov(t23)[0]} | {fmt(s19)} | 首長 {head_of_gov(t19)[0]} |")
        for shift in (False, True):
            print(f"| 切線{'位移半區' if shift else '基準'} | {fmt(chamber(units(2023), shift=shift)[0])} | | {fmt(chamber(units(YEARS[-1]), shift=shift)[0])} |")
        nat = national(units(2023))
        for d in (-6, -3, 3, 6):
            t = dict(nat)
            t["Smer"] = nat["Smer"] + d / 100
            t["PS"] = nat["PS"] - d / 100
            smd, _, total, _, _ = chamber(scale(units(2023), t))
            print(f"| Smer {d:+d}／PS {-d:+d} 點 | {fmt(smd)} | {fmt(total)} | 首長 {head_of_gov(total)[0]} |")
        for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4)]), ("全部重體制", [(1.0, 0.4, 1.0)])):
            print("總統 2024", label, presidential(types)[:3])
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for y in YEARS:
        print("\n實際：", ACTUAL[y][0], "；", ACTUAL[y][1])
        report({2023: "2023-09", 2020: "2020-02"}[y], units(y))
    w, cyc, P, tot = presidential()
    print(f"\n## 總統 2024 top-3（Korčok、Pellegrini、Harabin）：{w}；循環 {cyc}；兩兩 {P}")


if __name__ == "__main__":
    main()
