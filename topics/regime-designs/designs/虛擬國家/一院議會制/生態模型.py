"""範例國一院議會制（格式範本）：虛構得票 → 選制 → 席次 → 行政首長。

    python 生態模型.py              # 2026-04、2022-04 大選重算與民調
    python 生態模型.py --projection # 推估第 3 屆
    python 生態模型.py --sweep      # 敏感度檢查

本檔為格式範本的示範模型（虛構數字），直接內建 60 個單一選區與 4 個複數選區（北區 16、中區 14、南區 9、海外 1）的合成得票，
示範 `shared/tools/偏好模型.py` 與 `shared/tools/席次圖表格.py` 所需的標準輸出格式。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, *[".."] * 5, "shared", "tools"))
from 偏好模型 import Prefs  # noqa: E402

POS = {
    "甲": (0.0, 0.1),    # 居中
    "乙": (0.7, 0.6),    # 右
    "丙": (-0.5, -0.4),  # 左
    "丁": (-0.9, -0.8),  # 極左
    "戊": (1.0, 0.9),    # 極右
}
TYPES = [(0.5, 1.0, 0.5), (0.2, 0.5, 1.0), (0.3, 0.8, 0.8)]
BALANCED = (0.8, 0.8)
BLOC = {"甲": "中", "乙": "右", "戊": "右", "丙": "左", "丁": "左"}
SMD_TOTAL, LIST_TOTAL, NEED = 60, 40, 51
REGIONS = ["北區", "中區", "南區"]
SMD_N = {"北區": 24, "中區": 21, "南區": 15}
LIST_M = {"北區": 16, "中區": 14, "南區": 9, "海外": 1}


def prefs():
    return Prefs(POS, BLOC, 0.0, 0.0, {})


def head_of_gov(total):
    parties = [p for p, n in total.items() if n and p in POS]
    pr = prefs()
    groups = [(p, 1.0, pr.rank(pr.pos[p], p, parties, BALANCED)) for p in parties]
    # 孔多賽兩兩對決
    duel = {}
    for a in parties:
        wins = 0
        for b in parties:
            if a == b:
                continue
            ab = sum(total[g] for g, _, r in groups if r.index(a) < r.index(b))
            ba = sum(total[g] for g, _, r in groups if r.index(b) < r.index(a))
            if a == "甲":
                duel[b] = (ab, ba)
            if ab > ba:
                wins += 1
        if wins == len(parties) - 1:
            return a, 0, duel
    return "甲", 0, duel


def coalition(total, pm, need=NEED):
    return prefs().coalition(total, pm, need, BALANCED)


def fmt(d):
    order = ["甲", "乙", "丙", "丁", "戊"]
    return "、".join(f"{k} {d[k]}" for k in order if d.get(k))


SCENARIOS = {
    "2026-04": {
        "actual": "甲 41、乙 33、丙 18、丁 8（100）；甲＋丙 59 組閣",
        "share": {"甲": 32.0, "乙": 27.0, "丙": 17.0, "丁": 14.0, "戊": 10.0},
        "smd": {"甲": 38, "乙": 14, "丙": 8},
        "by": {
            "北區": {"甲": 16, "乙": 6, "丙": 2},
            "中區": {"甲": 14, "乙": 5, "丙": 2},
            "南區": {"甲": 8, "乙": 3, "丙": 4},
        },
        "st": {"循環": 0, "非第一偏好第一名當選": 14, "第一偏好過半": 0, "當選者第一偏好中位數": 33.4},
        "lst": {"甲": 12, "乙": 11, "丙": 7, "丁": 6, "戊": 4},
    },
    "2022-04": {
        "actual": "甲 36、乙 31、丙 24、丁 9（100）；甲＋丙 60 組閣",
        "share": {"甲": 28.0, "乙": 26.0, "丙": 21.0, "丁": 15.0, "戊": 10.0},
        "smd": {"甲": 31, "乙": 16, "丙": 13},
        "by": {
            "北區": {"甲": 13, "乙": 7, "丙": 4},
            "中區": {"甲": 12, "乙": 6, "丙": 3},
            "南區": {"甲": 6, "乙": 3, "丙": 6},
        },
        "st": {"循環": 0, "非第一偏好第一名當選": 16, "第一偏好過半": 0, "當選者第一偏好中位數": 30.8},
        "lst": {"甲": 11, "乙": 10, "丙": 9, "丁": 7, "戊": 3},
    },
    "民調 甲公司（2026-10-01..07）": {
        "actual": None,
        "share": {"甲": 34.0, "乙": 26.0, "丙": 17.0, "丁": 13.0, "戊": 10.0},
        "smd": {"甲": 36, "乙": 16, "丙": 8},
        "by": {
            "北區": {"甲": 15, "乙": 7, "丙": 2},
            "中區": {"甲": 13, "乙": 6, "丙": 2},
            "南區": {"甲": 8, "乙": 3, "丙": 4},
        },
        "st": {"循環": 0, "非第一偏好第一名當選": 12, "第一偏好過半": 0, "當選者第一偏好中位數": 34.2},
        "lst": {"甲": 10, "乙": 13, "丙": 8, "丁": 6, "戊": 3},
    },
    "推估第 3 屆": {
        "actual": None,
        "share": {"甲": 35.0, "乙": 25.5, "丙": 16.5, "丁": 13.0, "戊": 10.0},
        "smd": {"甲": 41, "乙": 12, "丙": 7},
        "by": {
            "北區": {"甲": 17, "乙": 5, "丙": 2},
            "中區": {"甲": 15, "乙": 4, "丙": 2},
            "南區": {"甲": 9, "乙": 3, "丙": 3},
        },
        "st": {"循環": 0, "非第一偏好第一名當選": 11, "第一偏好過半": 0, "當選者第一偏好中位數": 35.6},
        "lst": {"甲": 13, "乙": 10, "丙": 8, "丁": 6, "戊": 3},
    },
}


def report(label):
    sc = SCENARIOS[label]
    if sc["actual"]:
        print(f"\n實際：{sc['actual']}")
    smd, lst, st, by = sc["smd"], sc["lst"], sc["st"], sc["by"]
    total = {k: smd.get(k, 0) + lst.get(k, 0) for k in POS}
    pm, cyc, duel = head_of_gov(total)
    seq, acc = coalition(total, pm)
    print(f"## {label}")
    print("得票%：", "、".join(f"{k} {v:.1f}" for k, v in sc["share"].items()))
    print(f"單一 {SMD_TOTAL}：", fmt(smd), st)
    print("    各區：", "；".join(f"{r}（{SMD_N[r]}）{fmt(by[r])}" for r in REGIONS))
    print(f"複數 {LIST_TOTAL}：", fmt(lst))
    print(f"全院 {SMD_TOTAL + LIST_TOTAL}：", fmt(total), "合計", sum(total.values()))
    print(f"行政首長：{pm}；循環 {cyc}；對決 {duel}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(seq)}＝{acc}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"單一 {SMD_TOTAL}：", SMD_N)
    print(f"複數 {LIST_TOTAL}：", LIST_M)
    if "--sweep" in sys.argv:
        rows = [
            ("基準", "甲 38、乙 14、丙 8", "甲", "甲 31、乙 16、丙 13", "甲"),
            ("全部重軸一", "甲 39、乙 13、丙 8", "甲", "甲 32、乙 15、丙 13", "甲"),
            ("全部重軸二", "甲 36、乙 15、丙 9", "甲", "甲 30、乙 17、丙 13", "甲"),
            ("切線位移半區", "甲 37、乙 15、丙 8", "甲", "甲 31、乙 15、丙 14", "甲"),
            ("甲 −6／乙 ＋6 點", "甲 28、乙 24、丙 8", "甲", "甲 22、乙 25、丙 13", "甲"),
        ]
        for label, s26, pm26, s22, pm22 in rows:
            print(f"| {label} | {s26} | {pm26} | {s22} | {pm22} |")
        return
    if "--projection" in sys.argv:
        report("推估第 3 屆")
        return
    for label in ("2026-04", "2022-04", "民調 甲公司（2026-10-01..07）"):
        report(label)


if __name__ == "__main__":
    main()
