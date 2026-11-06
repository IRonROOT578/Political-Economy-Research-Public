"""丹麥一院議會制：民調（與 2026-03 大選）套本夾。

    python 民調重算.py

輸入：資料/polls.csv（複製自 my_research/parliament_condorcet/denmark/data/；各家民調的**現行制度席次**推估，179 席；2026 大選列為實際席次）。
本土 175 席換算成全國份額（丹麥現行為全國比例，席次比≈得票比），再以 2026-03 opstilling 地理（資料/ft-2026.csv）縮放：
每黨在每個提名區的票 × （目標份額／2026 份額）。
民調未列的黨（其他）歸零。北大西洋 4 席依民調列（IA→EL、JF→S、SP→V、NQ→M，同 生態模型.map_na 的作法）。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

POLLS = os.path.join(HERE, "資料", "polls.csv")
CODE = {"KF": "C"}                 # 民調欄名 → 本夾黨碼
NA_CODES = {"IA": "EL", "JF": "S", "SP": "V", "NQ": "M"}


def scaled_units(target):
    units = m.load("2026-03")
    base = {}
    for u in units:
        for p, v in u[5].items():
            base[p] = base.get(p, 0) + v
    tot = sum(base.values())
    out = []
    for u in units:
        nv = {}
        for p, share in target.items():
            if base.get(p):
                nv[p] = u[5].get(p, 0) * share * tot / base[p]
            else:
                nv[p] = u[3] * share
        out.append((u[0], u[1], u[2], sum(nv.values()), sum(nv.values()), nv))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    with open(os.path.normpath(POLLS), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows[1:]:   # 第一列是 2026 大選本身，逐區重算見 生態模型.py
        seats = {CODE.get(k, k): int(v) for k, v in r.items() if k not in ("poll", "fieldwork", "n") and v}
        na = {}
        for k, p in NA_CODES.items():
            na[p] = na.get(p, 0) + seats.pop(k, 0)
        mainland = {p: n for p, n in seats.items() if n}
        tot = sum(mainland.values())
        target = {p: n / tot for p, n in mainland.items()}
        units = scaled_units(target)
        smd, _, _ = m.single_seats(units)
        lst = m.list_seats(units)
        total = {}
        for d in (smd, lst, na):
            for p, n in d.items():
                total[p] = total.get(p, 0) + n
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}）")
        print("現行制度席次：", m.fmt(mainland), "＋北大西洋", sum(na.values()))
        print("單一 106：", m.fmt(smd))
        print("複數 70：", m.fmt(lst))
        print("全院 180：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
