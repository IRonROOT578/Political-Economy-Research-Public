"""維基 June/May 2023 Greek parliamentary election 的 By constituency 表（百分比）＋選區表（居民、席次）→ CSV。
Usage: parse.py ELECTION.wiki CONSTITUENCIES.wiki OUTCSV"""
import csv, re, sys
W, C, OUT = sys.argv[1:4]
sys.stdout.reconfigure(encoding="utf-8")
def clean(c):
    c = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", c)
    c = re.sub(r"\{\{[^{}]*\}\}", "", c)
    if re.match(r'\s*(style|align|rowspan|colspan)=', c) and "|" in c:
        c = c.split("|", 1)[1]
    c = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", c).replace("'''", "")
    return c.strip()
ALIAS = {"Aetolia-Akarnania": "Aetolia-Acarnania", "Arkadia": "Arcadia"}
def name(n):
    n = re.sub(r"\s*\(constituency\)", "", n)
    n = n.split(" – ")[0].strip()
    return ALIAS.get(n, n)
# 選區表
t = open(C, encoding="utf-8").read()
i = t.index("{|"); j = t.index("|}", i)
rows, cur = [], []
for l in t[i:j].splitlines():
    if l.startswith("|-"):
        if cur: rows.append(cur)
        cur = []
    elif l.startswith("|") and not l.startswith("|+"):
        cur += [clean(x) for x in l[1:].split("||")]
if cur: rows.append(cur)
meta = {}
for r in rows:
    if len(r) >= 3 and r[1].replace(",", "").isdigit():
        meta[name(r[0])] = (int(r[1].replace(",", "")), int(r[2]))
# 選舉表
t = open(W, encoding="utf-8").read()
i = re.search(r"=+ *By constituency *=+|=+ *Results by constituency *=+|=+ *Results by region *=+", t).start()
i = t.index("{|", i); j = t.index("|}", i)
lines = t[i:j].splitlines()
hdr = [clean(x) for x in lines[1].lstrip("!").split("!!") if clean(x)]
parties = [h for h in hdr if h != "Constituency"]
out = []
for l in lines:
    if not re.match(r'\|\s*align="?left"?', l):
        continue
    cells = [clean(x) for x in l[1:].split("||")]
    nm = name(cells[0])
    vals = cells[1:]
    pct = [float(vals[2 * k]) if re.fullmatch(r"[\d.]+", vals[2 * k] or "") else 0.0 for k in range(len(parties))]
    out.append([nm] + list(meta.get(nm, (0, 0))) + pct)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["選區", "居民2021", "現行席次"] + parties)
    w.writerows(out)
miss = [o[0] for o in out if not o[1]]
print(OUT, len(out), "選區；parties", parties, "；居民對不上", miss)
print("residents total", sum(o[1] for o in out), "seats", sum(o[2] for o in out))
