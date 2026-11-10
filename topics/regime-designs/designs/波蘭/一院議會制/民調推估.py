"""波蘭一院議會制：民調套本夾。

    python 民調推估.py

輸入：資料/polls.csv（維基 Opinion polling for the next Polish parliamentary election，投票意向；不知道、不回答不計，其餘正規化）。
2023 後分裂或分開參選的黨，用 2023 母黨的逐投票所地理按民調比例拆開：
  TD → 波蘭 2050（PL2050）＋人民黨（PSL）；Lewica → Lewica＋Razem；Konf → Konf＋KKP；PiS → PiS＋R+（2026-07 分出）。
再以 2023 逐投票所地理縮放（每黨票 × 民調份額／2023 份額），跑單一 204 top-3 孔多賽與複數 136 聖拉古。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

SPLIT = {"TD": ("PL2050", "PSL"), "Lewica": ("Lewica", "Razem"), "Konf": ("Konf", "KKP"), "PiS": ("PiS", "R+")}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = ["PiS", "KO", "PL2050", "PSL", "Lewica", "Razem", "Konf", "KKP", "R+", "其他"]
    for r in rows:
        raw = {c: float(r[c] or 0) for c in cols}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        us = m.units(2023)
        for parent, kids in SPLIT.items():
            us = m.split_party(us, parent, {k: raw[k] for k in kids})
        for p in ("BS", "MN"):        # 民調沒列 → 併入其他
            us = [(u[0], u[1], u[2], u[3], u[4], {**{k: v for k, v in u[5].items() if k != p}, "其他": u[5].get("其他", 0) + u[5].get(p, 0)}) for u in us]
        us = m.scale(us, target)
        smd, lst, total, st, _ = m.chamber(us)
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）")
        print("民調%：", m.fmt({c: round(v * 100, 1) for c, v in target.items()}))
        print("單一 204：", m.fmt(smd), "；當選者第一偏好中位數", st["當選者第一偏好中位數"])
        print("複數 136：", m.fmt(lst))
        print("全院 340：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
