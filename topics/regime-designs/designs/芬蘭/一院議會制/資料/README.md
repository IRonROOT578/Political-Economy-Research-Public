# 資料

| 檔 | 內容 |
|---|---|
| [`fi-2023.csv`](fi-2023.csv) | 2023-04 市鎮×黨 |
| [`fi-2019.csv`](fi-2019.csv) | 2019-04 同上 |
| [`fi-2015.csv`](fi-2015.csv) | 2015-04 市鎮×黨（317 市鎮、有效票 2,968,462） |
| [`polls.csv`](polls.csv) | 2027 大選前民調（Yle／Taloustutkimus、HS／Verian 各最新一筆） |

來源：正義部 tulospalvelu。2019、2023 是 `EKV-{年}/ekv-{年}_puo_maa.csv.zip`；2015 是 `E-2015/e-2015_puo_maa.csv.zip` 的市鎮層（檔內 A／K／V 三層只取 K）。全國有效票 2,968,462，中間黨 626,218，與正義部公布一致。`district`＝vaalipiiri；模型內 remap 八區＋奧蘭。新地西市鎮清單見 `生態模型.py` `UUSIMAA_WEST`。2011 的同路徑回 404，這次沒有加。民調來源見維基 Opinion polling for the 2027 Finnish parliamentary election。
