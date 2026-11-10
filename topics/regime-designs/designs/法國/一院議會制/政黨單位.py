"""法國一院議會制：政黨層級的共用計算（近期大選推估、民調推估、生態模型三支共用）。

呈現原則（方案 A）：所有表、席次圖、首長、組閣一律用同一組 10 個政黨名稱，不混用陣營：
  國民聯盟系、收復黨、共和黨系、鄉村聯盟、復興系（含 Ensemble 盟友民主運動、地平線）、
  社會黨系、生態派、共產黨系、不屈法國系、各類極左。
本制下各黨自行參選（沒有兩輪制的聯合推人誘因），所以第一偏好用各黨的「真誠第一偏好」：
2024 歐洲議會（法國唯一的全國政黨名單選舉）各省政黨票，依 2024 國會第一輪逐投票所的陣營分布
分到「市鎮×選區」單位；陣營在該選區讓出時，改用盟友陣營的分布。

第二偏好：二維空間（左右 × 開放／威權），三型選民（重左右、重開放、均衡）依距離排序。
與 2024 第二輪轉移調查一致：左派各黨 左 > 復興系 > 共和黨系 > 國民聯盟系；復興系 約 65% 偏社會黨系、
35% 偏共和黨系，強烈排斥國民聯盟系；共和黨系 約 65% 復興系 > 國民聯盟系、35% 反之。
"""
import 近期大選推估 as R
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), *[".."] * 5, "shared", "tools"))
from 參選判定 import finalists as _finalists  # noqa: E402

POS = {
    "各類極左": (-1.00, -0.35),
    "不屈法國系": (-0.85, -0.40),
    "共產黨系": (-0.75, -0.25),
    "生態派": (-0.55, -0.85),
    "社會黨系": (-0.35, -0.55),
    "復興系": (0.15, -0.45),
    "共和黨系": (0.50, 0.20),
    "鄉村聯盟": (0.45, 0.55),
    "國民聯盟系": (0.55, 0.95),
    "收復黨": (0.85, 1.00),
}
TYPES = [(0.35, 1.0, 0.5), (0.35, 0.5, 1.0), (0.30, 0.8, 0.8)]   # (比例, 左右權重, 開放權重)
BALANCED = (0.8, 0.8)
NEED = 201

# 歐洲議會名單 → (本夾政黨, 國會第一輪陣營欄 0國 1左 2中 3共 4右 5極 6他)
PANEL_MAP = [
    (5, "國民聯盟系", 0), (11, "復興系", 2), (27, "社會黨系", 1), (4, "不屈法國系", 1),
    (18, "共和黨系", 3), (6, "生態派", 1), (3, "收復黨", 4), (33, "共產黨系", 1),
    (29, "鄉村聯盟", 6), (8, "動物黨", 6), (35, "中間生態", 2), (15, "法國退歐", 4),
    (24, "愛國者", 4), (19, "各類極左", 5),
]
CAMP = {"國民聯盟系": "國", "復興系": "中", "中間生態": "他", "社會黨系": "左", "不屈法國系": "左",
        "生態派": "左", "共產黨系": "左", "共和黨系": "共", "收復黨": "右", "法國退歐": "右", "愛國者": "右",
        "各類極左": "極", "鄉村聯盟": "他", "動物黨": "他", "其他": "他"}


def rank_from(me, cands, w):
    a = POS[me]
    return sorted(cands, key=lambda c: (sum((wi * (x - y)) ** 2 for wi, x, y in zip(w, POS[c], a)), c))


def voter_groups(parties, types=TYPES):
    return [(p, t[0], rank_from(p, parties, t[1:])) for p in parties for t in types]


def pairwise_winner(cands, groups, weight):
    """孔多賽；循環時 Ranked Pairs。回傳 (勝者, 是否循環, 兩兩表)。"""
    cands = sorted(cands)
    P = {(a, b): 0.0 for a in cands for b in cands if a != b}
    for src, w, order in groups:
        v = weight(src) * w
        if not v:
            continue
        r = [c for c in order if c in cands]
        for i, a in enumerate(r):
            for b in r[i + 1:]:
                P[(a, b)] += v
    for a in cands:
        if all(P[(a, b)] > P[(b, a)] for b in cands if b != a):
            return a, False, P
    wins = sorted(((P[(a, b)], a, b) for a in cands for b in cands if a != b and P[(a, b)] > P[(b, a)]), reverse=True)
    locked = set()

    def reach(x, y):
        st, seen = [x], set()
        while st:
            u = st.pop()
            if u == y:
                return True
            for s, t in locked:
                if s == u and t not in seen:
                    seen.add(t)
                    st.append(t)
        return False

    for _, a, b in wins:
        if not reach(b, a):
            locked.add((a, b))
    top = [c for c in cands if not any(t == c for _, t in locked)] or list(cands)
    return top[0], True, P


def party_units_2024():
    """2024 歐洲議會各省政黨票 → 2024 國會「市鎮×選區」單位（依陣營分布）。"""
    by_dep = {}
    for u in R.CIRC_2024:
        by_dep.setdefault(u[0], []).append(u)
    out = []
    for dep, units in by_dep.items():
        ev, e_other = R.EURO_2024[dep]
        circ_camp = {}
        for _, key, _, votes in units:
            cc = circ_camp.setdefault(key[1], [0] * 7)
            for i in range(7):
                cc[i] += votes[i]
        unit_w, dep_w, tot_sum = [], [0.0] * 7, 0.0
        for _, key, ins, votes in units:
            cc = circ_camp[key[1]]
            tot = sum(votes) or ins or 1
            tot_sum += tot
            w = [0.0] * 7
            for i in range(7):
                if cc[i] > 0:
                    w[i] = float(votes[i])
                elif i == 2:   # 中間讓出：用共和黨系＋三成左翼
                    w[i] = float(votes[3] + 0.3 * votes[1]) or tot * 0.15
                elif i == 3:   # 共和黨系讓出：用中間＋半數國民聯盟
                    w[i] = float(votes[2] + 0.5 * votes[0]) or tot * 0.10
                elif i == 4:
                    w[i] = float(votes[0] + 0.5 * votes[3]) or tot * 0.05
                elif i == 5:
                    w[i] = float(votes[1]) or tot * 0.01
                else:
                    w[i] = float(tot)
                dep_w[i] += w[i]
            unit_w.append((w, tot))
        for (dep, key, ins, _), (w, tot) in zip(units, unit_w):
            pv = {}
            for idx, (_, name, c) in enumerate(PANEL_MAP):
                share = w[c] / dep_w[c] if dep_w[c] > 0 else tot / tot_sum
                pv[name] = pv.get(name, 0.0) + ev[idx] * share
            pv["其他"] = e_other * tot / tot_sum
            out.append((dep, key, ins, pv))
    return out


def party_units_2022():
    """2022 國會第一輪各陣營票，依該省 2024 歐洲議會陣營內政黨比例拆成政黨。"""
    out = []
    for dep, key, ins, votes in R.CIRC_2022:
        ev, e_other = R.EURO_2024[dep]
        camp = [0.0] * 7
        for idx, (_, _, c) in enumerate(PANEL_MAP):
            camp[c] += ev[idx]
        camp[6] += e_other
        pv = {}
        for idx, (_, name, c) in enumerate(PANEL_MAP):
            pv[name] = pv.get(name, 0.0) + (votes[c] * ev[idx] / camp[c] if camp[c] else 0.0)
        pv["其他"] = votes[6] * e_other / camp[6] if camp[6] else 0.0
        out.append((dep, key, ins, pv))
    return out


def _scale(units, key, targets):
    tot = {}
    for dep, _, _, pv in units:
        if dep == R.DROPPED:
            continue
        for p, v in pv.items():
            tot[key(p)] = tot.get(key(p), 0.0) + v
    s, t = sum(tot.values()), sum(targets.values())
    k = {g: (targets.get(g, 0.0) / t) / (tot[g] / s) if tot.get(g) else 0.0 for g in tot}
    return [(dep, kk, ins, {p: v * k[key(p)] for p, v in pv.items()}) for dep, kk, ins, pv in units]


def scale_by_camp(units, targets):
    """民調只有陣營份額（國左中共右極他）：陣營內各黨等比縮放。"""
    return _scale(units, lambda p: CAMP[p], targets)


def scale_by_party(units, targets):
    """生態模型的政黨份額假設：逐黨縮放（未列者歸零）。"""
    return _scale(units, lambda p: p, targets)


def _cut(units, m):
    u = sorted(units, key=lambda x: x[1])
    target = sum(x[2] for x in u) / m
    res = [{} for _ in range(m)]
    d, acc = 0, 0.0
    for _, _, ins, votes in u:
        rem = float(ins)
        while rem > 1e-9:
            need = target - acc
            last = d == m - 1 or rem <= need + 1e-9
            take = rem if last else need
            f = take / ins if ins else 0.0
            for p, v in votes.items():
                res[d][p] = res[d].get(p, 0.0) + v * f
            rem -= take
            if last:
                acc += take
            else:
                d, acc = d + 1, 0.0
    return res


def merge_p(units, seats):
    """單一 230：14 區內依省、市鎮座標 Hilbert 序切等大新區（同 近期大選推估.merge）。"""
    by_dep = {}
    for u in units:
        by_dep.setdefault(u[0], []).append(u)
    out = []
    for i, ds in enumerate(R.DEPTS):
        reg = sorted((x for d in ds for x in by_dep.get(d, [])), key=lambda x: (ds.index(x[0]), x[1]))
        reg = [(d, n, ins, v) for n, (d, _, ins, v) in enumerate(reg)]
        for fp in _cut(reg, seats[i]):
            out.append((i, fp))
    return out


def _dist(a, b):
    return sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[a], POS[b])) ** 0.5


def single_p(districts, types=TYPES, k=3):
    """top-k 孔多賽。回傳 ({黨: 席}, 統計)。"""
    out = {}
    st = {"循環": 0, "過半": 0, "逆轉": 0, "共同提名": 0}
    groups = voter_groups(list(POS), types)
    for _, fp in districts:
        parties = [p for p in POS if fp.get(p, 0) > 0]
        wt = lambda s: fp.get(s, 0)
        # 參選方層：新人民陣線的單一提名是兩輪制（12.5% 門檻、避免分票）的產物，不照搬；
        # 改由參選判定.finalists 依新制誘因判定相鄰政黨的共同提名（notes/算法/選舉結果計算方式.md）
        fin, mlog = _finalists({p: fp[p] for p in parties}, k, lambda f: pairwise_winner(f, groups, wt)[0], _dist,
                               universe=list(POS), return_log=True, withdraw=True)
        st["共同提名"] += bool(mlog)
        for sm, bg, *_ in mlog:
            st.setdefault("整合", {})
            st["整合"][f"{sm}→{bg}"] = st["整合"].get(f"{sm}→{bg}", 0) + 1
        w, cyc, _ = pairwise_winner(fin, groups, wt)
        out[w] = out.get(w, 0) + 1
        st["循環"] += cyc
        st["過半"] += fp[w] > sum(fp.values()) / 2
        st["逆轉"] += w != fin[0]
    return out, st


def list_p(units, tiny=25):
    """複數 170：14 區聖拉古、無門檻；「其他」拆成 tiny 張小名單。"""
    by_dep = {}
    for dep, _, _, pv in units:
        d = by_dep.setdefault(dep, {})
        for p, v in pv.items():
            d[p] = d.get(p, 0.0) + v
    out = {}
    for i, ds in enumerate(R.DEPTS):
        w = {}
        for dep in ds:
            for p, v in by_dep.get(dep, {}).items():
                if p == "其他":
                    for t in range(tiny):
                        w[f"其他{t}"] = w.get(f"其他{t}", 0.0) + v / tiny
                else:
                    w[p] = w.get(p, 0.0) + v
        for p, n in R.sainte_lague(w, R.LIST_M[i]).items():
            if n:
                key = "其他" if p.startswith("其他") else p
                out[key] = out.get(key, 0) + n
    return out


def head_of_gov(total):
    """全院記名排名：各黨議員依均衡型排序投，孔多賽。回傳 (首長, 是否循環, 最弱一場得票)。"""
    parties = sorted(p for p, n in total.items() if n and p in POS)
    groups = [(p, 1.0, rank_from(p, parties, BALANCED)) for p in parties]
    w, cyc, P = pairwise_winner(parties, groups, lambda s: total.get(s, 0))
    return w, cyc, min(P[(w, b)] for b in parties if b != w)


def coalition(total, pm, need=NEED):
    """多數派政府：由首長所屬黨由近到遠加入，直到過半。"""
    d = lambda p: sum((w * (x - y)) ** 2 for w, x, y in zip(BALANCED, POS[p], POS[pm])) ** 0.5
    seq, acc = [], 0
    for p in sorted((p for p in total if total[p] and p in POS), key=lambda p: (d(p), -total[p], p)):
        seq.append(p)
        acc += total[p]
        if acc >= need:
            break
    return seq, acc


def fmt(d):
    return "、".join(f"{p} {n}" for p, n in sorted(d.items(), key=lambda x: (-x[1], x[0])) if n)


def report(title, units, seats=None):
    """印出一筆（top4_all 可解析的格式）。回傳 (單一, 複數, 全院)。"""
    seats = seats or R.region_seats(R.CIRC_2024)
    s, st = single_p(merge_p(units, seats))
    l = list_p(units)
    tot = {p: s.get(p, 0) + l.get(p, 0) for p in set(s) | set(l) if p != "其他"}
    pm, cyc, worst = head_of_gov(tot)
    seq, acc = coalition(tot, pm)
    nat = {}
    for dep, _, _, pv in units:
        if dep != R.DROPPED:
            for p, v in pv.items():
                nat[p] = nat.get(p, 0) + v
    t = sum(nat.values())
    print(f"## {title}")
    print("（第一偏好：" + "、".join(f"{p} {v / t:.1%}" for p, v in sorted(nat.items(), key=lambda x: -x[1]) if v / t >= 0.005) + "）")
    print(f"單一 230：{fmt(s)}")
    print(f"（循環 {st['循環']}、當選者第一偏好過半 {st['過半']}、非第一輪最高票當選 {st['逆轉']}、共同提名 {st['共同提名']} 區 {st.get('整合', {})}）")
    print(f"複數 170：{fmt({p: n for p, n in l.items() if p != '其他'})}")
    print(f"全院 400：{fmt(tot)}")
    print(f"行政首長（全院 ≥{NEED}）：{pm}（{'循環' if cyc else '孔多賽'}；最弱一場 {worst:.0f}）")
    print(f"組閣（多數派政府）：{'＋'.join(f'{p} {tot[p]}' for p in seq)}＝{acc}")
    print()
    return s, l, tot
