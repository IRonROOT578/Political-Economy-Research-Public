"""斯洛伐克一院議會制：民調套本夾。

    python 民調推估.py

輸入：資料/polls.csv（維基 Opinion polling for the next Slovak parliamentary election，投票意向）。
2023 年 OĽaNO a priatelia 名單裡的 Slovensko（Matovič）、Za ľudí、基督教聯盟（KÚ），用 OĽaNO 的逐投票區地理按民調比例拆開；
再以 2023 地理縮放（每黨票 × 民調份額／2023 份額），跑單一 90 top-3 孔多賽與複數 60 聖拉古。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

COLS = ["Smer", "PS", "Hlas", "Slovensko", "ZĽ", "KÚ", "KDH", "SaS", "SNS", "Republika", "Aliancia", "Demokrati", "SmeRodina", "ĽSNS", "其他"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        raw = {c: float(r[c] or 0) for c in COLS}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        kids = {k: raw[k] for k in ("Slovensko", "ZĽ", "KÚ") if raw[k]}
        us = m.scale(m.split_party(m.units(2023), "OĽaNO", kids), target)
        smd, lst, total, st, _ = m.chamber(us)
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）")
        print("民調%：", m.fmt({c: round(v * 100, 1) for c, v in target.items()}))
        print("單一 90：", m.fmt(smd), "；當選者第一偏好中位數", st["當選者第一偏好中位數"])
        print("複數 60：", m.fmt(lst))
        print("全院 150：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
