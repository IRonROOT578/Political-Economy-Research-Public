"""希臘一院議會制：民調套本夾。

    python 民調推估.py

輸入：資料/polls.csv（維基 Opinion polling for the next Greek parliamentary election，投票意向；未決定不計，其餘正規化）。
2023 年後的新黨用母黨的逐選區地理拆出：SYRIZA → SYRIZA＋ELAS（Tsipras）＋DPK（Kasselakis）＋NA（新左翼）；
EL → EL＋FL（理性之聲）＋SE（希臘人聯盟）；ELPIDA（民主希望）沒有母黨，用全國均勻分布。
再以 2023-06 地理縮放（每黨票 × 民調份額／基準份額），跑單一 132 與複數 88。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

SPLIT = {"SYRIZA": ("SYRIZA", "ELAS", "DPK", "NA"), "EL": ("EL", "FL", "SE")}
COLS = ["ND", "SYRIZA", "PASOK", "KKE", "Spartans", "EL", "Victory", "PE", "MERA25", "FL", "NA", "SE", "DPK", "ELPIDA", "ELAS"]


def derive(units, raw):
    out = []
    for reg, c, res, v in units:
        v = dict(v)
        tot = sum(v.values())
        for parent, kids in SPLIT.items():
            x = v.pop(parent, 0)
            s = sum(raw[k] for k in kids) or 1
            for k in kids:
                v[k] = v.get(k, 0) + x * (raw[k] / s if s else 0)
        v["ELPIDA"] = tot * 0.01        # 均勻：之後縮放到民調份額
        out.append((reg, c, res, v))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        raw = {c: float(r[c] or 0) for c in COLS}
        t = sum(raw.values())
        target = {c: v / t for c, v in raw.items()}
        target["其他"] = 0.0
        us = m.scale(derive(m.load("2023-06"), raw), target)
        smd, lst, total, st, _ = m.chamber(us)
        pm, _, duel = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## {r['poll']}（{r['fieldwork']}，n＝{r['n']}）")
        print("民調%：", m.fmt({c: round(v * 100, 1) for c, v in target.items()}))
        print("單一 132：", m.fmt(smd), "；當選者第一偏好中位數", st["當選者第一偏好中位數"])
        print("複數 88：", m.fmt(lst))
        print("全院 220：", m.fmt(total))
        print(f"首長 {pm}；對決 {duel}；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
