"""法國一院議會制：民調套本夾。

    python 民調重算.py

輸入：資料/polls.csv（維基 Next French legislative election 投票意向表，「新人民陣線聯合推人」情境；
2025-10 之後無新的國會投票意向民調）。欄位併成本夾 7 群：
國＝RN＋UDR；左＝NFP＋DVG；中＝ENS＋DVC；共＝LR＋DVD；右＝REC＋DLF；極＝EXG；他＝ECO＋其他。

單一 230：2024 逐投票所單位（資料/legis-2024.csv）每群的票 × 民調份額／2024 實際份額，
  再用 近期大選重算.merge（同一張新選區圖）與 top-3 孔多賽。
複數 170：2024 歐洲議會各省名單票，依名單所屬陣營等比縮放到民調份額，14 區聖拉古（同主算）。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import csv  # noqa: E402
import 近期大選重算 as R  # noqa: E402

BLOC_COLS = {"國": ["RN_UDR"], "左": ["NFP", "DVG"], "中": ["ENS", "DVC"], "共": ["LR", "DVD"],
             "右": ["REC", "DLF"], "極": ["EXG"], "他": ["ECO", "其他"]}
ORDER = ["國", "左", "中", "共", "右", "極", "他"]          # = 近期大選重算.COLS 的順序
EURO_BLOC = {"國民聯盟系": "國", "復興系（中間）": "中", "社會黨系": "左", "不屈法國系": "左", "生態派": "左",
             "共產黨系": "左", "共和黨系": "共", "收復黨": "右", "法國退歐": "右", "愛國者": "右", "工人鬥爭": "極",
             "鄉村聯盟": "他", "動物黨": "他", "中間生態": "他"}


def scale_units(target):
    base = R.national(R.CIRC_2024)                      # {群: 份額}，不含海外法國人
    k = [target[g] / base[c] if base[c] else 0 for g, c in zip(ORDER, R.COLS)]
    return [(d, key, ins, tuple(v * f for v, f in zip(votes, k))) for d, key, ins, votes in R.CIRC_2024]


def scaled_euro(target, tiny=25):
    tot = {g: 0.0 for g in ORDER}
    for d, (v, other) in R.EURO_2024.items():
        for p, n in zip(R.EURO_PANELS, v):
            tot[EURO_BLOC[R.EURO_LABEL[p]]] += n
        tot["他"] += other
    s = sum(tot.values())
    k = {g: target[g] / (tot[g] / s) if tot[g] else 0 for g in ORDER}
    ws = []
    for ds in R.DEPTS:
        w = {}
        for d in ds:
            v, other = R.EURO_2024[d]
            for p, n in zip(R.EURO_PANELS, v):
                lab = R.EURO_LABEL[p]
                w[lab] = w.get(lab, 0) + n * k[EURO_BLOC[lab]]
            for i in range(tiny):
                w[f"其他{i}"] = w.get(f"其他{i}", 0) + other * k["他"] / tiny
        ws.append(w)
    return R._alloc(ws)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    seats = R.region_seats(R.CIRC_2024)
    o = R.all_orders()
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    import 政黨單位 as PU
    base = PU.party_units_2024()
    for r in rows:
        raw = {g: sum(float(r[c] or 0) for c in cs) for g, cs in BLOC_COLS.items()}
        print("（七群：" + "、".join(f"{g} {raw[g]:g}%" for g in ORDER) + "；陣營內各黨依 2024 歐洲議會比例）")
        PU.report(f"{r['poll']}（{r['fieldwork']}，n＝{r['n']}）", PU.scale_by_camp(base, raw), seats)


if __name__ == "__main__":
    main()
