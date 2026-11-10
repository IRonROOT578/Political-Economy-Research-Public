# 資料

| 檔 | 內容 |
|---|---|
| `provinces.csv` | 24 省＋自治市：人口（INDEC 2022 普查約數）、質心經緯、複數區代碼 |
| `votes-2025.csv` | 2025-10-26 眾議院有效票（省×聯盟）。全國總數對齊維基；各省在已知結果上校準（布宜諾斯艾利斯省 LLA 41.5／FP 40.8 等）。官方站本機連不上，方法見 `14` |
| `circ-2023.csv` | **2023-10-22 眾議院有效票，選舉區（circuito）× 政黨**，5,752 列；由 DINE 逐投票桌暫定開票彙整（`_build_circ.py`，來源 datos.gob.ar `2023_generales_1.zip`）。模型的 2023 與 2025 省內分布都用它 |
| `votes-2023.csv` | 舊版省級推估（已不使用，保留對照） |

來源：Wikipedia *2025 Argentine legislative election*、*2023 Argentine general election*；人口 INDEC。
