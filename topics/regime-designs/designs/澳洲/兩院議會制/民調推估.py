# -*- coding: utf-8 -*-
"""澳洲兩院：同一份 2026 民調，套進眾議院 180 與參議院 120。

    python 民調推估.py

票檔與 polls.csv 在一院夾。縮放規則與一院的 民調推估.py 相同。
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UNI = os.path.normpath(os.path.join(HERE, "..", "一院議會制"))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402

_spec = importlib.util.spec_from_file_location("au_uni_poll", os.path.join(UNI, "民調推估.py"))
poll = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(poll)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    base, _ = m.load("2025-05")
    for name, spec in poll.read_polls():
        units = poll.scale_units(base, spec)
        smd, _ = m.single_seats(units)
        house_u = m.assign_regions(units, m.HOUSE_POOL, m.HOUSE_M)
        senate_u = m.assign_regions(units, m.SENATE_POOL, m.SENATE_M)
        lst = m.list_seats(house_u, m.HOUSE_M)
        senate = m.list_seats(senate_u, m.SENATE_M)
        total = {}
        for d in (smd, lst):
            for p, n in d.items():
                total[p] = total.get(p, 0) + n
        pm, _, _ = m.head_of_gov(total)
        seq, acc = m.coalition(total, pm)
        print(f"## 民調 {name}")
        print(f"單一 {m.SMD}：", m.fmt(smd))
        print(f"複數 {m.HOUSE_PR}：", m.fmt(lst))
        print(f"全院 {m.HOUSE}：", m.fmt(total))
        print(f"行政首長：{pm}")
        print(f"組閣：{'＋'.join(seq)}＝{acc}")
        print(f"參議院 {m.SENATE}：", m.fmt(senate))
        print()


if __name__ == "__main__":
    main()
