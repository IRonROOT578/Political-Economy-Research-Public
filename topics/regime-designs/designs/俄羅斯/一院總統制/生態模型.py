"""俄羅斯一院總統制：預期政治生態的機械效應模型。

把 16-預期政治生態.md 的「得票 → 選制 → 結果」算出來。所有輸入都是**假設**（見 16 §2），
出發點是官方公布的 2021 年杜馬與 2024 年總統選舉數字——那些數字本身有爭議，本檔只拿來定量級。
改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 16 用的數字
    python 生態模型.py --sweep    # 統一俄羅斯得票的敏感度

單一席次 180：top-3 孔多賽（第一輪取第一偏好前 3 名，第二輪對三人跑孔多賽完成法；
循環時 Ranked Pairs，完整排序下勝方得票與勝差等價）。複數 120：11 區，聖拉古法，無全國門檻。
"""
import random
import sys

UR, KP, LD, SR, NP, OT = "統一俄羅斯", "俄羅斯聯邦共產黨", "俄羅斯自由民主黨", "公正俄羅斯", "新人", "其他"
PARTIES = [UR, KP, LD, SR, NP]

# 各黨選民的完整排序（比例）。「其他」的選民（亞博盧等）沒有自己的候選人進前 3。
ORDERS = {
    UR: [(0.5, [UR, LD, NP, SR, KP]), (0.3, [UR, SR, LD, NP, KP]), (0.2, [UR, NP, LD, SR, KP])],
    KP: [(0.6, [KP, SR, LD, NP, UR]), (0.25, [KP, LD, SR, UR, NP]), (0.15, [KP, UR, SR, LD, NP])],
    LD: [(0.5, [LD, UR, NP, KP, SR]), (0.5, [LD, KP, SR, NP, UR])],
    SR: [(0.6, [SR, KP, LD, NP, UR]), (0.4, [SR, UR, KP, LD, NP])],
    NP: [(0.5, [NP, UR, LD, SR, KP]), (0.5, [NP, SR, KP, LD, UR])],
    OT: [(0.7, [NP, SR, KP, LD, UR]), (0.3, [KP, SR, NP, LD, UR])],
}

# 11 個名單區：名稱、人口（萬，約）、統一俄羅斯得票相對全國的偏移（百分點，示意）
REGIONS = [
    ("莫斯科市", 1310, -15),
    ("中部北", 1400, -4),
    ("中部南", 1400, +2),
    ("西北", 1350, -8),
    ("伏爾加西", 1340, +10),
    ("伏爾加東", 1560, -3),
    ("南部", 1500, +3),
    ("北高加索", 1000, +30),
    ("烏拉爾", 1220, -2),
    ("西伯利亞西", 1070, -7),
    ("西伯利亞東與遠東", 1600, -5),
]


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


def dhondt(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (got[x] + 1))
        got[k] += 1
    return got


def shift(fp, lean):
    """統一俄羅斯加減 lean，其餘各黨依比例吸收。"""
    d = dict(fp)
    rest = sum(v for k, v in d.items() if k != UR)
    d[UR] = max(5.0, d[UR] + lean)
    scale = (100 - d[UR]) / rest
    for k in d:
        if k != UR:
            d[k] *= scale
    return d


def condorcet(fp):
    """fp：第一偏好（含「其他」）。回傳 (當選者, 是否循環, 前三名)。"""
    finals = sorted(PARTIES, key=lambda p: fp.get(p, 0), reverse=True)[:3]
    ballots = {}
    for grp, share in fp.items():
        for w, order in ORDERS[grp]:
            r = tuple(p for p in order if p in finals)
            ballots[r] = ballots.get(r, 0) + share * w
    P = {(a, c): sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
         for a in finals for c in finals if a != c}
    for a in finals:
        if all(P[(a, c)] > P[(c, a)] for c in finals if c != a):
            return a, False, finals
    wins = sorted(((P[(a, c)], a, c) for a in finals for c in finals
                   if a != c and P[(a, c)] > P[(c, a)]), reverse=True)
    losers = {c for _, _, c in wins[:2]}
    return next(a for a in finals if a not in losers), True, finals


def single_seats(fp, seed=11):
    rng = random.Random(seed)
    seats = largest_remainder({r[0]: r[1] for r in REGIONS}, 180)
    out = {p: 0 for p in PARTIES}
    cyc = 0
    for name, _, lean in REGIONS:
        for _ in range(seats[name]):
            d = shift(fp, rng.gauss(lean, 8.0))
            w, c, _ = condorcet(d)
            out[w] += 1
            cyc += c
    return out, cyc


TERMS = {
    # 屆: (區域第一偏好, 名單得票)；其他＝亞博盧、退休者黨等，名單上分散成多張小名單
    3: ({UR: 48, KP: 19, LD: 8, SR: 8, NP: 7, OT: 10},
        {UR: 47, KP: 19, LD: 8, SR: 8, NP: 7, OT: 11}),
    5: ({UR: 45, KP: 18, LD: 8, SR: 8, NP: 10, OT: 11},
        {UR: 44, KP: 18, LD: 8, SR: 8, NP: 10, OT: 12}),
    8: ({UR: 42, KP: 17, LD: 7, SR: 8, NP: 14, OT: 12},
        {UR: 41, KP: 17, LD: 7, SR: 8, NP: 14, OT: 13}),
}


def split_other(lst, k=6):
    """把「其他」拆成 k 張小名單，各自分配。"""
    d = {p: v for p, v in lst.items() if p != OT}
    for i in range(k):
        d[f"其他{i}"] = lst[OT] / k
    return d


def run(t, formula=None):
    formula = formula or sainte_lague
    dfp, lst = TERMS[t]
    s, cyc = single_seats(dfp)
    shares = split_other(lst)
    m = largest_remainder({r[0]: r[1] for r in REGIONS}, 120)
    assert all(8 <= v <= 14 for v in m.values()), m
    l = {p: 0 for p in shares}
    for name, _, lean in REGIONS:
        for p, n in formula(shift(shares, lean), m[name]).items():
            l[p] += n
    other = sum(v for k, v in l.items() if k.startswith("其他"))
    l = {k: v for k, v in l.items() if not k.startswith("其他")}
    l["其他"] = other
    return s, cyc, l, m


ORDER = [KP, SR, NP, UR, LD]       # 比較用的光譜次序（左→右）


def compare_rules():
    """雙鑰匙的杜馬那一把、未覆蓋部分由誰表決：全院 300 或單一 180（見 03 §2.5）。"""
    import importlib.util as iu, pathlib
    tool = pathlib.Path(__file__).resolve().parents[5] / "shared" / "tools" / "組閣比較.py"
    spec = iu.spec_from_file_location("組閣比較", tool)
    cmp = iu.module_from_spec(spec)
    spec.loader.exec_module(cmp)
    print("| 統一俄羅斯區域／名單得票 | 單一 180（≥91）單獨握有者 | 全院 300（≥151）單獨握有者 | 全院的最小相鄰多數 |")
    print("|:--:|:--:|:--:|:--:|")
    for ur in (30, 35, 38, 40, 42, 45, 48):
        dfp = {UR: ur, KP: 19, LD: 8, SR: 8, NP: 8, OT: 100 - ur - 43}
        lst = {UR: ur - 1, KP: 19, LD: 8, SR: 8, NP: 8, OT: 100 - ur - 42}
        TERMS[0] = (dfp, lst)
        s, _, l, _ = run(0)
        full = {p: s.get(p, 0) + l.get(p, 0) for p in PARTIES}
        alone = lambda d, need: next((f"{p} {v}" for p, v in d.items() if v >= need), "無")
        wins = cmp.connected_winning({k: v for k, v in full.items() if v}, 151, ORDER)
        best = "＋".join(wins[0][0]) + f"（{wins[0][1]}）" if wins else "無"
        print(f"| {ur}% | {alone(s, 91)} | {alone(full, 151)} | {best} |")
    del TERMS[0]


def main():
    if "--某些議員" in sys.argv:
        compare_rules()
        return
    if "--sweep" in sys.argv:
        print("| 統一俄羅斯區域／名單得票 | 單一 180 | 複數 120（聖拉古） | 全院 | 過 2/3（200）？ | 複數過 2/3（80）？ |")
        print("|:--:|:--:|:--:|:--:|:--:|:--:|")
        for ur in (35, 40, 45, 50, 55):
            dfp = {UR: ur, KP: 19, LD: 8, SR: 8, NP: 8, OT: 100 - ur - 43}
            lst = {UR: ur - 1, KP: 19, LD: 8, SR: 8, NP: 8, OT: 100 - ur - 42}
            TERMS[0] = (dfp, lst)
            s, _, l, _ = run(0)
            tot = s[UR] + l[UR]
            print(f"| {ur}% | {s[UR]} | {l[UR]} | {tot} | {'是' if tot >= 200 else '否'} | {'是' if l[UR] >= 80 else '否'} |")
        return
    for t in (3, 5, 8):
        s, cyc, l, m = run(t)
        _, _, ld, _ = run(t, dhondt)
        print(f"第 {t} 屆 單一 180：{s}（循環 {cyc}）")
        print(f"    複數 120：{l}  全院統一俄羅斯 {s[UR] + l[UR]}")
        print(f"    （若用杭特法，複數：{ld}）")
    print("各區 M：", run(3)[3])


if __name__ == "__main__":
    main()
