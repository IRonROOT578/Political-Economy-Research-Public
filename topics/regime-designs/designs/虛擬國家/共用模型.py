"""虛擬國家三個版本共用：議會（單一 60＋複數 40，數字沿用一院議會制）、參議院（3 區比例 50）、總統（全國 top-3 孔多賽）。

虛構國家、虛構數字。民意層＝各情境的政黨得票（比例名單票）；參選方層＝每個政黨推一人，前 3 名進決選；
制度層＝選民依政黨位置排序（與一院議會制同一套 Prefs），孔多賽完成法、聖拉古。

    python 共用模型.py            # 三版的總統、參議院、組閣
    python 共用模型.py --charts   # 另畫兩院、總統兩夾的席次圖
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "shared", "tools"))
_spec = importlib.util.spec_from_file_location("vc_one", os.path.join(HERE, "一院議會制", "生態模型.py"))
ONE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ONE)

SENATE_M = {"北區": 20, "中區": 17, "南區": 13}          # 參議院 50，依人口；每區 M 寫成區間 [10, 22]
TILT = {"北區": {"甲": 1.0, "乙": 1.0}, "中區": {}, "南區": {"丙": 2.0, "丁": 1.0, "乙": -1.0}}  # 區域偏移（百分點，虛構）


def sainte_lague(votes, m):
    got = {p: 0 for p in votes}
    for _ in range(m):
        p = max(votes, key=lambda x: (votes[x] / (2 * got[x] + 1), x))
        got[p] += 1
    return got


def senate(share):
    out = {}
    for reg, m in SENATE_M.items():
        v = {p: max(0.1, s + TILT[reg].get(p, 0)) for p, s in share.items()}
        for p, n in sainte_lague(v, m).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out


def president(share, k=3):
    """全國一區：前 k 名進決選；選民（依政黨）排序，孔多賽完成法，循環時 Ranked Pairs。"""
    from 參選判定 import smd_k
    k = smd_k(k)
    pr = ONE.prefs()
    from 參選判定 import finalists

    def pairs(fin):
        P = {(a, b): 0.0 for a in fin for b in fin if a != b}
        for g, w in share.items():
            r = [x for x in pr.rank(pr.pos[g], g, list(share), ONE.BALANCED) if x in fin]
            for i, a in enumerate(r):
                for b in r[i + 1:]:
                    P[(a, b)] += w
        return P

    def cw(fin):
        P = pairs(fin)
        return next((a for a in fin if all(P[(a, b)] > P[(b, a)] for b in fin if b != a)), fin[0])
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(ONE.POS[a], ONE.POS[b])) ** 0.5
    # 參選方層：低票讓低票、高票讓低票、單純退選（shared/tools/參選判定.py，withdraw=True）
    fin = finalists(share, k, cw, dist, universe=list(ONE.POS), withdraw=True)
    P = pairs(fin)
    win = next((a for a in fin if all(P[(a, b)] > P[(b, a)] for b in fin if b != a)), None)
    cyc = win is None
    if cyc:
        wins = sorted(((P[(a, b)], a, b) for a in fin for b in fin if a != b and P[(a, b)] > P[(b, a)]), reverse=True)
        locked = set()

        def reach(x, y):
            st, seen = [x], set()
            while st:
                u = st.pop()
                if u == y:
                    return True
                seen.add(u)
                st += [c for a, c in locked if a == u and c not in seen]
            return False
        for _, a, b in wins:
            if not reach(b, a):
                locked.add((a, b))
        win = next(a for a in fin if not any(c == a for _, c in locked))
    duel = {f"{a}對{b}": round(100 * P[(a, b)] / (P[(a, b)] + P[(b, a)]), 1) for i, a in enumerate(fin) for b in fin[i + 1:]}
    return win, cyc, fin, duel


def house(label):
    sc = ONE.SCENARIOS[label]
    total = {p: sc["smd"].get(p, 0) + sc["lst"].get(p, 0) for p in ONE.POS}
    return sc, {p: n for p, n in total.items() if n}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    for label in ONE.SCENARIOS:
        sc, total = house(label)
        pm, _, _ = ONE.head_of_gov(total)
        seq, acc = ONE.coalition(total, pm)
        sen = senate(sc["share"])
        w, cyc, fin, duel = president(sc["share"])
        print(f"## {label}")
        print("議會 100：", ONE.fmt(total), "；首長（議會制）", pm, "；組閣", "＋".join(seq), acc)
        print("參議院 50：", ONE.fmt(sen))
        print("總統：決選", "、".join(fin), duel, "勝者", w, "（循環）" if cyc else "")
        rows.append((label, total, sen, w))
    if "--charts" in sys.argv:
        import parliament_diagram as pdg
        order = [("丁", "#FDD835"), ("甲", "#1E88E5"), ("丙", "#43A047"), ("乙", "#E53935"), ("戊", "#8E24AA")]
        for label, total, sen, w in rows:
            tag = label.split("（")[0].replace("民調 ", "民調-").replace(" ", "")
            for folder, d, name, title in (("兩院議會制", total, f"席次圖-國民院-{tag}.svg", f"{label} 國民院（100）"),
                                          ("兩院議會制", sen, f"席次圖-參議院-{tag}.svg", f"{label} 參議院（50）"),
                                          ("一院總統制", total, f"席次圖-{tag}.svg", f"{label} 國會（100）")):
                svg = pdg.render_svg(pdg.paint(d, order, "虛擬國家"), title=title, caption=f"虛構數字；總統 {w}" if folder == "一院總統制" else "虛構數字")
                with open(os.path.join(HERE, folder, name), "w", encoding="utf-8") as f:
                    f.write(svg)


if __name__ == "__main__":
    main()
