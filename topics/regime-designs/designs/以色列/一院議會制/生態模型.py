"""以色列一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py            # 2019–2022 五次＋2026-10 大選重算
    python 生態模型.py --sweep    # 敏感度

得票：中央選舉委員會逐票匭結果（data.gov.il 第 21–25 屆；2026＝madad120 彙整之官方票匭 CSV），彙整成 資料/knesset-NN.csv 的「單位」：
小鎮一個單位，大城市依票匭序切成約 2 萬選舉人一塊。「雙層信封」票（士兵、住院者、外交人員等，
2022 年約占有效票 9.6%）無法定位到選區：單一席次不計，複數席次依選舉人數攤到 5 區。
單一 70：依選舉人數分到 5 區（最大餘數），區內依城鎮座標的希爾伯特曲線順序（城鎮座標＝
教育部學校座標的中位數）連續切成選舉人數相近的選區（整塊切，不拆單位；同城各塊依票匭序）；top-3 孔多賽，循環用 Ranked Pairs。
複數 50：5 區（北部；海法＋夏隆；中部；特拉維夫；耶路撒冷＋猶太與撒馬利亞＋南部），聖拉古，無法定門檻。
偏好：四軸空間（安全：鴿 −1 … 鷹 +1；宗教：世俗 −1 … 宗教 +1；人物：反 Netanyahu −1 … 挺 +1；
阿拉伯政黨 1，其餘 0）。每黨選民分三型（重安全、重宗教、重人物）。
行政首長：全院 120 記名排名投票，議員依所屬政黨的均衡型排序；孔多賽完成法；須 ≥61 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = ["北部", "海法－夏隆", "中部", "特拉維夫", "耶路撒冷－南部"]

# (安全, 宗教, 人物, 阿拉伯)。位置是假設（12 §2.1）；同名政黨在不同屆可覆寫。
POS = {
    "利庫德": (0.6, 0.2, 1.0, 0),
    "宗教錫安": (1.0, 0.7, 0.8, 0),
    "右翼聯盟": (1.0, 0.7, 0.8, 0),
    "猶太力量": (1.0, 0.6, 0.7, 0),
    "猶太之家": (0.8, 0.6, 0.3, 0),
    "亞米納": (0.9, 0.5, 0.6, 0),
    "新右翼": (0.9, 0.2, 0.6, 0),
    "澤胡特": (0.7, 0.1, 0.3, 0),
    "沙斯": (0.5, 0.8, 0.9, 0),
    "聖經猶太": (0.4, 1.0, 0.9, 0),
    "我們的家": (0.6, -0.8, -0.7, 0),
    "庫拉努": (0.3, -0.1, 0.5, 0),
    "新希望": (0.7, 0.0, -0.8, 0),
    "藍白": (0.1, -0.4, -0.9, 0),
    "國家團結": (0.2, -0.2, -0.8, 0),
    "Yashar": (0.3, -0.3, -0.9, 0),       # Eisenkot；安全中間、反 Netanyahu
    "Together": (0.7, 0.2, -0.6, 0),       # Bennett；偏右但反 Netanyahu 任總理
    "未來黨": (-0.1, -0.7, -1.0, 0),
    "格謝爾": (0.0, -0.2, -0.5, 0),
    "工黨": (-0.5, -0.6, -1.0, 0),
    "工黨–梅雷茲": (-0.6, -0.7, -1.0, 0),
    "梅雷茲": (-0.8, -0.8, -1.0, 0),
    "民主黨": (-0.6, -0.7, -1.0, 0),
    "民主聯盟": (-0.8, -0.8, -1.0, 0),
    "拉姆": (-0.5, 0.6, -0.3, 1),
    "拉姆–巴拉德": (-0.8, 0.3, -1.0, 1),
    "哈達什–塔阿勒": (-0.9, -0.4, -1.0, 1),
    "巴拉德": (-1.0, -0.2, -1.0, 1),
    "聯合名單": (-0.9, -0.2, -1.0, 1),
}
OVERRIDE = {
    "2019-04": {"我們的家": (0.7, -0.8, 0.3, 0)},             # 2019-09 以前仍屬 Netanyahu 陣營
    "2021-03": {"亞米納": (0.8, 0.4, 0.0, 0), "藍白": (0.0, -0.4, -0.8, 0)},
}
# 選民三型：(比例, 安全權重, 宗教權重, 人物權重, 阿拉伯權重)
TYPES = [(0.35, 1.0, 0.4, 0.6, 2.0), (0.30, 0.4, 1.0, 0.6, 2.0), (0.35, 0.5, 0.4, 1.0, 2.0)]
BALANCED = (0.6, 0.6, 0.7, 2.0)

ELECTIONS = {"2019-04": 21, "2019-09": 22, "2020-03": 23, "2021-03": 24, "2022-11": 25, "2026-10": 26}
# 實際席次（Bader-Ofer，3.25% 門檻）
ACTUAL = {
    "2019-04": {"利庫德": 35, "藍白": 35, "沙斯": 8, "聖經猶太": 8, "哈達什–塔阿勒": 6, "工黨": 6, "我們的家": 5,
                "右翼聯盟": 5, "梅雷茲": 4, "庫拉努": 4, "拉姆–巴拉德": 4},
    "2019-09": {"藍白": 33, "利庫德": 32, "聯合名單": 13, "沙斯": 9, "我們的家": 8, "聖經猶太": 7, "亞米納": 7,
                "工黨": 6, "民主聯盟": 5},
    "2020-03": {"利庫德": 36, "藍白": 33, "聯合名單": 15, "沙斯": 9, "聖經猶太": 7, "工黨–梅雷茲": 7, "我們的家": 7,
                "亞米納": 6},
    "2021-03": {"利庫德": 30, "未來黨": 17, "沙斯": 9, "藍白": 8, "亞米納": 7, "工黨": 7, "聖經猶太": 7, "我們的家": 7,
                "宗教錫安": 6, "聯合名單": 6, "新希望": 6, "梅雷茲": 6, "拉姆": 4},
    "2022-11": {"利庫德": 32, "未來黨": 24, "宗教錫安": 14, "國家團結": 12, "沙斯": 11, "聖經猶太": 7, "我們的家": 6,
                "拉姆": 5, "哈達什–塔阿勒": 5, "工黨": 4},
    "2026-10": {"利庫德": 27, "Yashar": 21, "Together": 12, "聯合名單": 11, "民主黨": 8, "拉姆": 8,
                "我們的家": 7, "猶太力量": 7, "聖經猶太": 7, "沙斯": 6, "宗教錫安": 6},
}
# Netanyahu 陣營（實際組閣談判的分界）
BIBI = {"利庫德", "宗教錫安", "右翼聯盟", "猶太力量", "沙斯", "聖經猶太", "亞米納", "新右翼", "澤胡特", "庫拉努"}


def load(label):
    """回傳 (單位列表, 信封票, 政黨欄)。單位：(區, 排序鍵, 名稱, 選舉人, {黨: 票})。"""
    path = os.path.join(HERE, "資料", f"knesset-{ELECTIONS[label]}.csv")
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][9:]
    env = {c: int(v) for c, v in zip(cols, rows[1][9:])}
    units = []
    for r in rows[2:]:
        units.append((r[0], (hilbert(float(r[6]), float(r[7])), int(r[3]), int(r[4])), r[5], int(r[8]),
                      {c: int(v) for c, v in zip(cols, r[9:])}))
    return units, env, cols


def hilbert(x, y, order=10):
    """ITM 公里座標 → 希爾伯特曲線序號（全國 300×500 公里框，1024×1024 格）。相鄰序號在地圖上相鄰。"""
    n = 1 << order
    xi = min(n - 1, max(0, int((x - 100) / 200 * n)))
    yi = min(n - 1, max(0, int((y - 350) / 450 * n)))
    d, s = 0, n >> 1
    while s:
        rx, ry = int(xi & s > 0), int(yi & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                xi, yi = s - 1 - xi, s - 1 - yi
            xi, yi = yi, xi
        s >>= 1
    return d


def merged(label, merge):
    """推估用：把幾個政黨的票併成一個（例：工黨＋梅雷茲 → 民主黨）。"""
    units, env, cols = load(label)
    def m(v):
        out = {}
        for c, x in v.items():
            k = merge.get(c, c)
            out[k] = out.get(k, 0) + x
        return out
    return [u[:4] + (m(u[4]),) for u in units], m(env), cols


# 推估：新制運行後的第 3 屆（12 §2.3）。2022 年的地理與得票，加上 2024 年實際發生的工黨＋梅雷茲合併。
PROJECTION = ("2022-11", {"工黨": "民主黨", "梅雷茲": "民主黨"})


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


def electorate(units):
    e = {r: 0 for r in REGIONS}
    for u in units:
        e[u[0]] += u[3]
    return e


def pos(label, p):
    return OVERRIDE.get(label, {}).get(p, POS[p])


def rank_from(label, me, cands, w):
    a = pos(label, me)
    d = lambda c: sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, pos(label, c), a))
    return sorted(cands, key=d)


def voter_groups(label, parties, types=TYPES):
    return [(p, t[0], rank_from(label, p, parties, t[1:])) for p in parties for t in types]


def pairwise_winner(cands, groups, weight):
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        v = weight(src) * w
        if not v:
            continue
        r = [c for c in order if c in cands]
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
            for s, t in locked:
                if s == u and t not in seen:
                    seen.add(t)
                    st.append(t)
        return False
    for _, a, b in wins:
        if not reach(b, a):
            locked.add((a, b))
    top = [c for c in cands if not any(t == c for _, t in locked)]
    if len(top) > 1:                     # 平手（例 60:60）：把他排第一的票較多者為先
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


def districts(units, n_by_region, shift=False):
    """回傳 [(區, 選舉人, {黨: 票}, [單位名])]。依排序鍵連續切；shift＝把開頭約半個選區移到最後再切。"""
    out = []
    for reg in REGIONS:
        rows = sorted((u for u in units if u[0] == reg), key=lambda u: u[1])
        n = n_by_region[reg]
        target = sum(u[3] for u in rows) / n
        if shift:
            acc, k = 0, 0
            while acc < target / 2:
                acc += rows[k][3]
                k += 1
            rows = rows[k:] + rows[:k]
        cur, made, acc = None, 0, 0
        for u in rows:
            if cur is None:
                cur = [reg, 0, {}, []]
            cur[1] += u[3]
            acc += u[3]
            for c, v in u[4].items():
                cur[2][c] = cur[2].get(c, 0) + v
            cur[3].append(u[2])
            if acc >= target * (made + 1) - u[3] / 2 and made < n - 1:   # 累計切點，整塊不拆
                out.append(tuple(cur))
                cur, made = None, made + 1
        out.append(tuple(cur))
        assert sum(1 for d in out if d[0] == reg) == n, (reg, n)
    return out


def single_seats(label, units, n_by_region, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for reg, el, votes, names in districts(units, n_by_region, shift):
        parties = [p for p in votes if p != "其他" and votes[p] > 0]
        groups = voter_groups(label, parties, types)
        _w = lambda s: votes.get(s, 0)
        # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
        finals = _finals_for({p: votes[p] for p in parties}, k, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, groups, _w)[0], POS, withdraw=True)
        w, cyc, _ = pairwise_winner(finals, groups, _w)
        out[w] = out.get(w, 0) + 1
        tot = sum(votes.values())
        stats["循環"] += cyc
        stats["第一偏好過半"] += votes[w] > tot / 2
        stats["非第一偏好第一名當選"] += w != finals[0]
        detail.append((reg, names[0], len(names), w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, env, m_by_region, tiny=6):
    el = electorate(units)
    tot_el = sum(el.values())
    out = {}
    for reg in REGIONS:
        w = {}
        for u in units:
            if u[0] == reg:
                for c, v in u[4].items():
                    w[c] = w.get(c, 0) + v
        for c, v in env.items():                          # 信封票依選舉人數攤
            w[c] = w.get(c, 0) + v * el[reg] / tot_el
        o = w.pop("其他", 0)
        for i in range(tiny):                             # 「其他」視為數張小名單
            w[f"其他{i}"] = o / tiny
        for p, n in sainte_lague(w, m_by_region[reg]).items():
            if n:
                key = "其他" if p.startswith("其他") else p
                out[key] = out.get(key, 0) + n
    return out


def head_of_gov(label, total):
    parties = [p for p, n in total.items() if n and p != "其他"]
    groups = [(p, 1.0, rank_from(label, p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min((P[(w, b)] for b in parties if b != w), default=total[w])
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def national(units, env):
    t = dict(env)
    for u in units:
        for c, v in u[4].items():
            t[c] = t.get(c, 0) + v
    s = sum(t.values())
    return {c: v * 100 / s for c, v in t.items()}


def seats_layout(units):
    el = electorate(units)
    return largest_remainder(el, 70), largest_remainder(el, 50), el


def run(label, types=TYPES, k=3, shift=False, units_env=None):
    units, env, _ = units_env or load(label)
    smd_n, list_m, _ = seats_layout(load("2022-11")[0])     # 選區數固定用 2022 年選舉人數
    smd, stats, detail = single_seats(label, units, smd_n, types, k, shift)
    lst = list_seats(units, env, list_m)
    total = {p: smd.get(p, 0) + lst.get(p, 0) for p in set(smd) | set(lst)}
    return smd, lst, total, stats, detail


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def bloc(total):
    b = sum(v for p, v in total.items() if p in BIBI)
    return b, sum(total.values()) - b


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    smd_n, list_m, el = seats_layout(load("2022-11")[0])
    if "--sweep" in sys.argv:
        print("| 選民類型 | " + " | ".join(ELECTIONS) + " |")
        print("|---|" + "---|" * len(ELECTIONS))
        for name, types in (("基準", TYPES), ("全部重安全", [(1.0, 1.0, 0.4, 0.6, 2.0)]),
                            ("全部重宗教", [(1.0, 0.4, 1.0, 0.6, 2.0)]), ("全部重人物", [(1.0, 0.5, 0.4, 1.0, 2.0)])):
            cells = []
            for label in ELECTIONS:
                smd, _, total, _, _ = run(label, types)
                w, _, _ = head_of_gov(label, total)
                cells.append(f"單一：{fmt(smd)}；首長 {w}")
            print(f"| {name} | " + " | ".join(cells) + " |")
        print()
        for label in ELECTIONS:
            a = run(label, shift=True)
            b = run(label, k=2)
            print(f"{label} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(label, a[2])[0]}")
            print(f"{label} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；首長 {head_of_gov(label, b[2])[0]}")
        return
    if "--projection" in sys.argv:
        label, merge = PROJECTION
        ue = merged(label, merge)
        smd, lst, total, stats, detail = run(label, units_env=ue)
        w, cyc, worst = head_of_gov(label, total)
        print("## 推估（2022 地理，工黨＋梅雷茲＝民主黨）")
        print("單一 70：", fmt(smd), stats)
        print("複數 50：", fmt(lst))
        print("全院 120：", fmt(total), "；Netanyahu 陣營 %d／其他 %d" % bloc(total))
        print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        for sw in (-6, -3, 3, 6):                        # 利庫德均勻擺動，其餘按比例
            def swing(v, sw=sw):
                t = sum(v.values())
                if not t or "利庫德" not in v:
                    return v
                lk = max(0.0, v["利庫德"] + sw / 100 * t)
                rest = t - v["利庫德"]
                return {c: (lk if c == "利庫德" else x * (t - lk) / rest if rest else x) for c, x in v.items()}
            us = [u[:4] + (swing(u[4]),) for u in ue[0]]
            a = run(label, units_env=(us, swing(ue[1]), ue[2]))
            print(f"利庫德 {sw:+d} 點：單一 {fmt(a[0])}；全院 {fmt(a[2])}；首長 {head_of_gov(label, a[2])[0]}")
        return
    print("2022 選舉人（不含信封）：", el)
    print("單一 70 分區：", smd_n, "；複數 50 的 M：", list_m)
    for label in ELECTIONS:
        units, env, _ = load(label)
        smd, lst, total, stats, detail = run(label)
        nat = national(units, env)
        w, cyc, worst = head_of_gov(label, total)
        print(f"\n## {label}")
        print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(nat.items(), key=lambda x: -x[1]) if v >= 0.5))
        print("實際 120：", fmt(ACTUAL[label]), "；Netanyahu 陣營 %d／其他 %d" % bloc(ACTUAL[label]))
        print("單一 70：", fmt(smd), stats)
        print("複數 50：", fmt(lst))
        print("全院 120：", fmt(total), "；Netanyahu 陣營 %d／其他 %d" % bloc(total))
        print(f"行政首長（全院排名投票）：{w}；循環 {cyc}；最弱一場對決 {worst:.0f} 票（≥61 {worst >= 61}）")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者單獨：全院 {total[w]}；複數 {lst.get(w, 0)}")
        for reg in REGIONS:
            c = {}
            for d in detail:
                if d[0] == reg:
                    c[d[3]] = c.get(d[3], 0) + 1
            print(f"    {reg}（{smd_n[reg]}）：{fmt(c)}")
        if "-v" in sys.argv:
            for d in detail:
                print("     ", d[0], d[1], f"({d[2]} 單位)", d[3], "／".join(d[4]), f"{d[5]:.0%}")


if __name__ == "__main__":
    main()
