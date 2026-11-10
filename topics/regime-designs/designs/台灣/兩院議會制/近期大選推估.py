"""台灣兩院議會制（方案 B）：拿往期大選實際得票與民調套本夾（17-近期大選重算.md）。

    python 近期大選推估.py               # 主算：2024／2020／2016／2012 不分區政黨票＋2026 民調
    python 近期大選推估.py --projection  # 長期推估（第 3 屆）
    python 近期大選推估.py --sweep       # 第二偏好 q 的敏感度

得票：中選會選舉資料庫逐村里結果（共用 ../一院議會制/資料/村里-YYYY.csv、名單-YYYY.csv）。
- 國民院單一 120：各區席次照 生態模型.region_seats(119)＋澎金馬 1；區內依「縣市碼 → 現行立委選區 → 鄉鎮 → 村里」連續切；
  多黨 top-3 孔多賽（第二偏好 Q_DEFAULT；小黨依 名單-YYYY.csv 各區實際政黨得票拆回各真實政黨），循環 Ranked Pairs。
- 國民院複數 30：全國一區，政黨票聖拉古、無門檻。
- 參議院 75：6 區比例（生態模型.SEN_M），政黨票聖拉古、無門檻；「其餘縣市與離島」的名單票依村里政黨票權重拆回縣市。
- 首長：國民院全院 150 記名排名（MP_RANK），≥76。普通法律：參議院擱置否決、國民院全院 ≥76 重新表決。
  中位法：國民院 ≥90 且參議院 ≥50。
★ 2012／2016 尚無民眾黨：村里檔「民眾黨」欄＝親民黨，輸出時改標「親民黨」。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED_TW = os.path.abspath(os.path.join(HERE, "..", "一院議會制"))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if SHARED_TW not in sys.path:
    sys.path.append(SHARED_TW)
import 方案A對照 as A  # noqa: E402
from 生態模型 import (  # noqa: E402
    AMEND_NA, AMEND_SEN, LIST_N, NEED, ORG_NA, ORG_SEN, PARTIES, Q_DEFAULT, SEN_M, SEN_N, SENATE_ORDER,
    SENATE_REGIONS, SMD_N, fmt, head_of_gov, region_seats, sainte_lague,
)
from 政黨單位 import condorcet_multi, region_minor_shares, village_party_prefs  # noqa: E402

Q = Q_DEFAULT
SEN_HALF = SEN_N // 2 + 1  # 38
REGION_TO_SEN = {"臺北市": "臺北基宜", "新北市": "新北", "桃園＋新竹縣市": "桃竹苗", "臺中＋彰化": "中彰投",
                 "雲嘉南": "雲嘉南", "高屏": "高屏花東澎金馬", "澎金馬": "高屏花東澎金馬"}
COUNTY_TO_SEN = {c: r for r, cs in SENATE_REGIONS.items() for c in cs}
COUNTY_TO_SEN["桃園縣"] = "桃竹苗"


def districts(rows):
    smd = region_seats(SMD_N - 1)
    out = []
    for reg in A.REGION_ORDER:
        part = [r for r in rows if r["區"] == reg]
        out += [(reg, d) for d in A.cut(part, smd[reg])]
    out.append(("澎金馬", [r for r in rows if r["區"] == "澎金馬"]))
    return out


def single(rows, q=Q, mode="政黨", year=2024, lmap=None, k=3):
    if mode != "政黨":
        raise ValueError("單一選區第一偏好只用不分區政黨票")
    seats, detail = {p: 0 for p in PARTIES}, []
    lmap = A.load_list(year) if lmap is None else lmap
    rg, rng = region_minor_shares(lmap, year, A.REGION_ORDER)
    for reg, d in districts(rows):
        fp = village_party_prefs(d, reg, year, mode, rg, rng)
        w, cyc, _, _, top1 = condorcet_multi(fp, q, k=k)
        seats[w] = seats.get(w, 0) + 1
        detail.append((reg, w, top1, cyc))
    return seats, detail


def senate_votes(year, rows):
    """名單票 → 參議院 6 區。"""
    raw = A.load_list(year)
    out = {r: {} for r in SENATE_ORDER}
    for reg, t in REGION_TO_SEN.items():
        for p, v in raw.get(reg, {}).items():
            out[t][p] = out[t].get(p, 0) + v
    rest = [r for r in rows if r["區"] == "其餘縣市與離島"]
    tot = sum(int(r["政黨票"]) for r in rest)
    w = {}
    for r in rest:
        t = COUNTY_TO_SEN[r["縣市"]]
        w[t] = w.get(t, 0) + int(r["政黨票"])
    for p, v in raw["其餘縣市與離島"].items():
        for t, x in w.items():
            out[t][p] = out[t].get(p, 0) + round(v * x / tot)
    return out


def pr(votes_by_region, m_map):
    out, by = {}, {}
    for reg, m in m_map.items():
        got = sainte_lague(votes_by_region[reg], m)
        for p, n in got.items():
            if n:
                sp = A.SHORT.get(p, p)
                out[sp] = out.get(sp, 0) + n
                by.setdefault(reg, {})[sp] = by.setdefault(reg, {}).get(sp, 0) + n
    return out, by


def national_list(year):
    raw = A.load_list(year)
    t = {}
    for reg, d in raw.items():
        for p, v in d.items():
            t[p] = t.get(p, 0) + v
    return t


def rules(total, sen, seq):
    """普通法律、中位法、修憲在兩院的結果（以首長的組閣陣營計）。"""
    na = sum(total.get(p, 0) for p in seq)
    se = sum(sen.get(p, 0) for p in seq)
    law = "兩院皆過" if na >= NEED and se >= SEN_HALF else ("參議院可擱置、國民院 ≥76 重新表決成立" if na >= NEED else "國民院不過")
    org = "可" if na >= ORG_NA and se >= ORG_SEN else "不可"
    return na, se, law, org


def combos(total, sen):
    big = [p for p in ("民進黨", "國民黨", "民眾黨", "親民黨") if total.get(p, 0) or sen.get(p, 0)]
    out = []
    for i, a in enumerate(big):
        for b in big[i + 1:]:
            na = total.get(a, 0) + total.get(b, 0)
            se = sen.get(a, 0) + sen.get(b, 0)
            out.append((f"{a}＋{b}", na, se, "可" if na >= ORG_NA and se >= ORG_SEN else "不可"))
    return out


def run(year, mode="政黨", q=Q, rows=None, list_votes=None, sen_votes=None, k=3):
    rows = A.load(year) if rows is None else rows
    s, detail = single(rows, q, mode, year=year, k=k)
    nl = national_list(year) if list_votes is None else list_votes
    l30, _ = pr({"全國": nl}, {"全國": LIST_N})
    sen, sen_by = pr(senate_votes(year, rows) if sen_votes is None else sen_votes, SEN_M)
    s = A.relabel_pre_tpp(year, s)
    l30 = A.relabel_pre_tpp(year, l30)
    sen = A.relabel_pre_tpp(year, sen)
    total = dict(l30)
    for p, n in s.items():
        if n:
            total[p] = total.get(p, 0) + n
    w, duel, seq, acc = head_of_gov(total, NEED)
    return dict(s=s, l=l30, total=total, sen=sen, sen_by=sen_by, w=w, duel=duel, seq=seq, acc=acc, detail=detail)


def report(label, r, year=2024):
    na, se, law, org = rules(r["total"], r["sen"], r["seq"])
    print(f"\n## {label}")
    print(f"單一 {SMD_N}：", fmt(r["s"]), "；循環", sum(d[3] for d in r["detail"]), "；當選者非第一偏好最多者",
          sum(1 for d in r["detail"] if d[1] != d[2]))
    print(f"複數 {LIST_N}：", fmt(r["l"]))
    print(f"全院 {SMD_N + LIST_N}：", fmt(r["total"]))
    print(f"參議院 {SEN_N}：", fmt(r["sen"]))
    print("    參議院各區：", "；".join(f"{k}（{SEN_M[k]}）{fmt(v)}" for k, v in r["sen_by"].items()))
    by = {}
    for reg, w, _, _ in r["detail"]:
        lab = "親民黨" if year < 2020 and w == "民眾黨" else w
        by.setdefault(reg, {}).setdefault(lab, 0)
        by[reg][lab] += 1
    print("    國民院各區單一：", "；".join(f"{k} {fmt(v)}" for k, v in by.items()))
    print(f"行政首長：{r['w']}；對決 {r['duel']}")
    print(f"組閣聯盟／多數派政府（由近到遠）：{'＋'.join(r['seq'])}＝{r['acc']}")
    print(f"規則：組閣陣營 國民院 {na}／參議院 {se}；普通法律 {law}；中位法 {org}（國民院 ≥{ORG_NA} 且參議院 ≥{ORG_SEN}）")
    print("    兩黨組合（國民院／參議院／中位法）：", "；".join(f"{a} {b}／{c} {d}" for a, b, c, d in combos(r["total"], r["sen"])))


POLLS_2026 = A.POLLS_2026


def scaled_rows(rows, share):
    tot = {p: sum(int(r[p]) for r in rows) for p in PARTIES}
    sc = {p: share[p] / tot[p] * sum(tot.values()) / sum(share.values()) for p in PARTIES}
    out = []
    for r in rows:
        nr = dict(r)
        for p in PARTIES:
            nr[p] = str(round(int(r[p]) * sc[p]))
        nr["綠系小黨"] = nr["地方型"] = nr["其他"] = "0"
        nr["政黨票"] = str(sum(int(nr[p]) for p in PARTIES))
        out.append(nr)
    return out


def three_party(rows):
    nat = {p: sum(int(r[p]) for r in rows) for p in PARTIES}
    sen = {k: {p: 0 for p in PARTIES} for k in SENATE_ORDER}
    for r in rows:
        for p in PARTIES:
            sen[COUNTY_TO_SEN[r["縣市"]]][p] += int(r[p])
    return nat, sen


def polls(k=3):
    rows = A.load(2024)
    for label, poll in POLLS_2026:
        sr = scaled_rows(rows, poll)
        nat, sen = three_party(sr)
        report(f"民調 {label}", run(2024, rows=sr, list_votes=nat, sen_votes=sen, k=k))


def projection(k=3):
    """第 3 屆（推測）：2024 地理；民進黨、國民黨各讓出 1/8 第一偏好給民眾黨（居中第三黨）。"""
    rows = A.load(2024)
    tot = {p: sum(int(r[p]) for r in rows) for p in PARTIES}
    share = {"民進黨": tot["民進黨"] * 7 / 8, "國民黨": tot["國民黨"] * 7 / 8}
    share["民眾黨"] = tot["民眾黨"] + (tot["民進黨"] + tot["國民黨"]) / 8
    sr = scaled_rows(rows, share)
    nat, sen = three_party(sr)
    return run(2024, rows=sr, list_votes=nat, sen_votes=sen, k=k)


YEARS = ((2024, "政黨"), (2020, "政黨"), (2016, "政黨"), (2012, "政黨"))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(f"國民院單一 {SMD_N} 各區：", dict(region_seats(SMD_N - 1), 澎金馬=1), f"；複數 {LIST_N} 全國一區；參議院 {SEN_N} 各區 M：", SEN_M)
    if "--projection" in sys.argv:
        report("推估第 3 屆", projection())
        return
    if "--sweep" in sys.argv:
        for year, mode in YEARS:
            print(f"\n### {year} {mode}票：q民進")
            print(f"| q民進 | 國民院單一 {SMD_N} | 國民院全院 150 | 首長 | 組閣 |")
            print("|:--:|---|---|---|---|")
            for qd in (0.2, 0.35, 0.5, 0.65, 0.8):
                r = run(year, mode, dict(Q, **{"民進黨": qd}))
                print(f"| {qd:.0%} | {fmt(r['s'])} | {fmt(r['total'])} | {r['w']} | {'＋'.join(r['seq'])}＝{r['acc']} |")
        return
    for year, mode in YEARS:
        mid = "親民黨" if year < 2020 else "民眾黨"
        report(f"{year}-01 {mode}票（中位第三黨＝{mid}）", run(year, mode), year)
    polls()


if __name__ == "__main__":
    main()
