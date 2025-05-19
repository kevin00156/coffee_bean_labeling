# 咖啡豆標籤工具 (PyQt5 版本)

這是使用 PyQt5 實現的咖啡豆標籤工具，相比原版 Matplotlib 實現有以下優點：

1. 更快的圖片載入速度，尤其在總覽模式
2. 更流暢的使用者界面
3. 更好的內存管理
4. 更穩定的性能

## 標註前注意：
請先查看dataset/README.md文件，以確定標註標準

## 安裝依賴

```bash
pip install PyQt5 numpy Pillow pyyaml
```

## 運行程式

**建議使用命令提示符 (CMD) 運行該程式，而非 PowerShell**：

```bash
# 進入 dataset 目錄
cd dataset

# 運行程式
python dataset_label_marking_pyqt.py
```

或者直接通過 IDE (如 PyCharm、VSCode 等) 運行 `dataset_label_marking_pyqt.py` 文件。

## 功能說明

程式保留了原版所有功能，並優化了性能：

- 左右方向鍵：切換圖片
- 數字鍵：切換標籤
- Q 鍵：儲存並退出
- Home 鍵：跳到第一張圖片
- End 鍵：跳到最後一張圖片
- PageUp/PageDown：快速前後翻頁（10張）
- Insert：跳到上一張未標註OK的圖片
- Delete：跳到下一張未標註OK的圖片
- m 鍵：跳到下一張有多標籤的圖片
- M 鍵：跳到上一張有多標籤的圖片
- c 鍵：清除該圖片的所有標籤
- w 鍵：切換到總覽模式
- shift+左右方向鍵：查看上一個/下一個含有白名單標籤的圖片

總覽模式下：
- 左右方向鍵：切換顯示模式 (全部標籤或特定標籤)
- 上下方向鍵：翻頁
- 點擊圖片：打開標記視窗
- Q 鍵：返回主界面

## 備註

如果在運行過程中發現路徑問題，程式會嘗試自動尋找替代路徑。如仍有問題，可編輯程式中的路徑常量(utils/constants.py)：

```python
# 常數設定(以相對路徑呈現)
DATASET_NAME = "dataset/coffee_bean_dataset"
SUB_DATASET_NAME = "splits/split_1"  # 換分割檔的時候改這裡
WHITE_LIST = ["LOOKS_WEIRD"]  # 白名單標籤，如果你想要只審核某部分的類別改這裡
```

將其修改為實際的數據集路徑。