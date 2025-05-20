import os

# 獲取目前工作目錄 - 從constants.py向上三層為工作目錄
WORKING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# 數據集相關常數
DATASET_NAME = "dataset/coffee_bean_dataset"
SUB_DATASET_NAME = "splits/split_9"  # 換分割檔的時候改這裡
THUMBNAIL_SIZE = (200, 200)  # 縮圖尺寸用於總覽
WHITE_LIST = ["IMMATURE"]  # 白名單標籤

# 文件路徑配置
def get_path_configs():
    """獲取文件路徑配置，返回有效的路徑集合"""
    # 嘗試多個可能的路徑
    possible_paths = [
        # 1. 原始相對路徑
        {
            "folder": os.path.join(WORKING_DIR, DATASET_NAME, SUB_DATASET_NAME),
            "yaml_file": os.path.join(WORKING_DIR, DATASET_NAME, f"{SUB_DATASET_NAME}_dataset.yaml"),
            "settings_yaml": os.path.join(WORKING_DIR, "dataset", "settings.yaml")
        },
        # 2. 上一級目錄
        {
            "folder": os.path.join(os.path.dirname(WORKING_DIR), DATASET_NAME, SUB_DATASET_NAME),
            "yaml_file": os.path.join(os.path.dirname(WORKING_DIR), DATASET_NAME, f"{SUB_DATASET_NAME}_dataset.yaml"),
            "settings_yaml": os.path.join(os.path.dirname(WORKING_DIR), "settings.yaml")
        },
        # 3. dataset 子目錄中
        {
            "folder": os.path.join(WORKING_DIR, "dataset", DATASET_NAME, SUB_DATASET_NAME),
            "yaml_file": os.path.join(WORKING_DIR, "dataset", DATASET_NAME, f"{SUB_DATASET_NAME}_dataset.yaml"),
            "settings_yaml": os.path.join(WORKING_DIR, "dataset", "settings.yaml")
        }
    ]
    
    return possible_paths

# 預設設定
DEFAULT_SETTINGS = {
    "labels": {
        "1": "OK",
        "2": "IMMATURE",
        "3": "LOOKS_WEIRD",
        "4": "INSECT_DAMAGE",
        "5": "BROKEN"
    },
    "last_index": 0
}

# UI 相關常數
STATUS_MESSAGES = {
    "ready": "準備就緒",
    "loading": "載入中...",
    "saving": "儲存中...",
    "error": "發生錯誤",
    "completed": "操作完成"
}

# 顏色常數
COLORS = {
    "error": "#FF6666",
    "warning": "#FFCC66",
    "success": "#66CC99",
    "default": "#F0F0F0",
    "highlight": "#A3C2C2"
}

# 圖示和樣式
STYLES = {
    "widget": """
        QWidget {
            background-color: #f0f0f0;
            border-radius: 5px;
        }
        QLabel {
            color: #333;
        }
    """,
    "button": """
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
    """,
    "highlighted_button": """
        QPushButton {
            background-color: #a3c2c2;
            border: 1px solid #8ab;
            border-radius: 3px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #b4d3d3;
        }
        QPushButton:pressed {
            background-color: #92b1b1;
        }
    """
} 