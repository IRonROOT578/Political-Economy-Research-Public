# 資料

| 檔 | 內容 |
|---|---|
| [`ft-2022.csv`](ft-2022.csv) | 2022-11 Folketing：92 opstillingskreds × 主要政黨有效票 |
| [`ft-2019.csv`](ft-2019.csv) | 2019-06 同上 |

來源：Danmarks Statistik Statistikbanken API 表 **FV22TOTA**／**FV19TOTA**（`OMRÅDE` id 20–111）。重抓：[`../_fetch_dst.py`](../_fetch_dst.py)。

`land` 欄對應本夾五區（storkreds 10–13→Hovedstaden；14→Sjælland；15–16→Syddanmark；17–18→Midtjylland；19→Nordjylland）。不入庫 API 原始 JSON。
