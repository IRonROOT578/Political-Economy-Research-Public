"""南韓一院總統制：民調套本夾（政黨支持率的「相對選前變化」法）。

    python 民調重算.py

南韓公開民調多是**政黨支持率**，不是投票意向：無黨派約兩到三成，祖國革新黨的支持率（3%）遠低於它 2024 年的
名單得票（24%）。直接把支持率正規化當得票率會錯（同日本夾的教訓）。改法：
  r[黨] =（最新支持率＋0.5）／（同一家民調 2024 選前最後一期支持率＋0.5）
  區域：2024 逐邑面洞得票（資料/emd-2024.csv）每黨 × r，再切 150 區、top-3 孔多賽（同 近期大選重算.py）。
  名單：2024 各市道名單得票率每黨 × r 後正規化，8 區黑爾＋最大餘數。
  民調未列或選前未列的黨（進步黨、綠色正義、新未來、自由統一、無黨籍等）r＝1。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 近期大選重算 as K  # noqa: E402

CODE = {"民主黨": "民", "國民力量": "國", "祖國革新黨": None, "改革新黨": "改"}   # 進步黨選前未列（<0.5%），不調整
LIST = {"民主黨": "民主黨", "國民力量": "國民力量", "祖國革新黨": "祖國革新黨", "改革新黨": "改革新黨"}


def ratios(base, new):
    return {p: (float(new[p]) + 0.5) / (float(base[p]) + 0.5) for p in CODE}


def run(r):
    units = []
    for p, n, e, v in K.DISTRICTS_2024:
        nv = dict(v)
        for party, c in CODE.items():
            if c and c in nv:
                nv[c] *= r[party]
        units.append((p, n, e, nv))
    prov = {}
    for p, sh in K.shares_2024().items():
        w = {k: x * r[k] if k in LIST else x for k, x in sh.items()}
        t = sum(w.values())
        prov[p] = {k: x * 100 / t for k, x in w.items()}
    s, bp, st = K.single(K.merge(units))
    l, _, _ = K.lists(prov)
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
        print("r：", "、".join(f"{p} {v:.2f}" for p, v in r.items()))
        print("單一 150：", dict(sorted(s.items(), key=lambda kv: -kv[1])), " 相對多數：", st["相對多數"])
        print("複數 100：", dict(sorted(l.items(), key=lambda kv: -kv[1])))
        print("全院 250：", t)
        print()


if __name__ == "__main__":
    main()
