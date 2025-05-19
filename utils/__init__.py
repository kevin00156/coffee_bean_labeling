"""
咖啡豆標籤工具 - 工具模組包

本包包含用於咖啡豆標籤工具的各種工具模組，包括:
- constants: 常數定義
- logger: 日誌功能
- file_utils: 文件操作工具
- image_loader: 圖像加載工具
- widgets: 自定義UI小部件
"""

# 使常用類和方法可以直接從包導入
from .logger import get_logger, set_global_log_level, app_logger
from .constants import WORKING_DIR, THUMBNAIL_SIZE, WHITE_LIST
from .file_utils import normalize_path, load_settings, save_settings, load_dataset, save_dataset, clean_dataset, get_image_list
from .image_loader import ImageLoader, load_image
from .widgets import ThumbnailWidget, LoadingDialog

# 設置版本信息
__version__ = '0.1.0' 
 