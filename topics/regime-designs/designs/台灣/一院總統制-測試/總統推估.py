"""台灣一院總統制兩夾：直選總統的估計（全國一區 top-3 孔多賽）。

民意層：當年不分區政黨票（逐村里），不用總統第一輪實際得票（受棄保、禮讓影響）、不用個別候選人。
參選方層：每個政黨都可以推一組正副總統；全國前 3 名進入決選。2012–2024 的前 3 名都是三個大黨，
相鄰小黨的共同提名不會改變決選名單。
制度層：與議會單一選區同一套排序（一院議會制 `政黨單位.py` 的 tw_orders、q＝第 3 屆參數），
6 格完整排序，孔多賽完成法（循環時 Ranked Pairs）。

    python 總統推估.py            # 2024／2020／2016／2012 與兩份民調
    python 總統推估.py --sweep    # q民進（民進黨選民把民眾黨排在國民黨前）、q民眾（民眾黨選民把國民黨排在民進黨前）敏感度
"""
import importlib.util
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_LEGDIR = _HERE.parent / "一院議會制"
sys.path.insert(0, str(_LEGDIR))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LEG = _load("tw_leg_hist_pres", _LEGDIR / "近期大選推估.py")
from 政黨單位 import condorcet_multi  # noqa: E402

POLLS = [
    ("美麗島 2026-09（喜好度換算）", {"民進黨": 43.1, "國民黨": 26.5, "民眾黨": 21.0}),
    ("戴立安 2026-10（好感度換算）", {"民進黨": 49.0, "國民黨": 27.9, "民眾黨": 26.3}),
]
PARTIES3 = ["民進黨", "國民黨", "民眾黨"]


def national_fp(rows, year):
    """全國第一偏好：各區依村里政黨票算偏好，再以票數加權加總。"""
    lmap = LEG.load_list(year)
    rg, rng = LEG.region_minor_shares(lmap, year, LEG.REGION_ORDER)
    tot = {}
    for reg in LEG.REGION_ORDER + ["澎金馬"]:
        part = [r for r in rows if r["區"] == reg]
        if not part:
            continue
        w = sum(int(r["政黨票"]) for r in part)
        fp = LEG.village_party_prefs(part, reg, year, "政黨", rg, rng)
        for p, v in fp.items():
            tot[p] = tot.get(p, 0) + v * w
    s = sum(tot.values())
    return {p: v / s for p, v in tot.items()}


def scaled(rows, share):
    tot = {p: sum(int(r[p]) for r in rows) for p in PARTIES3}
    sc = {p: share[p] / tot[p] * sum(tot.values()) / sum(share.values()) for p in PARTIES3}
    out = []
    for r in rows:
        nr = dict(r)
        for p in PARTIES3:
            nr[p] = str(round(int(r[p]) * sc[p]))
        nr["綠系小黨"] = nr["地方型"] = nr["其他"] = "0"
        nr["政黨票"] = str(sum(int(nr[p]) for p in PARTIES3))
        out.append(nr)
    return out


def label(year, p):
    return "親民黨" if year < 2020 and p == "民眾黨" else p


def run(name, rows, year, q, k=3):
    fp = national_fp(rows, year)
    w, cyc, P, fin, top1 = condorcet_multi(fp, q, k=k)
    duel = "、".join(
        f"{label(year, a)} 對 {label(year, b)} {100 * P[(a, b)] / (P[(a, b)] + P[(b, a)]):.1f}"
        for i, a in enumerate(fin) for b in fin[i + 1:] if P[(a, b)] + P[(b, a)])
    first = "、".join(f"{label(year, p)} {100 * fp[p]:.1f}%" for p in sorted(fp, key=lambda x: -fp[x])[:5] if fp[p] > 0)
    return w, cyc, fin, first, duel


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    q = LEG.Q
    if "--sweep" in sys.argv:
        rows = {year: LEG.load(year) for year in (2024, 2020, 2016, 2012)}
        for key, vals in (("民進黨", (0.3, 0.4, 0.5, 0.6, 0.7)), ("民眾黨", (0.35, 0.45, 0.55, 0.65, 0.75))):
            print(f"\n| q{key} | 2024 | 2020 | 2016 | 2012 |")
            print("|:--:|---|---|---|---|")
            for qq in vals:
                qx = dict(q, **{key: qq})
                cells = []
                for year in (2024, 2020, 2016, 2012):
                    w, cyc, *_ = run("", rows[year], year, qx)
                    cells.append(label(year, w) + ("（循環）" if cyc else ""))
                print(f"| {qq:.2f} | " + " | ".join(cells) + " |")
        return
    for year in (2024, 2020, 2016, 2012):
        w, cyc, fin, first, duel = run(str(year), LEG.load(year), year, q)
        print(f"## {year}：第一偏好 {first}")
        print(f"決選 {'、'.join(label(year, p) for p in fin)}；兩兩 {duel}；勝者 **{label(year, w)}**{'（循環，Ranked Pairs）' if cyc else ''}")
    base = LEG.load(2024)
    for name, poll in POLLS:
        w, cyc, fin, first, duel = run(name, scaled(base, poll), 2024, q)
        print(f"## 民調 {name}：第一偏好 {first}")
        print(f"決選 {'、'.join(fin)}；兩兩 {duel}；勝者 **{w}**{'（循環，Ranked Pairs）' if cyc else ''}")


if __name__ == "__main__":
    main()
