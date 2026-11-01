# 資料

| 檔 | 內容 |
|---|---|
| [`ge-2023.csv`](ge-2023.csv) | 2023-10 投票所政黨票（校準官方選區總票） |
| [`ge-2020.csv`](ge-2020.csv) | 2020-10 同上 |
| [`ge-2017.csv`](ge-2017.csv) | 2017-09 同上 |
| [`ge-2014.csv`](ge-2014.csv) | 2014-09 同上 |

- **單位**：Electoral Commission 投票所（提前＋當日同址合併）；含原毛利選區所（本夾廢平行選區席，併入四區切開）。
- **校準**：sage-archive 投票所層 × scgElectionsNZ 官方選區政黨票縮放。
- **重抓**：[`../_fetch_sage.py`](../_fetch_sage.py)。不入庫 parquet／rda 原檔。
