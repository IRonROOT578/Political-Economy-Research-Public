"""日本一院議會制：2026-10 政黨支持率套本夾（相對大選前同一家民調的變化）。

    python 民調推估.py

政黨支持率不是投票意向：約四成「支持なし」，直接把表列政黨重新正規化會把自民放大到六成以上。
所以改用**同一家民調的變化**：每黨比例 r＝(最新＋0.5)／(基準＋0.5)（＋0.5 壓住小黨的雜訊），
基準＝大選前一週的同家調查；目標得票＝2026-02 實際比例票 × r，再正規化，
再以 2026 市區町村地理（資料/shugiin-2026.csv）逐單位縮放後跑本夾。
中道＝中道改革連合；2026-10 的民調把立憲系與公明分列，這裡相加對到中道。減稅日本・憂國連合計在其他。
來源：資料/polls.csv（基準列摘自 Wikipedia「Opinion polling for the 2026 Japanese general election」；最新列同 my_research/parliament_condorcet/japan/data/input_vote_shares.csv）。
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import 生態模型 as m  # noqa: E402


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    with open(os.path.join(HERE, "資料", "polls.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    base = {r["poll"]: r for r in rows if r["role"] == "基準"}
    units = m.load(2026)
    vote = m.national(units)
    for r in rows:
        if r["role"] != "最新":
            continue
        b = base[r["poll"]]
        ratio = {p: (float(r[p]) + 0.5) / (float(b[p]) + 0.5) for p in vote if p in r}
        tgt = {p: vote[p] * ratio.get(p, 1.0) for p in vote}
        s = sum(tgt.values())
        tgt = {p: v * 100 / s for p, v in tgt.items()}
        mult = {p: tgt[p] / vote[p] for p in vote if vote[p]}
        su = [u[:5] + ({p: v * mult.get(p, 1.0) for p, v in u[5].items()},) for u in units]
        smd, lst, total, stats, _ = m.run(2026, units=su)
        w, cyc, worst = m.head_of_gov(total)
        seq, acc = m.coalition(total, w)
        print(f"## {r['poll']}（{r['fieldwork']}，基準 {b['fieldwork']}）")
        print("換算得票%：", "、".join(f"{p} {v:.1f}" for p, v in sorted(tgt.items(), key=lambda x: -x[1])))
        print("單一 280：", m.fmt(smd))
        print("複數 185：", m.fmt(lst))
        print("全院 465：", m.fmt(total))
        print(f"首長 {w}（最弱 {worst:.0f}）；組閣 {'＋'.join(seq)}＝{acc}")
        print()


if __name__ == "__main__":
    main()
