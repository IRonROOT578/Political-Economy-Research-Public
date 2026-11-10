"""台灣一院總統制-測試：議會選制與一院議會制相同，過去大選沿用那一夾的重算。

直選總統不在這支腳本。`k` 寫在本檔的 `report`，top-4／全候選人測試會改這個預設值再傳進去。
"""
import importlib.util
import pathlib
import sys

_LEG = pathlib.Path(__file__).resolve().parent.parent / "一院議會制" / "近期大選推估.py"


_cached = None


def _leg():
    # _run_k 會先把本夾的生態模型掛成「生態模型」；議會重算要的是一院議會制那支。
    global _cached
    if _cached is not None:
        return _cached
    sys.modules.pop("生態模型", None)
    spec = importlib.util.spec_from_file_location("tw_leg_hist", _LEG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _cached = mod
    return mod


def report(year, mode="政黨", q=None, verbose=True, k=3):
    leg = _leg()
    return leg.report(year, mode, leg.Q if q is None else q, verbose, k)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for year, mode in ((2024, "政黨"), (2020, "政黨"), (2016, "政黨"), (2012, "政黨")):
        report(year, mode)


if __name__ == "__main__":
    main()
