"""秘魯（一院總統制、一院議會制兩夾共用）：得票 → 選制 → 席次 → 總統／行政首長。

偏好位置與選民類型是**假設**（見兩夾的 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2026、2021 國會重算；總統 top-3；議會制首長
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：
- 2021：ONPE 逐投票桌（datosabiertos.gob.pe），同一區（distrito）每 25 桌合成一個單位（4,727 個）→ 資料/eg-2021.csv（_build_eg2021.py）。
- 2026：ONPE 結果網站擋自動存取，只有維基的全國眾議院得票與各省總統第一輪。各黨沿用 2021 年「母黨」的單位分布，
  按各省總統第一輪調整省級總量，再縮放到全國眾議院得票 → 資料/eg-2026.csv（_build_eg2026.py）。**省內分布是推估**。
區：國內 5 區（利馬北東－卡亞俄、利馬中南、北部、中部與亞馬遜、南部）＋海外。區內依區座標的 Hilbert 序連續切單一選區。
國會 160＝單一 96（top-3 孔多賽）＋複數 64（聖拉古、無門檻）。
偏好：二維（經濟：國家、再分配 −1 … 市場 +1；體制：自由民主、反貪 −1 … 威權、保守、恩庇 +1）。每黨選民分三型。
校準：人民力量的體制軸位置使 2021（Castillo 對 Fujimori）、2026（Fujimori 對 Sánchez）兩次決選的模型對決都接近 50：50。
總統（總統制夾）：全國 top-3 孔多賽。首長（議會制夾）：全院 160 記名排名投票，須 ≥81。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402
from 總統民意 import president as _president, fmt as _pfmt  # noqa: E402
from 參選判定 import finals_for as _finals_for  # noqa: E402

POS = {
    "PL": (-0.9, 0.4),      # 自由秘魯（2021 Castillo）
    "JP": (-0.8, -0.2),     # 團結秘魯（2026 見 OVERRIDE）
    "FA": (-0.7, -0.4),
    "PNP": (-0.6, 0.3),     # 民族主義黨（Humala）
    "UPP": (-0.5, 0.7),     # 秘魯聯盟（Antauro Humala 派）
    "AP": (0.0, 0.0),       # 人民行動
    "SP": (0.0, 0.1),       # 我們是秘魯
    "APP": (0.2, 0.3),      # 進步聯盟
    "Pod": (0.1, 0.6),      # 我們能秘魯
    "PM": (0.1, -0.8),      # 紫色黨
    "VN": (0.4, -0.3),      # 國家勝利（Forsyth）
    "AvP": (0.8, 0.0),      # 國家前進（de Soto）
    "PPC": (0.6, 0.3),      # 基督教人民黨
    "FP": (0.5, 1.4),       # 人民力量（藤森）：體制軸 1.4＝反藤森主義，用 2021、2026 兩次決選校準（見 12 §2）
    "RP": (0.9, 1.1),       # 人民革新（López Aliaga）：2026 指控舞弊、呼籲起事；體制軸次於 FP
    "FREPAP": (-0.1, 0.9),  # 農業人民陣線
    # 2026 新黨
    "PBG": (-0.3, -0.5),    # 好政府黨（Nieto）
    "AN": (-0.6, 0.0),      # 此刻民族（López Chau）
    "OBRAS": (-0.1, 0.6),   # OBRAS（Belmont）
    "PPT": (0.3, 0.5),      # 全民國家（Álvarez）
    "PLG": (0.0, -0.6),     # 人民優先
    "APRA": (0.2, 0.3),     # 阿普拉黨
}
OVERRIDE = {2026: {"JP": (-0.85, 0.3)}}   # 2026 團結秘魯（Sánchez，Castillo 路線、反建制）
# 選民三型：(比例, 經濟權重, 體制權重)
TYPES = [(0.5, 1.0, 0.5), (0.2, 0.5, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.2, 0.4)), (0.5, (-0.3, 0.2))]
BALANCED = (0.8, 0.8)
YEAR = [2021]

REGIONS = ["利馬北東－卡亞俄", "利馬中南", "北部", "中部與亞馬遜", "南部"]
ABROAD = "海外"
SMD_TOTAL, LIST_TOTAL, NEED = 96, 64, 81


def P(c):
    return OVERRIDE.get(YEAR[0], {}).get(c, POS[c])


# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {"PL": "左", "JP": "左", "FA": "左", "PNP": "左", "UPP": "左", "AN": "左",
        "FP": "右", "RP": "右", "AvP": "右", "PPC": "右"}
BETA, SPREAD, ALPHA = 0.0, 0.0, {}


def prefs():
    return Prefs({c: P(c) for c in POS}, BLOC, BETA, SPREAD, ALPHA)


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
    """[(區, (UBIGEO, 塊), 經度, 緯度, 國會有效票, {黨: 票})]，區內依 Hilbert 排序。"""
    if year not in _UNITS:
        with open(os.path.join(HERE, "資料", f"eg-{year}.csv"), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        cc = [(k, c[2:]) for k, c in enumerate(rows[0]) if c.startswith("C_")]
        us = []
        for r in rows[1:]:
            v = {c: int(r[k]) for k, c in cc}
            us.append((r[0], (r[2], int(r[3])), float(r[4]), float(r[5]), sum(v.values()), v))
        out = []
        for reg in REGIONS:
            part = [u for u in us if u[0] == reg]
            xs, ys = [u[2] for u in part], [u[3] for u in part]
            x0, y0 = min(xs), min(ys)
            span = max(max(xs) - x0, max(ys) - y0) or 1.0
            part.sort(key=lambda u: (hilbert(int((u[2] - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1]))
            out += part
        out += [u for u in us if u[0] == ABROAD]
        _UNITS[year] = out
    return _UNITS[year]


def pres_2021():
    """2021 總統第一輪全國得票（同一份逐桌檔的 P_ 欄）。"""
    with open(os.path.join(HERE, "資料", "eg-2021.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    pc = [(k, c[2:]) for k, c in enumerate(rows[0]) if c.startswith("P_")]
    t = {}
    for r in rows[1:]:
        for k, c in pc:
            t[c] = t.get(c, 0) + int(r[k])
    return t


def layout():
    """席次分配固定用 2021 國會有效票：單一 96 依國內 5 區；複數海外 [2,8]，其餘 5 區。"""
    v = {}
    for u in units(2021):
        v[u[0]] = v.get(u[0], 0) + u[4]
    dom = {r: v[r] for r in REGIONS}
    smd = largest_remainder(dom, SMD_TOTAL)
    abroad = min(8, max(2, round(v[ABROAD] * LIST_TOTAL / sum(v.values()))))
    lst = largest_remainder(dom, LIST_TOTAL - abroad)
    lst[ABROAD] = abroad
    return smd, lst


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
            _g = voter_groups(cands, types)
            _w = lambda s: d.get(s, 0)
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
            finals = _finals_for({p: d[p] for p in cands}, 3, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, _g, _w)[0], POS)
            w, cyc, _ = pairwise_winner(finals, _g, _w)
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
    2021: ("一院 130：PL 37、FP 24、AP 16、APP 15、RP 13、AvP 7、JP 5、SP 5、Pod 5、PM 3", "總統 Castillo（PL）決選 50.13%"),
    2026: ("眾議院 130：FP 41、JP 32、PBG 18、RP 15、OBRAS 14、AN 10（另參議院 60）", "總統 Keiko Fujimori（FP）決選 50.13%"),
}

# 2026 總統第一輪（維基 2026 Peruvian general election 的 Election results 模板，引 ONPE；全部有效票 16,738,039）
PRES_2026 = {"FP": 2877678, "JP": 2015114, "RP": 1993905, "PBG": 1837517, "OBRAS": 1698903, "PPT": 1326717,
             "AN": 1221272, "PLG": 571170, "Pod": 266768, "APP": 192516, "APRA": 161248, "SP": 153073,
             "PL": 100073, "PM": 82196}
PRES_2026["其他"] = 16738039 - sum(PRES_2026.values())
RUNOFF = {2021: "Castillo（PL）50.13：Fujimori（FP）49.87", 2026: "Fujimori（FP）50.13：Sánchez（JP）49.87"}


def presidential(year, types=TYPES):
    """全國 top-3 孔多賽：前三名進入兩兩對決；各黨第一偏好選民依自己位置排序三人。"""
    YEAR[0] = year
    votes = pres_2021() if year == 2021 else PRES_2026
    cands = [p for p in votes if p in POS and votes[p] > 0]
    finals = sorted(cands, key=lambda p: -votes[p])[:3]
    w, cyc, Pw = pairwise_winner(finals, voter_groups(cands, types), lambda s: votes.get(s, 0))
    pct = {f"{a}>{b}": round(Pw[(a, b)] * 100 / (Pw[(a, b)] + Pw[(b, a)]), 1) for a in finals for b in finals if a < b}
    return finals, w, cyc, pct


def presidential_list(year, types=TYPES):
    """總統主版（notes/算法/選舉結果計算方式.md）：民意層＝同日國會名單票，政黨層級，不用現實總統第一輪、不用個別候選人；
    參選方層＝每黨可推人，參選判定.finalists 決定相鄰政黨的共同提名；前 3 名孔多賽。"""
    fp = {p: v for p, v in national(units(year)).items() if p in POS and v > 0}
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(P(a), P(b))) ** 0.5
    return _president(fp, lambda parties, cands: voter_groups(parties, types), dist, list(POS)), fp


def projection():
    """第 3 屆（推測）：以 2026 推估地理；兩端（RP、JP、AN、FREPAP）各讓出 1/8 第一偏好給居中政黨（PBG、APP 各半）。"""
    YEAR[0] = 2026
    us = units(2026)
    nat = national(us)
    t = dict(nat)
    moved = 0
    for p in ("RP", "JP", "AN", "FREPAP"):
        t[p] = nat[p] * 7 / 8
        moved += nat[p] / 8
    t["PBG"] += moved / 2
    t["APP"] += moved / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print("單一 96：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print("複數 64：", fmt(lst))
    print("全院 160：", fmt(total), "合計", sum(total.values()))
    print(f"［議會制夾］首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"［議會制夾］組閣聯盟（由近到遠）：{'＋'.join(seq)}＝{acc}")
    return total


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("單一 96：", SMD_N)
    print("複數 64：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重經濟", [(1.0, 1.0, 0.5)]), ("全部重體制", [(1.0, 0.5, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.8)])):
            out = []
            for y in (2026, 2021):
                YEAR[0] = y
                s_, _, t_, _, _ = chamber(units(y), types)
                out.append(f"{fmt(s_)} ｜ 首長 {head_of_gov(t_)[0]} ｜ 總統 {presidential_list(y, types)[0]['winner']}")
            print(f"| {label} | " + " | ".join(out) + " |")
        for shift in (False, True):
            cells = []
            for y in (2026, 2021):
                YEAR[0] = y
                cells.append(fmt(chamber(units(y), shift=shift)[0]))
            print(f"| 切線{'位移半區' if shift else '基準'} | " + " | ".join(cells) + " |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for y in (2026, 2021):
        YEAR[0] = y
        print()
        print("實際：", ACTUAL[y][0], "；", ACTUAL[y][1])
        report(str(y), units(y))
        res, fp = presidential_list(y)
        print(f"［總統制夾］總統（主版：同日國會名單票 × 參選方層）：{_pfmt(res, fp)}")
        finals, w, cyc, pct = presidential(y)
        print(f"  對照：現實第一輪前三（{'、'.join(finals)}）：{w}；循環 {cyc}；兩兩 {pct}")


if __name__ == "__main__":
    main()
