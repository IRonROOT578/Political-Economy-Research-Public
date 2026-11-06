"""愛沙尼亞一院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（維基 Opinion polling for the next Estonian parliamentary election（投票意向；每家民調取最新一筆）。
ERK（Estonian Nationalists and Conservatives，自 EKRE 分出）用 EKRE 的逐投票所地理按民調比例拆出；Vasakliit＋Koos 併入 EÜVP。）
以 2023 逐投票所地理縮放（每黨票 × 民調份額／2023 份額），跑單一 top-3 孔多賽與複數聖拉古。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

COLS = ["RE", "EKRE", "KESK", "E200", "SDE", "IE", "EÜVP", "PP", "EER", "ERK", "其他"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        raw = {c: float(r[c] or 0) for c in COLS}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        kids = {k: raw[k] for k in ("EKRE", "ERK") if raw[k]}
        us = m.scale(m.split_party(m.units(2023), "EKRE", kids), target)
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
