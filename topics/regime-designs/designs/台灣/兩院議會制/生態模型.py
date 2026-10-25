"""台灣兩院議會制：預期政治生態的機械效應模型。

國民院 100：單一選區 top-3 孔多賽（第一輪單記取前 3；第二輪 6 格完整排序單選，
    孔多賽完成法，循環時 Ranked Pairs）。
參議院 80：7 大區彈性名單，每區聖拉古，無得票門檻。

兩種選制與一院議會制夾的兩個成分相同，所以直接載入那一夾 生態模型.py 的選制函式；
本檔只放**本夾自己的假設**，另算兩院制才有的東西：普通法案的雙重同意、
中位法與修憲的兩院門檻，以及選民「制衡式分裂投票」的敏感度。
所有輸入都是假設（見 15 §2）；改假設就重跑，不要手改表。

    python 生態模型.py            # 印出 15 用的數字
    python 生態模型.py --sweep    # 制衡式分裂投票、第二偏好的敏感度
"""
import importlib.util
import itertools
import pathlib
import sys

_A = pathlib.Path(__file__).resolve().parent.parent / "一院議會制" / "生態模型.py"
_spec = importlib.util.spec_from_file_location("選制", _A)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

NA, SEN = 100, 80
LAW = (NA // 2 + 1, SEN // 2 + 1)                     # 普通法案：兩院各過總額半數
MID = (-(-NA * 3 // 5), -(-SEN * 3 // 5))             # 中位法、修憲提案：兩院各 3/5
URG = (-(-NA * 2 // 3), -(-SEN * 2 // 3))             # 急迫修憲：兩院各 2/3

# ---------------------------------------------------------------- 假設
# 國民院單一選區的第一偏好與第二偏好：同一批選民、同一種選制，沿用與一院議會制夾相同的假設。
# 參議院名單票：在一院議會制夾，名單那一票同樣進入全院組閣、也決定法案找誰談，
# 與本夾參議院（聯席組閣＋第二道同意）的功能相同，所以基準情境用同一組數字；選民為了制衡而把參議院票投給第三黨，
# 放在 --sweep 看（BALANCE）。
TERMS = {
    3: ({"民進黨": 38, "國民黨": 34, "民眾黨": 21, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.55},
        {"民進黨": 32, "國民黨": 30, "民眾黨": 21, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 3, "其他名單": 5}),
    5: ({"民進黨": 39, "國民黨": 35, "民眾黨": 19, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.85, "民眾黨": 0.50},
        {"民進黨": 32, "國民黨": 31, "民眾黨": 19, "時代力量": 5, "綠黨與環境團體聯盟": 4,
         "台灣基進": 4, "其他名單": 5}),
    8: ({"民進黨": 40, "國民黨": 36, "民眾黨": 17, "綠系小黨": 3, "地方型": 4},
        {"民進黨": 0.50, "國民黨": 0.80, "民眾黨": 0.45},
        {"民進黨": 32, "國民黨": 31, "民眾黨": 17, "時代力量": 6, "綠黨與環境團體聯盟": 5,
         "台灣基進": 4, "其他名單": 5}),
}


def senate(lst, gov=None, balance=0.0, to="民眾黨"):
    """參議院 80。balance：政府黨的名單票有這個比例改投 to（制衡式分裂投票）。"""
    lst = dict(lst)
    if gov and balance:
        moved = lst[gov] * balance
        lst[gov] -= moved
        lst[to] += moved
    shares = {k: v for k, v in lst.items() if k != "其他名單"}
    for i in range(5):
        shares[f"其他{i}"] = lst["其他名單"] / 5
    seats, mm = m.list_seats(shares, m.lean_of)
    other = sum(v for k, v in seats.items() if k.startswith("其他"))
    seats = {k: v for k, v in seats.items() if not k.startswith("其他")}
    seats["其他名單"] = other
    return seats, mm


def coalitions(na, sen, need, must=None, limit=2):
    """兩院都過 need 的最小組合（含 must 黨），回傳最多 limit 個。"""
    parties = sorted(set(na) | set(sen), key=lambda p: -(na.get(p, 0) + sen.get(p, 0)))
    out = []
    for k in range(1, len(parties) + 1):
        for c in itertools.combinations(parties, k):
            if must and must not in c:
                continue
            if any(set(o) <= set(c) for o, _, _ in out):
                continue
            a = sum(na.get(p, 0) for p in c)
            b = sum(sen.get(p, 0) for p in c)
            if a >= need[0] and b >= need[1]:
                out.append((c, a, b))
        if out:
            return out[:limit]
    return out


def run(t, balance=0.0, q=None):
    fp, q0, lst = TERMS[t]
    na = m.single_seats(fp, q or q0)
    gov = max(na, key=na.get)
    sen, mm = senate(lst, gov, balance)
    return na, sen, gov, mm


ORDER = ["台灣基進", "時代力量", "綠黨與環境團體聯盟", "民進黨", "民眾黨", "國民黨"]


def compare_rules():
    """某些議員取不同範圍時，政府怎麼組（見 00 §3.1）。"""
    import importlib.util as iu
    tool = pathlib.Path(__file__).resolve().parents[5] / "shared" / "tools" / "組閣比較.py"
    spec = iu.spec_from_file_location("組閣比較", tool)
    cmp = iu.module_from_spec(spec)
    spec.loader.exec_module(cmp)
    for t in TERMS:
        na, sen, gov, _ = run(t)
        sen = {k: v for k, v in sen.items() if k != "其他名單"}
        joint = {p: na.get(p, 0) + sen.get(p, 0) for p in set(na) | set(sen)}
        rows = cmp.compare([("甲 國民院 100", na, LAW[0]), ("乙 兩院聯席 180", joint, 91)], ORDER)
        print(f"第 {t} 屆")
        print(cmp.table(rows))
        both = coalitions(na, sen, LAW, None, 2)
        print("丙 兩院各自過半（最小組合）：" + "；".join(f"{'＋'.join(c)}（{a}、{b}）" for c, a, b in both))
        print()


def main():
    if "--某些議員" in sys.argv:
        compare_rules()
        return
    if "--sweep" in sys.argv:
        fp, q, lst = TERMS[3]
        na = m.single_seats(fp, q)
        print("| 國民黨名單票改投他黨的比例 | 改投民眾黨：國民＋民眾 | 改投民進黨：國民＋民眾 |")
        print("|:--:|:--:|:--:|")
        for b in (0.0, 0.05, 0.10, 0.15, 0.20):
            s1, _ = senate(lst, "國民黨", b, "民眾黨")
            s2, _ = senate(lst, "國民黨", b, "民進黨")
            print(f"| {b:.0%} | {s1['國民黨'] + s1['民眾黨']} | {s2['國民黨'] + s2['民眾黨']} |")
        print()
        print("| 民進黨選民把民眾黨排在國民黨前 | 第 3 屆國民院 民進／國民／民眾 | 政府黨 |")
        print("|:--:|:--:|:--:|")
        fp, q, _ = TERMS[3]
        for qd in (0.3, 0.4, 0.5, 0.6, 0.7):
            na, _, gov, _ = run(3, q=dict(q, **{"民進黨": qd}))
            print(f"| {qd:.0%} | {na['民進黨']}／{na['國民黨']}／{na['民眾黨']} | {gov} |")
        return
    for t in TERMS:
        na, sen, gov, mm = run(t)
        fp, q, _ = TERMS[t]
        ds = m.districts(fp, q)
        cyc = sum(c for _, _, c in ds)
        print(f"第 {t} 屆 國民院 100：{na}（循環 {cyc}）  政府黨 {gov}（{na[gov]}）")
        print(f"    參議院 80：{sen}")
        for name, need in (("普通法案", LAW), ("中位法／修憲", MID), ("急迫修憲", URG)):
            cs = coalitions(na, sen, need, None, 3)
            txt = "；".join(f"{'＋'.join(c)}（{a}、{b}）" for c, a, b in cs)
            print(f"    {name} {need}：{txt}")
        cs = coalitions(na, sen, LAW, gov, 2)
        txt = "；".join(f"{'＋'.join(c)}（{a}、{b}）" for c, a, b in cs)
        print(f"    政府黨要過普通法案：{txt}")
        for p in ("民進黨", "國民黨"):
            print(f"    {p} 派系 國民院 服務/政策 {m.factions(na[p], '單一')}  參議院 服務/政策 {m.factions(sen[p], '複數')}")
    print("參議院各區 M：", run(3)[3])


if __name__ == "__main__":
    main()
