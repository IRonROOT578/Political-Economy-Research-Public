"""日本一院議會制：預期政治生態的機械效應模型。

把 12-預期政治生態.md 與 14-近期大選重算.md 的「得票 → 選制 → 席次 → 行政首長」算出來。
偏好位置是**假設**（見 12 §2），改假設就重跑，不要手改表。

    python 生態模型.py              # 2024-10、2021-10 眾議院重算
    python 生態模型.py --sweep      # 敏感度

得票：總務省「市區町村別得票數」的**比例代表**政黨票（跨小選舉區的市區已按選區拆開），彙整成 資料/shugiin-YYYY.csv；
每列依名稱對到現行小選舉區，作為地理順序（2024 年 3 列、2021 年 26 列對不上，歸到前一列的選區）。
第一偏好用比例票，避開小選舉區層的在野協調與公明黨不推人。
單一 280：依 2024 有效票分到 47 都道府縣（最大餘數，每縣至少 1），縣內依「現行小選舉區序 → 原列序」
連續切成有效票相近的選區；top-3 孔多賽，循環 Ranked Pairs，平手以排第一者多為先。
複數 185：以 11 個比例區為底，合併或拆成 16 區，聖拉古，無法定門檻，M∈[8,16]。
偏好：四維空間（經濟：重分配 −1 … 市場 +1；安保與憲法：鴿 −1 … 鷹 +1；建制：反建制、改革 −1 … 建制 +1；
組織宗教：公明黨 1、其餘 0）。
每黨選民分四型。行政首長：全院 465 記名排名投票；須 ≥233 排在「維持空缺」之上。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (經濟, 安保與憲法, 建制, 組織宗教)。第四軸只有公明黨是 1：它的選民是組織化的宗教票，其他選民很少把它當第二偏好。
POS = {
    "自民": (0.5, 0.7, 0.9, 0), "公明": (0.0, 0.0, 0.8, 1), "立憲": (-0.5, -0.6, 0.4, 0), "國民": (0.1, 0.2, 0.1, 0),
    "維新": (0.6, 0.5, -0.2, 0), "共產": (-0.9, -0.9, -0.3, 0), "令和": (-0.9, -0.5, -0.9, 0), "參政": (0.2, 0.8, -0.9, 0),
    "社民": (-0.8, -0.9, -0.2, 0), "保守": (0.6, 1.0, -0.6, 0),
    # 2026 新黨（假設）：中道改革連合＝立憲與公明的眾院合流，取兩者之間、帶一半組織宗教；未來＝チームみらい，科技中間、反建制
    "中道": (-0.3, -0.35, 0.55, 0.4), "未來": (0.2, -0.2, -0.5, 0),
}
OVERRIDE = {}
RELIGION = 1.2                      # 組織宗教軸的權重（12 §6 敏感度）
TYPES = [(0.25, 1.0, 0.5, 0.5, RELIGION), (0.25, 0.5, 1.0, 0.5, RELIGION), (0.25, 0.5, 0.5, 1.0, RELIGION),
         (0.25, 0.8, 0.8, 0.8, RELIGION)]
BALANCED = (0.8, 0.8, 0.8, RELIGION)
CURRENT = [2024]
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県",
         "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県",
         "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県",
         "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
LIST_GROUPS = [
    ("北海道–東北", ("北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"), 2),
    ("北關東", ("茨城県", "栃木県", "群馬県", "埼玉県"), 2),
    ("南關東", ("千葉県", "神奈川県", "山梨県"), 2),
    ("東京", ("東京都",), 2),
    ("北陸信越", ("新潟県", "富山県", "石川県", "福井県", "長野県"), 1),
    ("東海", ("岐阜県", "静岡県", "愛知県", "三重県"), 2),
    ("近畿", ("滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"), 2),
    ("中國–四國", ("鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県"), 1),
    ("九州", ("福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"), 2),
]
ACTUAL = {
    2026: {"自民": 316, "中道": 49, "維新": 36, "國民": 28, "參政": 15, "未來": 11, "共產": 4, "令和": 1, "其他": 5},
    2024: {"自民": 191, "立憲": 148, "維新": 38, "國民": 28, "公明": 24, "令和": 9, "共產": 8, "參政": 3, "保守": 3, "社民": 1, "其他": 12},
    2021: {"自民": 259, "立憲": 96, "維新": 41, "公明": 32, "國民": 11, "共產": 10, "令和": 3, "社民": 1, "其他": 12},
}


def pos(p):
    return OVERRIDE.get(CURRENT[0], {}).get(p, POS[p])


def load(year):
    with open(os.path.join(HERE, "資料", f"shugiin-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][5:]
    return [(r[0], PREFS.index(r[0]) * 1000 + int(r[1]), int(r[2]), r[3], int(r[4]),
             {c: int(v) for c, v in zip(cols, r[5:])}) for r in rows[1:]]


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
    a = pos(me)
    return sorted(cands, key=lambda c: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, pos(c), a)), c))


def voter_groups(parties, types=TYPES):
    return [(p, t[0], rank_from(p, parties, t[1:])) for p in parties for t in types]


def pairwise_winner(cands, groups, weight):
    cands = sorted(cands)
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
    top = [c for c in cands if not any(t == c for _, t in locked)] or list(cands)
    if len(top) > 1:                     # 平手：把他排第一的票較多者為先
        first = {c: 0.0 for c in top}
        for src, w, order in groups:
            r = [c for c in order if c in cands]
            if r and r[0] in first:
                first[r[0]] += weight(src) * w
        top.sort(key=lambda c: (-first[c], c))
    return top[0], True, P


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
    while not out[-1] and len(out) > 1 and len(out[-2]) > 1:
        out[-1].append(out[-2].pop())
    assert len(out) == n and all(out)
    return out


def order(units):
    return sorted(units, key=lambda u: (u[1], u[2]))


def layout():
    units = load(2024)
    by = {}
    for u in units:
        by[u[0]] = by.get(u[0], 0) + u[4]
    smd = largest_remainder(by, 280, floor=1)
    regions = []
    for name, regs, k in LIST_GROUPS:
        rows = order([u for u in units if u[0] in regs])
        parts = cut(rows, k) if k > 1 else [rows]
        for i, part in enumerate(parts):
            regions.append((name if k == 1 else f"{name}{'一二'[i]}", regs, sum(u[4] for u in part)))
    m = largest_remainder({r[0]: r[2] for r in regions}, 185)
    return smd, [(r[0], r[1], m[r[0]]) for r in regions]


SMD_N, LIST_REGIONS = layout()
LIST_M = {r[0]: r[2] for r in LIST_REGIONS}


def single_seats(units, types=TYPES, k=3, shift=False):
    out, detail = {}, []
    stats = {"循環": 0, "第一偏好過半": 0, "非第一偏好第一名當選": 0}
    for reg, n in sorted(SMD_N.items()):
        for part in cut(order([u for u in units if u[0] == reg]), n, shift):
            votes = {}
            for u in part:
                for c, v in u[5].items():
                    votes[c] = votes.get(c, 0) + v
            parties = sorted(p for p in votes if p in POS and votes[p] > 0)
            finals = sorted(parties, key=lambda p: (-votes[p], p))[:k]
            w, cyc, _ = pairwise_winner(finals, voter_groups(parties, types), lambda s: votes.get(s, 0))
            out[w] = out.get(w, 0) + 1
            tot = sum(votes.values())
            stats["循環"] += cyc
            stats["第一偏好過半"] += votes[w] > tot / 2
            stats["非第一偏好第一名當選"] += w != finals[0]
            detail.append((reg, part[0][3], len(part), w, finals, votes[w] / tot))
    return out, stats, detail


def list_seats(units, tiny=6):
    out, acc, done = {}, {}, set()
    for name, regs, m in LIST_REGIONS:
        if regs in done:
            continue
        done.add(regs)
        parts = [r for r in LIST_REGIONS if r[1] == regs]
        rows = order([u for u in units if u[0] in regs])
        chunks = cut(rows, len(parts)) if len(parts) > 1 else [rows]
        for (pname, _, _), chunk in zip(parts, chunks):
            acc[pname] = {}
            for u in chunk:
                for c, v in u[5].items():
                    acc[pname][c] = acc[pname].get(c, 0) + v
    for name, _, m in LIST_REGIONS:
        d = dict(acc[name])
        o = d.pop("其他", 0)
        for i in range(tiny):
            d[f"其他{i}"] = o / tiny
        for p, n in sainte_lague(d, m).items():
            if n:
                key = "其他" if p.startswith("其他") else p
                out[key] = out.get(key, 0) + n
    return out


def head_of_gov(total):
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    worst = min(P[(w, b)] for b in parties if b != w)
    head_of_gov.last = {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}
    return w, cyc, worst


def coalition(total, pm, need=233):
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, pos(p), pos(pm))) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def run(year, types=TYPES, k=3, shift=False, units=None):
    CURRENT[0] = year
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


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: (-x[1], x[0])) if v)


def report(label, year, units):
    smd, lst, total, stats, detail = run(year, units=units)
    w, cyc, worst = head_of_gov(total)
    seq, acc = coalition(total, w)
    print(f"\n## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sorted(national(units).items(), key=lambda x: -x[1])))
    print("實際 465：", fmt(ACTUAL[year]))
    print("單一 280：", fmt(smd), stats)
    print("複數 185：", fmt(lst))
    print("全院 465：", fmt(total))
    print(f"行政首長：{w}；循環 {cyc}；最弱 {worst:.0f}（≥233 {worst >= 233}）")
    print("    對決：", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in head_of_gov.last.items()))
    print(f"    組閣陣營（由近到遠）：{'＋'.join(f'{p} {total[p]}' for p in seq)}＝{acc}")
    by = {}
    for d in detail:
        by.setdefault(d[0], {}).setdefault(d[3], 0)
        by[d[0]][d[3]] += 1
    print("    各區單一：", "；".join(f"{r}（{SMD_N[r]}）{fmt(c)}" for r, c in sorted(by.items())))
    combos = {}
    for d in detail:
        key = "／".join(sorted(d[4]))
        combos[key] = combos.get(key, 0) + 1
    print("    決選三人：", sorted(combos.items(), key=lambda x: -x[1])[:6])
    sh = sorted(d[5] for d in detail)
    print(f"    當選者第一偏好：中位 {sh[len(sh) // 2]:.0%}、最低 {sh[0]:.0%}")


def swing(units, party, pts):
    out = []
    for u in units:
        t = sum(u[5].values())
        v = u[5].get(party, 0)
        nv = max(0.0, v + pts / 100 * t)
        rest = t - v
        out.append(u[:5] + ({c: (nv if c == party else x * (t - nv) / rest if rest else x) for c, x in u[5].items()},))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if "--sweep" in sys.argv:
        for name, types in (("全部重經濟", [(1.0, 1.0, 0.5, 0.5, RELIGION)]), ("全部重安保", [(1.0, 0.5, 1.0, 0.5, RELIGION)]),
                            ("全部重建制", [(1.0, 0.5, 0.5, 1.0, RELIGION)]), ("全部均衡", [(1.0, 0.8, 0.8, 0.8, RELIGION)]),
                            ("組織宗教軸權重 0（無此軸）", [(t[0], *t[1:4], 0.0) for t in TYPES]),
                            ("組織宗教軸權重 2.0", [(t[0], *t[1:4], 2.0) for t in TYPES])):
            for year in (2024, 2021):
                smd, _, total, _, _ = run(year, types)
                print(f"{name} {year}：單一 {fmt(smd)}；首長 {head_of_gov(total)[0]}")
        for year in (2024, 2021):
            a = run(year, shift=True)
            b = run(year, k=2)
            print(f"{year} 切點平移半區：單一 {fmt(a[0])}；首長 {head_of_gov(a[2])[0]}")
            print(f"{year} 兩輪多數決（前 2 名對決）：單一 {fmt(b[0])}；全院 {fmt(b[2])}；首長 {head_of_gov(b[2])[0]}")
        for pts in (-6, -3, 3, 6):
            smd, lst, total, _, _ = run(2024, units=swing(load(2024), "自民", pts))
            print(f"2024 自民 {pts:+d} 點：單一 {fmt(smd)}；全院 {fmt(total)}；首長 {head_of_gov(total)[0]}")
        return
    print("單一 280 各都道府縣：", SMD_N)
    print("複數 185 各區 M：", LIST_M)
    for year in (2026, 2024, 2021):
        report(f"{year}", year, load(year))


if __name__ == "__main__":
    main()
