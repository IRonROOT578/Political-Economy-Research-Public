"""芬蘭一院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（維基 Opinion polling for the 2027 Finnish parliamentary election；
Yle／Taloustutkimus、HS／Verian 各取最新一筆）。
以 2023-04 市鎮地理縮放（每黨票 × 民調份額／2023 份額），奧蘭單位原樣保留，
再跑單一 top-3 孔多賽與複數聖拉古。
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, *[".."] * 6, "shared", "tools"))
with contextlib.redirect_stdout(io.StringIO()):
    import 生態模型 as m  # noqa: E402
from 民調縮放 import read_polls, report, scale  # noqa: E402


def apply_poll(target: dict) -> list:
    units = m.load("2023-04")
    aland = [u for u in units if u[0] == "奧蘭"]
    rest = [u for u in units if u[0] != "奧蘭"]
    scaled = scale(rest, target, idx=5)
    out = []
    for u in scaled:
        # 保持浮點：小市鎮整數四捨五入會整區歸零
        votes = {p: float(v) for p, v in u[5].items() if v and float(v) > 0}
        valid = sum(votes.values())
        out.append((u[0], u[1], u[2], valid, valid, votes))
    out.extend(aland)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for name, w in read_polls(os.path.join(HERE, "資料", "polls.csv")):
        us = apply_poll(w)
        smd, lst, total, stats = m.run("2023-04", units=us)
        pm = m.head_of_gov(total)[0]
        print("stats", stats)
        report(name, smd, lst, total, pm, m.coalition(total, pm))


if __name__ == "__main__":
    main()
