"""愛沙尼亞一院議會制：得票 → 選制 → 席次 → 行政首長。

偏好位置與選民類型是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2023-03、2019-03 國會重算
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：國家選舉委員會開放資料 opendata.valimised.ee（RK_2023）逐投票所紙本票＋市鎮網路票依比例分回 → 資料/rk-2023.csv
（_build_ee.py；405 個投票所；選區×政黨總數與官方一致，網路票分回投票所是推估）。
2019：rk2019.valimised.ee 網頁表格逐投票所紙本＋網路（網路票按選民所屬投票所公布）→ 資料/rk-2019.csv（_build_ee2019.py；451 個）。
座標：Wikidata EHAK 代碼（P1140）。
區：12 個現行選區合成 7 個區（塔林西、塔林東、哈留－拉普拉、西部、東北、南部、塔爾圖）。區內依座標 Hilbert 序連續切單一選區。
全院 101＝單一 61（top-3 孔多賽）＋複數 40（7 區、聖拉古、無門檻）。
偏好：二維（地緣：親西方、對俄強硬 −1 … 對俄緩和 +1；文化：自由 −1 … 民族保守 +1）。每黨選民分三型。
行政首長：全院 101 記名排名投票，孔多賽完成法；須 ≥51。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402
from 參選判定 import finals_for as _finals_for  # noqa: E402

# 位置參考 CHES 2024 愛沙尼亞（eu_position、對俄、galtan），見 12 §2.1
POS = {
    "RE": (-0.85, -0.5),    # 改革黨（Reformierakond）
    "E200": (-0.8, -0.6),   # Eesti 200
    "SDE": (-0.9, -0.65),   # 社會民主黨
    "IE": (-0.4, 0.55),     # 祖國（Isamaa）
    "PP": (-0.5, -0.2),     # 右派（Parempoolsed）
    "EER": (-0.6, -0.7),    # 綠黨（Rohelised）
    "KESK": (0.1, 0.1),     # 中間黨（Keskerakond）
    "EKRE": (0.5, 0.85),    # 保守人民黨
    "EÜVP": (0.6, 0.5),     # 聯合左翼（Koos／EÜVP；2026 Vasakliit）
    "ERK": (0.45, 0.9),     # 民族主義者與保守派（2024 自 EKRE 分出）
}
TYPES = [(0.5, 1.0, 0.5), (0.2, 0.5, 1.0), (0.3, 0.8, 0.8)]
OTHER_POS = [(0.5, (0.2, 0.3)), (0.5, (-0.4, 0.0))]
BALANCED = (0.8, 0.8)

_DIST = ["塔林一", "塔林二", "塔林三", "哈留－拉普拉", "三島", "西維魯", "東維魯", "耶爾瓦－維爾揚迪", "約蓋瓦－塔爾圖縣", "塔爾圖市", "東南", "派爾努"]
# 12 個現行選區合成 6 個複數區（M∈[5,9]，少於計劃的 8 是因為 40 席分 6 區）；單一席次在區內切
MERGE = {"塔林一": "塔林西", "塔林三": "塔林西", "塔林二": "塔林東", "哈留－拉普拉": "哈留－拉普拉", "三島": "西部", "派爾努": "西部",
         "西維魯": "東北", "東維魯": "東北", "耶爾瓦－維爾揚迪": "南部", "東南": "南部", "約蓋瓦－塔爾圖縣": "塔爾圖", "塔爾圖市": "塔爾圖"}
REGIONS = ["塔林西", "塔林東", "哈留－拉普拉", "西部", "東北", "南部", "塔爾圖"]
ABROAD = "海外"   # 2023 檔沒有海外列（海外票併入各選區）；複數不設海外區
SMD_TOTAL, LIST_TOTAL, NEED = 61, 40, 51

# 偏好引擎參數（notes/sdd/距離模型-計劃.md）：陣營、陣營加分 β、選民分散 s、政黨反感 α
BLOC = {p: ("俄語、主權" if POS[p][0] > 0 else "親西方") for p in POS}
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
    """[(區, (市鎮, 投票所), 經度, 緯度, 有效票, {黨: 票})]，區內依 Hilbert 排序。"""
    if year not in _UNITS:
        with open(os.path.join(HERE, "資料", f"rk-{year}.csv"), encoding="utf-8") as f:
            rows = list(csv.reader(f))
        cols = rows[0][6:]
        us = [(MERGE[r[0]], (r[1], int(r[2])), float(r[3]), float(r[4]), int(r[5]), {c: int(v) for c, v in zip(cols, r[6:])})
              for r in rows[1:]]
        out = []
        for reg in REGIONS:
            part = [u for u in us if u[0] == reg]
            xs, ys = [u[2] * 0.52 for u in part], [u[3] for u in part]
            x0, y0 = min(xs), min(ys)
            span = max(max(xs) - x0, max(ys) - y0) or 1.0
            part.sort(key=lambda u: (hilbert(int((u[2] * 0.52 - x0) / span * 1023), int((u[3] - y0) / span * 1023)), u[1]))
            out += part
        out += [u for u in us if u[0] == ABROAD]
        _UNITS[year] = out
    return _UNITS[year]


def layout():
    """席次分配固定用 2023 有效票：單一 61、複數 40，都依 7 個區最大餘數。"""
    v = {}
    for u in units(2023):
        v[u[0]] = v.get(u[0], 0) + u[4]
    dom = {r: v[r] for r in REGIONS}
    return largest_remainder(dom, SMD_TOTAL), largest_remainder(dom, LIST_TOTAL)


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
    2019: ("改革黨 34、中間黨 26、EKRE 19、祖國 12、社民黨 10（101）", "Ratas（中間黨）：中間黨＋EKRE＋祖國 57；2021-01 起 Kallas：改革黨＋中間黨 60"),
    2023: ("改革黨 37、EKRE 17、中間黨 16、Eesti 200 14、社民黨 9、祖國 8（101）", "Kallas（改革黨）：改革黨＋Eesti 200＋社民黨 60；2024-07 起 Michal；2025-03 社民黨出局，改革黨＋Eesti 200"),
}
NAMES = {2023: "2023-03", 2019: "2019-03"}


def projection():
    """第 3 屆（推測）：以 2023 地理；兩翼（社民黨、EKRE、聯合左翼）各讓出 1/8 第一偏好給居中政黨（改革黨、中間黨各半）。"""
    us = units(2023)
    nat = national(us)
    t = dict(nat)
    moved = 0
    for p in ("SDE", "EKRE", "EÜVP"):
        t[p] = nat[p] * 7 / 8
        moved += nat[p] / 8
    t["RE"] += moved / 2
    t["KESK"] += moved / 2
    return scale(us, t)


def report(label, us):
    smd, lst, total, st, by = chamber(us)
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", fmt({p: round(v * 100, 1) for p, v in national(us).items()}))
    print(f"單一 {SMD_TOTAL}：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by.get(r, {}))}" for r in REGIONS))
    print(f"複數 {LIST_TOTAL}：", fmt(lst))
    print(f"全院 {SMD_TOTAL + LIST_TOTAL}：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(seq)}＝{acc}")
    return total


YEARS = [y for y in (2023, 2019) if os.path.exists(os.path.join(HERE, "資料", f"rk-{y}.csv"))]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"單一 {SMD_TOTAL}：", SMD_N)
    print(f"複數 {LIST_TOTAL}：", LIST_M)
    if "--sweep" in sys.argv:
        for label, types in (("基準", TYPES), ("全部重地緣", [(1.0, 1.0, 0.4)]), ("全部重文化", [(1.0, 0.4, 1.0)]),
                             ("全部均衡", [(1.0, 0.8, 0.6)])):
            a = chamber(units(2023), types)
            b = chamber(units(2019), types)
            print(f"| {label} | {fmt(a[0])} | 首長 {head_of_gov(a[2])[0]} | {fmt(b[0])} | 首長 {head_of_gov(b[2])[0]} |")
        for shift in (False, True):
            print(f"| 切線{'位移半區' if shift else '基準'} | {fmt(chamber(units(2023), shift=shift)[0])} | | {fmt(chamber(units(2023), shift=shift)[0])} |")
        nat = national(units(2023))
        for d in (-6, -3, 3, 6):
            t = dict(nat)
            t["RE"] = nat["RE"] + d / 100
            t["EKRE"] = nat["EKRE"] - d / 100
            smd, _, total, _, _ = chamber(scale(units(2023), t))
            print(f"| 改革黨 {d:+d}／EKRE {-d:+d} 點 | {fmt(smd)} | {fmt(total)} | 首長 {head_of_gov(total)[0]} |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    for y in YEARS:
        print("\n實際：", ACTUAL[y][0], "；", ACTUAL[y][1])
        report(NAMES[y], units(y))


if __name__ == "__main__":
    main()
