"""台灣一院總統制-測試：預期政治生態的機械效應模型。

議會的選制（單一 100 top-3 孔多賽、複數 80 七區聖拉古）與一院議會制夾相同，
所以直接載入那一夾的 生態模型.py 的選制函式；本檔只放**本夾自己的假設**，
另加全國直選總統那一場（top-3 孔多賽）。

    python 生態模型.py            # 印出 15 用的數字
    python 生態模型.py --sweep    # 總統與單一席次對第二偏好的敏感度
"""
import importlib.util
import pathlib
import sys

_A = pathlib.Path(__file__).resolve().parent.parent / "一院議會制" / "生態模型.py"
_spec = importlib.util.spec_from_file_location("選制", _A)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

# ---------------------------------------------------------------- 假設
TERMS = {
    # 屆: (總統第一偏好, 區域第一偏好, 第二偏好 q, 名單得票)
    3: ({"民進黨": 39, "國民黨": 33, "民眾黨": 25, "綠系小黨": 1, "地方型": 2},
        {"民進黨": 38, "國民黨": 33, "民眾黨": 20, "綠系小黨": 3, "地方型": 6},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.55},
        {"民進黨": 33, "國民黨": 30, "民眾黨": 20, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 3, "其他名單": 5}),
    5: ({"民進黨": 40, "國民黨": 34, "民眾黨": 23, "綠系小黨": 1, "地方型": 2},
        {"民進黨": 39, "國民黨": 34, "民眾黨": 18, "綠系小黨": 3, "地方型": 6},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.50},
        {"民進黨": 33, "國民黨": 31, "民眾黨": 18, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 4, "其他名單": 5}),
    8: ({"民進黨": 41, "國民黨": 35, "民眾黨": 21, "綠系小黨": 1, "地方型": 2},
        {"民進黨": 40, "國民黨": 35, "民眾黨": 16, "綠系小黨": 3, "地方型": 6},
        {"民進黨": 0.50, "國民黨": 0.80, "民眾黨": 0.45},
        {"民進黨": 33, "國民黨": 31, "民眾黨": 16, "時代力量": 6, "綠黨與環境團體聯盟": 5,
         "台灣基進": 4, "其他名單": 5}),
}


def pairwise(ballots):
    C = m.PARTIES
    return {(a, c): sum(v for r, v in ballots.items() if r.index(a) < r.index(c))
            for a in C for c in C if a != c}


def president(fp, q):
    """全國一場：依人口加權各區傾向後加總，回傳 (當選者, 兩兩表, 是否循環)。"""
    total = {}
    pop = sum(r[1] for r in m.REGIONS)
    for name, p, lean, tl in m.REGIONS:
        d = {**fp, "民進黨": fp["民進黨"] + lean / 2, "國民黨": fp["國民黨"] - lean / 2,
             "民眾黨": fp["民眾黨"] + tl}
        s = sum(d.values())
        d = {k: v / s for k, v in d.items()}
        for r, v in m.rankings(d, q).items():
            total[r] = total.get(r, 0) + v * p / pop
    return m.condorcet(total), pairwise(total), not m.has_winner(total)


def run(term):
    pfp, dfp, q, lst = TERMS[term]
    pres = president(pfp, q)
    s = m.single_seats(dfp, q)
    shares = {k: v for k, v in lst.items() if k != "其他名單"}
    for i in range(5):
        shares[f"其他{i}"] = lst["其他名單"] / 5
    l, _ = m.list_seats(shares, m.lean_of)
    l = {k: v for k, v in l.items() if not k.startswith("其他")}
    ds = m.districts(dfp, q)
    return pres, s, l, sum(c for _, _, c in ds)


def main():
    if "--sweep" in sys.argv:
        pfp, _, q, _ = TERMS[3]
        dfp = TERMS[3][1]
        print("| 民進黨選民把民眾黨排在國民黨前 | 總統 | 民眾對民進 | 國民對民眾 | 民進對國民 | 單一 民進／國民／民眾 |")
        print("|:--:|:--:|:--:|:--:|:--:|:--:|")
        for qd in (0.4, 0.5, 0.55, 0.6, 0.65, 0.7):
            qq = dict(q, **{"民進黨": qd})
            w, P, _ = president(pfp, qq)
            s = m.single_seats(dfp, qq)
            f = lambda a, b: f"{P[(a, b)]:.1%}"
            print(f"| {qd:.0%} | {w} | {f('民眾黨', '民進黨')} | {f('國民黨', '民眾黨')} | {f('民進黨', '國民黨')} "
                  f"| {s['民進黨']}／{s['國民黨']}／{s['民眾黨']} |")
        return
    for t in TERMS:
        (w, P, cyc), s, l, dc = run(t)
        print(f"第 {t} 屆 總統：{w}（循環 {cyc}）"
              f" 民眾對民進 {P[('民眾黨', '民進黨')]:.1%}、國民對民眾 {P[('國民黨', '民眾黨')]:.1%}、"
              f"民進對國民 {P[('民進黨', '國民黨')]:.1%}")
        print(f"    單一 100：{s}（循環選區 {dc}）  複數 80：{l}")
        for p in ("民進黨", "國民黨"):
            print(f"    {p} 派系 單一 服務/政策 {m.factions(s[p], '單一')}  複數 服務/政策 {m.factions(l[p], '複數')}")


if __name__ == "__main__":
    main()
