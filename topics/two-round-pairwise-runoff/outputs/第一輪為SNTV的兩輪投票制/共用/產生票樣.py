"""產生三種情況的票樣（md＋可列印 html）。

選項號在同一情況的不同排版之間**固定不變**：計票紙只看選項號，不看排版。
  六選項：①–⑥ 為三人完整順序（字典序）
  九選項：①–⑥ 同上；⑦⑧⑨＝只選 1／2／3
  二十四選項：①–㉔ 為四人完整順序（字典序）
執行：python 產生票樣.py（任何目錄皆可）
"""
import itertools
import os
import html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CIRC = [chr(0x2460 + i) for i in range(20)] + [chr(0x3251 + i) for i in range(4)]  # ①..⑳ ㉑..㉔

FIRST = [  # 第一輪樣張候選人（號次, 姓名, 推薦政黨）
    (1, "林志明", "民治黨"), (2, "陳雅婷", "公正黨"), (3, "瑪拉歐斯·達拉阿道", "無"),
    (4, "Kaliting Tjaljaljav", "台灣原住民族自治與土地正義聯盟"), (5, "歐陽文心", "改革黨"),
    (6, "吳淑芬", "同心黨"), (7, "鄭雅文", "民生黨"), (8, "許建宏", "無"),
    (9, "蔡佩君", "協力黨"), (10, "張家豪", "綠色未來黨"),
]
FINAL3 = [(1, "林志明", "民治黨"), (2, "瑪拉歐斯·達拉阿道", "無"),
          (3, "Kaliting Tjaljaljav", "台灣原住民族自治與土地正義聯盟")]
FINAL4 = FINAL3 + [(4, "陳雅婷", "公正黨")]

LEGEND3 = "讀法：1＞3＞2＝最喜歡 1 號，其次 3 號，最後 2 號。"
LEGEND4 = "讀法：1＞3＞4＞2＝最喜歡 1 號，其次 3 號，再來 4 號，最後 2 號。"
NOTICE = "**請只圈選一格。圈選兩個以上、空白或塗改者，無效。**"


def perms(m):
    return list(itertools.permutations(range(1, m + 1)))


def ordstr(p):
    return "＞".join(str(x) for x in p)


def options(case):
    """回傳 [(選項號, 種類, 內容)]；種類 full／bullet。"""
    if case == "k3-六選項":
        return [(CIRC[i], "full", p) for i, p in enumerate(perms(3))]
    if case == "k3-九選項":
        o = [(CIRC[i], "full", p) for i, p in enumerate(perms(3))]
        return o + [(CIRC[6 + i], "bullet", (i + 1,)) for i in range(3)]
    return [(CIRC[i], "full", p) for i, p in enumerate(perms(4))]


def label(o):
    num, kind, p = o
    return f"{num}　只選 {p[0]}" if kind == "bullet" else f"{num}　{ordstr(p)}"


def cname(cands, i):
    c = cands[i - 1]
    return f"{c[0]}　{c[1]}"


def group_first(opts, i):
    g = [o for o in opts if o[2][0] == i]
    g.sort(key=lambda o: o[1] != "bullet")  # 「只選」排在該組最前
    return g


# ------------------------------------------------------------ markdown
def md_ids(cands, title="決選號次"):
    return "\n".join([
        f"| {title} | " + " | ".join(str(c[0]) for c in cands) + " |",
        "|:---:|" + ":---:|" * len(cands),
        "| 個人照片 | " + " | ".join("〔相片〕" for _ in cands) + " |",
        "| 姓名 | " + " | ".join(f"**{c[1]}**" for c in cands) + " |",
        "| 推薦政黨 | " + " | ".join(c[2] for c in cands) + " |",
    ])


def md_cells(opts):
    return "| " + " | ".join(f"○　{label(o)}" for o in opts) + " |\n|" + ":---:|" * len(opts)


def md_rows(cands, opts):
    return "\n\n".join(f"**最喜歡　{cname(cands, i)}**\n\n{md_cells(group_first(opts, i))}"
                       for i in range(1, len(cands) + 1))


def md_cols(cands, opts, grouped=False):
    m = len(cands)
    lines = ["| " + " | ".join(f"最喜歡 **{cname(cands, i)}**" for i in range(1, m + 1)) + " |",
             "|" + ":---:|" * m,
             "| " + " | ".join("〔相片〕" for _ in cands) + " |",
             "| " + " | ".join(c[2] for c in cands) + " |"]
    cols = []
    for i in range(1, m + 1):
        if grouped:
            col = []
            for j in [x for x in range(1, m + 1) if x != i]:
                col.append(f"*其次 {j} 號*")
                col += [f"○　{label(o)}" for o in opts if o[2][0] == i and o[2][1] == j]
        else:
            col = [f"○　{label(o)}" for o in group_first(opts, i)]
        cols.append(col)
    for r in range(len(cols[0])):
        lines.append("| " + " | ".join(c[r] for c in cols) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------ html
CSS = """
@page { size: A4 landscape; margin: 8mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Noto Sans TC","Source Han Sans TC","Microsoft JhengHei",sans-serif; color:#111; background:#fff; }
.ballot { max-width: 285mm; margin: 12px auto; border: 4px solid #111; padding: 8px 10px 10px; page-break-after: always; }
.head { display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid #111; padding-bottom:6px; margin-bottom:8px; }
.head h1 { margin:0; font-size:17px; letter-spacing:.06em; }
.head .meta { font-size:12px; }
.notice { text-align:center; font-size:15px; font-weight:700; margin:0 0 4px; }
.legend { text-align:center; font-size:13px; margin:0 0 8px; }
table.ids, table.grid { width:100%; border-collapse:collapse; table-layout:fixed; }
.ids th, .ids td, .grid td, .grid th { border:1px solid #111; text-align:center; vertical-align:middle; padding:4px 3px; }
.ids th { width:4.6em; font-size:12px; background:#f2f2f2; }
.grid th { background:#f2f2f2; font-weight:400; font-size:12px; }
.photo { margin:3px auto; height:46px; width:36px; border:1px dashed #666; font-size:11px; color:#444; display:flex; align-items:center; justify-content:center; }
.name { font-size:14px; font-weight:700; line-height:1.25; word-break:keep-all; overflow-wrap:normal; }
.party { font-size:12px; line-height:1.25; word-break:normal; overflow-wrap:anywhere; }
.mark { display:inline-block; width:18px; height:18px; border:2px solid #111; border-radius:50%; vertical-align:middle; margin-right:5px; }
.circle { width:24px; height:24px; }
.opt { font-size:14px; white-space:nowrap; padding:9px 4px; }
.opt .n { font-weight:700; margin-right:4px; }
.bullet { background:#fbfbef; }
.sub { font-size:12px; font-style:italic; background:#f7f7f7; padding:2px; }
.rowlab { text-align:left !important; font-size:13px; font-weight:700 !important; width:30%; }
.sect { margin:8px 0 3px; text-align:center; font-weight:700; font-size:13px; }
.foot { display:flex; justify-content:space-between; margin-top:8px; font-size:12px; }
"""


def h(s):
    return html.escape(str(s))


def h_name(n):  # 只在「·」與空格後換行，不從字中間斷
    return h(n).replace("·", "·<wbr>").replace(" ", " <wbr>")


def h_opt(o):
    num, kind, p = o
    txt = f"只選 {p[0]}" if kind == "bullet" else ordstr(p)
    cls = "opt bullet" if kind == "bullet" else "opt"
    return f'<td class="{cls}"><span class="mark"></span><span class="n">{num}</span>{h(txt)}</td>'


def h_ids_rows(cands, title="決選號次"):
    return ("<tr><th>" + title + "</th>" + "".join(f"<td><b>{c[0]}</b></td>" for c in cands) + "</tr>"
            + '<tr><th>個人照片</th>' + "".join('<td><div class="photo">相片</div></td>' for _ in cands) + "</tr>"
            + '<tr><th>姓名</th>' + "".join(f'<td class="name">{h_name(c[1])}</td>' for c in cands) + "</tr>"
            + '<tr><th>推薦政黨</th>' + "".join(f'<td class="party">{h_name(c[2])}</td>' for c in cands) + "</tr>")


def h_ids(cands):
    return '<table class="ids">' + h_ids_rows(cands) + "</table>"


def h_rows(cands, opts):
    return '<table class="grid">' + "".join(
        f'<tr><th class="rowlab">最喜歡　{h(cname(cands, i))}</th>' + "".join(h_opt(o) for o in group_first(opts, i)) + "</tr>"
        for i in range(1, len(cands) + 1)) + "</table>"


def h_cols(cands, opts, grouped=False):
    m = len(cands)
    head = "<tr>" + "".join(
        f'<th>最喜歡<div class="photo">相片</div><div class="name">{c[0]}　{h_name(c[1])}</div>'
        f'<div class="party">{h_name(c[2])}</div></th>' for c in cands) + "</tr>"
    cols = []
    for i in range(1, m + 1):
        if grouped:
            col = []
            for j in [x for x in range(1, m + 1) if x != i]:
                col.append(f'<td class="sub">其次 {j} 號</td>')
                col += [h_opt(o) for o in opts if o[2][0] == i and o[2][1] == j]
        else:
            col = [h_opt(o) for o in group_first(opts, i)]
        cols.append(col)
    body = "".join("<tr>" + "".join(c[r] for c in cols) + "</tr>" for r in range(len(cols[0])))
    return '<table class="grid">' + head + body + "</table>"


def h_one_row(opts):
    return '<table class="grid"><tr>' + "".join(h_opt(o) for o in opts) + "</tr></table>"


def h_wrap(title, meta, body, legend, foot):
    return (f'<div class="ballot"><div class="head"><h1>{h(title)}</h1><div class="meta">{h(meta)}</div></div>'
            '<p class="notice">請只圈選一格。圈選兩個以上、空白或塗改者，無效。</p>'
            + (f'<p class="legend">{h(legend)}</p>' if legend else "")
            + body + f'<div class="foot"><span>選舉委員會製　樣張</span><span>{h(foot)}</span></div></div>')


def h_page(title, ballots):
    return ('<!DOCTYPE html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
            f"<title>{h(title)}</title><style>{CSS}</style></head><body>\n"
            + "\n".join(ballots) + "\n</body></html>\n")


# ------------------------------------------------------------ 輸出
def write(rel, text):
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def second_round(case, key, desc, md_body, h_body, cands, legend):
    k = len(options(case))
    meta = f"選區：○○　{len(cands)} 人決選　選項 {CIRC[0]}–{CIRC[k - 1]}　人工計票"
    write(f"{case}/第二輪/選票樣式-{key}.md",
          f"# ○○年○○選舉　第二輪決選選舉票（{key}）\n\n{meta}\n\n{NOTICE}\n\n{desc}\n\n"
          f"可列印：[`選票樣式-{key}.html`](選票樣式-{key}.html)。其他排版：[`選票樣式.md`](選票樣式.md)。"
          "選項號的意思在各排版之間都一樣，見 [`計票.md`](計票.md)。\n\n---\n\n"
          f"{legend}\n\n{md_body}\n\n選舉委員會製　　樣張\n")
    write(f"{case}/第二輪/選票樣式-{key}.html",
          h_page(f"第二輪決選（{case}・{key}）",
                 [h_wrap("○○年○○選舉　第二輪決選選舉票", f"{meta}　{key}", h_body, legend, "兩兩對決贏家當選")]))


def first_round():
    md_parts, h_parts = [], []
    for n in (4, 7, 10):
        c = FIRST[:n]
        md_parts.append(
            f"## 樣張：登記 {n} 人\n\n**請圈選一人**\n\n"
            + "| 圈選 | " + " | ".join("○" for _ in c) + " |\n|:---:|" + ":---:|" * n + "\n"
            + "| 號次 | " + " | ".join(str(x[0]) for x in c) + " |\n"
            + "| 個人照片 | " + " | ".join("〔相片〕" for _ in c) + " |\n"
            + "| 姓名 | " + " | ".join(f"**{x[1]}**" for x in c) + " |\n"
            + "| 推薦政黨 | " + " | ".join(x[2] for x in c) + " |\n\n"
            + "選舉委員會製　　樣張　　得票最高的 k 人進入第二輪")
        body = ('<table class="ids"><tr><th>圈選</th>'
                + "".join('<td><span class="mark circle"></span></td>' for _ in c) + "</tr>"
                + h_ids_rows(c, "號次") + "</table>")
        h_parts.append(h_wrap("○○年○○選舉　第一輪選舉票", f"選區：○○　登記 {n} 人　人工計票",
                              body, "", "得票最高的 k 人進入第二輪決選"))
    write("共用/第一輪/選票樣式.md",
          "# 第一輪選舉票（樣張，三種情況共用）\n\n選區：○○　台灣單一選區　人工計票\n\n" + NOTICE + "\n\n"
          "本張是兩輪一套的第一輪：**圈一個人**。得票最高的 k 人進第二輪（k＝3 或 4，依採用的情況）。"
          "登記人數 ≤ k 時不印本張，直接辦第二輪。\n\n"
          "每人一欄。圈選、號次、相片、姓名、推薦政黨**各佔一格**；只圈最上面的圓框。"
          "樣張刻意放入長名：複姓（歐陽文心）、漢字音譯傳統名字（瑪拉歐斯·達拉阿道）、"
          "**原住民族文字單列**的姓名（Kaliting Tjaljaljav）與長黨名（台灣原住民族自治與土地正義聯盟）。"
          "登記 10 人是 2024 年區域立委單一選區的最多人數。\n\n"
          "可列印：[`選票樣式.html`](選票樣式.html)。設計理由：[`選票設計.md`](選票設計.md)。\n\n---\n\n"
          + "\n\n---\n\n".join(md_parts) + "\n")
    write("共用/第一輪/選票樣式.html", h_page("第一輪選舉票（樣張）", h_parts))


def build():
    first_round()
    for case, cands, legend in (("k3-六選項", FINAL3, LEGEND3), ("k3-九選項", FINAL3, LEGEND3),
                                ("k4-二十四選項", FINAL4, LEGEND4)):
        opts = options(case)
        n = len(opts)
        sect = f'<p class="sect">請圈選一格（{CIRC[0]}–{CIRC[n - 1]}）</p>'
        ids_md, ids_h = md_ids(cands), h_ids(cands)
        if case == "k3-六選項":
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**，再從兩格裡挑一種完整順序。相片與推薦政黨印在欄首。",
                         md_cols(cands, opts), h_cols(cands, opts), cands, legend)
            second_round(case, "依第一偏好分列",
                         "上方是三位候選人的相片、姓名、推薦政黨。下方三列，每一列是「最喜歡某人」的兩種順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands, legend)
            second_round(case, "一列六選項",
                         "上方是三位候選人；下方一列六格，依號次順序排。最緊湊，但選民要自己找開頭的數字。",
                         ids_md + "\n\n" + md_cells(opts), ids_h + sect + h_one_row(opts), cands, legend)
        elif case == "k3-九選項":
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**：只想表態這一人，圈欄內第一格「只選」；願意排完，圈下面兩格之一。",
                         md_cols(cands, opts), h_cols(cands, opts), cands, legend)
            second_round(case, "依第一偏好分列",
                         "上方三位候選人；下方三列，每列是「最喜歡某人」的三種選法：只選他，或他開頭的兩種完整順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands, legend)
            full = [o for o in opts if o[1] == "full"]
            bul = [o for o in opts if o[1] == "bullet"]
            second_round(case, "兩段",
                         "上段六格是**完整喜歡順序**；下段三格是**只選一人**。先決定要不要排完，再找格子。",
                         ids_md + "\n\n**完整喜歡順序（①–⑥）**\n\n" + md_cells(full) + "\n\n**只選一人（⑦–⑨）**\n\n" + md_cells(bul),
                         ids_h + '<p class="sect">完整喜歡順序（①–⑥）</p>' + h_one_row(full)
                         + '<p class="sect">只選一人（⑦–⑨）</p>' + h_one_row(bul), cands, legend)
        else:
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**，欄內六種完整順序挑一格。",
                         md_cols(cands, opts), h_cols(cands, opts), cands, legend)
            second_round(case, "依第一偏好分欄-再依其次分組",
                         "同分欄版，但每欄再依**第二喜歡的人**分成三小組、每組兩格。找格變成三步：找欄（最喜歡）→ 找小組（其次）→ 兩格挑一。",
                         md_cols(cands, opts, grouped=True), h_cols(cands, opts, grouped=True), cands, legend)
            second_round(case, "依第一偏好分列",
                         "上方四位候選人；下方四列，每列是「最喜歡某人」的六種完整順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands, legend)


if __name__ == "__main__":
    build()
    print("ok")
