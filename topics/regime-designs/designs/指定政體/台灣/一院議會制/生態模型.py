"""台灣一院議會制：預期政治生態的機械效應模型。

把 15-預期政治生態.md 的「得票 → 選制 → 各組成席次」算出來，讓表上的數字可重現。
所有輸入都是**假設**（見 15 §2），不是開票紀錄；改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 15 用的表
    python 生態模型.py --sweep    # 印出關鍵參數的敏感度

單一席次 100：top-3 孔多賽。第一輪單記取前 3；第二輪 6 格完整排序單選，
    孔多賽完成法（循環時 Ranked Pairs；完整排序下勝方得票與勝差等價）。
複數席次 80：7 大區，每區聖拉古，無得票門檻。
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from 政黨單位 import condorcet_multi, decompose_term_prefs  # noqa: E402

# ---------------------------------------------------------------- 地理
# 人口（萬，約 2025），用來分配席次。
REGIONS = [
    # 名稱, 人口, 綠藍傾向（正＝偏綠，百分點）, 民眾黨傾向
    ("臺北市", 247, -4, +2),
    ("新北市", 405, -1, +1),
    ("桃園＋新竹縣市", 335, -3, +3),
    ("臺中＋彰化", 409, 0, 0),
    ("雲嘉南", 327, +8, -3),
    ("高屏", 351, +6, -2),
    ("其餘縣市與離島", 261, -8, -2),
]


def sainte_lague(weights, seats):
    got = {k: 0 for k in weights}
    for _ in range(seats):
        k = max(weights, key=lambda x: weights[x] / (2 * got[x] + 1))
        got[k] += 1
    return got


def region_seats(total, lo=None, hi=None):
    pop = {r[0]: r[1] for r in REGIONS}
    out = sainte_lague(pop, total)
    if lo is not None:
        assert all(lo <= v <= hi for v in out.values()), out
    return out


# ---------------------------------------------------------------- 單一席次
PARTIES = ["民進黨", "國民黨", "民眾黨"]


def district_first_prefs(base, lean, tpp_lean, rng):
    """一區的第一偏好：民進、國民、民眾、綠系小黨、地方型。"""
    swing = rng.gauss(lean, 6.0)
    d = base["民進黨"] + swing / 2
    k = base["國民黨"] - swing / 2
    t = max(3.0, rng.gauss(base["民眾黨"] + tpp_lean, 3.0))
    g = base["綠系小黨"]
    l = base["地方型"]
    s = d + k + t + g + l
    return {"民進黨": d / s, "國民黨": k / s, "民眾黨": t / s, "綠系小黨": g / s, "地方型": l / s}


def rankings(fp, q):
    """把第一偏好展開成三位決選者的完整排序票數。

    q["民進黨"]：民進黨選民把民眾黨排在國民黨前面的比例；
    q["國民黨"]：國民黨選民把民眾黨排在民進黨前面的比例；
    q["民眾黨"]：民眾黨選民把國民黨排在民進黨前面的比例。
    綠系小黨選民照 民進>民眾>國民；地方型選民照 國民>民眾>民進。
    """
    D, K, T = "民進黨", "國民黨", "民眾黨"
    b = {}
    b[(D, T, K)] = fp[D] * q[D] + fp["綠系小黨"]
    b[(D, K, T)] = fp[D] * (1 - q[D])
    b[(K, T, D)] = fp[K] * q[K] + fp["地方型"]
    b[(K, D, T)] = fp[K] * (1 - q[K])
    b[(T, K, D)] = fp[T] * q[T]
    b[(T, D, K)] = fp[T] * (1 - q[T])
    return b


def condorcet(ballots):
    cands = PARTIES
    P = {(a, c): sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
         for a in cands for c in cands if a != c}
    for a in cands:
        if all(P[(a, c)] > P[(c, a)] for c in cands if c != a):
            return a
    # Ranked Pairs（勝方得票；完整排序下與勝差排序相同）
    wins = sorted(((P[(a, c)], a, c) for a in cands for c in cands
                   if a != c and P[(a, c)] > P[(c, a)]), reverse=True)
    locked = set()

    def reach(x, y):
        stack, seen = [x], set()
        while stack:
            n = stack.pop()
            if n == y:
                return True
            seen.add(n)
            stack += [c for (a, c) in locked if a == n and c not in seen]
        return False

    for _, a, c in wins:
        if not reach(c, a):
            locked.add((a, c))
    return next(a for a in cands if not any(c2 == a for (_, c2) in locked))


def has_winner(ballots):
    P = lambda a, c: sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
    return any(all(P(a, c) > P(c, a) for c in PARTIES if c != a) for a in PARTIES)


def districts(base, q, seed=3, lst=None, k=3):
    """逐區回傳 (第一偏好最多者, 當選者, 是否循環)。"""
    rng = random.Random(seed)
    seats = region_seats(99)  # 澎金馬另 1 席
    todo = [(lean, tl) for name, _, lean, tl in REGIONS for _ in range(seats[name])]
    todo.append((-20, -4))  # 澎金馬：偏藍
    out = []
    for lean, tl in todo:
        fp = decompose_term_prefs(district_first_prefs(base, lean, tl, rng), lst)
        w, cyc, _, _, top1 = condorcet_multi(fp, q, k=k)
        out.append((top1, w, cyc))
    return out


def single_seats(base, q, seed=3, lst=None, k=3):
    out = {p: 0 for p in PARTIES}
    for _, w, _ in districts(base, q, seed, lst=lst, k=k):
        out[w] = out.get(w, 0) + 1
    return out


# ---------------------------------------------------------------- 複數席次
def list_seats(shares, lean_of):
    m = region_seats(80, 8, 14)
    out = {p: 0 for p in shares}
    for name, _, lean, tl in REGIONS:
        w = {p: max(0.1, s + lean_of(p, lean, tl)) for p, s in shares.items()}
        for p, n in sainte_lague(w, m[name]).items():
            out[p] += n
    return out, m


def lean_of(p, lean, tl):
    return {"民進黨": lean / 2, "國民黨": -lean / 2, "民眾黨": tl,
            "台灣基進": max(-2.0, lean / 4)}.get(p, 0.0)


# ---------------------------------------------------------------- 情境
TERMS = {
    # 屆: (單一席次第一偏好, 單一席次第二偏好 q, 名單得票)
    3: ({"民進黨": 38, "國民黨": 34, "民眾黨": 21, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.55},
        {"民進黨": 32, "國民黨": 30, "民眾黨": 21, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 3, "其他名單": 5}),
    5: ({"民進黨": 39, "國民黨": 35, "民眾黨": 19, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.50},
        {"民進黨": 32, "國民黨": 31, "民眾黨": 19, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 4, "其他名單": 5}),
    8: ({"民進黨": 40, "國民黨": 36, "民眾黨": 17, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.80, "民眾黨": 0.45},
        {"民進黨": 32, "國民黨": 31, "民眾黨": 17, "時代力量": 6, "綠黨與環境團體聯盟": 5,
         "台灣基進": 4, "其他名單": 5}),
}


def run(term, k=3):
    fp, q, lst = TERMS[term]
    s = single_seats(fp, q, lst=lst, k=k)
    # 「其他名單」是多張各約 1% 的名單，拆開分配
    shares = {k2: v for k2, v in lst.items() if k2 != "其他名單"}
    for i in range(5):
        shares[f"其他{i}"] = lst["其他名單"] / 5
    l, m = list_seats(shares, lean_of)
    other = sum(v for k2, v in l.items() if k2.startswith("其他"))
    l = {k2: v for k2, v in l.items() if not k2.startswith("其他")}
    l["其他名單"] = other
    return s, l, m


# 全院 180 選首長：各黨議員依下列順序記名排名（假設，見 15 §2.5）
ALL_MP_PARTIES = [
    "台灣基進", "台聯", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟",
    "小民參政歐巴桑聯盟", "民進黨", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "新黨",
]
MP_RANK = {
    "台灣基進": ["台灣基進", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台聯", "民進黨", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "新黨"],
    "台聯": ["台聯", "台灣基進", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "民眾黨", "無黨籍／地方", "親民黨", "國民黨", "新黨"],
    "時代力量": ["時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "民進黨", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "台聯", "新黨"],
    "綠黨與環境團體聯盟": ["綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "時代力量", "民進黨", "台灣基進", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "台聯", "新黨"],
    "綠黨": ["綠黨", "綠黨與環境團體聯盟", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "時代力量", "民進黨", "台灣基進", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "台聯", "新黨"],
    "綠黨社會民主黨聯盟": ["綠黨社會民主黨聯盟", "綠黨", "綠黨與環境團體聯盟", "小民參政歐巴桑聯盟", "時代力量", "民進黨", "台灣基進", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "台聯", "新黨"],
    "小民參政歐巴桑聯盟": ["小民參政歐巴桑聯盟", "綠黨", "綠黨與環境團體聯盟", "綠黨社會民主黨聯盟", "時代力量", "民進黨", "台灣基進", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "台聯", "新黨"],
    "民進黨": ["民進黨", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "時代力量", "台灣基進", "台聯", "民眾黨", "無黨籍／地方", "國民黨", "親民黨", "新黨"],
    "民眾黨": ["民眾黨", "國民黨", "親民黨", "無黨籍／地方", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "台聯", "新黨"],
    "無黨籍／地方": ["無黨籍／地方", "國民黨", "親民黨", "民眾黨", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "台聯", "新黨"],
    "國民黨": ["國民黨", "親民黨", "新黨", "民眾黨", "無黨籍／地方", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "台聯"],
    "親民黨": ["親民黨", "國民黨", "民眾黨", "無黨籍／地方", "新黨", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "台聯"],
    "新黨": ["新黨", "國民黨", "親民黨", "民眾黨", "無黨籍／地方", "民進黨", "時代力量", "綠黨與環境團體聯盟", "綠黨", "綠黨社會民主黨聯盟", "小民參政歐巴桑聯盟", "台灣基進", "台聯"],
}
NEED = 91


def head_of_gov(total):
    """全院記名排名、孔多賽；回傳首長所屬黨、對各黨的對決、組閣陣營（由首長所屬黨的排序往外加到 ≥91）。"""
    parties = [p for p, n in total.items() if n and p in MP_RANK]
    P = {(a, b): sum(n for p, n in total.items() if p in MP_RANK and MP_RANK[p].index(a) < MP_RANK[p].index(b))
         for a in parties for b in parties if a != b}
    win = [a for a in parties if all(P[(a, b)] > P[(b, a)] for b in parties if b != a)]
    w = win[0] if win else max(parties, key=lambda a: total[a])
    seq, acc = [], 0
    for p in MP_RANK[w]:
        if total.get(p):
            seq.append(p)
            acc += total[p]
            if acc >= NEED:
                break
    return w, {b: (P[(w, b)], P[(b, w)]) for b in parties if b != w}, seq, acc


# 派系：單一席次選區當選者多為地方服務派，名單上多為國會政策派（假設，見 15 §3）
SRV_SHARE = {"單一": 0.8, "複數": 0.4}


def factions(n, part):
    srv = round(n * SRV_SHARE[part])
    return srv, n - srv


def main():
    if "--sweep" in sys.argv:
        fp, q, lst = TERMS[3]
        print("| 民進黨選民把民眾黨排在國民黨前的比例 | 民進 | 國民 | 民眾 |")
        print("|:--:|:--:|:--:|:--:|")
        for qd in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
            s = single_seats(fp, dict(q, **{"民進黨": qd}), lst=lst)
            print(f"| {qd:.0%} | {s['民進黨']} | {s['國民黨']} | {s['民眾黨']} |")
        print()
        print("| 民眾黨選民把國民黨排在民進黨前的比例 | 民進 | 國民 | 民眾 |")
        print("|:--:|:--:|:--:|:--:|")
        for qt in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65):
            s = single_seats(fp, dict(q, **{"民眾黨": qt}), lst=lst)
            print(f"| {qt:.0%} | {s['民進黨']} | {s['國民黨']} | {s['民眾黨']} |")
        return
    for t in TERMS:
        s, l, m = run(t)
        fp, q, lst = TERMS[t]
        ds = districts(fp, q, lst=lst)
        cyc = sum(c for _, _, c in ds)
        upset = sum(1 for top, w, _ in ds if top != w)
        print(f"第 {t} 屆 單一 100：{s}  複數 80：{l}")
        print(f"    循環選區 {cyc}；當選者不是第一偏好最多者的選區 {upset}")
        for p in ("民進黨", "國民黨"):
            print(f"    {p} 派系 單一 服務/政策 {factions(s[p], '單一')}  複數 服務/政策 {factions(l[p], '複數')}")
        total = {p: s.get(p, 0) + l.get(p, 0) for p in set(s) | set(l) if p != "其他名單"}
        w, duel, seq, acc = head_of_gov(total)
        print(f"    全院 180：{dict(sorted(total.items(), key=lambda x: -x[1]))}")
        print(f"    首長（全院 ≥{NEED}）：{w}；對決 {duel}；組閣陣營 {'＋'.join(seq)}＝{acc}")
    print("複數各區 M：", run(3)[2])


if __name__ == "__main__":
    main()
