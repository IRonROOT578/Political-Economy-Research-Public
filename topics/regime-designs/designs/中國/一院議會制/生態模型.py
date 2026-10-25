"""中國一院議會制：預期政治生態的機械效應模型（以意識形態帶為單位）。

把 15-預期政治生態.md 的「得票 → 選制 → 席次」算出來。中國沒有可比的競爭性全國選舉，
所有輸入都是**大膽假設**（見 15 §2）；改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 15 用的數字
    python 生態模型.py --sweep    # 關鍵第二偏好的敏感度

單一席次 260：top-3 孔多賽（第一輪取第一偏好前 3 名；第二輪 6 格完整排序單選，
    孔多賽完成法，循環時 Ranked Pairs，勝方得票）。
複數席次 190：16 區，每區聖拉古，無得票門檻；彈性名單（模型不模擬個人票躍升）。
"""
import random
import sys

S, E, D, T, M, L = "社會保障", "環境與民生", "發展優先", "技術官僚中間", "市場改革", "地方分權"
BANDS = [S, E, D, T, M, L]          # 席次圖由左至右

# 各帶選民的完整排序（比例）。★ 假設：兩軸——國家介入強弱、中央與地方——壓出的鄰近關係。
ORDERS = {
    D: [(0.6, [D, T, S, L, M, E]), (0.4, [D, S, T, E, L, M])],
    S: [(0.5, [S, D, E, T, L, M]), (0.5, [S, E, D, T, L, M])],
    T: [(0.5, [T, M, D, E, S, L]), (0.5, [T, D, M, S, E, L])],
    M: [(0.6, [M, T, L, E, D, S]), (0.4, [M, L, T, E, S, D])],
    L: [(0.5, [L, M, T, E, S, D]), (0.5, [L, M, E, T, D, S])],
    E: [(0.6, [E, S, T, M, L, D]), (0.4, [E, T, M, S, L, D])],
}

# 16 個複數選區（人口，萬，2020 年普查約數）與各帶的區域偏移（百分點，★ 示意）。
# 偏移次序：社保、環境、發展、技術、市場、地方
REGIONS = [
    ("珠三角", 6300, (-3, +1, -6, +2, +5, +3)),
    ("粵東西北＋海南", 7309, (+1, 0, +1, -1, +1, +1)),
    ("山東", 10153, (0, -1, +3, 0, -1, -1)),
    ("河南", 9937, (+3, -2, +4, -2, -2, -1)),
    ("江蘇", 8475, (-2, +1, -2, +2, +3, +1)),
    ("四川＋西藏", 8732, (+1, 0, +1, -1, -1, +2)),
    ("北京＋河北", 9650, (0, +1, +1, +2, 0, -2)),
    ("浙江＋上海", 8944, (-4, +2, -6, +3, +6, +3)),
    ("湖南", 6644, (+2, -1, +3, -1, -2, 0)),
    ("湖北＋江西", 10294, (+2, -1, +2, -1, -1, 0)),
    ("安徽＋福建", 10257, (0, 0, 0, 0, +1, 0)),
    ("廣西＋雲南", 9734, (+2, +1, +1, -2, -2, +1)),
    ("貴州＋重慶", 7061, (+2, 0, +3, -2, -2, 0)),
    ("天津＋山西＋內蒙古", 7284, (+3, -1, +2, 0, -2, -1)),
    ("東北三省", 9851, (+6, -2, +1, -1, -3, -1)),
    ("西北五省區", 10352, (+2, -1, +3, -1, -3, +1)),
]

SMD, PR = 260, 190


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def shifted(fp, lean, rng=None, sd=0.0):
    d = {}
    for b, dl in zip(BANDS, lean):
        noise = rng.gauss(0, sd) if rng else 0.0
        d[b] = max(1.0, fp[b] + dl + noise)
    t = sum(d.values())
    return {k: v * 100 / t for k, v in d.items()}


def condorcet(fp, orders):
    finals = sorted(BANDS, key=lambda b: fp[b], reverse=True)[:3]
    ballots = {}
    for grp, share in fp.items():
        for w, order in orders[grp]:
            r = tuple(b for b in order if b in finals)
            ballots[r] = ballots.get(r, 0) + share * w
    P = {(a, c): sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
         for a in finals for c in finals if a != c}
    for a in finals:
        if all(P[(a, c)] > P[(c, a)] for c in finals if c != a):
            return a, False, finals[0]
    wins = sorted(((P[(a, c)], a, c) for a in finals for c in finals
                   if a != c and P[(a, c)] > P[(c, a)]), reverse=True)
    losers = {c for _, _, c in wins[:2]}
    return next(a for a in finals if a not in losers), True, finals[0]


def single_seats(fp, orders=ORDERS, seed=7):
    rng = random.Random(seed)
    alloc = sainte_lague({r[0]: r[1] for r in REGIONS}, SMD)
    out = {b: 0 for b in BANDS}
    cyc = upset = 0
    for name, _, lean in REGIONS:
        for _ in range(alloc[name]):
            w, c, top = condorcet(shifted(fp, lean, rng, 4.0), orders)
            out[w] += 1
            cyc += c
            upset += (w != top)
    return out, cyc, upset


def list_seats(lst):
    m = sainte_lague({r[0]: r[1] for r in REGIONS}, PR)
    assert all(8 <= v <= 14 for v in m.values()), m
    out = {b: 0 for b in BANDS}
    for name, _, lean in REGIONS:
        for b, n in sainte_lague(shifted(lst, lean), m[name]).items():
            out[b] += n
    return out, m


TERMS = {
    # 屆: (單一席次第一偏好, 名單得票)；★ 見 15 §2.2
    3: ({S: 19, E: 9, D: 33, T: 15, M: 14, L: 10},
        {S: 18, E: 11, D: 30, T: 15, M: 15, L: 11}),
    5: ({S: 18, E: 10, D: 30, T: 16, M: 15, L: 11},
        {S: 17, E: 12, D: 28, T: 16, M: 16, L: 11}),
}


def run(t, orders=ORDERS):
    fp, lst = TERMS[t]
    sm, cyc, upset = single_seats(fp, orders)
    pr, m = list_seats(lst)
    return sm, pr, cyc, upset, m


def compare_rules():
    """某些議員取不同範圍時，政府怎麼組（見 02 §2.1）。"""
    import importlib.util as iu, pathlib
    tool = pathlib.Path(__file__).resolve().parents[5] / "shared" / "tools" / "組閣比較.py"
    spec = iu.spec_from_file_location("組閣比較", tool)
    cmp = iu.module_from_spec(spec)
    spec.loader.exec_module(cmp)
    for t in TERMS:
        sm, pr, _, _, _ = run(t)
        full = {b: sm[b] + pr[b] for b in BANDS}
        rows = cmp.compare([("甲 全院 450", {k: v for k, v in full.items() if v}, 226),
                            ("乙 單一 260", {k: v for k, v in sm.items() if v}, 131)], BANDS)
        print(f"第 {t} 屆")
        print(cmp.table(rows))
        lead = max(full, key=full.get)
        print(f"  其餘各帶合計：全院 {450 - full[lead]}／226；單一 {260 - sm[lead]}／131（不論是否相鄰）")
        print()


def main():
    if "--某些議員" in sys.argv:
        compare_rules()
        return
    if "--sweep" in sys.argv:
        fp, _ = TERMS[3]
        print("| 發展優先選民把技術官僚排第二的比例 | 單一 260：發展／技術／社保 |")
        print("|:--:|:--:|")
        for share in (0.3, 0.45, 0.6, 0.75, 0.9):
            o = dict(ORDERS)
            o[D] = [(share, [D, T, S, L, M, E]), (1 - share, [D, S, T, E, L, M])]
            sm, _, _ = single_seats(fp, o)
            print(f"| {share:.0%} | {sm[D]}／{sm[T]}／{sm[S]} |")
        print()
        print("| 社會保障選民把發展優先排第二的比例 | 單一 260：發展／技術／社保 |")
        print("|:--:|:--:|")
        for share in (0.3, 0.5, 0.7, 0.9):
            o = dict(ORDERS)
            o[S] = [(share, [S, D, E, T, L, M]), (1 - share, [S, E, D, T, L, M])]
            sm, _, _ = single_seats(fp, o)
            print(f"| {share:.0%} | {sm[D]}／{sm[T]}／{sm[S]} |")
        return
    for t in TERMS:
        sm, pr, cyc, upset, m = run(t)
        full = {b: sm[b] + pr[b] for b in BANDS}
        print(f"第 {t} 屆 單一 260：{sm}（循環 {cyc}；當選者非第一偏好最多者 {upset}）")
        print(f"    複數 190：{pr}")
        print(f"    全院 450：{full}")
    print("複數各區 M：", run(3)[4])
    print("單一各區：", sainte_lague({r[0]: r[1] for r in REGIONS}, SMD))


if __name__ == "__main__":
    main()
