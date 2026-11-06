"""紐西蘭一院議會制：2026 大選前民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（政黨票 %；摘自 Wikipedia「Opinion polling for the 2026 New Zealand general election」，2026-11-03 抓取）。
以 2023-10 投票所地理（資料/ge-2023.csv）縮放：每黨在每個投票所的票 × （民調份額／2023 份額）。
民調未列的黨（保守黨等）併入「其他」，「其他」依 2023 其他票的分布縮放。單一 72 依四區有效票 Hare 配額，跑 top-3 孔多賽；複數 48 四區聖拉古。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402


def scaled_units(target):
    units = m.load("2023-10")
    base = {}
    for u in units:
        for p, v in u[5].items():
            q = p if p in target else "其他"
            base[q] = base.get(q, 0) + v
    tot = sum(base.values())
    out = []
    for u in units:
        raw = {}
        for p, v in u[5].items():
            q = p if p in target else "其他"
            raw[q] = raw.get(q, 0) + v
        nv = {p: raw.get(p, 0) * target[p] * tot / base[p] for p in target if base.get(p)}
        out.append((u[0], u[1], u[2], sum(nv.values()), sum(nv.values()), nv))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        pct = {k: float(v) for k, v in r.items() if k not in ("poll", "fieldwork", "n") and v not in ("", "–")}
        s = sum(pct.values())
        target = {p: v / s for p, v in pct.items()}
        units = scaled_units(target)
        smd_n = m.hare_smd(units)
        smd, stats, _ = m.single_seats(units, smd_n)
        lst = m.list_seats(units)
        total = {}
        for d in (smd, lst):
            for p, n in d.items():
                total[p] = total.get(p, 0) + n
        assert sum(total.values()) == m.TOTAL
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}）")
        print("政黨票%：", "、".join(f"{p} {v:g}" for p, v in pct.items()))
        print("單一 72：", m.fmt(smd), stats)
        print("複數 48：", m.fmt(lst))
        print("全院 120：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
