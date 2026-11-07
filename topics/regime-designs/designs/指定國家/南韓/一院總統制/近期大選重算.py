"""南韓一院總統制：把近期大選的**實際得票**套進本夾的制度。

與 生態模型.py 不同：這裡的第一偏好是開票紀錄，不是假設；只有第二偏好仍是 15 §2.3 的假設。

    python 近期大選重算.py            # 印出 17 用的數字
    python 近期大選重算.py --sweep    # 第二偏好與合併方式的敏感度

資料
- 2024-04 國會：中央選管委開票結果**逐邑面洞**（data.go.kr 15025527；資料/emd-2024.csv，2,847 個單位）。
  逐選區加總與舊版 254 區資料（ko/en.wikipedia）一致：民主黨 14,758,083、國民力量 13,179,769。
- 2024 比例代表各市道得票率、2025 與 2022 總統各市道得票：en.wikipedia 各選舉條目。

方法
- 單一 150：依各市道選舉人數以最大餘數分配，市道內把邑面洞依現行選區順序（大致依區、郡相鄰）、
  選區內官方邑面洞順序排好，按選舉人數切成等大的新區，跨界的邑面洞按比例拆分。
  第一偏好按**實際政黨**（build_kr_units）：2024 區域選舉是聯合推人（祖國革新黨未提名區域），
  所以每個邑面洞保留在地「進步 vs 保守」比例與改革新黨在地得票，陣營內各黨依市道名單得票拆分。
  決選者＝第一輪前 3 名政黨；top-3 孔多賽（kr_orders）。舊版只用區域候選人陣營的 single() 留給 --sweep。
- 複數 100：本夾 8 區（M 同 生態模型.py）；首都圈四區由首爾、仁川、京畿、江原的市道得票按人口混合。
  黑爾額數＋最大餘數、無門檻。「其他」名單拆成 10 個小名單。
- 總統：全國第一偏好＋第二偏好假設，孔多賽。
"""
import sys

import csv
import os
from 生態模型 import REGIONS, largest_remainder, region_seats

D, P, R, L, F, O = "民主黨", "國民力量", "改革新黨", "左翼小黨", "右翼小黨", "其他"
# 候選人政黨代碼 → 偏好群
GROUP = {"民": D, "國": P, "改": R, "進": L, "綠": L, "新": L, "統": F, "無": O, "他": O}
LABEL = {"民": "民主黨", "國": "國民力量", "改": "改革新黨", "進": "進步黨等", "綠": "綠色正義黨",
         "新": "新未來", "統": "自由統一黨等"}
Q = {D: 0.55, P: 0.90, R: 0.60}   # 15 §2.3


def orders(q):
    """各偏好群的完整排序與權重。O（無黨籍、其他）一半偏右、一半偏改革新黨→民主。"""
    return {
        D: [(q[D], [D, L, R, P, F]), (1 - q[D], [D, L, P, R, F])],
        P: [(q[P], [P, F, R, D, L]), (1 - q[P], [P, F, D, R, L])],
        R: [(q[R], [R, P, F, D, L]), (1 - q[R], [R, D, L, P, F])],
        L: [(1, [L, D, R, P, F])],
        F: [(1, [F, P, R, D, L])],
        O: [(0.5, [P, F, R, D, L]), (0.5, [R, D, L, P, F])],
    }


def pairwise(fp, a, b, q, override=None):
    """a 對 b 的得票。fp：{群: 票}。override：{群: a 排在 b 前的比例}，蓋過 orders。"""
    win = 0.0
    for g, v in fp.items():
        if override and g in override:
            win += v * override[g]
            continue
        for w, order in orders(q)[g]:
            if order.index(a) < order.index(b):
                win += v * w
    return win


def condorcet(fp, finalists, q, override=None):
    """三人 Ranked Pairs。回傳 (勝者, 是否循環, 兩兩表)。"""
    pw = {(a, b): pairwise(fp, a, b, q, override) for a in finalists for b in finalists if a != b}
    for a in finalists:
        if all(pw[(a, b)] > pw[(b, a)] for b in finalists if b != a):
            return a, False, pw
    wins = sorted(((pw[(a, b)], a, b) for a in finalists for b in finalists
                   if a != b and pw[(a, b)] > pw[(b, a)]), reverse=True)
    losers = {b for _, _, b in wins[:2]}
    return next(a for a in finalists if a not in losers), True, pw


# ---------------------------------------------------------------- 資料
# 2024 選區：(市道, 選區, 選舉人, {黨代碼: 得票})。代碼見 GROUP。
def load_units():
    """資料/emd-2024.csv（_build_emd.py；中央選管委 data.go.kr 15025527）：逐邑面洞（2,847 個）。
    選區層級的票（거소·선상、관외사전、국외부재자）依各邑面洞選舉日名冊比例分回；逐選區加總與原 254 區一致。
    回傳 [(市道, 選區/邑面洞, 選舉人, {黨代碼: 票})]，依選區、官方邑面洞順序。"""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "資料", "emd-2024.csv"), encoding="utf-8") as f:
        rows = list(csv.reader(f))
    cols = rows[0][4:]
    return [(r[0], f"{r[1]}/{r[2]}", int(r[3]), {c: int(v) for c, v in zip(cols, r[4:]) if int(v)}) for r in rows[1:]]


DISTRICTS_2024 = load_units()

# 省市: 投票者數(2024), 名單得票 % [國民未來, 更民主聯合, 祖國革新, 改革新, 自由統一, 綠色正義, 新未來, 其他],
#        2025 總統得票 [李在明, 金文洙, 李俊錫, 權英國, 宋鎮浩]
PROVINCES = {
    "서울": (5758158, [36.9, 26.2, 22.9, 4.4, 2.4, 2.7, 2.1, 2.4], [3105459, 2738405, 655346, 83900, 5998]),
    "부산": (1947016, [45.9, 20.8, 22.5, 3.2, 2.3, 1.6, 1.3, 2.5], [895213, 1146238, 168473, 18189, 2099]),
    "대구": (1312721, [60.2, 13.7, 11.8, 4.7, 3.0, 1.9, 1.2, 3.5], [379130, 1103913, 135376, 12531, 1362]),
    "인천": (1685267, [34.9, 30.0, 22.7, 3.3, 2.5, 2.3, 1.8, 2.6], [1044295, 776952, 176739, 20743, 2098]),
    "광주": (818073, [5.8, 36.3, 47.7, 2.3, 0.7, 1.5, 2.9, 2.9], [844682, 79937, 62104, 8767, 934]),
    "대전": (819637, [35.5, 27.7, 24.0, 3.8, 2.7, 1.9, 2.1, 2.3], [470321, 393549, 94724, 9905, 1109]),
    "울산": (624852, [41.8, 24.2, 22.2, 3.2, 1.8, 2.0, 1.4, 3.4], [315820, 353180, 63177, 9299, 899]),
    "세종": (211329, [29.9, 25.1, 30.9, 4.7, 1.8, 2.1, 3.4, 2.2], [140620, 83965, 25004, 2961, 235]),
    "경기": (7729678, [33.9, 29.1, 24.3, 4.1, 2.4, 2.2, 1.7, 2.3], [4821148, 3504620, 816435, 84074, 8356]),
    "강원": (887270, [43.6, 24.9, 20.1, 3.1, 2.3, 2.0, 1.3, 2.9], [449161, 483360, 78704, 9422, 1137]),
    "충북": (894695, [39.1, 27.5, 21.9, 3.1, 2.2, 2.1, 1.4, 2.8], [501990, 457065, 86984, 10169, 1228]),
    "충남": (1185666, [39.0, 28.3, 21.1, 2.9, 2.5, 2.0, 1.4, 2.8], [661316, 600108, 111092, 12893, 1519]),
    "전북": (1022298, [8.5, 37.6, 45.5, 2.0, 1.1, 1.5, 1.6, 2.3], [1023272, 134996, 67961, 10061, 1719]),
    "전남": (1080060, [6.6, 39.9, 44.0, 2.0, 0.9, 1.4, 2.3, 3.0], [1111941, 110624, 60822, 9352, 2104]),
    "경북": (1447715, [60.2, 14.7, 11.7, 3.2, 3.1, 1.9, 1.1, 4.0], [442683, 1159594, 116094, 13884, 1788]),
    "경남": (1877551, [46.2, 21.5, 20.5, 3.0, 2.0, 2.2, 1.2, 3.3], [851733, 1123843, 161579, 21809, 2678]),
    "제주": (352464, [31.4, 28.3, 27.9, 3.0, 1.3, 4.1, 1.5, 2.5], [228729, 145290, 36909, 6191, 528]),
}


# ---------------------------------------------------------------- 單一 150
def merge(districts=None, seats=150):
    """把現行選區切成 seats 個新區。回傳 [(市道, {黨代碼: 票}, 選舉人)]。"""
    districts = districts or DISTRICTS_2024
    prov = {}
    for p, _, e, v in districts:
        prov.setdefault(p, []).append((e, v))
    n = largest_remainder({p: sum(e for e, _ in rows) for p, rows in prov.items()}, seats)
    out = []
    for p, rows in prov.items():
        size = sum(e for e, _ in rows) / n[p]
        cur, room = {}, size
        for e, v in rows:
            left = e
            while left > 1e-6:
                take = min(left, room)
                for k, x in v.items():
                    cur[k] = cur.get(k, 0) + x * take / e
                left -= take
                room -= take
                if room <= 1e-6:
                    out.append((p, cur, size))
                    cur, room = {}, size
        if cur and sum(cur.values()) > 0:
            out.append((p, cur, size))
    assert len(out) == seats, len(out)
    return out


def groups(v):
    g = {}
    for k, x in v.items():
        g[GROUP[k]] = g.get(GROUP[k], 0) + x
    return g


def single(merged, q=Q, override=None):
    """回傳 ({黨: 席}, {市道: {黨: 席}}, 統計)。"""
    seats, by_prov = {}, {}
    st = {"循環": 0, "鐵票": 0, "相對多數不同": 0, "相對多數": {}}
    for p, v, _ in merged:
        g = groups(v)
        fin = sorted((x for x in g if x != O), key=lambda x: -g[x])[:3]
        w, cyc, _ = condorcet(g, fin, q, override)
        if w == L:   # 標出左翼小黨裡最大的那一黨
            name = LABEL[max((k for k in v if GROUP[k] == L), key=v.get)]
        else:
            name = w
        seats[name] = seats.get(name, 0) + 1
        by_prov.setdefault(p, {})
        by_prov[p][name] = by_prov[p].get(name, 0) + 1
        st["循環"] += cyc
        tot = sum(g.values())
        bloc = {D: g.get(D, 0) + g.get(L, 0), L: g.get(D, 0) + g.get(L, 0),
                P: g.get(P, 0) + g.get(F, 0), F: g.get(P, 0) + g.get(F, 0), R: g.get(R, 0)}[w]
        st["鐵票"] += bloc / tot > 0.5
        plur = LABEL.get(max(v, key=v.get), max(v, key=v.get))
        plur = {"民主黨": D, "國民力量": P}.get(plur, plur)
        st["相對多數"][plur] = st["相對多數"].get(plur, 0) + 1
        st["相對多數不同"] += plur != name
    return seats, by_prov, st


# ---------------------------------------------------------------- 複數 100
LIST_PARTIES = ["國民力量", "民主黨", "祖國革新黨", "改革新黨", "自由統一黨", "綠色正義黨", "新未來", "其他"]
# 本夾 8 區 = 各市道投票者 × 比例
MIX = {
    "首爾北＋京畿東北": {"서울": 0.5, "경기": 0.16},
    "首爾南＋京畿南": {"서울": 0.5, "경기": 0.16},
    "仁川＋京畿西": {"인천": 1, "경기": 0.29},
    "京畿東南＋江原": {"경기": 0.39, "강원": 1},
    "忠清": {"대전": 1, "세종": 1, "충북": 1, "충남": 1},
    "湖南＋濟州": {"광주": 1, "전북": 1, "전남": 1, "제주": 1},
    "大邱慶北＋蔚山": {"대구": 1, "경북": 1, "울산": 1},
    "釜山慶南": {"부산": 1, "경남": 1},
}


def region_shares(prov_shares):
    """prov_shares：{市道: {黨: %}} → {區: {黨: 票}}。"""
    out = {}
    for reg, mix in MIX.items():
        w = {}
        for p, f in mix.items():
            voters = PROVINCES[p][0] * f
            for k, x in prov_shares[p].items():
                w[k] = w.get(k, 0) + voters * x / 100
        out[reg] = w
    return out


def lists(prov_shares):
    m = region_seats(100)
    seats, by_reg = {}, {}
    for reg, w in region_shares(prov_shares).items():
        w = dict(w)
        other = w.pop("其他", 0)
        for i in range(10):
            w[f"其他{i}"] = other / 10
        got = largest_remainder(w, m[reg])
        by_reg[reg] = {k: x for k, x in got.items() if x}
        for k, x in got.items():
            if x:
                seats[k] = seats.get(k, 0) + x
    return seats, by_reg, m


def shares_2024():
    return {p: dict(zip(LIST_PARTIES, v[1])) for p, v in PROVINCES.items()}


# ---------------------------------------------------------------- 2025 民意代理
def swing_2025():
    """2024 選區得票加上各市道到 2025 總統得票的擺動。

    民主黨、國民力量：市道內加法擺動；改革新黨（李俊錫）、左翼小黨（權英國）：市道內均勻。
    """
    base = {}
    for p, _, e, v in DISTRICTS_2024:
        g = groups(v)
        b = base.setdefault(p, {})
        for k in (D, P):
            b[k] = b.get(k, 0) + g.get(k, 0)
        b["計"] = b.get("計", 0) + sum(g.values())
    out = []
    for p, n, e, v in DISTRICTS_2024:
        g = groups(v)
        t = sum(g.values())
        lee, kim, ljs, kwon, song = PROVINCES[p][2]
        pt = lee + kim + ljs + kwon + song
        new = {}
        new["民"] = max(0.005, g.get(D, 0) / t + lee / pt - base[p][D] / base[p]["計"])
        new["國"] = max(0.005, g.get(P, 0) / t + kim / pt - base[p][P] / base[p]["計"])
        new["改"] = ljs / pt
        new["進"] = kwon / pt
        new["他"] = song / pt
        s = sum(new.values())
        out.append((p, n, e, {k: x / s * t for k, x in new.items()}))
    return out


def shares_2025():
    """名單代理：2024 名單得票按陣營縮放到 2025 總統得票。
    左（民主、祖國革新、綠色正義、新未來）→ 李在明＋權英國；右（國民力量、自由統一）→ 金文洙；改革新黨 → 李俊錫。"""
    out = {}
    for p, (_, sh, pres) in PROVINCES.items():
        s = dict(zip(LIST_PARTIES, sh))
        pt = sum(pres)
        left = ["民主黨", "祖國革新黨", "綠色正義黨", "新未來"]
        right = ["國民力量", "自由統一黨"]
        lt, rt = sum(s[k] for k in left), sum(s[k] for k in right)
        new = {k: s[k] / lt * (pres[0] + pres[3]) / pt * 100 for k in left}
        new.update({k: s[k] / rt * pres[1] / pt * 100 for k in right})
        new["改革新黨"] = pres[2] / pt * 100
        new["其他"] = pres[4] / pt * 100
        out[p] = new
    return out


# ---------------------------------------------------------------- 總統
PRES_2025 = {D: 17287513, P: 14395639, R: 2917523, L: 344150, O: 35791}
# 2022：尹錫悅、李在明、沈相奵（正義黨）；許京寧等列 O，金在姸（進步黨）等左派列 L，趙源鎮等列 F
PRES_2022 = {P: 16394815, D: 16147738, "沈": 803358, L: 37366 + 18105 + 9176,
             F: 25972 + 4970, O: 281481 + 17305 + 11708 + 8317}


def president_2025(q=Q):
    w, cyc, pw = condorcet(PRES_2025, [D, P, R], q)
    return w, cyc, pw


def president_2022(sim_lee):
    """sim_lee：沈相奵選民把李在明排在尹錫悅前的比例。沈相奵的選民當作 L 群。"""
    fp = dict(PRES_2022)
    sim = fp.pop("沈")
    # 沈相奵是第三名決選者；她自己不可能是孔多賽贏家，勝負只看李對尹
    lee = fp[D] + sim * sim_lee + fp[L] + fp[O] * 0.5
    yoon = fp[P] + sim * (1 - sim_lee) + fp[F] + fp[O] * 0.5
    return lee, yoon


# ---------------------------------------------------------------- 政黨層級（主算）
# 2024 區域選舉兩大黨聯合推人（民主黨讓祖國革新黨不提名區域、綠色正義黨等在多數區讓出），
# 區域得票不是本制下的真誠第一偏好。主算把每個邑面洞拆回實際政黨：
#   保留該邑面洞的「進步 vs 保守」比例與改革新黨的在地得票（未提名處用市道名單得票率），
#   陣營內各黨依該市道名單得票比例（祖國革新黨在洞〔都市〕略強、邑面〔鄉村〕略弱）。
KJ, KL, KN, KF = "祖國革新黨", "綠色正義黨", "新未來", "自由統一黨"
QK = dict(Q)   # 15 §2.3：民主黨選民 55% 把改革新黨排在國民力量前、國民力量選民 90% 把改革新黨排在民主黨前、改革新黨選民 60% 把國民力量排在民主黨前


def kr_orders(q=QK):
    return {
        D: [(q[D], [D, KJ, KL, KN, R, P, KF]), (1 - q[D], [D, KJ, KL, KN, P, R, KF])],
        KJ: [(0.95, [KJ, D, KL, KN, R, P, KF]), (0.05, [KJ, KL, D, KN, P, R, KF])],
        KL: [(1.0, [KL, KJ, D, KN, R, P, KF])],
        KN: [(0.80, [KN, R, D, KJ, KL, P, KF]), (0.20, [KN, D, R, KJ, KL, P, KF])],
        R: [(q[R] * 0.6, [R, P, KF, KN, D, KJ, KL]), (q[R] * 0.4, [R, P, KF, KN, KJ, D, KL]),
            ((1 - q[R]) * 0.7, [R, KN, D, KJ, KL, P, KF]), ((1 - q[R]) * 0.3, [R, KN, KJ, D, KL, P, KF])],
        P: [(q[P] * 0.6, [P, KF, R, KN, D, KJ, KL]), (q[P] * 0.4, [P, KF, R, KN, KJ, D, KL]),
            (1 - q[P], [P, KF, KN, D, R, KJ, KL])],
        KF: [(1.0, [KF, P, R, KN, D, KJ, KL])],
        O: [(0.5, [P, KF, R, KN, D, KJ, KL]), (0.5, [R, KN, D, KJ, KL, P, KF])],
    }


def build_kr_units(districts, prov_shares):
    """逐邑面洞 {黨代碼: 票} → {政黨: 票}。"""
    stat = {}
    for p, name, e, v in districts:
        tot = sum(v.values()) or e or 1
        dong = 1.0 if name.split("/")[1].endswith("동") else 0.0
        s = stat.setdefault(p, [0.0, 0.0])
        s[0] += tot
        s[1] += tot * dong
    out = []
    for p, name, e, v in districts:
        sh = prov_shares[p]
        tot = sum(v.values()) or e or 1
        vl = sum(v.get(x, 0) for x in ("民", "進", "綠", "新"))
        vr = sum(v.get(x, 0) for x in ("國", "統"))
        vc = v.get("改", 0)
        dong = 1.0 if name.split("/")[1].endswith("동") else 0.0
        mod = 1.0 + 0.20 * (dong - stat[p][1] / stat[p][0])
        base_ref = sh.get("改革新黨", 0.0) / 100.0 * mod
        ref = max(vc / tot, base_ref) if vc > 0 else base_ref
        oth = sh.get("其他", 0.0) / 100.0
        rem = max(0.0, 1.0 - ref - oth)
        lk = [x for x in (D, KJ, KL, KN) if sh.get(x, 0.0) > 0]
        rk = [x for x in (P, KF) if sh.get(x, 0.0) > 0]
        sl, sr = sum(sh[x] for x in lk) or 1.0, sum(sh[x] for x in rk) or 1.0
        lr = vl / (vl + vr) if vl + vr > 0 else sl / (sl + sr)
        raw = {x: sh[x] for x in lk}
        if KJ in raw:
            raw[KJ] = sh[KJ] * mod
            raw[D] = max(0.1, sh[D] - sh[KJ] * (mod - 1.0))
        rs = sum(raw.values()) or 1.0
        pv = {x: tot * rem * lr * raw[x] / rs for x in lk}
        pv.update({x: tot * rem * (1 - lr) * sh[x] / sr for x in rk})
        pv[R] = tot * ref
        pv[O] = tot * oth
        out.append((p, name, e, pv))
    return out


def units_by_ratio(r, prov=None):
    """各黨相對 2024 的倍數 r → (逐邑面洞政黨票, 各市道名單得票%)。民調與生態模型推估共用。"""
    prov = prov or shares_2024()
    new = {}
    for p, sh in prov.items():
        w = {k: x * r.get(k, 1.0) for k, x in sh.items()}
        t = sum(w.values())
        new[p] = {k: x * 100 / t for k, x in w.items()}
    scaled = []
    for p, name, e, v in DISTRICTS_2024:
        nv = dict(v)
        sh = prov[p]
        if "民" in nv:
            nv["民"] *= (sh[D] * r.get(D, 1) + sh[KJ] * r.get(KJ, 1)) / (sh[D] + sh[KJ])
        if "國" in nv:
            nv["國"] *= r.get(P, 1)
        if "改" in nv:
            nv["改"] *= r.get(R, 1)
        scaled.append((p, name, e, nv))
    return build_kr_units(scaled, new), new


def kr_single(merged, q=QK, k=3):
    """top-k 孔多賽（Ranked Pairs）。回傳 ({黨: 席}, {市道: {黨: 席}}, 統計)。"""
    ords = kr_orders(q)
    seats, by_prov = {}, {}
    st = {"循環": 0, "鐵票": 0, "相對多數不同": 0, "相對多數": {}}
    left = (D, KJ, KL, KN)
    for p, v, _ in merged:
        fin = sorted((x for x in v if x != O and v[x] > 0), key=lambda x: (-v[x], x))[:k]
        pw = {(a, b): 0.0 for a in fin for b in fin if a != b}
        for g, val in v.items():
            for w, od in ords.get(g, []):
                rr = [x for x in od if x in fin]
                for i, a in enumerate(rr):
                    for b in rr[i + 1:]:
                        pw[(a, b)] += val * w
        win = next((a for a in fin if all(pw[(a, b)] > pw[(b, a)] for b in fin if b != a)), None)
        cyc = win is None
        if cyc:
            locked = set()

            def reach(x, y):
                todo, seen = [x], set()
                while todo:
                    u = todo.pop()
                    if u == y:
                        return True
                    seen.add(u)
                    todo += [b for a, b in locked if a == u and b not in seen]
                return False

            for _, a, b in sorted(((pw[(a, b)], a, b) for a in fin for b in fin
                                   if a != b and pw[(a, b)] > pw[(b, a)]), reverse=True):
                if not reach(b, a):
                    locked.add((a, b))
            win = next(a for a in fin if a not in {b for _, b in locked})
        seats[win] = seats.get(win, 0) + 1
        by_prov.setdefault(p, {})
        by_prov[p][win] = by_prov[p].get(win, 0) + 1
        st["循環"] += cyc
        tot = sum(v.values())
        bloc = sum(v.get(x, 0) for x in left) if win in left else (v.get(P, 0) + v.get(KF, 0) if win in (P, KF) else v.get(win, 0))
        st["鐵票"] += bloc / tot > 0.5
        st["相對多數"][fin[0]] = st["相對多數"].get(fin[0], 0) + 1
        st["相對多數不同"] += fin[0] != win
    return seats, by_prov, st


# ---------------------------------------------------------------- 輸出
THRESH = {"全院過半": 126, "全院 3/5": 150, "全院 2/3": 167}


def fmt(d):
    return "、".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0])) if v)


def total(s, l):
    t = dict(l)
    for k, x in s.items():
        k = {"進步黨等": "進步黨"}.get(k, k)
        t[k] = t.get(k, 0) + x
    return dict(sorted(t.items(), key=lambda kv: -kv[1]))


def report(title, districts, prov_shares, units=None):
    units = units or build_kr_units(districts, prov_shares)
    s, bp, st = kr_single(merge(units))
    l, br, m = lists(prov_shares)
    l = {k: x for k, x in l.items() if not k.startswith("其他")}
    print(f"## {title}")
    print(f"單一 150：{fmt(s)}")
    print(f"（第一輪最高票：{fmt(st['相對多數'])}；孔多賽與最高票不同 {st['相對多數不同']} 區；"
          f"循環 {st['循環']}；鐵票區 {st['鐵票']}）")
    print("（各市道：" + "；".join(f"{p} {fmt(v)}" for p, v in bp.items()) + "）")
    print(f"複數 100：{fmt(l)}")
    for reg, v in br.items():
        print(f"（{reg} M={m[reg]}：{fmt({k: x for k, x in v.items() if not k.startswith('其他')})}）")
    t = total(s, l)
    print(f"全院 250：{fmt(t)}")
    print()
    return s, l, t


def main():
    if "--sweep" in sys.argv:
        print("| 改革新黨選民把國民力量排前 | 2024 單一 民主／國民力量／其他 | 2025 代理 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|:--:|")
        for qr in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            q = dict(Q, **{R: qr})
            a, _, _ = single(merge(), q)
            b, _, _ = single(merge(swing_2025()), q)
            print(f"| {qr:.0%} | {a.get(D,0)}／{a.get(P,0)}／{150-a.get(D,0)-a.get(P,0)} "
                  f"| {b.get(D,0)}／{b.get(P,0)}／{b.get(R,0)} |")
        print()
        print("| 國民力量選民把改革新黨排前 | 2025 代理 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|")
        for qp in (0.5, 0.7, 0.9, 1.0):
            b, _, _ = single(merge(swing_2025()), dict(Q, **{P: qp}))
            print(f"| {qp:.0%} | {b.get(D,0)}／{b.get(P,0)}／{b.get(R,0)} |")
        print()
        print("| 民主黨選民把改革新黨排前 | 2025 代理 單一 民主／國民力量／改革 |")
        print("|:--:|:--:|")
        for qd in (0.3, 0.55, 0.8, 1.0):
            b, _, _ = single(merge(swing_2025()), dict(Q, **{D: qd}))
            print(f"| {qd:.0%} | {b.get(D,0)}／{b.get(P,0)}／{b.get(R,0)} |")
        print()
        print("合併順序反轉（市道內由後往前切）：")
        rev = []
        for p in dict.fromkeys(x[0] for x in DISTRICTS_2024):
            rev += [x for x in DISTRICTS_2024 if x[0] == p][::-1]
        a, _, _ = single(merge(rev))
        print("  2024 單一：", a)
        print()
        print("2022 總統：沈相奵選民把李在明排在尹錫悅前的比例")
        for x in (0.5, 0.6, 0.65, 0.7, 0.8, 0.9):
            lee, yoon = president_2022(x)
            print(f"  {x:.0%}：李 {lee/(lee+yoon):.2%} 尹 {yoon/(lee+yoon):.2%}")
        return

    report("2024-04 國會（實際得票）", DISTRICTS_2024, shares_2024())
    print()
    report("2025-06 民意代理（總統得票擺動）", swing_2025(), shares_2025())
    print()
    w, cyc, pw = president_2025()
    tot = sum(PRES_2025.values())
    print(f"2025 總統：{w}（循環 {cyc}）",
          {f"{a}對{b}": f"{pw[(a, b)] / (pw[(a, b)] + pw[(b, a)]):.1%}" for a, b in pw if a < b})
    lee, yoon = president_2022(0.8)
    print(f"2022 總統（沈相奵選民 80% 把李排前）：李 {lee/(lee+yoon):.2%}")
    for x in [i / 1000 for i in range(400, 1001)]:
        lee, yoon = president_2022(x)
        if lee > yoon:
            print(f"  李在明勝出所需：沈相奵選民 ≥{x:.1%} 把李排在尹前")
            break


if __name__ == "__main__":
    main()
