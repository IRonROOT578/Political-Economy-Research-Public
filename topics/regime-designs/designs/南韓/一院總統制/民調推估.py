"""南韓一院總統制：民調套本夾（政黨支持率的「相對選前變化」法）。

    python 民調推估.py

南韓公開民調多是**政黨支持率**，不是投票意向：無黨派約兩到三成，祖國革新黨的支持率（3%）遠低於它 2024 年的
名單得票（24%）。直接把支持率正規化當得票率會錯（同日本夾的教訓）。改法：
  r[黨] =（最新支持率＋0.5）／（同一家民調 2024 選前最後一期支持率＋0.5）
  區域：2024 逐邑面洞（資料/emd-2024.csv）先拆回實際政黨（近期大選推估.build_kr_units），各黨 × r，
  再切 150 區、top-3 孔多賽（祖國革新黨也是區域候選人）。
  名單：2024 各市道名單得票率每黨 × r 後正規化，8 區黑爾＋最大餘數。
  民調未列或選前未列的黨（進步黨、綠色正義、新未來、自由統一、無黨籍等）r＝1。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 近期大選推估 as K  # noqa: E402

CODE = {"民主黨": "民", "國民力量": "國", "祖國革新黨": "祖", "改革新黨": "改"}   # 進步黨選前未列（<0.5%），不調整


def ratios(base, new):
    return {p: (float(new[p]) + 0.5) / (float(base[p]) + 0.5) for p in CODE}


def run(r):
    units, prov = K.units_by_ratio(r)
    s, bp, st = K.kr_single(K.merge(units))
    l, _, _ = K.lists(prov)
    l = {k: x for k, x in l.items() if not k.startswith("其他")}
    return s, l, K.total(s, l), st


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    base = next(x for x in rows if x["role"] == "基準")
    for x in rows:
        if x["role"] == "基準":
            continue
        r = ratios(base, x)
        s, l, t, st = run(r)
        print(f"## {x['poll']} {x['fieldwork']}（{x['role']}；基準 {base['fieldwork']}）")
        print("（r：" + "、".join(f"{p} {v:.2f}" for p, v in r.items()) + "）")
        print(f"單一 150：{K.fmt(s)}")
        print(f"（第一輪最高票：{K.fmt(st['相對多數'])}）")
        print(f"複數 100：{K.fmt(l)}")
        print(f"全院 250：{K.fmt(t)}")
        print()


if __name__ == "__main__":
    main()
