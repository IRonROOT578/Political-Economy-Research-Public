"""拉脫維亞一院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（維基 2026 Latvian parliamentary election 的 Opinion polls（**選前**最後一個月各家最新一筆；選後尚無民調）。）
以 2026 逐投票所地理縮放（每黨票 × 民調份額／2026 份額），跑單一 top-3 孔多賽與複數聖拉古。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

COLS = ["JV", "ZZS", "AS", "NA", "S!", "LPV", "PRO", "AP", "SDPS", "GS", "SV", "K", "ASL", "MMN"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        raw = {c: float(r[c] or 0) for c in COLS}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        us = m.scale(m.units(2026), target)
        smd, lst, total, st, _ = m.chamber(us)
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）")
        print("民調%：", m.fmt({c: round(v * 100, 1) for c, v in target.items()}))
        print(f"單一 {m.SMD_TOTAL}：", m.fmt(smd), "；當選者第一偏好中位數", st["當選者第一偏好中位數"])
        print(f"複數 {m.LIST_TOTAL}：", m.fmt(lst))
        print(f"全院 {m.SMD_TOTAL + m.LIST_TOTAL}：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
