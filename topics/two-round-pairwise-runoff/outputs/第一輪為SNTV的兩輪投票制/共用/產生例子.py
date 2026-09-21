"""產生並驗算三種情況的「票型分布例子」。

每個例子的每一張表都由本程式從票數算出來；assert 檢查當選人與文字敘述一致。
執行：python 產生例子.py（任何目錄皆可）。改了例子就重跑，不要手改輸出檔的數字。

計票規則（三種情況相同，見 ../共用/對決強度.md）：
  1. 兩兩對決：每場數「甲排在乙前面」的票。完整順序票對每場都表態；
     「只選甲」的票只在甲參加的兩場算甲贏，另外那場不表態。
  2. 有人對每位都贏 → 當選。
  3. 否則由強到弱採認（強度＝勝方得票；同強度比負方較少者較強），
     會和已採認者形成循環就跳過，排出名次，第一名當選。
     三人時這就等於「不採認最弱的那一場」。
"""
import itertools
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def perms(m):
    return list(itertools.permutations(range(1, m + 1)))


TAG = "甲乙丙丁"


def t(i):
    return TAG[i - 1]


def s(p):
    return ">".join(t(x) for x in p)


def optno(m, key):
    """選項號次：完整順序依字典序 1..m!；九選項的「只選」接在後面（7、8、9）。"""
    if key[0] == "只":
        return len(perms(m)) + key[1]
    return perms(m).index(key) + 1


def cell(m, key):
    return f"選項 {optno(m, key)}（只選{t(key[1])}）" if key[0] == "只" else f"選項 {optno(m, key)}（`{s(key)}`）"


def pairwise(m, ballots):
    P = {a: {b: 0 for b in range(1, m + 1)} for a in range(1, m + 1)}
    for key, c in ballots.items():
        if key[0] == "只":
            for y in range(1, m + 1):
                if y != key[1]:
                    P[key[1]][y] += c
        else:
            for i in range(m):
                for j in range(i + 1, m):
                    P[key[i]][key[j]] += c
    return P


def cw(m, P):
    for a in range(1, m + 1):
        if all(P[a][b] > P[b][a] for b in range(1, m + 1) if b != a):
            return a
    return None


def ranked_pairs(m, P):
    """回傳 (當選人, 採認紀錄)。強度＝勝方得票，次比負方較少。"""
    defs = []
    for a, b in itertools.combinations(range(1, m + 1), 2):
        if P[a][b] == P[b][a]:
            continue
        w, l = (a, b) if P[a][b] > P[b][a] else (b, a)
        defs.append((P[w][l], -P[l][w], w, l))
    defs.sort(reverse=True)
    locked, log = [], []

    def reach(x, y, edges):
        st, seen = [x], set()
        while st:
            u = st.pop()
            if u == y:
                return True
            for (p, q) in edges:
                if p == u and q not in seen:
                    seen.add(q); st.append(q)
        return False

    for sw, nl, w, l in defs:
        if reach(l, w, locked):
            log.append((w, l, sw, -nl, "跳過"))
        else:
            locked.append((w, l)); log.append((w, l, sw, -nl, "採認"))
    losers = {l for _, l in locked}
    top = [c for c in range(1, m + 1) if c not in losers]
    return (top[0] if len(top) == 1 else None), log


def first_prefs(m, ballots):
    f = {i: 0 for i in range(1, m + 1)}
    for key, c in ballots.items():
        f[key[1] if key[0] == "只" else key[0]] += c
    return f


def irv(m, ballots):
    alive = set(range(1, m + 1))
    while len(alive) > 1:
        f = {i: 0 for i in alive}
        for key, c in ballots.items():
            seq = [key[1]] if key[0] == "只" else list(key)
            for x in seq:
                if x in alive:
                    f[x] += c; break
        tot = sum(f.values())
        top = max(f, key=f.get)
        if f[top] * 2 > tot:
            return top
        alive.remove(min(f, key=f.get))
    return alive.pop()


# ------------------------------------------------------------ markdown
def ballot_table(m, ballots):
    keys = [k for k in ballots if ballots[k]]
    keys = sorted(keys, key=lambda k: optno(m, k))
    head = "| 圈的格 | " + " | ".join(cell(m, k) for k in keys) + " | 其餘 |"
    sep = "|:--|" + ":--:|" * (len(keys) + 1)
    row = "| 票 | " + " | ".join(str(ballots[k]) for k in keys) + " | 0 |"
    return "\n".join([head, sep, row]) + f"\n\n有效票 **{sum(ballots.values())}**。"


def pair_table(m, P, show_part=False):
    lines = ["| 對決 | 票數 | 結果 | 勝方得票 |" + (" 參與票數 |" if show_part else ""),
             "|------|------|------|:--:|" + (":--:|" if show_part else "")]
    for a, b in itertools.combinations(range(1, m + 1), 2):
        x, y = P[a][b], P[b][a]
        res = f"**{t(a)}勝{t(b)}**" if x > y else (f"**{t(b)}勝{t(a)}**" if y > x else "平手")
        lines.append(f"| {t(a)}對{t(b)} | {x} : {y} | {res} | {max(x, y)} |" + (f" {x + y} |" if show_part else ""))
    return "\n".join(lines)


def rp_table(log, three):
    if three:
        lines = ["| 對決 | 勝方得票 | 處理 |", "|------|:--:|------|"]
        weakest = log[-1]
        for w, l, sw, sl, act in log:
            lines.append(f"| {t(w)}勝{t(l)} | {sw} | {'**不採認（最弱）**' if (w, l) == weakest[:2] else '採認'} |")
    else:
        lines = ["| 順序 | 對決 | 勝方得票 | 處理 |", "|:--:|------|:--:|------|"]
        for i, (w, l, sw, sl, act) in enumerate(log, 1):
            lines.append(f"| {i} | {t(w)}勝{t(l)} | {sw} | {'**跳過**（會和已採認的形成循環）' if act == '跳過' else '採認'} |")
    return "\n".join(lines)


def example(m, title, ballots, expect, intro="", outro="", show_part=False, compare=()):
    P = pairwise(m, ballots)
    w0 = cw(m, P)
    out = [f"## {title}", ""]
    if intro:
        out += [intro, ""]
    out += [ballot_table(m, ballots), "", pair_table(m, P, show_part), ""]
    if w0:
        out.append(f"{t(w0)}對其他每位都贏 → **兩兩對決贏家 → {t(w0)}當選**。不必動用卡住時的規則。")
        win = w0
    else:
        win, log = ranked_pairs(m, P)
        if m == 3:
            out += ["沒有人對每位都贏（對決卡住）。三場依**勝方得票**由強到弱：", "", rp_table(log, True), "",
                    f"其餘兩場排出名次，**{t(win)}當選**。"]
        else:
            out += ["沒有人對每位都贏（對決卡住）。依**勝方得票**由強到弱採認：", "", rp_table(log, False), "",
                    f"採認的對決排出名次，**{t(win)}當選**。"]
    assert win == expect, (title, win, expect)
    comp = []
    fp = first_prefs(m, ballots)
    for c in compare:
        if c == "FPTP":
            f = max(fp, key=fp.get)
            comp.append(f"- **同票用 FPTP**（第一志願最多者當選）：第一志願 " + "、".join(f"{t(k)}有 {v}" for k, v in fp.items()) + f" → {t(f)}當選。")
        if c == "top2":
            a, b = sorted(fp, key=lambda k: -fp[k])[:2]
            w = a if P[a][b] > P[b][a] else b
            comp.append(f"- **同票用 top-2**（第一志願前二再比）：前二是 {t(a)}、{t(b)}；{t(a)}對{t(b)} 為 {P[a][b]}:{P[b][a]} → {t(w)}當選。")
        if c == "IRV":
            comp.append(f"- **同票用澳洲排序複選（IRV）**：逐輪淘汰第一志願最少者 → {t(irv(m, ballots))}當選。")
    if comp:
        out += ["", *comp]
    if outro:
        out += ["", outro]
    return "\n".join(out)


def page(case, header, examples):
    text = header + "\n\n---\n\n" + "\n\n---\n\n".join(examples) + "\n"
    with open(os.path.join(ROOT, case, "第二輪", "票型分布例子.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def O(*p):
    return tuple(p)


def B(i):
    return ("只", i)


# ------------------------------------------------------------ 三人・六選項
SIX_HEAD = """# 第二輪票型分布例子（k＝3・六選項）

規則：[`選制.md`](選制.md)。怎麼加總：[`計票.md`](計票.md)。本檔由 [`../../共用/產生例子.py`](../../共用/產生例子.py) 產生，每張表的數字都由程式從票數算出。

候選人以甲、乙、丙表示；每一格有選項號次：選項 1 `甲>乙>丙`、2 `甲>丙>乙`、3 `乙>甲>丙`、4 `乙>丙>甲`、5 `丙>甲>乙`、6 `丙>乙>甲`。下列都是已晉級的三人（或兩人）決選；票數取整數方便手算。"""


def six():
    ex = [
        example(3, "例一：有兩兩對決贏家（最常見）",
                {O(1, 2, 3): 40, O(1, 3, 2): 20, O(2, 1, 3): 15, O(2, 3, 1): 10, O(3, 1, 2): 10, O(3, 2, 1): 5}, 1,
                outro="實際選舉裡幾乎總是這樣（Foley & Maskin 2025；Munger 2022）。卡住時的規則仍須事先寫死。"),
        example(3, "例二：第一志願最少的人，仍是兩兩對決贏家（相對 IRV）",
                {O(1, 2, 3): 40, O(2, 1, 3): 29, O(3, 2, 1): 31}, 2,
                intro="結構比照阿拉斯加 2022 年眾議員特別選舉（Begich 第一志願最少、卻對另外兩人都贏；Graham-Squire & McCune, *TME*，https://doi.org/10.54870/1551-3440.1686）。",
                compare=("IRV",)),
        example(3, "例三：第一志願最多的人不是兩兩對決贏家（相對 FPTP）",
                {O(1, 2, 3): 35, O(2, 1, 3): 40, O(3, 1, 2): 25}, 1,
                compare=("FPTP",),
                outro="丙的支持者把丙排第一，不必棄保；他們排在第二位的甲仍贏過乙。"),
        example(3, "例四：第三名才是大家都能接受的人（相對 top-2）",
                {O(1, 3, 2): 35, O(2, 3, 1): 33, O(3, 1, 2): 16, O(3, 2, 1): 16}, 3,
                compare=("top2",),
                outro="這就是「中間人擠壓」：丙的第一志願最少，但甲、乙的支持者都把丙排第二。top-2 在第一輪就把他淘汰，本制讓前三名都進決選。"),
        example(3, "例五：三人卡住 → 不採認最弱的那一場",
                {O(1, 3, 2): 25, O(2, 1, 3): 45, O(3, 1, 2): 15, O(3, 2, 1): 15}, 2,
                compare=("IRV",),
                outro="對外說：三場裡「丙贏乙」這場贏的一方票最少，那一場不算，其餘照算。三人時這和 Ranked Pairs、minimax、Schulze 選出同一人（Brandt, Dong & Peters, *GEB* 2025）。"),
        example(3, "例六：文獻常用的卡住例（75／65／60）",
                {O(1, 2, 3): 40, O(2, 3, 1): 35, O(3, 1, 2): 25}, 1,
                intro="Wikipedia *Ranked pairs* 用來說明「先採認贏得多的對決」的三人例。"),
        example(2, "例七：只有兩人決選（登記 2 人，跳過第一輪）",
                {O(1, 2): 70, O(2, 1): 30}, 1,
                intro="票面只印選項 1 `甲>乙`、選項 2 `乙>甲` 兩格。"),
    ]
    page("k3-六選項", SIX_HEAD, ex)


# ------------------------------------------------------------ 三人・九選項
NINE_HEAD = """# 第二輪票型分布例子（k＝3・九選項）

規則：[`選制.md`](選制.md)。怎麼加總：[`計票.md`](計票.md)。本檔由 [`../../共用/產生例子.py`](../../共用/產生例子.py) 產生，每張表的數字都由程式從票數算出。

候選人以甲、乙、丙表示；選項號次：1–6 同六選項（1 `甲>乙>丙` …… 6 `丙>乙>甲`），7 只選甲、8 只選乙、9 只選丙。

「只選甲」的票：甲參加的兩場算甲贏；另外兩人那一場**不表態**。所以本檔的對決表多一欄「參與票數」。"""


def nine():
    ex = [
        example(3, "例一：沒有人只選一人——和六選項一模一樣",
                {O(1, 2, 3): 40, O(1, 3, 2): 20, O(2, 1, 3): 15, O(2, 3, 1): 10, O(3, 1, 2): 10, O(3, 2, 1): 5}, 1,
                show_part=True,
                outro="九選項是六選項的延伸：沒有人圈選項 7–9（只選一人）時，結果與 [`../../k3-六選項/第二輪/票型分布例子.md`](../../k3-六選項/第二輪/票型分布例子.md) 例一相同。"),
        example(3, "例二：有人只選一人，仍有兩兩對決贏家",
                {O(1, 2, 3): 25, O(1, 3, 2): 10, O(2, 1, 3): 15, O(2, 3, 1): 10, O(3, 1, 2): 8, O(3, 2, 1): 7,
                 B(1): 15, B(2): 5, B(3): 5}, 1, show_part=True,
                outro="選項 7（只選甲）的 15 票只進「甲對乙」「甲對丙」兩場；「乙對丙」那場它不表態，所以該場參與票數是 100－15＝85。"),
        example(3, "例三：強迫排完會被票面順序污染——九選項避開",
                {O(1, 3, 2): 10, O(2, 3, 1): 32, O(3, 2, 1): 28, B(1): 30}, 3, show_part=True,
                intro="有 30 人只在乎甲，對乙、丙沒有意見。九選項讓他們圈選項 7（只選甲）。"),
        example(3, "例三（續）：同一群人若被迫排完，照票面位置圈第一格（選項 1 `甲>乙>丙`）",
                {O(1, 2, 3): 30, O(1, 3, 2): 10, O(2, 3, 1): 32, O(3, 2, 1): 28}, 2,
                outro="那 30 人其實不在乎乙和丙誰好，卻因為被迫排完，把「乙對丙」這場從 **丙贏** 推成 **乙贏**，當選人跟著換掉。候選人名單排在前面的人會多拿票，是有實證的：紐約市 1998 年民主黨初選，排第一位讓 180 位候選人中 89% 得票較多（Koppell & Steen, *Journal of Politics* 66(1), 2004，https://doi.org/10.1046/j.1468-2508.2004.00151.x）。若這 30 人改成隨機一半 `甲>乙>丙`、一半 `甲>丙>乙`，結果回到丙當選——問題出在「沒有意見卻被迫表態」，而九選項讓他們可以不表態。"),
        example(3, "例四：用「只選一人」操弄——真誠投票時",
                {O(1, 3, 2): 140, O(2, 3, 1): 100, O(3, 1, 2): 20, O(3, 2, 1): 30}, 3, show_part=True,
                intro="真誠投票下，丙是兩兩對決贏家。圈 `甲>丙>乙` 的那 140 人最喜歡甲，他們想讓甲當選。"),
        example(3, "例四（續）：那 140 人改圈選項 7（只選甲）",
                {B(1): 140, O(2, 3, 1): 100, O(3, 1, 2): 20, O(3, 2, 1): 30}, 3, show_part=True,
                outro="""那 140 人不再表態「丙比乙好」，「乙對丙」從 190:100 變成 **100:50**，乙贏——製造出卡住（甲勝乙、丙勝甲、乙勝丙）。

- 若強度用**勝差**：三場勝差是甲勝乙差 30、丙勝甲差 10、乙勝丙差 50，最弱是「丙勝甲」→ 不採認 → **甲當選，操弄成功**。
- 本制用**勝方得票**：三場勝方得票 160、150、100，最弱是「乙勝丙（100）」→ 不採認 → **丙仍當選，操弄無效**。

靠「抽走票」翻過來的那一場，勝方票本來就少，用勝方得票量就是最弱、最先丟掉的那一場。見 [`../../共用/對決強度.md`](../../共用/對決強度.md)。"""),
        example(3, "例五：只選一人造成平手的那一場",
                {O(1, 2, 3): 30, O(3, 2, 1): 20, B(1): 20, B(3): 10}, 1, show_part=True,
                outro="「乙對丙」30:30 平手。平手只代表那一場沒有勝負；甲在自己的兩場都贏，仍是兩兩對決贏家。平手只有在沒有人對每位都贏時才要處理（視為最弱的一場，[`../../共用/對決強度.md`](../../共用/對決強度.md) §同分）。"),
        example(2, "例六：只有兩人決選",
                {O(1, 2): 55, O(2, 1): 45}, 1,
                intro="m＝2 時只印選項 1 `甲>乙`、選項 2 `乙>甲`。「只選甲」與 `甲>乙` 意思完全相同，所以不另印。"),
    ]
    page("k3-九選項", NINE_HEAD, ex)


# ------------------------------------------------------------ 四人・二十四選項
K4_HEAD = """# 第二輪票型分布例子（k＝4・二十四選項）

規則：[`選制.md`](選制.md)。怎麼加總、由強到弱採認：[`計票.md`](計票.md)。本檔由 [`../../共用/產生例子.py`](../../共用/產生例子.py) 產生，每張表的數字都由程式從票數算出。

候選人以甲、乙、丙、丁表示；選項號次 1–24 依字典序對應 24 種順序（1 `甲>乙>丙>丁`、2 `甲>乙>丁>丙` …… 24 `丁>丙>乙>甲`）。表中同時寫選項號次與順序。"""


def k4():
    ex = [
        example(4, "例一：有兩兩對決贏家",
                {O(1, 2, 3, 4): 60, O(2, 1, 3, 4): 40}, 1),
        example(4, "例二：第一志願第三的人，仍是兩兩對決贏家（相對 top-2 與 IRV）",
                {O(1, 3, 2, 4): 32, O(2, 3, 1, 4): 30, O(3, 1, 2, 4): 22, O(4, 2, 1, 3): 16}, 3,
                compare=("top2", "IRV")),
        example(4, "例三：第一志願最多的人，兩兩對決全輸（相對 FPTP）",
                {O(1, 2, 3, 4): 42, O(2, 3, 4, 1): 26, O(3, 4, 2, 1): 15, O(4, 3, 2, 1): 17}, 2,
                intro="文獻常用的「田納西州首府」分布（Wikipedia *Condorcet method*）：甲是人口最多、但在地理一端的城市。",
                compare=("FPTP",)),
        example(4, "例四：四人卡住 → 由強到弱採認",
                {O(1, 3, 4, 2): 3, O(1, 4, 2, 3): 5, O(2, 1, 3, 4): 4, O(2, 3, 4, 1): 5,
                 O(3, 1, 4, 2): 2, O(3, 4, 1, 2): 5, O(4, 1, 2, 3): 2, O(4, 2, 1, 3): 4}, 4,
                intro="Schulze（*Voting Matters* 17, 2003）的 30 票例，Munger（*CPE* 2022）用來比較 Ranked Pairs 與 Schulze。",
                outro="同一組票若用 Schulze（最強路徑）會選甲——四人時各種卡住規則會分岔，所以必須事先寫死。本制完整排序下，勝方得票與勝差排出的順序相同。"),
    ]
    ex.append("""## 例五：登記 3 人（跳過第一輪）

k＝4 的套在 n＝3 時只印 6 格，計票與 k＝3 六選項完全相同，例子見 [`../../k3-六選項/第二輪/票型分布例子.md`](../../k3-六選項/第二輪/票型分布例子.md)。n＝2 只印 2 格。""")
    page("k4-二十四選項", K4_HEAD, ex)


if __name__ == "__main__":
    six(); nine(); k4()
    print("ok")
