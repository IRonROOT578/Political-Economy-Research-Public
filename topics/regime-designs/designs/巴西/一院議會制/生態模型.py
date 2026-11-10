"""巴西一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2026-10、2022-10 眾議院重算；2018、2022、2026 總統 top-3 反事實
    python 生態模型.py --sweep      # 敏感度
    python 生態模型.py --projection # 推估第 3 屆

得票：高等選舉法院（TSE）逐市鎮×選舉區（munzona）的聯邦眾議員得票，彙整成 資料/camara-YYYY.csv：
小市鎮一個單位，有效票逾 15 萬且有多個選舉區的大城市每個選舉區一個單位。政黨聯盟（federação）併計。
單一 300：依 2026 有效票分到 27 州（最大餘數，每州至少 1），州內沿市鎮座標的希爾伯特曲線連續切成
有效票相近的選區（同城各選舉區依編號）；top-3 孔多賽，循環用 Ranked Pairs。
複數 213：18 區（以州為積木，大州拆、小州併），聖拉古，無法定門檻，M∈[8,16]。
偏好：二維空間（陣營：Lula −1 … Bolsonaro +1；政治風格：綱領型 −1 … 恩庇、中間大團 +1）。
每黨選民分三型（重陣營、重風格、均衡）。
行政首長：全院 513 記名排名投票，議員依所屬政黨的均衡型排序；孔多賽完成法；須 ≥257 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 總統民意 import president as _president, fmt as _pfmt  # noqa: E402
from 參選判定 import finals_for as _finals_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# (陣營, 風格)。位置是假設（12 §2.1）。
POS = {
    "PSOL": (-1.0, -0.6), "PT": (-0.9, -0.2), "PDT": (-0.5, 0.0), "PSB": (-0.5, 0.1),
    "PSDB": (0.0, -0.1), "MDB": (-0.1, 0.6), "PSD": (0.0, 0.7), "AVANTE": (0.0, 0.6),
    "PODE": (0.3, 0.4), "União": (0.3, 0.7), "PP": (0.5, 0.8), "União–PP": (0.4, 0.75),
    "REP": (0.6, 0.5), "PRD": (0.5, 0.6), "MISSÃO": (0.6, -0.6), "NOVO": (0.8, -0.7), "PL": (1.0, 0.0),
}
TYPES = [(0.40, 1.0, 0.3), (0.25, 0.7, 1.0), (0.35, 1.0, 0.7)]
BALANCED = (1.0, 0.7)
CENTRAO = {"PSD", "MDB", "União", "PP", "União–PP", "REP", "PODE", "AVANTE", "PRD"}
LEFT = {"PT", "PSOL", "PSB", "PDT"}

# 複數席次 18 區：(區名, 州, 拆成幾區)
LIST_GROUPS = [
    ("西北", ("AM", "RR", "AC", "RO", "MT"), 1), ("帕拉", ("PA", "AP"), 1), ("中西", ("GO", "DF", "TO"), 1),
    ("馬拉尼昂–皮奧伊", ("MA", "PI"), 1), ("塞阿拉", ("CE",), 1), ("北里奧格蘭德–帕拉伊巴", ("RN", "PB"), 1),
    ("伯南布哥", ("PE",), 1), ("巴伊亞–塞爾希培–阿拉戈斯", ("BA", "SE", "AL"), 2),
    ("米納斯–聖埃斯皮里圖", ("MG", "ES"), 2), ("里約", ("RJ",), 1), ("聖保羅", ("SP",), 3),
    ("巴拉那–南馬托格羅索", ("PR", "MS"), 1), ("南大河–聖卡塔琳娜", ("RS", "SC"), 2),
]
# 實際席次（513，開放名單、州為選區）
ACTUAL = {
    2026: {"PL": 121, "PT": 88, "União–PP": 87, "PSD": 43, "REP": 41, "MDB": 36, "PODE": 27, "其他": 70},
    2022: {"PL": 99, "PT": 80, "União": 59, "PP": 47, "PSD": 42, "MDB": 42, "REP": 41, "其他": 103},
}
# 總統第一輪（候選人所屬政黨的全國有效票）與實際決選
PRES = {
    2018: ({"PL": 49277010, "PT": 31342051, "PDT": 13344371, "PSDB": 5096350, "NOVO": 2679745, "PRD": 1348323,
            "MDB": 1288950, "PSOL": 1069578 + 617122, "PODE": 859601}, ("PL", "PT", 55.13)),
    2022: ({"PT": 57259504, "PL": 51072345, "MDB": 4915423, "PDT": 3599287, "União": 600955, "NOVO": 559708},
           ("PT", "PL", 50.90)),
    2026: ({"PL": 56104503, "PT": 53879538, "AVANTE": 3448569, "MISSÃO": 2675887, "PSD": 2605148, "NOVO": 326488},
           ("PT", "PL", 51.79)),
}
PRES_LIST = {2022: 2022, 2026: 2026}   # 總統主版用同日眾議院名單票（2018 沒有逐區名單票資料，只有對照）


def load(year):
    with open(os.path.join(HERE, "資料", f"camara-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][7:]
    return [(r[0], hilbert(float(r[4]), float(r[5])), int(r[2]), r[3], int(r[6]), {c: int(v) for c, v in zip(cols, r[7:])})
            for r in rows[1:]]


def hilbert(lon, lat, order=12):
    """經緯度 → 希爾伯特曲線序號（巴西框 −74…−34、−34…6）。"""
    n = 1 << order
    xi = min(n - 1, max(0, int((lon + 74) / 40 * n)))
    yi = min(n - 1, max(0, int((lat + 34) / 40 * n)))
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


def largest_remainder(weights, seats, floor=0):
    got = {k: floor for k in weights}
    rest = seats - floor * len(weights)
    tot = sum(weights.values())
    q = {k: v * rest / tot for k, v in weights.items()}
    for k in q:
        got[k] += int(q[k])
    for k in sorted(q, key=lambda k: q[k] - int(q[k]), reverse=True)[:seats - sum(got.values())]:
        got[k] += 1
    return got


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def rank_from(me, cands, w):
    a = POS[me]
    return sorted(cands, key=lambda c: sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, POS[c], a)))


def voter_groups(parties, types=TYPES):
    return [(p, t[0], rank_from(p, parties, t[1:])) for p in parties for t in types]


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


def cut(rows, n, shift=False):
    """依排序把 rows 連續切成 n 段有效票相近的組。rows：已排序的單位。"""
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
    assert len(out) == n
    return out


def order(units):
    return sorted(units, key=lambda u: (u[1], u[2]))


def layout():
    """單一 300 的州配額、複數 213 的區與 M（固定用 2026 有效票）。"""
    units = load(2026)
    by_uf = {}
    for u in units:
        by_uf[u[0]] = by_uf.get(u[0], 0) + u[4]
    smd = largest_remainder(by_uf, 300, floor=1)
    regions = []
    for name, ufs, k in LIST_GROUPS:
        rows = order([u for u in units if u[0] in ufs])
        parts = cut(rows, k) if k > 1 else [rows]
        for i, part in enumerate(parts):
            regions.append((name if k == 1 else f"{name}{'一二三'[i]}", {(u[0], u[3], u[2]) for u in part},
                            sum(u[4] for u in part)))
    m = largest_remainder({r[0]: r[2] for r in regions}, 213)
    return smd, [(r[0], r[1], m[r[0]]) for r in regions]


SMD_N, LIST_REGIONS = layout()


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for uf, n in SMD_N.items():
        for part in cut(order([u for u in units if u[0] == uf]), n, shift):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    votes[c] = votes.get(c, 0) + v
            parties = [p for p in votes if p in POS and votes[p] > 0]
            _g = voter_groups(parties, types)
            _w = lambda s: votes.get(s, 0)
            # 參選方層：新制誘因下相鄰政黨的共同提名（shared/tools/參選判定.py；notes/算法/選舉結果計算方式.md）
            finals = _finals_for({p: votes[p] for p in parties}, k, lambda f: f[0] if len(f) == 1 else pairwise_winner(f, _g, _w)[0], POS, withdraw=True)
            w, cyc, _ = pairwise_winner(finals, _g, _w)
            out[w] = out.get(w, 0) + 1
            tot = sum(votes.values())
            stats["循環"] += cyc
            stats["第一偏好過半"] += votes[w] > tot / 2
            stats["非第一偏好第一名當選"] += w != finals[0]
            detail.append((uf, part[0][3], len(part), w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, tiny=8):
    where = {}
    for name, members, m in LIST_REGIONS:
        for key in members:
            where[key] = name
    w = {name: {} for name, _, _ in LIST_REGIONS}
    for u in units:
        reg = where.get((u[0], u[3], u[2]))
        if reg is None:                                # 2022 年的單位對不上 2026 的區界：歸到同州第一個區
            reg = next(n for n, mem, _ in LIST_REGIONS if any(k[0] == u[0] for k in mem))
        for c, v in u[5].items():
            w[reg][c] = w[reg].get(c, 0) + v
    out = {}
    for name, _, m in LIST_REGIONS:
        d = dict(w[name])
        o = d.pop("其他", 0)
        for i in range(tiny):
            d[f"其他{i}"] = o / tiny
        for p, n in sainte_lague(d, m).items():
            if n:
                key = "其他" if p.startswith("其他") else p
                out[key] = out.get(key, 0) + n
    return out


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p in POS]
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min(P[(w, b)] for b in parties if b != w)
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def run(year, types=TYPES, k=3, shift=False, units=None):
    units = units or load(year)
    smd, stats, detail = single_seats(units, types, k, shift)
    lst = list_seats(units)
    total = {p: smd.get(p, 0) + lst.get(p, 0) for p in set(smd) | set(lst)}
    return smd, lst, total, stats, detail


def national(units):
    t = {}
    for u in units:
        for c, v in u[5].items():
            t[c] = t.get(c, 0) + v
    s = sum(t.values())
    return {c: v * 100 / s for c, v in t.items()}


def presidential_list(fp, types=TYPES):
    """總統主版（notes/算法/選舉結果計算方式.md）：民意層＝國會名單票（同日眾議院名單票），政黨層級，不用現實總統第一輪、
    不用個別候選人；參選方層＝每黨可推人，參選判定.finalists 決定相鄰政黨的共同提名；前 3 名孔多賽。"""
    fp = {p: v for p, v in fp.items() if p in POS and v > 0}
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(POS[a], POS[b])) ** 0.5
    return _president(fp, lambda parties, cands: voter_groups(parties, types), dist, POS, withdraw=True)

def presidential(year, types=TYPES):
    fp, (a, b, actual_a) = PRES[year]
    finals = sorted(fp, key=fp.get, reverse=True)[:3]
    groups = voter_groups(list(fp), types)
    w, cyc, P = pairwise_winner(finals, groups, lambda s: fp.get(s, 0))
    ab = P[(a, b)] / (P[(a, b)] + P[(b, a)]) * 100
    return finals, w, P, ab, actual_a


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def blocs(total):
    c = sum(v for p, v in total.items() if p in CENTRAO)
    l = sum(v for p, v in total.items() if p in LEFT)
    r = sum(v for p, v in total.items() if p in ("PL", "NOVO", "MISSÃO"))
    return f"左 {l}／中間大團 {c}／右 {r}"


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        out.append(u[:5] + ({c: (nv if c == party else x * (t - nv) / rest if rest else x) for c, x in u[5].items()},))
    return out


def merge(units, mapping):
    out = []
    for u in units:
        d = {}
        for c, v in u[5].items():
            k = mapping.get(c, c)
            d[k] = d.get(k, 0) + v
        out.append(u[:5] + (d,))
    return out


def shift(units, gains, donors=CENTRAO):
    """gains＝{黨: 百分點}，從 donors 按比例扣。用於「新制下中間大團的地方機器變弱」的推估。"""
    out = []
    for u in units:
        t = sum(u[5].values())
        d = dict(u[5])
        need = sum(gains.values()) / 100 * t
        pool = sum(v for c, v in d.items() if c in donors)
        take = min(need, pool * 0.9)
        for c in d:
            if c in donors and pool:
                d[c] -= take * d[c] / pool
        for c, pts in gains.items():
            d[c] = d.get(c, 0) + take * pts / sum(gains.values())
        out.append(u[:5] + (d,))
    return out


# 推估第 3 屆（12 §2.3）：2026 地理；議員修正案廢除後，中間大團的地方機器變弱，
# PT 與 PL 各從中間大團拿回 4 點（按比例）。
PROJECTION = {"PT": 4, "PL": 4}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if "--sweep" in sys.argv:
        for name, types in (("全部重陣營", [(1.0, 1.0, 0.3)]), ("全部重風格", [(1.0, 0.7, 1.0)]), ("全部均衡", [(1.0, 1.0, 0.7)])):
            for year in (2026, 2022):
                smd, _, total, _, _ = run(year, types)
                print(f"{name} {year}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for year in (2026, 2022):
            a = run(year, shift=True)
            b = run(year, k=2)
            print(f"{year} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{year} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for pts in (-6, -3, 3, 6):
            u = swing(load(2026), "PL", pts)
            smd, lst, total, _, _ = run(2026, units=u)
            print(f"2026 PL {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        for pts in (4, 8, 12):
            u = shift(load(2026), {"PT": pts, "PL": pts})
            smd, lst, total, _, _ = run(2026, units=u)
            print(f"2026 PT、PL 各從中間大團拿 {pts} 點：單一 {fmt(smd)}；全院 {fmt(total)}；{blocs(total)}；首長 {head_of_gov(total)[0]}")
        return
    if "--projection" in sys.argv:
        u = shift(load(2026), PROJECTION)
        smd, lst, total, stats, detail = run(2026, units=u)
        w, cyc, worst = head_of_gov(total)
        print("## 推估第 3 屆")
        print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(u).items(), key=lambda x: -x[1])))
        print("單一 300：", fmt(smd), stats)
        print("複數 213：", fmt(lst))
        print("全院 513：", fmt(total), "；", blocs(total))
        print(f"首長：{w}；循環 {cyc}；最弱 {worst:.0f}")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者：全院 {total[w]}、複數 {lst.get(w, 0)}；中間大團複數 {sum(v for p, v in lst.items() if p in CENTRAO)}")
        return
    print("單一 300 州配額：", SMD_N)
    print("複數 213 區與 M：", [(n, m) for n, _, m in LIST_REGIONS])
    for year in (2026, 2022):
        units = load(year)
        smd, lst, total, stats, detail = run(year)
        w, cyc, worst = head_of_gov(total)
        print(f"\n## {year}")
        print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
        print("實際 513：", fmt(ACTUAL[year]))
        print("單一 300：", fmt(smd), stats)
        print("複數 213：", fmt(lst))
        print("全院 513：", fmt(total), "；", blocs(total))
        print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥257 {worst >= 257}）")
        print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
        print(f"    勝者：全院 {total[w]}、複數 {lst.get(w, 0)}；PL 複數 {lst.get('PL', 0)}、PT 複數 {lst.get('PT', 0)}")
        by = {}
        for d in detail:
            by.setdefault(d[0], {}).setdefault(d[3], 0)
            by[d[0]][d[3]] += 1
        print("    各州單一：", "；".join(f"{uf} {fmt(c)}" for uf, c in sorted(by.items())))
        if "-v" in sys.argv:
            for d in detail:
                print("     ", d[0], d[1], f"({d[2]})", d[3], "／".join(d[4]), f"{d[5]:.0%}")
    print("\n## 總統（主版：同日眾議院名單票 × 參選方層）")
    for year, ly in PRES_LIST.items():
        fp = national(load(ly))
        print(f"{year}：{_pfmt(presidential_list(fp), fp)}")
    print("\n## 總統 對照：現實第一輪（受棄保影響，政黨層級）")
    for year in PRES:
        finals, w, P, ab, actual = presidential(year)
        print(f"{year}：決選 {'、'.join(finals)}；孔多賽勝者 {w}；"
              + "、".join(f"{a} 對 {b} {P[(a, b)] / (P[(a, b)] + P[(b, a)]):.1%}" for a in finals for b in finals if a < b)
              + f"；模型決選 {ab:.1f}%（實際 {actual}%）")


if __name__ == "__main__":
    main()
