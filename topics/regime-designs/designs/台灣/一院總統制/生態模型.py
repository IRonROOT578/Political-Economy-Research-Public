"""台灣一院總統制：預期政治生態的機械效應模型。

本夾與一院總統制-測試夾的選舉完全相同（總統全國 top-3 孔多賽、單一 100 top-3 孔多賽、
複數 80 七區聖拉古），兩夾只差預算規則（本夾不用預提）。預算規則不進入模型的投票行為，
所以直接載入測試夾的 生態模型.py 執行；假設與輸出相同。

    python 生態模型.py            # 印出 15 用的數字
    python 生態模型.py --sweep    # 總統與單一席次對第二偏好的敏感度
"""
import importlib.util
import pathlib

_B = pathlib.Path(__file__).resolve().parent.parent / "一院總統制-測試" / "生態模型.py"
_spec = importlib.util.spec_from_file_location("一院總統制選舉", _B)
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)

if __name__ == "__main__":
    b.main()
