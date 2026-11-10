"""西班牙：民調套本夾。

    python 民調推估.py

民調輸入：資料/polls.csv（維基、parliament_condorcet 彙整）。方法：以 2023-07 逐市鎮 的地理單位為基準，按民調權重縮放各黨得票（shared/tools/民調縮放.py；
民調裡的新黨從母黨依比例拆出：{"PODE": "SUMAR", "SALF": "VOX", "FV": "其他", "ADEL": "其他"}），再跑 生態模型.py 的同一套選制。
2026-11-04 依 估計結果.md §2 的民調輸入補寫（原本的民調圖沒有留下可重跑的程式）。
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
with contextlib.redirect_stdout(io.StringIO()):
    import 生態模型 as m  # noqa: E402
from 民調縮放 import read_polls, report, scale  # noqa: E402

PARENT = {"PODE": "SUMAR", "SALF": "VOX", "FV": "其他", "ADEL": "其他"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for kid, mom in PARENT.items():   # 新黨沿用母黨的政策位置（沒有位置就進不了單一席次的競爭）
        if mom in m.POS and kid not in m.POS:
            m.POS[kid] = m.POS[mom]
    for name, w in read_polls(os.path.join(HERE, "資料", "polls.csv")):
        w.setdefault("其他", max(0.0, 100 - sum(w.values())))
        us = scale(m.load("congreso-2023"), w, PARENT)
        smd, lst, total, _, _ = m.run("congreso-2023", units=us)
        pm = m.head_of_gov(total)[0]
        report(name, smd, lst, total, pm, m.coalition(total, pm))


if __name__ == "__main__":
    main()
