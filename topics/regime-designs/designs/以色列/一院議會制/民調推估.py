"""以色列：民調套本夾。

    python 民調推估.py

民調輸入：資料/polls.csv（維基；現行比例制席次當權重）。方法：以 2026-10 逐票匭（含信封票） 的地理單位為基準，按民調權重縮放各黨得票（shared/tools/民調縮放.py；
民調裡的新黨從母黨依比例拆出：{}），再跑 生態模型.py 的同一套選制。
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

PARENT = {}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for name, w in read_polls(os.path.join(HERE, "資料", "polls.csv")):
        units, env, cols = m.load("2026-10")
        both = scale(units + [("信封", None, None, 0, env)], w, PARENT, idx=4)
        smd, lst, total, _, _ = m.run("2026-10", units_env=(both[:-1], both[-1][4], cols))
        report(name, smd, lst, total, m.head_of_gov("2026-10", total)[0])


if __name__ == "__main__":
    main()
