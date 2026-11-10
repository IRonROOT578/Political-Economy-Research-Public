"""南韓一院總統制：預期政治生態的機械效應模型。

把 15-預期政治生態.md 的「得票 → 選制 → 結果」算出來。所有輸入都是**假設**（見 15 §2），
不是開票紀錄；改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 15 用的數字
    python 生態模型.py --sweep    # 關鍵第二偏好的敏感度

總統：全國 top-3 孔多賽。單一席次 150：top-3 孔多賽。複數 100：8 區，
黑爾額數＋最大餘數，無得票門檻。循環時 Ranked Pairs（完整排序下勝方得票與勝差等價）。
"""
import random
import sys

D, P, R = "民主黨", "國民力量", "改革新黨"
FINALISTS = [D, P, R]

# ---------------------------------------------------------------- 地理
# 名稱, 人口（萬）, 民主減國民力量的差距相對全國的偏移（百分點）
# 偏移取自 2025 年總統選舉各地差距減去全國差距（+8.3），首都圈四區為示意切法。
REGIONS = [
    ("首爾北＋京畿東北", 690, -1),
    ("首爾南＋京畿南", 690, -2),
    ("仁川＋京畿西", 690, +6),
    ("京畿東南＋江原", 680, +2),
    ("忠清", 555, -4),
    ("湖南＋濟州", 563, +62),
    ("大邱慶北＋蔚山", 602, -45),
    ("釜山慶南", 653, -19),
]


def largest_remainder(weights, seats):
    tot = sum(weights.values())
    q = {k: v * seats / tot for k, v in weights.items()}
    got = {k: int(v) for k, v in q.items()}
    rest = seats - sum(got.values())
    for k in sorted(q, key=lambda k: q[k] - got[k], reverse=True)[:rest]:
        got[k] += 1
    return got


def region_seats(total):
    return largest_remainder({r[0]: r[1] for r in REGIONS}, total)


# ---------------------------------------------------------------- 排序
def rankings(fp, q):
    """第一偏好展開成三位決選者的完整排序。

    q[D]：民主黨選民把改革新黨排在國民力量前的比例
    q[P]：國民力量選民把改革新黨排在民主黨前的比例
    q[R]：改革新黨選民把國民力量排在民主黨前的比例
    進步小黨（祖國革新黨、進步黨等）選民照 民主 > 改革 > 國民力量。
    """
    b = {
        (D, R, P): fp[D] * q[D] + fp["進步小黨"],
        (D, P, R): fp[D] * (1 - q[D]),
        (P, R, D): fp[P] * q[P] + fp["其他"] / 2,
        (P, D, R): fp[P] * (1 - q[P]),
        (R, P, D): fp[R] * q[R],
        (R, D, P): fp[R] * (1 - q[R]) + fp["其他"] / 2,
    }
    return b


def pairwise(b):
    return {(a, c): sum(v for r, v in b.items() if r.index(a) < r.index(c))
            for a in FINALISTS for c in FINALISTS if a != c}


def condorcet(b):
    Pw = pairwise(b)
    for a in FINALISTS:
        if all(Pw[(a, c)] > Pw[(c, a)] for c in FINALISTS if c != a):
            return a, False
    # 三人循環：三場勝場依勝方得票排序，丟掉最弱的一場（Ranked Pairs 在三人時的結果）
    wins = sorted(((Pw[(a, c)], a, c) for a in FINALISTS for c in FINALISTS
                   if a != c and Pw[(a, c)] > Pw[(c, a)]), reverse=True)
    losers = {c for _, _, c in wins[:2]}
    return next(a for a in FINALISTS if a not in losers), True


def district(fp, lean, rng):
    s = rng.gauss(lean, 7.0)
    d = {**fp, D: fp[D] + s / 2, P: fp[P] - s / 2}
    d[R] = max(1.0, rng.gauss(fp[R], 2.0))
    t = sum(d.values())
    return {k: v / t for k, v in d.items()}


YEONGNAM = ("大邱慶北＋蔚山", "釜山慶南")


def single_seats(fp, q, seed=7, by_region=False):
    """by_region=True 時另回傳 (國民力量在嶺南的席次, 鐵票區數)。

    鐵票區：當選人所屬陣營的第一偏好就過半（民主黨＋進步小黨，或國民力量），
    第二偏好一票都用不到。
    """
    rng = random.Random(seed)
    seats = region_seats(150)
    out = {p: 0 for p in FINALISTS}
    ppp_yeongnam = safe = cycles = 0
    for name, _, lean in REGIONS:
        for _ in range(seats[name]):
            fp_d = district(fp, lean, rng)
            w, c = condorcet(rankings(fp_d, q))
            out[w] += 1
            cycles += c
            ppp_yeongnam += (w == P and name in YEONGNAM)
            bloc = fp_d[D] + fp_d["進步小黨"] if w == D else fp_d[w]
            safe += bloc > 0.5
    if by_region:
        return out, cycles, (ppp_yeongnam, safe)
    return out, cycles


def president(fp, q):
    total = {}
    pop = sum(r[1] for r in REGIONS)
    for name, p, lean in REGIONS:
        d = {**fp, D: fp[D] + lean / 2, P: fp[P] - lean / 2}
        t = sum(d.values())
        for r, v in rankings({k: x / t for k, x in d.items()}, q).items():
            total[r] = total.get(r, 0) + v * p / pop
    w, c = condorcet(total)
    return w, pairwise(total), c


def list_seats(shares):
    m = region_seats(100)
    assert all(10 <= v <= 14 for v in m.values()), m
    out = {p: 0 for p in shares}
    for name, _, lean in REGIONS:
        w = dict(shares)
        w[D] = max(0.1, w[D] + lean / 2)
        w[P] = max(0.1, w[P] - lean / 2)
        for p, n in largest_remainder(w, m[name]).items():
            out[p] += n
    return out, m


# ---------------------------------------------------------------- 情境
TERMS = {
    # 屆: (總統第一偏好, 區域第一偏好, 第二偏好 q, 名單得票)
    3: ({D: 48, P: 40, R: 9, "進步小黨": 2, "其他": 1},
        {D: 46, P: 40, R: 8, "進步小黨": 4, "其他": 2},
        {D: 0.55, P: 0.90, R: 0.60},
        {D: 36, P: 34, "祖國革新黨": 10, R: 9, "進步黨": 4, "正義黨": 3, "其他名單": 4}),
    5: ({D: 44, P: 43, R: 10, "進步小黨": 2, "其他": 1},
        {D: 43, P: 43, R: 8, "進步小黨": 4, "其他": 2},
        {D: 0.55, P: 0.90, R: 0.65},
        {D: 34, P: 36, "祖國革新黨": 9, R: 9, "進步黨": 4, "正義黨": 3, "其他名單": 5}),
    8: ({D: 45, P: 41, R: 11, "進步小黨": 2, "其他": 1},
        {D: 44, P: 41, R: 9, "進步小黨": 4, "其他": 2},
        {D: 0.60, P: 0.85, R: 0.55},
        {D: 35, P: 33, "祖國革新黨": 8, R: 11, "進步黨": 5, "正義黨": 3, "其他名單": 5}),
}


def run(t):
    pfp, dfp, q, lst = TERMS[t]
    pres = president(pfp, q)
    s, cyc = single_seats(dfp, q)
    shares = {k: v for k, v in lst.items() if k != "其他名單"}
    for i in range(5):
        shares[f"其他{i}"] = lst["其他名單"] / 5
    l, m = list_seats(shares)
    l = {k: v for k, v in l.items() if not k.startswith("其他")}
    return pres, s, cyc, l, m


def main():
    if "--sweep" in sys.argv:
        pfp, dfp, q, _ = TERMS[3]
        print("| 改革新黨選民把國民力量排在民主黨前 | 總統 | 民主對國民力量 | 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|:--:|:--:|")
        for qr in (0.4, 0.5, 0.6, 0.7, 0.8):
            qq = dict(q, **{R: qr})
            w, Pw, _ = president(pfp, qq)
            s, _ = single_seats(dfp, qq)
            print(f"| {qr:.0%} | {w} | {Pw[(D, P)]:.1%} | {s[D]}／{s[P]}／{s[R]} |")
        print()
        print("| 國民力量選民把改革新黨排在民主黨前 | 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|")
        for qp in (0.7, 0.8, 0.9, 0.95):
            s, _ = single_seats(dfp, dict(q, **{P: qp}))
            print(f"| {qp:.0%} | {s[D]}／{s[P]}／{s[R]} |")
        print()
        print("| 民主黨選民把改革新黨排在國民力量前 | 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|")
        for qd in (0.4, 0.55, 0.7, 0.85):
            s, _ = single_seats(dfp, dict(q, **{D: qd}))
            print(f"| {qd:.0%} | {s[D]}／{s[P]}／{s[R]} |")
        return
    # 國會主算：2024 實際 2,847 邑面洞地理拆回實際政黨，逐黨縮放到各屆假設的全國份額（PARTY_TERMS），
    # 同一張新選區圖、top-3 孔多賽（祖國革新黨也是區域候選人）；名單 8 區黑爾＋最大餘數。
    import 近期大選推估 as K
    prov = K.shares_2024()
    w = {p: K.PROVINCES[p][0] for p in prov}
    nat = {k: sum(prov[p][k] * w[p] for p in prov) / sum(w.values()) for k in K.LIST_PARTIES}
    for t in TERMS:
        (pw, Pw, pc) = president(TERMS[t][0], TERMS[t][2])
        print(f"第 {t} 屆 總統：{pw}（循環 {pc}） 民主對國民力量 {Pw[(D, P)]:.1%}、"
              f"改革對國民力量 {Pw[(R, P)]:.1%}、改革對民主 {Pw[(R, D)]:.1%}")
        r = {k: PARTY_TERMS[t].get(k, 0) / nat[k] for k in K.LIST_PARTIES}
        K.report(f"第 {t} 屆（推估）", None, *reversed(K.units_by_ratio(r)))
    print("（複數各區 M：", run(3)[4], "）")


# 國會主算用：各屆名單（＝區域真誠第一偏好）全國份額假設（%）。綠色正義黨＝進步黨＋正義黨等左派小黨。
PARTY_TERMS = {
    3: {"民主黨": 36, "國民力量": 34, "祖國革新黨": 10, "改革新黨": 9, "綠色正義黨": 7, "自由統一黨": 2, "新未來": 1, "其他": 1},
    5: {"民主黨": 34, "國民力量": 36, "祖國革新黨": 9, "改革新黨": 9, "綠色正義黨": 7, "自由統一黨": 2, "新未來": 1, "其他": 2},
    8: {"民主黨": 35, "國民力量": 33, "祖國革新黨": 8, "改革新黨": 11, "綠色正義黨": 8, "自由統一黨": 2, "新未來": 1, "其他": 2},
}


if __name__ == "__main__":
    main()
