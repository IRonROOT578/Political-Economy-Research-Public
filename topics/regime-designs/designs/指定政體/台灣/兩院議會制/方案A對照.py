"""台灣兩院議會制【方案 A 對照】：舊結構（國民院 90＋60、參議院縣市單一 75）套往期大選（17 §5 並排用）。

    python 方案A對照.py           # 主算：2024／2020／2016／2012 政黨票＋總統票版＋2026 民調
    python 方案A對照.py --sweep   # 第二偏好 q 的敏感度

得票：中選會選舉資料庫（votedata.zip）逐村里結果（共用 ../一院議會制/資料/村里-YYYY.csv、名單-YYYY.csv）。
第二偏好：沿用 生態模型.py 的 Q_DEFAULT（民進黨選民把中位第三黨排在國民黨前 50%、國民黨選民把中位第三黨排在民進黨前 85%、
中位第三黨選民把國民黨排在民進黨前 55%；綠系小黨 民進>中位>國民、地方型 國民>中位>民進）。
★ 2012／2016 尚無民眾黨：村里檔「民眾黨」欄＝**親民黨**政黨票（或總統票＝宋楚瑜），輸出時改標「親民黨」。
- 國民院單一 90：各區席次照 生態模型.region_seats(89)＋澎金馬 1（得跨縣市）；區內依「縣市碼 → 現行立委選區 → 鄉鎮 → 村里」連續切成
  政黨票相近的選區；三黨 top-3 孔多賽，循環 Ranked Pairs。
- 國民院複數 60：5 大區（北北基宜 14、桃竹苗 11、中彰投 13、雲嘉南 10、高屏東＋花東＋澎金馬 12），聖拉古、無門檻。
- 參議院單一 75：澎金馬 1＋本島 19 縣市各保底 1 席後依人口聖拉古分配共 74 席（選區不跨縣市），top-3 孔多賽。
- 行政首長：國民院全院 150 記名排名投票（生態模型.MP_RANK），過半門檻 ≥76；普通法律另須參議院 ≥38 雙重同意；
  基本法與修憲提案須國民院 ≥90（且複數席次 ≥36/60）且參議院 ≥45。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "資料") if os.path.isdir(os.path.join(HERE, "資料")) else os.path.join(HERE, "..", "一院議會制", "資料")
sys.path.insert(0, HERE)
from 生態模型 import (  # noqa: E402
    COUNTY_ORDER,
    MACRO_5_ORDER,
    M_NA_60,
    NEED,
    PARTIES,
    Q_DEFAULT,
    SEN_NEED,
    condorcet,
    fmt,
    head_of_gov,
    rankings,
    region_seats,
    sainte_lague,
    senate_county_seats,
)

Q = Q_DEFAULT
GROUPS = ["民進黨", "國民黨", "民眾黨", "綠系小黨", "地方型"]
REGION_ORDER = ["臺北市", "新北市", "桃園＋新竹縣市", "臺中＋彰化", "雲嘉南", "高屏", "其餘縣市與離島"]

REST_TO_MACRO5 = {
    "基隆市": "北北基宜",
    "宜蘭縣": "北北基宜",
    "苗栗縣": "桃竹苗",
    "南投縣": "中彰投",
    "花蓮縣": "高屏東＋花東＋澎金馬",
    "臺東縣": "高屏東＋花東＋澎金馬",
}

MACRO5_COUNTIES = {
    "北北基宜": {"臺北市", "新北市", "基隆市", "宜蘭縣"},
    "桃竹苗": {"桃園市", "桃園縣", "新竹縣", "新竹市", "苗栗縣"},
    "中彰投": {"臺中市", "彰化縣", "南投縣"},
    "雲嘉南": {"雲林縣", "嘉義縣", "嘉義市", "臺南市"},
    "高屏東＋花東＋澎金馬": {"高雄市", "屏東縣", "臺東縣", "花蓮縣", "澎湖縣", "金門縣", "連江縣"},
}

SHORT = {
    "民主進步黨": "民進黨",
    "中國國民黨": "國民黨",
    "台灣民眾黨": "民眾黨",
    "親民黨": "親民黨",
    "時代力量": "時代力量",
    "台灣團結聯盟": "台聯",
    "台灣綠黨": "綠黨",
    "綠黨": "綠黨",
    "綠黨社會民主黨聯盟": "綠黨社會民主黨聯盟",
    "台灣基進": "台灣基進",
    "新黨": "新黨",
}


def load(year):
    with open(os.path.join(DATA, f"村里-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    h = rows[0]
    return [dict(zip(h, r)) for r in rows[1:]]


def load_list(year):
    with open(os.path.join(DATA, f"名單-{year}.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return {r[0]: {p: int(v) for p, v in zip(rows[0][1:], r[1:])} for r in rows[1:]}


def _split_row(r):
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
    smd = region_seats(89)
    out = []
    for reg in REGION_ORDER:
        part = [r for r in rows if r["區"] == reg]
        out += [(reg, d) for d in cut(part, smd[reg])]
    out.append(("澎金馬", [r for r in rows if r["區"] == "澎金馬"]))
    return out


def senate_districts(rows):
    """參議院 75 席縣市單一選區（本島 19 縣市不跨界共 74 席＋澎金馬 1 席）。"""
    cs_map = senate_county_seats(74)
    out = []
    for c in COUNTY_ORDER:
        part = [r for r in rows if r["縣市"] == c]
        out += [(c, d) for d in cut(part, cs_map[c])]
    out.append(("澎金馬", [r for r in rows if r["區"] == "澎金馬"]))
    return out


def first_prefs(villages, mode):
    if mode == "總統":
        t = {"民進黨": 0, "國民黨": 0, "民眾黨": 0}
        for r in villages:
            for p in t:
                t[p] += int(r[f"總統_{p}"])
        t["綠系小黨"] = t["地方型"] = 0
    else:
        t = {g: sum(int(r[g]) for r in villages) for g in GROUPS}
    s = sum(t.values())
    return {g: v / s for g, v in t.items()}


def single(rows, q=Q, mode="政黨"):
    seats, detail = {p: 0 for p in PARTIES}, []
    for reg, d in districts(rows):
        fp = first_prefs(d, mode)
        b = rankings(fp, q)
        w = condorcet(b)
        P = lambda a, c: sum(v for r, v in b.items() if r.index(a) < r.index(c))
        cyc = not any(all(P(a, c) > P(c, a) for c in PARTIES if c != a) for a in PARTIES)
        seats[w] += 1
        detail.append((reg, d[0]["縣市"], d[0]["村里"], w, max(PARTIES, key=fp.get), cyc, fp))
    return seats, detail


def senate_single(rows, q=Q, mode="政黨"):
    seats, detail = {p: 0 for p in PARTIES}, []
    for c, d in senate_districts(rows):
        fp = first_prefs(d, mode)
        b = rankings(fp, q)
        w = condorcet(b)
        P = lambda a, c2: sum(v for r, v in b.items() if r.index(a) < r.index(c2))
        cyc = not any(all(P(a, c2) > P(c2, a) for c2 in PARTIES if c2 != a) for a in PARTIES)
        seats[w] += 1
        detail.append((c, d[0]["縣市"], d[0]["村里"], w, max(PARTIES, key=fp.get), cyc, fp))
    return seats, detail


def votes_macro5(year, rows=None):
    """將 7 區名單得票依村里政黨票權重拆回 5 大區（北北基宜、桃竹苗、中彰投、雲嘉南、高屏東＋花東＋澎金馬）。"""
    rows = load(year) if rows is None else rows
    raw = load_list(year)
    out = {k: {} for k in MACRO_5_ORDER}
    for reg, target in (
        ("臺北市", "北北基宜"),
        ("新北市", "北北基宜"),
        ("桃園＋新竹縣市", "桃竹苗"),
        ("臺中＋彰化", "中彰投"),
        ("雲嘉南", "雲嘉南"),
        ("高屏", "高屏東＋花東＋澎金馬"),
        ("澎金馬", "高屏東＋花東＋澎金馬"),
    ):
        for p, v in raw.get(reg, {}).items():
            out[target][p] = out[target].get(p, 0) + v
    rest_rows = [r for r in rows if r["區"] == "其餘縣市與離島"]
    tot_rest = sum(int(r["政黨票"]) for r in rest_rows)
    w_target = {}
    for r in rest_rows:
        t = REST_TO_MACRO5[r["縣市"]]
        w_target[t] = w_target.get(t, 0) + int(r["政黨票"])
    for p, v in raw["其餘縣市與離島"].items():
        for t, w in w_target.items():
            out[t][p] = out[t].get(p, 0) + round(v * w / tot_rest)
    return out


def lists_5(year, m_map, rows=None):
    v5 = votes_macro5(year, rows)
    out = {}
    for reg in MACRO_5_ORDER:
        for p, n in sainte_lague(v5[reg], m_map[reg]).items():
            if n:
                sp = SHORT.get(p, p)
                out[sp] = out.get(sp, 0) + n
    return out


def relabel_pre_tpp(year, d):
    if year >= 2020 or "民眾黨" not in d:
        return d
    out = dict(d)
    out["親民黨"] = out.get("親民黨", 0) + out.pop("民眾黨", 0)
    return out


def report(year, mode="政黨", q=Q, verbose=True):
    rows = load(year)
    s, detail = single(rows, q, mode)
    l60 = lists_5(year, M_NA_60, rows)
    sen75, sen_detail = senate_single(rows, q, mode)
    s = relabel_pre_tpp(year, s)
    sen75 = relabel_pre_tpp(year, sen75)
    total = dict(l60)
    for p, n in s.items():
        if n:
            total[p] = total.get(p, 0) + n
    w, duel, seq, acc = head_of_gov(total, NEED)
    _, _, sen_seq, sen_acc = head_of_gov(sen75, SEN_NEED)
    if not verbose:
        return s, total, w, sen75
    mid = "親民黨" if year < 2020 else "民眾黨"
    print(f"\n## {year}（第一偏好＝{mode}票；中位第三黨＝{mid}）")
    print("國民院單一 90：", fmt(s), "；循環", sum(d[5] for d in detail), "；當選者非第一偏好最多者",
          sum(1 for d in detail if d[3] != d[4]))
    print("國民院複數 60：", fmt(l60))
    print("國民院全院 150：", fmt(total))
    print("參議院單一 75：", fmt(sen75), "；循環", sum(d[5] for d in sen_detail), "；當選者非第一偏好最多者",
          sum(1 for d in sen_detail if d[3] != d[4]))
    print(f"行政首長（國民院全院 150，≥{NEED}）：{w}；對決 {duel}；組閣陣營 {'＋'.join(seq)}＝{acc}")
    print(f"參議院 75（雙重同意 ≥{SEN_NEED}）：{fmt(sen75)}；同陣營在參議院 {'＋'.join(p for p in seq if sen75.get(p))}＝{sum(sen75.get(p, 0) for p in seq)}（過半需 {'＋'.join(sen_seq)}＝{sen_acc}）")
    by = {}
    for d in detail:
        lab = "親民黨" if year < 2020 and d[3] == "民眾黨" else d[3]
        by.setdefault(d[0], {}).setdefault(lab, 0)
        by[d[0]][lab] += 1
    print("國民院各區單一：", "；".join(f"{r} {fmt(c)}" for r, c in by.items()))
    by_sen = {}
    for d in sen_detail:
        lab = "親民黨" if year < 2020 and d[3] == "民眾黨" else d[3]
        by_sen.setdefault(d[0], {}).setdefault(lab, 0)
        by_sen[d[0]][lab] += 1
    print("參議院各縣市單一：", "；".join(f"{r} {fmt(c)}" for r, c in by_sen.items()))
    return s, total, w, sen75


POLLS_2026 = [
    ("美麗島（2026-09-29..10-02）", {"民進黨": 43.1, "國民黨": 26.5, "民眾黨": 21.0}),
    ("戴立安（2026-10-20..22）", {"民進黨": 49.0, "國民黨": 27.9, "民眾黨": 26.3}),
]


def report_polls():
    rows = load(2024)
    tot_2024 = {p: sum(int(r[p]) for r in rows) for p in PARTIES}
    for label, poll in POLLS_2026:
        scale = {p: poll[p] / tot_2024[p] * sum(tot_2024.values()) / sum(poll.values()) for p in PARTIES}
        scaled = []
        for r in rows:
            nr = dict(r)
            for p in PARTIES:
                nr[p] = str(round(int(r[p]) * scale[p]))
            nr["綠系小黨"] = nr["地方型"] = "0"
            nr["政黨票"] = str(sum(int(nr[p]) for p in PARTIES))
            scaled.append(nr)
        s90, _ = single(scaled, Q, "政黨")
        sen75, _ = senate_single(scaled, Q, "政黨")
        l60 = {p: 0 for p in PARTIES}
        for reg, cs in MACRO5_COUNTIES.items():
            part = [r for r in scaled if r["縣市"] in cs]
            w = {p: sum(int(r[p]) for r in part) for p in PARTIES}
            for p, n in sainte_lague(w, M_NA_60[reg]).items():
                l60[p] += n
        tot150 = {p: s90[p] + l60[p] for p in PARTIES}
        hog, duel, seq, acc = head_of_gov(tot150, NEED)
        print(f"\n## 民調 {label}")
        print("國民院單一 90：", fmt(s90))
        print("國民院複數 60：", fmt(l60))
        print("國民院全院 150：", fmt(tot150))
        print(f"行政首長（國民院全院 150，≥{NEED}）：{hog}；組閣陣營 {'＋'.join(seq)}＝{acc}；參議院單一 75：{fmt(sen75)}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("國民院單一 90 各區：", dict(region_seats(89), 澎金馬=1), "；國民院複數 60 各大區 M：", M_NA_60, "；參議院單一 75 各縣市：", dict(senate_county_seats(74), 澎金馬=1))
    years_modes = ((2024, "政黨"), (2024, "總統"), (2020, "政黨"),
                   (2016, "政黨"), (2016, "總統"), (2012, "政黨"), (2012, "總統"))
    if "--sweep" in sys.argv:
        for year, mode in years_modes:
            print(f"\n### {year} {mode}票：民進黨選民把中位第三黨排在國民黨前的比例 q民進")
            print("| q民進 | 國民院單一 90 | 國民院全院 150 | 參議院單一 75 | 首長 |")
            print("|:--:|---|---|---|---|")
            for qd in (0.2, 0.35, 0.5, 0.65, 0.8):
                s, tot, w, sen = report(year, mode, dict(Q, **{"民進黨": qd}), verbose=False)
                print(f"| {qd:.0%} | {fmt(s)} | {fmt(tot)} | {fmt(sen)} | {w} |")
        return
    for year, mode in years_modes:
        report(year, mode)
    report_polls()


if __name__ == "__main__":
    main()
