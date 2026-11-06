"""內政部國會第一輪：2024 逐投票所（bv24.csv＋逐選區檔對候選人回推選區）、2022 逐市鎮（subcom）→ 市鎮×選區 單位 CSV。
Usage: build.py DLDIR OUTDIR"""
import collections, csv, sys
DL, OUT = sys.argv[1:3]
sys.stdout.reconfigure(encoding="utf-8")
COLS = ["國", "左", "中", "共", "右", "極", "他"]
M24 = {**dict.fromkeys(["RN", "UXD"], "國"), **dict.fromkeys(["UG", "FI", "SOC", "COM", "VEC", "DVG"], "左"),
       **dict.fromkeys(["ENS", "HOR", "DVC"], "中"), **dict.fromkeys(["LR", "DVD", "UDI"], "共"),
       **dict.fromkeys(["REC", "EXD", "DSV"], "右"), "EXG": "極", **dict.fromkeys(["REG", "DIV", "ECO", "RDG"], "他")}
M22 = {"RN": "國", "NUP": "左", "DVG": "左", "ENS": "中", "DVC": "中", "LR": "共", "DVD": "共", "UDI": "共",
       "REC": "右", "DXD": "右", "DSV": "右", "DXG": "極", **dict.fromkeys(["ECO", "REG", "DIV", "RDG"], "他")}
Z = {"ZA": "971", "ZB": "972", "ZC": "973", "ZD": "974", "ZM": "976", "ZN": "988", "ZP": "987", "ZS": "975", "ZW": "986"}
dep = lambda d: Z.get(d, d.lstrip("0") or "0")


def write(name, units):
    with open(f"{OUT}/{name}", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["省", "選區", "市鎮", "選舉人"] + COLS)
        for (d, c, com), (ins, v) in sorted(units.items(), key=lambda k: (k[0][0], k[0][1], k[0][2])):
            w.writerow([d, c, com, ins] + [v.get(g, 0) for g in COLS])
    print(name, len(units), "單位")


# 2024：候選人 → 選區
cand = {}
r = csv.reader(open(f"{DL}/leg24_t1_circ.csv", encoding="utf-8"), delimiter=";")
h = next(r)
for row in r:
    c = int(row[2][-2:]) if row[2][-2:].isdigit() else row[2]
    for i, x in enumerate(h):
        if x.startswith("Nom candidat") and row[i]:
            cand[(row[0], row[i], row[i + 1])] = c
units, miss = {}, 0
r = csv.reader(open(f"{DL}/bv24.csv", encoding="utf-8"), delimiter=";")
h = next(r)
nom = [i for i, x in enumerate(h) if x.startswith("Nom candidat")]
for row in r:
    cs = {cand.get((row[0], row[i], row[i + 1])) for i in nom if row[i]} - {None}
    if len(cs) != 1:
        miss += 1
        continue
    key = (dep(row[0]), cs.pop(), row[2].zfill(5) if row[2].isdigit() else row[2])
    u = units.setdefault(key, [0, collections.Counter()])
    u[0] += int(row[5] or 0)
    for i in nom:
        if row[i]:
            u[1][M24[row[i - 1]]] += int(row[i + 3] or 0)
print("2024 對不上選區的投票所", miss)
write("legis-2024.csv", units)
units = {}
for l in open(f"{DL}/sub22.txt", encoding="latin1"):
    f = l.rstrip("\n").split(";")
    if f[0].startswith("Code"):
        continue
    d = f[0]
    com = (d.zfill(2) + f[4]) if d.isdigit() else (Z[d][:3] + f[4][-2:] if d in Z else d + f[4])
    key = (dep(d), int(f[2]), com)
    u = units.setdefault(key, [0, collections.Counter()])
    u[0] += int(f[7])
    for i in range(25, len(f), 8):
        u[1][M22[f[i]]] += int(f[i + 1])
write("legis-2022.csv", units)
