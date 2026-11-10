# 資料

| 檔 | 內容 |
|---|---|
| `raw-2025.csv` | AEC 事件 31496，眾議院候選人×票種第一偏好。最終結果，2025-06-16 產生 |
| `raw-2022.csv` | AEC 事件 27966，同一格式 |
| `polls.csv` | 2026 年各家最新投票意向。維基 Opinion polling for the next Australian federal election，2026-11-08 頁面 |

第一行是 AEC 的產生資訊，欄位名在 `StateAb` 那一列。`TotalVotes` 是該候選人的第一偏好合計。`PartyAb` 空白的列是非正式票，模型不計。

黨籍代碼對到 [`../生態模型.py`](../生態模型.py) 的 `PARTY`。沒對上的小黨計入「未入模型票」，不進席次。獨立候選人保留選區與姓氏。
