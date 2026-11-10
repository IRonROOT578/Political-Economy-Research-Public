# -*- coding: utf-8 -*-
"""澳洲：2025 選區第一偏好，按 2026 年各家最新投票意向縮放。

    python 民調推估.py

輸入：資料/polls.csv。維基 Opinion polling for the next Australian federal election，
2026-11-08 頁面，每家取最新一筆。聯盟欄是自由黨＋自由國家黨＋國家黨＋鄉村自由黨的合計，
依 2025 這四黨在模型裡的得票比例拆開。Roy Morgan 把自由黨與國家黨分開，自由黨欄含昆士蘭自由國家黨，
國家黨欄含鄉村自由黨，同樣按 2025 比例拆。其餘（獨立、卡特、合法大麻等）維持彼此比例，
一起乘上「其他」的倍數。
"""
from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

COAL = ("自由黨", "自由國家黨", "國家黨", "鄉村自由黨")
LIB = ("自由黨", "自由國家黨")
NAT = ("國家黨", "鄉村自由黨")
NAMED = ("工黨", "綠黨", "一國黨") + COAL


def read_polls(path=None):
    path = path or os.path.join(HERE, "資料", "polls.csv")
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            def num(k):
                v = (r.get(k) or "").strip()
                return float(v) if v else None
            spec = {
                "工黨": num("工黨"),
                "聯盟": num("聯盟"),
                "自由黨": num("自由黨"),
                "國家黨": num("國家黨"),
                "綠黨": num("綠黨"),
                "一國黨": num("一國黨"),
                "其他": num("其他"),
            }
            name = f"{r['poll']}（{r['fieldwork']}，n＝{r['n']}）"
            out.append((name, spec))
    return out


def _split(total, parts, nat):
    base = sum(nat.get(p, 0) for p in parts)
    if not base:
        return {}
    return {p: total * nat.get(p, 0) / base for p in parts}


def scale_units(units, spec):
    nat = {}
    for u in units:
        for p, v in u[5].items():
            nat[p] = nat.get(p, 0) + v
    modeled = sum(nat.values()) or 1
    if spec["自由黨"] is not None:
        targets = {}
        targets.update(_split(spec["自由黨"], LIB, nat))
        targets.update(_split(spec["國家黨"] or 0, NAT, nat))
    else:
        targets = _split(spec["聯盟"], COAL, nat)
    targets["工黨"] = spec["工黨"]
    targets["綠黨"] = spec["綠黨"]
    targets["一國黨"] = spec["一國黨"]
    other_old = sum(v for p, v in nat.items() if p not in NAMED) / modeled
    ratios = {}
    for p, pct in targets.items():
        old = nat.get(p, 0) / modeled
        if old:
            ratios[p] = (pct / 100) / old
    other_ratio = (spec["其他"] / 100) / other_old if other_old else 0
    out = []
    for u in units:
        nv = {}
        for p, v in u[5].items():
            nv[p] = v * ratios.get(p, other_ratio)
        w = sum(nv.values())
        out.append((u[0], u[1], u[2], w, w, nv, u[6]))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    base, _ = m.load("2025-05")
    for name, spec in read_polls():
        units = m.assign_regions(m_scale(base, spec))
        smd, _ = m.single_seats(units)
        lst = m.list_seats(units)
        total = {}
        for d in (smd, lst):
            for p, n in d.items():
                total[p] = total.get(p, 0) + n
        pm, _, _ = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        shown = "、".join(
            f"{k} {spec[k]:g}" for k in ("工黨", "聯盟", "自由黨", "國家黨", "綠黨", "一國黨", "其他") if spec[k] is not None
        )
        print(f"## 民調 {name}")
        print("投票意向%", shown)
        print(f"單一 {m.SMD}：", m.fmt(smd))
        print(f"複數 {m.PR}：", m.fmt(lst))
        print(f"全院 {m.TOTAL}：", m.fmt(total))
        print(f"行政首長：{pm}")
        print(f"組閣：{'＋'.join(seq)}＝{acc}")
        print()


def m_scale(base, spec):
    return scale_units(base, spec)


if __name__ == "__main__":
    main()
