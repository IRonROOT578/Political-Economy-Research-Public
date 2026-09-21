"""產生三種情況的票樣（md＋可列印 html）。

標示規則（見 ../共用/候選人與選項的標示.md）：
  - 第二輪每一格有**選項號次**（1、2、3……），唱票唱「選項 7，1 票」，記票紙一欄一個號次。
  - 第二輪的候選人**不用數字**，用「甲、乙、丙、丁」：依第一輪號次由小到大依序給，不重抽。
    所以第二輪票上的數字只有選項號次一種，不會和候選人號次搞混。
  - 選項號次依甲乙丙丁的字典序編：同一號次在各排版都是同一種順序。
執行：python 產生票樣.py（任何目錄皆可）
"""
import itertools
import os
import html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FIRST = [  # 第一輪樣張候選人（號次, 姓名, 推薦政黨）
    (1, "林志明", "民治黨"), (2, "陳雅婷", "公正黨"), (3, "瑪拉歐斯·達拉阿道", "無"),
    (4, "Kaliting Tjaljaljav", "台灣原住民族自治與土地正義聯盟"), (5, "歐陽文心", "改革黨"),
    (6, "吳淑芬", "同心黨"), (7, "鄭雅文", "民生黨"), (8, "許建宏", "無"),
    (9, "蔡佩君", "協力黨"), (10, "張家豪", "綠色未來黨"),
]
BY_NO = {c[0]: c for c in FIRST}
# 晉級者：第一輪 1、4、10 號（k＝3）；1、3、4、10 號（k＝4）。第二輪依號次由小到大稱甲乙丙丁
TAG = "甲乙丙丁"


def finalists(nos):
    """依第一輪號次由小到大給甲乙丙丁。回傳 (代號, 姓名, 推薦政黨, 第一輪號次)。"""
    return [(TAG[i], BY_NO[n][1], BY_NO[n][2], n) for i, n in enumerate(sorted(nos))]


FINAL3 = finalists((1, 4, 10))
FINAL4 = finalists((1, 3, 4, 10))

NOTICE = "**請只圈選一格。圈選兩個以上、空白或塗改者，無效。**"


def legend(cands):
    a = [c[0] for c in cands]
    ex = (a[1], a[0], a[2]) if len(a) == 3 else (a[1], a[3], a[0], a[2])
    words = "，".join(["最喜歡" + ex[0]] + ["其次" + ex[1]] + (["再來" + ex[2]] if len(ex) == 4 else []) + ["最後" + ex[-1]])
    return f"讀法：{ordstr(ex)}＝{words}。每一格前面的數字是選項號次，開票時唱這個號次。"


def ordstr(p):
    return "＞".join(p)


def options(case, cands):
    """回傳 [(選項號次, 種類, 內容)]；內容是甲乙丙丁 tuple。完整順序依字典序編號。"""
    tags = [c[0] for c in cands]
    full = [(i + 1, "full", p) for i, p in enumerate(itertools.permutations(tags))]
    if case == "k3-九選項":
        return full + [(len(full) + i + 1, "bullet", (t,)) for i, t in enumerate(tags)]
    return full


def content(o):
    return f"只選{o[2][0]}" if o[1] == "bullet" else ordstr(o[2])


def label(o):
    return f"**{o[0]}**　{content(o)}"


def cname(c):
    return f"{c[0]}　{c[1]}"


def group_first(opts, t):
    g = [o for o in opts if o[2][0] == t]
    g.sort(key=lambda o: o[1] != "bullet")  # 「只選」排在該組最前
    return g


# ------------------------------------------------------------ markdown
def md_ids(cands):
    return "\n".join([
        "| 決選代號 | " + " | ".join(f"**{c[0]}**" for c in cands) + " |",
        "|:---:|" + ":---:|" * len(cands),
        "| 個人照片 | " + " | ".join("〔相片〕" for _ in cands) + " |",
        "| 姓名 | " + " | ".join(f"**{c[1]}**" for c in cands) + " |",
        "| 推薦政黨 | " + " | ".join(c[2] for c in cands) + " |",
    ])


def md_cells(opts):
    return "| " + " | ".join(f"○　{label(o)}" for o in opts) + " |\n|" + ":---:|" * len(opts)


def md_rows(cands, opts):
    return "\n\n".join(f"**最喜歡　{cname(c)}**\n\n{md_cells(group_first(opts, c[0]))}" for c in cands)


def md_cols(cands, opts, grouped=False):
    lines = ["| " + " | ".join(f"最喜歡 **{cname(c)}**" for c in cands) + " |",
             "|" + ":---:|" * len(cands),
             "| " + " | ".join("〔相片〕" for _ in cands) + " |",
             "| " + " | ".join(c[2] for c in cands) + " |"]
    cols = []
    for c in cands:
        if grouped:
            col = []
            for d in cands:
                if d[0] == c[0]:
                    continue
                col.append(f"*其次{d[0]}*")
                col += [f"○　{label(o)}" for o in opts if o[2][0] == c[0] and o[2][1] == d[0]]
        else:
            col = [f"○　{label(o)}" for o in group_first(opts, c[0])]
        cols.append(col)
    for r in range(len(cols[0])):
        lines.append("| " + " | ".join(col[r] for col in cols) + " |")
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
.no { font-size:18px; font-weight:700; }
.photo { margin:3px auto; height:46px; width:36px; border:1px dashed #666; font-size:11px; color:#444; display:flex; align-items:center; justify-content:center; }
.name { font-size:14px; font-weight:700; line-height:1.25; word-break:keep-all; overflow-wrap:normal; }
.party { font-size:12px; line-height:1.25; word-break:normal; overflow-wrap:anywhere; }
.mark { display:inline-block; width:18px; height:18px; border:2px solid #111; border-radius:50%; vertical-align:middle; margin-right:6px; flex-shrink:0; }
.circle { width:24px; height:24px; }
.opt { font-size:15px; white-space:nowrap; padding:9px 4px; letter-spacing:.04em; }
.onum { display:inline-block; min-width:1.9em; border:1.5px solid #111; border-radius:3px; font-weight:700; margin-right:6px; text-align:center; font-size:14px; }
.tag { font-size:20px; font-weight:700; }
.bullet { background:#fbfbef; }
.sub { font-size:12px; font-style:italic; background:#f7f7f7; padding:2px; }
.rowlab { text-align:left !important; font-size:13px; font-weight:700 !important; width:24%; }
.sect { margin:8px 0 3px; text-align:center; font-weight:700; font-size:13px; }
.foot { display:flex; justify-content:space-between; margin-top:8px; font-size:12px; }
"""


def h(s):
    return html.escape(str(s))


def h_name(n):  # 只在「·」與空格後換行，不從字中間斷
    return h(n).replace("·", "·<wbr>").replace(" ", " <wbr>")


def h_opt(o):
    cls = "opt bullet" if o[1] == "bullet" else "opt"
    return f'<td class="{cls}"><span class="mark"></span><span class="onum">{o[0]}</span>{h(content(o))}</td>'


def h_ids_rows(cands):
    return ("<tr><th>決選代號</th>" + "".join(f'<td class="tag">{c[0]}</td>' for c in cands) + "</tr>"
            + '<tr><th>個人照片</th>' + "".join('<td><div class="photo">相片</div></td>' for _ in cands) + "</tr>"
            + '<tr><th>姓名</th>' + "".join(f'<td class="name">{h_name(c[1])}</td>' for c in cands) + "</tr>"
            + '<tr><th>推薦政黨</th>' + "".join(f'<td class="party">{h_name(c[2])}</td>' for c in cands) + "</tr>")


def h_ids(cands):
    return '<table class="ids">' + h_ids_rows(cands) + "</table>"


def h_rows(cands, opts):
    return '<table class="grid">' + "".join(
        f'<tr><th class="rowlab">最喜歡　{h(cname(c))}</th>' + "".join(h_opt(o) for o in group_first(opts, c[0])) + "</tr>"
        for c in cands) + "</table>"


def h_cols(cands, opts, grouped=False):
    head = "<tr>" + "".join(
        f'<th>最喜歡<div class="tag">{c[0]}</div><div class="photo">相片</div><div class="name">{h_name(c[1])}</div>'
        f'<div class="party">{h_name(c[2])}</div></th>' for c in cands) + "</tr>"
    cols = []
    for c in cands:
        if grouped:
            col = []
            for d in cands:
                if d[0] == c[0]:
                    continue
                col.append(f'<td class="sub">其次{d[0]}</td>')
                col += [h_opt(o) for o in opts if o[2][0] == c[0] and o[2][1] == d[0]]
        else:
            col = [h_opt(o) for o in group_first(opts, c[0])]
        cols.append(col)
    body = "".join("<tr>" + "".join(col[r] for col in cols) + "</tr>" for r in range(len(cols[0])))
    return '<table class="grid">' + head + body + "</table>"


def h_one_row(opts):
    return '<table class="grid"><tr>' + "".join(h_opt(o) for o in opts) + "</tr></table>"


def h_wrap(title, meta, body, leg, foot):
    return (f'<div class="ballot"><div class="head"><h1>{h(title)}</h1><div class="meta">{h(meta)}</div></div>'
            '<p class="notice">請只圈選一格。圈選兩個以上、空白或塗改者，無效。</p>'
            + (f'<p class="legend">{h(leg)}</p>' if leg else "")
            + body + f'<div class="foot"><span>選舉委員會製　樣張</span><span>{h(foot)}</span></div></div>')


def h_page(title, ballots):
    return ('<!DOCTYPE html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
            f"<title>{h(title)}</title><style>{CSS}</style></head><body>\n"
            + "\n".join(ballots) + "\n</body></html>\n")


# ------------------------------------------------------------ 輸出
def write(rel, text):
    with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def second_round(case, key, desc, md_body, h_body, cands):
    k = len(options(case, cands))
    meta = f"選區：○○　{len(cands)} 人決選　選項 1–{k}　唱票式人工計票"
    leg = legend(cands)
    write(f"{case}/第二輪/選票樣式-{key}.md",
          f"# ○○年○○選舉　第二輪決選選舉票（{key}）\n\n{meta}\n\n{NOTICE}\n\n{desc}\n\n"
          f"可列印：[`選票樣式-{key}.html`](選票樣式-{key}.html)。其他排版：[`選票樣式.md`](選票樣式.md)。"
          "每一格前面的粗體數字是**選項號次**（開票唱這個號次）；候選人用甲乙丙丁表示，為什麼這樣標示見 "
          "[`../../共用/候選人與選項的標示.md`](../../共用/候選人與選項的標示.md)。\n\n---\n\n"
          f"{leg}\n\n{md_body}\n\n選舉委員會製　　樣張\n")
    write(f"{case}/第二輪/選票樣式-{key}.html",
          h_page(f"第二輪決選（{case}・{key}）",
                 [h_wrap("○○年○○選舉　第二輪決選選舉票", f"{meta}　{key}", h_body, leg, "兩兩對決贏家當選")]))


def first_round():
    md_parts, h_parts = [], []
    for n in (4, 7, 10):
        c = FIRST[:n]
        md_parts.append(
            f"## 樣張：登記 {n} 人\n\n**請圈選一人**\n\n"
            + "| 圈選 | " + " | ".join("○" for _ in c) + " |\n|:---:|" + ":---:|" * n + "\n"
            + "| 號次 | " + " | ".join(f"**{x[0]}**" for x in c) + " |\n"
            + "| 個人照片 | " + " | ".join("〔相片〕" for _ in c) + " |\n"
            + "| 姓名 | " + " | ".join(f"**{x[1]}**" for x in c) + " |\n"
            + "| 推薦政黨 | " + " | ".join(x[2] for x in c) + " |\n\n"
            + "選舉委員會製　　樣張　　得票最高的 k 人進入第二輪")
        body = ('<table class="ids"><tr><th>圈選</th>'
                + "".join('<td><span class="mark circle"></span></td>' for _ in c) + "</tr>"
                + h_ids_rows(c).replace("<th>決選代號</th>", "<th>號次</th>").replace('class="tag"', 'class="no"') + "</table>")
        h_parts.append(h_wrap("○○年○○選舉　第一輪選舉票", f"選區：○○　登記 {n} 人　人工計票",
                              body, "", "得票最高的 k 人進入第二輪決選"))
    write("共用/第一輪/選票樣式.md",
          "# 第一輪選舉票（樣張，三種情況共用）\n\n選區：○○　台灣單一選區　人工計票\n\n" + NOTICE + "\n\n"
          "本張是兩輪一套的第一輪：**圈一個人**。得票最高的 k 人進第二輪（k＝3 或 4，依採用的情況）。"
          "登記人數 ≤ k 時不印本張，直接辦第二輪。**晉級者在第二輪依本輪號次由小到大稱甲、乙、丙（、丁）。**\n\n"
          "每人一欄。圈選、號次、相片、姓名、推薦政黨**各佔一格**；只圈最上面的圓框。"
          "樣張刻意放入長名：複姓（歐陽文心）、漢字音譯傳統名字（瑪拉歐斯·達拉阿道）、"
          "**原住民族文字單列**的姓名（Kaliting Tjaljaljav）與長黨名（台灣原住民族自治與土地正義聯盟）。"
          "登記 10 人是 2024 年區域立委單一選區的最多人數。\n\n"
          "可列印：[`選票樣式.html`](選票樣式.html)。設計理由：[`選票設計.md`](選票設計.md)。\n\n---\n\n"
          + "\n\n---\n\n".join(md_parts) + "\n")
    write("共用/第一輪/選票樣式.html", h_page("第一輪選舉票（樣張）", h_parts))


def build():
    first_round()
    for case, cands in (("k3-六選項", FINAL3), ("k3-九選項", FINAL3), ("k4-二十四選項", FINAL4)):
        opts = options(case, cands)
        sect = f'<p class="sect">請圈選一格（選項 1–{len(opts)}）</p>'
        ids_md, ids_h = md_ids(cands), h_ids(cands)
        if case == "k3-六選項":
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**，再從兩格裡挑一種完整順序。相片與推薦政黨印在欄首。",
                         md_cols(cands, opts), h_cols(cands, opts), cands)
            second_round(case, "依第一偏好分列",
                         "上方是三位候選人的代號（甲乙丙）、相片、姓名、推薦政黨。下方三列，每一列是「最喜歡某人」的兩種順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands)
            second_round(case, "一列六格",
                         "上方是三位候選人；下方一列六格，依選項號次排。最緊湊，但選民要自己找開頭的代號。",
                         ids_md + "\n\n" + md_cells(opts), ids_h + sect + h_one_row(opts), cands)
        elif case == "k3-九選項":
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**：只想表態這一人，圈欄內第一格「只選」；願意排完，圈下面兩格之一。",
                         md_cols(cands, opts), h_cols(cands, opts), cands)
            second_round(case, "依第一偏好分列",
                         "上方三位候選人；下方三列，每列是「最喜歡某人」的三種選法：只選他，或他開頭的兩種完整順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands)
            full = [o for o in opts if o[1] == "full"]
            bul = [o for o in opts if o[1] == "bullet"]
            second_round(case, "兩段",
                         "上段六格是**完整喜歡順序**；下段三格是**只選一人**。先決定要不要排完，再找格子。",
                         ids_md + "\n\n**完整喜歡順序（選項 1–6）**\n\n" + md_cells(full) + "\n\n**只選一人（選項 7–9）**\n\n" + md_cells(bul),
                         ids_h + '<p class="sect">完整喜歡順序（選項 1–6）</p>' + h_one_row(full)
                         + '<p class="sect">只選一人（選項 7–9）</p>' + h_one_row(bul), cands)
        else:
            second_round(case, "依第一偏好分欄",
                         "每一欄是一位候選人。**你最喜歡誰，就到誰的那一欄**，欄內六種完整順序挑一格。",
                         md_cols(cands, opts), h_cols(cands, opts), cands)
            second_round(case, "依第一偏好分欄-再依其次分組",
                         "同分欄版，但每欄再依**第二喜歡的人**分成三小組、每組兩格。找格變成三步：找欄（最喜歡）→ 找小組（其次）→ 兩格挑一。",
                         md_cols(cands, opts, grouped=True), h_cols(cands, opts, grouped=True), cands)
            second_round(case, "依第一偏好分列",
                         "上方四位候選人；下方四列，每列是「最喜歡某人」的六種完整順序。",
                         ids_md + "\n\n" + md_rows(cands, opts), ids_h + sect + h_rows(cands, opts), cands)


if __name__ == "__main__":
    build()
    print("ok")
