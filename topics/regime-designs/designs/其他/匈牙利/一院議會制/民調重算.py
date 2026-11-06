"""匈牙利一院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（維基 Opinion polling for the 2030 Hungarian parliamentary election；有政黨偏好者的份額）。
以 2026-04 逐投票所地理縮放（每黨票 × 民調份額／2026 份額），跑單一 120 top-3 孔多賽與複數 80 聖拉古。
海外郵寄票那一列一併縮放（民調不含海外選民，這是簡化）。民調未列的德意志族名單併入其他。
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
    cols = ["TISZA", "FIDESZ", "MI", "DK", "MKKP", "其他"]
    base = []
    for u in m.units(2026):
        v = dict(u[5])
        v["其他"] = v.get("其他", 0) + v.pop("德意志族", 0)
        base.append((u[0], u[1], u[2], u[3], u[4], v))
    for r in rows:
        raw = {c: float(r[c] or 0) for c in cols}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        smd, lst, total, st, _ = m.chamber(m.scale(base, target))
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）{r['備註']}")
        print("民調%：", m.fmt({c: round(v * 100, 1) for c, v in target.items()}))
        print("單一 120：", m.fmt(smd), "；當選者第一偏好中位數", st["當選者第一偏好中位數"])
        print("複數 80：", m.fmt(lst))
        print("全院 200：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
