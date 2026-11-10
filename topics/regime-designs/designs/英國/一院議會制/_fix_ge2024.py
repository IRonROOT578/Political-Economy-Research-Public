"""補 資料/ge-2024.csv 缺的兩區（原表解析失敗）：Chorley（議長選區）、North Norfolk。

    python _fix_ge2024.py

來源：英文維基 Chorley (constituency)、North Norfolk (constituency) 的 2024 General election 開票表（2026-11-10 取得）。
座標沿用 資料/ge-2019.csv 的同名選區。

Chorley：議長 Lindsay Hoyle 25,238（＝Green 4,663＋多數 20,575）；Green 4,663；Democracy for Chorley 2,424；
English Constitution Party 1,007；TUSC 632；有效票 33,964。依慣例各大黨不推人與議長對壘——這是議會慣例，
不是相對多數制的分票考量；但新制下現行選區會併成較大的新選區，議長不再有自己的選區（14 §1）。
所以依算法規劃 §5：議長票按西北區（NW）2024 年工黨、保守黨、Reform、自民黨的得票比例分回四黨；
Green 照實；其他三位併入「其他」。

North Norfolk：自民黨 Steff Aquarone 19,488（＝保守黨 16,903＋多數 2,585）；保守黨 16,903；Reform 6,368；
工黨 2,878；Green 1,406；有效票 47,043。
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "資料", "ge-2024.csv")
rows = list(csv.reader(open(P, encoding="utf-8")))
hdr, data = rows[0], rows[1:]
names = {r[1] for r in data}
cols = hdr[5:]
nw = {c: 0 for c in ("Lab", "Con", "Reform", "LD")}
for r in data:
    if r[0] == "NW":
        for c in nw:
            nw[c] += int(r[hdr.index(c)])
tot = sum(nw.values())
speaker = 25238
add = []
if "Chorley" not in names:
    v = {c: 0 for c in cols}
    for c in nw:
        v[c] = round(speaker * nw[c] / tot)
    v["Green"] = 4663
    v["其他"] = 2424 + 1007 + 632
    add.append(["NW", "Chorley", "-2.62586", "53.65759", str(sum(v.values()))] + [str(v[c]) for c in cols])
if "North Norfolk" not in names:
    v = {c: 0 for c in cols}
    v.update({"LD": 19488, "Con": 16903, "Reform": 6368, "Lab": 2878, "Green": 1406})
    add.append(["E", "North Norfolk", "1.315708", "52.8289", str(sum(v.values()))] + [str(v[c]) for c in cols])
if add:
    with open(P, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(add)
print("補", [a[1] for a in add], "；西北區四黨比例", {c: round(n / tot, 3) for c, n in nw.items()})
