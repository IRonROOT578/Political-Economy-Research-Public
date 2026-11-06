"""中央選管委 第 22 屆國會議員選舉 地域區 開票結果（data.go.kr 15025527，逐 邑面洞×投票區）→ 逐邑面洞 CSV。
選區層級的票（거소·선상、관외사전、국외부재자、잘못 투입）依各邑面洞的選舉日投票區選舉人數比例分回。
Usage: build.py SMDCSV(utf-8) OUTCSV"""
import collections, csv, sys
SRC, OUT = sys.argv[1:3]
sys.stdout.reconfigure(encoding="utf-8")
PROV = {"서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주", "대전": "대전", "울산": "울산", "세종": "세종",
        "경기": "경기", "강원": "강원", "충청북": "충북", "충청남": "충남", "전라북": "전북", "전북": "전북", "전라남": "전남", "경상북": "경북", "경상남": "경남", "제주": "제주"}
PARTY = {"더불어민주당": "民", "국민의힘": "國", "개혁신당": "改", "진보당": "進", "녹색정의당": "綠", "새로운미래": "新", "자유통일당": "統", "무소속": "無",
         "소나무당": "進", "새진보연합": "進", "노동당": "進", "우리공화당": "統", "자유민주당": "統"}
CODES = ["民", "國", "改", "進", "綠", "新", "統", "無", "他"]
POOL = {"거소·선상투표", "관외사전투표", "국외부재자투표", "잘못 투입·구분된 투표지"}
prov = lambda s: next(v for k, v in PROV.items() if s.startswith(k))
dorder, units, pools = [], collections.OrderedDict(), collections.defaultdict(collections.Counter)
for r in list(csv.reader(open(SRC, encoding="utf-8")))[1:]:
    p, d, dong, booth, cand, n = prov(r[0]), r[1], r[2], r[3], r[4], int(r[5] or 0)
    if (p, d) not in dorder:
        dorder.append((p, d))
    if cand in ("투표수", "무효 투표수", "기권자수"):
        continue
    if dong in POOL:
        pools[(p, d)]["_e" if cand == "선거인수" else PARTY.get(cand.split(" ")[0], "他")] += n
        continue
    u = units.setdefault((p, d, dong), [0, collections.Counter(), 0])
    if cand == "선거인수":
        u[0] += n                      # 選舉日名冊＋관내사전（其선거인수＝投票數）
        if booth != "관내사전투표":
            u[2] += n
    else:
        u[1][PARTY.get(cand.split(" ")[0], "他")] += n
for (p, d), pool in pools.items():
    us = [(k, u) for k, u in units.items() if k[0] == p and k[1] == d]
    tot = sum(u[2] for _, u in us)
    for _, u in us:
        for c, n in pool.items():
            if c == "_e":
                u[0] += n * u[2] / tot
            else:
                u[1][c] += n * u[2] / tot
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["市道", "選區", "邑面洞", "選舉人"] + CODES)
    for (p, d) in dorder:
        for k, u in units.items():
            if k[0] == p and k[1] == d:
                w.writerow([p, d, k[2], round(u[0])] + [round(u[1].get(c, 0)) for c in CODES])
print(len(units), "邑面洞單位；", len(dorder), "選區")
