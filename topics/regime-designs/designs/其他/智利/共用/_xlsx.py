"""極簡 xlsx 讀取器（只讀第一張工作表的儲存格值）。"""
import re, zipfile
import xml.etree.ElementTree as ET
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
def col_idx(ref):
    s = re.match(r"[A-Z]+", ref).group()
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n - 1
def read(path, sheet=1):
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    names = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))
    root = ET.fromstring(z.read(names[sheet - 1]))
    rows = []
    for r in root.iter("{%s}row" % NS["m"]):
        row = {}
        for c in r.findall("m:c", NS):
            v = c.find("m:v", NS)
            if v is None:
                is_ = c.find("m:is", NS)
                val = "".join(t.text or "" for t in is_.iter("{%s}t" % NS["m"])) if is_ is not None else None
            elif c.get("t") == "s":
                val = shared[int(v.text)]
            else:
                val = v.text
            row[col_idx(c.get("r"))] = val
        if row:
            rows.append([row.get(i) for i in range(max(row) + 1)])
    return rows, len(names)
