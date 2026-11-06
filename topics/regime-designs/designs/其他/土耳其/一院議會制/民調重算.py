"""土耳其：民調套本夾。

    python 民調重算.py

民調輸入：資料/polls.csv（PolitPro 等彙整）。方法：以 2023-05 逐縣 的地理單位為基準，按民調權重縮放各黨得票（shared/tools/民調縮放.py；
民調裡的新黨從母黨依比例拆出：{"Yeni": "CHP", "Anahtar": "İYİ"}），再跑 生態模型.py 的同一套選制。
子黨比母黨大時（Yeni 對殘餘 CHP），子黨接手母黨位置、殘餘母黨只參加比例席次。
2026-11-04 依 估計結果.md §2 的民調輸入補寫（原本的民調圖沒有留下可重跑的程式）。
"""
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

PARENT = {"Yeni": "CHP", "Anahtar": "İYİ"}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pos0 = dict(m.POS)
    for kid, mom in PARENT.items():   # 新黨沿用母黨的政策位置（沒有位置就進不了單一席次的競爭）
        if mom in m.POS and kid not in m.POS:
            m.POS[kid] = m.POS[mom]
    for name, w in read_polls(os.path.join(HERE, "資料", "polls.csv")):
        m.POS.clear()
        m.POS.update(pos0)
        for kid, mom in PARENT.items():
            if mom in pos0:
                m.POS[kid] = pos0[mom]
                if w.get(kid, 0) > w.get(mom, 0):   # 子黨比母黨大（CHP 分裂後的繼承者）：殘餘母黨只參加比例席次
                    m.POS.pop(mom, None)
        us = scale(m.load("mv2023"), w, PARENT)
        smd, lst, total, _, _ = m.run("mv2023", units=us)
        pm = m.head_of_gov(total)[0]
        report(name, smd, lst, total, pm, m.coalition(total, pm))


if __name__ == "__main__":
    main()
