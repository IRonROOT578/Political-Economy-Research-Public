"""產生三套的第二輪 計票.md（記票紙、對決加總表）。執行：python 產生計票表.py

選項號次的編法與 產生票樣.py 相同：完整順序依甲乙丙丁字典序 1..m!；九選項的「只選」接在後面。
"""
import itertools
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TAG = "甲乙丙丁"


def perms(m):
    return list(itertools.permutations(TAG[:m]))


def s(p):
    return ">".join(p)


def sheet(m, bullets):
    P = perms(m)
    n = len(P)
    rows = ["| 選項號次 | 意思 | 劃記 |", "|:--:|------|------|"]
    for i, p in enumerate(P, 1):
        rows.append(f"| **{i}** | `{s(p)}` | |")
    if bullets:
        for j, c in enumerate(TAG[:m], 1):
            rows.append(f"| **{n + j}** | 只選{c} | |")
    rows.append("| 無效 | | |")
    return "\n".join(rows)


def pair_rows(m, bullets):
    P = perms(m)
    n = len(P)
    out = []
    for a, b in itertools.combinations(TAG[:m], 2):
        fa = [str(i) for i, p in enumerate(P, 1) if p.index(a) < p.index(b)]
        fb = [str(i) for i, p in enumerate(P, 1) if p.index(b) < p.index(a)]
        if bullets:
            fa.append(f"**{n + TAG.index(a) + 1}**")
            fb.append(f"**{n + TAG.index(b) + 1}**")
            other = [c for c in TAG[:m] if c not in (a, b)][0]
            out.append(f"| {a}對{b} | " + "＋".join(fa) + " | " + "＋".join(fb) + f" | {n + TAG.index(other) + 1} |")
        else:
            out.append(f"| {a}對{b} | " + "＋".join(fa) + " | " + "＋".join(fb) + " |")
    return "\n".join(out)


def page(title, m, bullets, extra_head, decide, tail):
    n = len(perms(m)) + (m if bullets else 0)
    head_cols = "| 對決 | 前者排在前面（加總這些選項） | 後者排在前面 |" + (" 不表態 |" if bullets else "")
    sep = "|------|------|------|" + (":--:|" if bullets else "")
    return f"""# 第二輪計票（{title}）

規則：[`選制.md`](選制.md)。例子：[`票型分布例子.md`](票型分布例子.md)。強度與同分：[`../../共用/對決強度.md`](../../共用/對決強度.md)。兩輪完整流程：[`../../共用/計票流程.md`](../../共用/計票流程.md)。本檔由 [`../../共用/產生計票表.py`](../../共用/產生計票表.py) 產生。

## 投票所：唱選項號次

唱票員高舉選票展示，唱所圈那一格的**選項號次**：「**選項 {min(7, n)}，1 票**」。記票員在記票紙該號次那一列劃「正」字。和現行「○號○○○ 1 票」一樣，一張票唱一個號碼。**所內不做兩兩對決。**

候選人在第二輪以甲、乙、丙{"、丁" if m == 4 else ""}表示（依第一輪號次由小到大），所以票上與記票紙上的數字只有選項號次一種。{extra_head}

記票紙（{n} 列＋無效票）：

{sheet(m, bullets)}

核對：各列票數＋無效票＝投票數。當場公告每一列的票數並張貼。

## 選委會：兩兩對決

加總各所公告的各列票數，再把選項號次分成兩半相加：

{head_cols}
{sep}
{pair_rows(m, bullets)}

任何人拿到各所公告的數字都能自己驗算。

## 決定當選

{decide}

{tail}
"""


DEC3 = """1. 有人兩場都贏 → **兩兩對決贏家，當選**。
2. 否則三場形成循環：**勝方得票最少**的那一場不採認；其餘兩場排出名次，第一名當選。
3. 同分：[`../../共用/對決強度.md`](../../共用/對決強度.md) §同分。"""

DEC4 = """1. 有人三場都贏 → **兩兩對決贏家，當選**。
2. 否則**由強到弱採認**：
   1. 六場（平手的不算）依**勝方得票**由多到少排序；同強度時負方得票較少者較強。
   2. 從最強的一場開始逐一採認。若採認某場會和已採認的結果形成循環（例：已採認丁勝乙、乙勝丙，此時「丙勝丁」會形成丁＞乙＞丙＞丁），**跳過**。
   3. 沒有輸掉任何已採認對決的人是第一名，當選。
3. 同分：[`../../共用/對決強度.md`](../../共用/對決強度.md) §同分。"""

pages = {
    "k3-六選項": page("k＝3・六選項", 3, False, "",
                    DEC3,
                    "兩人決選（m＝2）：只有選項 1 `甲>乙`、選項 2 `乙>甲`，多者當選。\n\n本套每張票都排完三人，每場參與票數都＝有效票數，所以「勝方得票最少」與「勝差最小」永遠是同一場。"),
    "k3-九選項": page("k＝3・九選項", 3, True,
                    "選項 1–6 與六選項完全相同；7、8、9 是只選甲、乙、丙。",
                    DEC3.replace("1. 有人兩場都贏 → **兩兩對決贏家，當選**。",
                                 "1. 有人兩場都贏 → **兩兩對決贏家，當選**。某場平手不影響這一步（例子檔例五）。"),
                    "和六選項的差別只有粗體那兩個號次：「只選甲」（選項 7）加進甲參加的兩場，甲不參加的那場它不表態。\n\n"
                    "**本套不能用「勝差最小」。** 有人只選一人時各場參與票數不同，勝差與勝方得票會指向不同的「最弱一場」；用勝差會讓「故意只選一人」變成可用的操弄（[`票型分布例子.md`](票型分布例子.md) 例四）。\n\n"
                    "兩人決選（m＝2）：只有選項 1 `甲>乙`、選項 2 `乙>甲`（「只選甲」與 `甲>乙` 意思相同，不另設），多者當選。"),
    "k4-二十四選項": page("k＝4・二十四選項", 4, False,
                        "選項 1–6 是最喜歡甲的六種、7–12 最喜歡乙、13–18 最喜歡丙、19–24 最喜歡丁，和建議預設排版的四欄一一對應。",
                        DEC4,
                        "三人決選（登記 3 人）只有選項 1–6，計票與 k＝3 六選項相同；兩人只有選項 1、2，多者當選。\n\n"
                        "本套每張票都排完四人，每場參與票數都＝有效票數，所以依勝方得票或依勝差排序結果相同（Tideman 1987 原文用勝差）。"),
}

if __name__ == "__main__":
    for case, text in pages.items():
        (ROOT / case / "第二輪" / "計票.md").write_text(text, encoding="utf-8", newline="\n")
    print("ok")
