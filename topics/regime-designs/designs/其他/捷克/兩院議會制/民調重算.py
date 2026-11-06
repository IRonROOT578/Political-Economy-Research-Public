"""捷克兩院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（得票推估；ODS＋TOP09＋KDU-ČSL 合為 SPOLU；摘自 parliament_condorcet/czechia/data/input_vote_shares.csv）。
各列換算成全國份額（欄位空白＝0，再正規化），以 2025-10 **逐投票區**地理縮放
（每黨在每個投票區的票 × 目標份額／2025 份額），跑本夾的單一 110 top-3 孔多賽與複數 90 聖拉古。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        raw = {p: float(r[p] or 0) for p in m.P25}
        t = sum(raw.values())
        target = {p: v / t for p, v in raw.items()}
        smd, lst, total, _, _ = m.chamber(2025, override=target)
        w, _, worst = m.head_of_gov(total)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）")
        print("| 政黨 | 得票推估% | 單一 110 | 複數 90 | 眾議院 200 |")
        print("|---|--:|--:|--:|--:|")
        for p in sorted(m.P25, key=lambda p: (-total.get(p, 0), -raw[p])):
            print(f"| {p} | {r[p] or 0}% | {smd.get(p, 0)} | {lst.get(p, 0)} | **{total.get(p, 0)}** |")
        print(f"首長 {w}（最弱一場 {worst:.0f}）；對決", "、".join(f"對{b} {a:.0f}:{c:.0f}" for b, (a, c) in m.head_of_gov.last.items()))
        print()


if __name__ == "__main__":
    main()
