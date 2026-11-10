"""台灣一院議會制：拿往期大選實際得票套本夾（17-近期大選重算.md）。

    python 近期大選推估.py           # 主算：2024／2020／2016／2012 不分區政黨票
    python 近期大選推估.py --sweep   # 第二偏好 q 的敏感度

得票：中選會選舉資料庫（votedata.zip）逐村里結果，彙整成 資料/村里-YYYY.csv、資料/名單-YYYY.csv。
第二偏好：沿用 生態模型.py 第 3 屆的 q（民進黨選民把中位第三黨排在國民黨前 50%、國民黨選民把中位第三黨排在民進黨前 85%、
中位第三黨選民把國民黨排在民進黨前 55%；綠系小黨與非綠小黨依 名單-YYYY.csv 各區實際政黨得票拆回各真實政黨）。
★ 2012／2016 尚無民眾黨：村里檔「民眾黨」欄＝**親民黨**不分區政黨票，輸出時改標「親民黨」。
單一 100：各區席次照 生態模型.region_seats(99)＋澎金馬 1；區內依「縣市碼 → 現行立委選區 → 鄉鎮 → 村里」連續切成
政黨票相近的選區（得跨縣市，與 01 §2.6 一致）；多黨 top-3 孔多賽，循環 Ranked Pairs。
複數 80：7 區，M＝生態模型.region_seats(80, 8, 14)，聖拉古、無門檻，每個政黨各自一張名單。
行政首長：全院 180 記名排名投票，議員依所屬政黨的固定排序（生態模型.MP_RANK）；須 ≥91。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from 生態模型 import NEED, PARTIES, TERMS, head_of_gov, region_seats, sainte_lague  # noqa: E402
from 政黨單位 import condorcet_multi, region_minor_shares, village_party_prefs  # noqa: E402

Q = TERMS[3][1]
GROUPS = ["民進黨", "國民黨", "民眾黨", "綠系小黨", "地方型"]
REGION_ORDER = ["臺北市", "新北市", "桃園＋新竹縣市", "臺中＋彰化", "雲嘉南", "高屏", "其餘縣市與離島"]


def load(year):
    with open(os.path.join(HERE, "資料", f"村里-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    h = rows[0]
    return [dict(zip(h, r)) for r in rows[1:]]


def load_list(year):
    with open(os.path.join(HERE, "資料", f"名單-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return {r[0]: {p: int(v) for p, v in zip(rows[0][1:], r[1:])} for r in rows[1:]}


def _split_row(r):
    """村里對半拆（票欄整數對分），供單位數 < 應切選區數時用。"""
    a, b = dict(r), dict(r)
    b["村里"] = r["村里"] + "·B"
    a["村里"] = r["村里"] + "·A"
    for k in r:
        if k in ("區", "縣市", "現行選區", "縣市碼", "鄉鎮碼", "村里碼", "村里"):
            continue
        try:
            v = int(r[k])
        except (TypeError, ValueError):
            continue
        a[k] = str(v // 2)
        b[k] = str(v - v // 2)
    return a, b


def cut(rows, n):
    rows = list(rows)
    if n <= 0:
        return []
    if not rows:
        raise ValueError(f"cut: empty rows for n={n}")
    guard = 0
    while len(rows) < n and guard < 5000:
        guard += 1
        i = max(range(len(rows)), key=lambda j: int(rows[j]["政黨票"]))
        if int(rows[i]["政黨票"]) <= 0:
            break
        a, b = _split_row(rows[i])
        rows[i:i + 1] = [a, b]
    target = sum(int(r["政黨票"]) for r in rows) / n if n else 0
    out, cur, acc = [], [], 0
    for r in rows:
        v = int(r["政黨票"])
        cur.append(r)
        acc += v
        if acc >= target * (len(out) + 1) - v / 2 and len(out) < n - 1:
            out.append(cur)
            cur = []
    out.append(cur)
    while len(out) < n:
        i = max(range(len(out)), key=lambda j: sum(int(x["政黨票"]) for x in out[j]))
        block = out[i]
        if len(block) < 2:
            block = list(_split_row(block[0]))
        mid = max(1, len(block) // 2)
        out[i:i + 1] = [block[:mid], block[mid:]]
    while len(out) > n:
        best = min(range(len(out) - 1),
                   key=lambda j: sum(int(x["政黨票"]) for x in out[j]) + sum(int(x["政黨票"]) for x in out[j + 1]))
        out[best:best + 2] = [out[best] + out[best + 1]]
    assert len(out) == n and all(out), (len(out), n, len(rows))
    return out


def districts(rows):
    smd = region_seats(99)
    out = []
    for reg in REGION_ORDER:
        part = [r for r in rows if r["區"] == reg]
        out += [(reg, d) for d in cut(part, smd[reg])]
    out.append(("澎金馬", [r for r in rows if r["區"] == "澎金馬"]))
    return out


def first_prefs(villages, mode="政黨"):
    if mode != "政黨":
        raise ValueError("單一選區第一偏好只用不分區政黨票")
    t = {g: sum(int(r[g]) for r in villages) for g in GROUPS}
    s = sum(t.values())
    return {g: v / s for g, v in t.items()}


def single(rows, q=Q, mode="政黨", year=2024, lmap=None, k=3):
    if mode != "政黨":
        raise ValueError("單一選區第一偏好只用不分區政黨票")
    seats, detail = {p: 0 for p in PARTIES}, []
    lmap = load_list(year) if lmap is None else lmap
    rg, rng = region_minor_shares(lmap, year, REGION_ORDER)
    for reg, d in districts(rows):
        fp = village_party_prefs(d, reg, year, mode, rg, rng)
        w, cyc, _, _, top1 = condorcet_multi(fp, q, k=k)
        seats[w] = seats.get(w, 0) + 1
        detail.append((reg, d[0]["縣市"], d[0]["村里"], w, top1, cyc, fp))
    return seats, detail


def lists(year):
    m = region_seats(80, 8, 14)
    votes = load_list(year)
    out = {}
    for reg in REGION_ORDER:
        d = dict(votes[reg])
        if reg == "其餘縣市與離島":
            for p, v in votes.get("澎金馬", {}).items():
                d[p] = d.get(p, 0) + v
        for p, n in sainte_lague(d, m[reg]).items():
            if n:
                out[p] = out.get(p, 0) + n
    return out, m


SHORT = {
    "民主進步黨": "民進黨", "中國國民黨": "國民黨", "台灣民眾黨": "民眾黨",
    "親民黨": "親民黨", "時代力量": "時代力量", "台灣團結聯盟": "台聯", "綠黨": "綠黨",
    "台灣綠黨": "綠黨",
}


def relabel_pre_tpp(year, d):
    """2012／2016：孔多賽中位槽在資料裡叫民眾黨，對外改親民黨。"""
    if year >= 2020 or "民眾黨" not in d:
        return d
    out = dict(d)
    v = out.pop("民眾黨", 0)
    if v:
        out["親民黨"] = out.get("親民黨", 0) + v
    return out


def head(total):
    """全院 180 選首長：回傳首長所屬黨、對決、組閣陣營與席次。"""
    w, duel, seq, acc = head_of_gov(total)
    return w, duel, seq, acc


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda x: -x[1]) if v)


def report(year, mode="政黨", q=Q, verbose=True, k=3):
    rows = load(year)
    s, detail = single(rows, q, mode, year=year, k=k)
    l, m = lists(year)
    l = {SHORT.get(p, p): n for p, n in l.items()}
    s = relabel_pre_tpp(year, s)
    total = dict(l)
    for p, n in s.items():
        if n:
            total[p] = total.get(p, 0) + n
    w, duel, seq, acc = head(total)
    if not verbose:
        return s, total, w
    mid = "親民黨" if year < 2020 else "民眾黨"
    print(f"\n## {year}（第一偏好＝{mode}票；中位第三黨＝{mid}）")
    print("單一 100：", fmt(s), "；循環", sum(d[5] for d in detail), "；當選者非第一偏好最多者",
          sum(1 for d in detail if d[3] != d[4]))
    print("複數 80：", fmt(l))
    print("全院 180：", fmt(total))
    print(f"行政首長（全院 180，≥{NEED}）：{w}；對決 {duel}；組閣陣營 {'＋'.join(seq)}＝{acc}")
    by = {}
    for d in detail:
        lab = "親民黨" if year < 2020 and d[3] == "民眾黨" else d[3]
        by.setdefault(d[0], {}).setdefault(lab, 0)
        by[d[0]][lab] += 1
    print("各區單一：", "；".join(f"{r} {fmt(c)}" for r, c in by.items()))
    if "-v" in sys.argv:
        for d in detail:
            print("   ", d[0], d[1], d[2], d[3], "循環" if d[5] else "", {k2: round(v * 100) for k2, v in d[6].items()})
    return s, total, w


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("單一 100 各區：", dict(region_seats(99), 澎金馬=1), "；複數 80 各區 M：", region_seats(80, 8, 14))
    years_modes = ((2024, "政黨"), (2020, "政黨"), (2016, "政黨"), (2012, "政黨"))
    if "--sweep" in sys.argv:
        for year, mode in years_modes:
            print(f"\n### {year} {mode}票：民進黨選民把中位第三黨排在國民黨前的比例 q民進")
            print("| q民進 | 單一 100 | 首長 |")
            print("|:--:|---|---|")
            for qd in (0.2, 0.35, 0.5, 0.65, 0.8):
                s, _, w = report(year, mode, dict(Q, **{"民進黨": qd}), verbose=False)
                print(f"| {qd:.0%} | {fmt(s)} | {w} |")
        return
    for year, mode in years_modes:
        report(year, mode)


if __name__ == "__main__":
    main()
