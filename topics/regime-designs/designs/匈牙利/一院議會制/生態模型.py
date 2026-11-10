"""匈牙利一院議會制：得票 → 選制 → 席次 → 行政首長。

偏好位置與選民類型是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2026-04、2022-04 國會重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：NVI（國家選舉辦公室）vtr 逐投票所（szavazókör）名單票 → 資料/ogy-2026.csv、ogy-2022.csv（_build_ogy.py）。
座標：NVI 投票所中心點（Szavkor-Topo 的 centrum）。海外郵寄票（levélszavazat）只有全國數字，單獨一列，只進海外複數區。
區：8 個 NUTS-2 區＋海外。區內依投票所座標的 Hilbert 序連續切單一選區。
全院 200＝單一 120（top-3 孔多賽）＋複數 80（8 國內區＋海外、聖拉古、無門檻）。
偏好：二維（地緣：歐盟整合 −1 … 主權 +1；體制：改革、反既得網絡 −1 … 既得網絡 +1）。每黨選民分三型。
行政首長：全院 200 記名排名投票，孔多賽完成法；須 ≥101。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402
from 參選判定 import finals_for as _finals_for  # noqa: E402

POS = {
    "TISZA": (-0.3, -0.7),
    "FIDESZ": (0.7, 0.9),     # Fidesz–KDNP
    "EGYSÉG": (-0.7, -0.3),   # 2022 反對聯盟（DK、Jobbik、Momentum、MSZP、LMP、Párbeszéd）
    "MI": (1.0, -0.2),        # Mi Hazánk
    "DK": (-0.9, 0.3),
    "MKKP": (-0.6, -0.9),     # 雙尾犬黨
    "德意志族": (0.4, 0.7),
}
# 選民三型：(比例, 地緣權重, 體制權重)
TYPES = [(0.4, 1.0, 0.5), (0.3, 0.5, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.0, -0.3)), (0.5, (0.3, 0.2))]
BALANCED = (0.8, 0.8)

REGIONS = ["布達佩斯", "佩斯", "中多瑙河外", "西多瑙河外", "南多瑙河外", "北匈牙利", "北大平原", "南大平原"]
ABROAD = "海外"
SMD_TOTAL, LIST_TOTAL, NEED = 120, 80, 101


# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {"FIDESZ": "政府", "TISZA": "反對派", "EGYSÉG": "反對派", "DK": "反對派", "MKKP": "反對派"}
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
    """[(區, 投票所碼, 經度, 緯度, 有效票, {黨: 票})]，區內依 Hilbert 排序。"""
    if year not in _UNITS:
        with open(os.path.join(HERE, "資料", f"ogy-{year}.csv"), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        cols = rows[0][5:]
        us = [(r[0], r[1], float(r[2]), float(r[3]), int(r[4]), {c: int(v) for c, v in zip(cols, r[5:])})
              for r in rows[1:]]
        out = []
        for reg in REGIONS:
            part = [u for u in us if u[0] == reg]
            xs, ys = [u[2] * 0.68 for u in part], [u[3] for u in part]
            x0, y0 = min(xs), min(ys)
            span = max(max(xs) - x0, max(ys) - y0) or 1.0
            part.sort(key=lambda u: (hilbert(int((u[2] * 0.68 - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1]))
            out += part
        out += [u for u in us if u[0] == ABROAD]
        _UNITS[year] = out
    return _UNITS[year]


def layout():
    """席次分配固定用 2026 有效票：單一 120 依國內 8 區；複數海外 [2,8]，其餘 8 區。"""
    v = {}
    for u in units(2026):
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
    """target：{黨: 全國份額}；每黨在每個投票所的票 ×（目標／實際）。"""
    base = national(us)
    return [(u[0], u[1], u[2], u[3], u[4], {p: v * target.get(p, 0) / base[p] if base.get(p) else 0 for p, v in u[5].items()})
            for u in us]


def split_party(us, parent, children):
    """把 parent 的票依比例拆成 children（同一地理），用於選後分裂／合流的政黨。"""
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
    2026: ("TISZA 名單 53.2%、Fidesz–KDNP 38.6%、Mi Hazánk 5.6%（199 席見 14）", ""),
    2022: ("Fidesz–KDNP 135、反對聯盟 57、Mi Hazánk 6、德意志族 1（199）", "Orbán：Fidesz–KDNP 單獨 2/3"),
}


def projection():
    """第 3 屆（推測）：以 2026 地理；兩翼（Fidesz、Mi Hazánk）各讓出 1/8 第一偏好給 TISZA 以外的中間選項不成立
    （匈牙利沒有中間黨），改為 Fidesz 讓出 1/8 給 Mi Hazánk 與 TISZA 各半，反映執政失利後的重組（假設）。"""
    us = units(2026)
    nat = national(us)
    t = dict(nat)
    d = nat["FIDESZ"] / 8
    t["FIDESZ"] -= d
    t["MI"] += d / 2
    t["TISZA"] += d / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print("單一 120：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print("複數 80：", fmt(lst))
    print("全院 200：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(seq)}＝{acc}")
    return total


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("單一 120：", SMD_N)
    print("複數 80：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.5)]), ("全部重體制", [(1.0, 0.5, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.8)])):
            s26, _, t26, _, _ = chamber(units(2026), types)
            s22, _, t22, _, _ = chamber(units(2022), types)
            print(f"| {label} | {fmt(s26)} | 首長 {head_of_gov(t26)[0]} | {fmt(s22)} | 首長 {head_of_gov(t22)[0]} |")
        for shift in (False, True):
            print(f"| 切線{'位移半區' if shift else '基準'} | {fmt(chamber(units(2026), shift=shift)[0])} | | {fmt(chamber(units(2022), shift=shift)[0])} |")
        nat = national(units(2026))
        for d in (-8, -4, 4, 8):
            t = dict(nat)
            t["FIDESZ"] = nat["FIDESZ"] + d / 100
            t["TISZA"] = nat["TISZA"] - d / 100
            smd, _, total, _, _ = chamber(scale(units(2026), t))
            print(f"| Fidesz {d:+d}／TISZA {-d:+d} 點 | {fmt(smd)} | {fmt(total)} | 首長 {head_of_gov(total)[0]} |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for y in (2026, 2022):
        print()
        print("實際：", ACTUAL[y][0], "；", ACTUAL[y][1])
        report(f"{y}-04", units(y))


if __name__ == "__main__":
    main()
