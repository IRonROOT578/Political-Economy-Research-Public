"""義大利：民調套本夾。

    python 民調推估.py

輸入：資料/polls.csv（PolitPro 等彙整）。以 2022-09 逐市鎮為地理，
依民調權重縮放（shared/tools/民調縮放.py），再跑 生態模型.py 的 top-3／聖拉古。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
import 生態模型 as m  # noqa: E402
from 民調縮放 import read_polls, report, scale  # noqa: E402

# 民調標籤 → 模型政黨（2022 地理裡已有的名字）
PARENT = {
    "主權派": "主權派",
    "第三極": "第三極",
    "溫和派": "溫和派",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    base = m.load(2022)
    for name, w in read_polls(os.path.join(HERE, "資料", "polls.csv")):
        units = scale(base, w, parent=PARENT, idx=5)
        smd, lst, total, _, _ = m.run(2022, units=units)
        pm = m.head_of_gov(total)[0]
        coal = m.coalition(total, pm)
        report(name, smd, lst, total, pm, coal)


if __name__ == "__main__":
    main()
