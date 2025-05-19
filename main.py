#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
咖啡豆標籤工具主程序

該程序用於標記咖啡豆圖片，支持多種標籤分類和總覽模式。
使用模塊化結構，便於維護和調試。
"""

import os
import sys
import time
import atexit
import yaml

from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QGridLayout, QScrollArea,
                            QPushButton, QStatusBar, QMessageBox, QSplitter,
                            QFrame, QToolBar, QAction, QSizePolicy, QProgressBar,
                            QShortcut)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QPalette, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QEvent, QRect
from PIL import Image
import numpy as np

# 導入自定義工具模塊
from utils import (
    # 常數
    WORKING_DIR, THUMBNAIL_SIZE, WHITE_LIST,
    # 日誌
    get_logger, set_global_log_level, app_logger,
    # 文件工具
    normalize_path, load_settings, save_settings, load_dataset, save_dataset, clean_dataset, get_image_list,
    # 圖像工具
    ImageLoader, load_image,
    # 小部件
    ThumbnailWidget, LoadingDialog
)
from utils.constants import get_path_configs, DEFAULT_SETTINGS, STATUS_MESSAGES, COLORS, STYLES

# 導入視窗類
from utils.windows import LabelingWindow, OverviewWindow

# 獲取當前模組的 logger
logger = get_logger('main')

# 檢查是否有必要的依賴
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    logger.error("錯誤: 找不到 PyQt5 庫，請安裝: pip install PyQt5")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    logger.error("錯誤: 找不到 numpy 庫，請安裝: pip install numpy")
    sys.exit(1)
    
try:
    from PIL import Image
except ImportError:
    logger.error("錯誤: 找不到 PIL 庫，請安裝: pip install Pillow")
    sys.exit(1)
    
try:
    import yaml
except ImportError:
    logger.error("錯誤: 找不到 yaml 庫，請安裝: pip install pyyaml")
    sys.exit(1)

# 獲取目前工作目錄
logger.info(f"工作目錄: {WORKING_DIR}")


# 嘗試多個可能的路徑
possible_paths = get_path_configs()

# 檢查每個可能的路徑
for i, path_set in enumerate(possible_paths):
    logger.info(f"嘗試路徑選項 {i+1}:")
    logger.info(f"  - 資料夾: {path_set['folder']}")
    if os.path.exists(path_set['folder']):
        logger.info(f"  - 資料夾存在 ✓")
        FOLDER = path_set['folder']
        YAML_FILE = path_set['yaml_file']
        SETTINGS_YAML = path_set['settings_yaml']
        break
    else:
        logger.info(f"  - 資料夾不存在 ✗")
else:
    # 如果沒有找到有效路徑，使用第一個選項並顯示警告
    logger.warning("警告: 沒有找到有效的資料夾路徑，將使用第一個選項並在啟動時提示用戶")
    FOLDER = possible_paths[0]['folder']
    YAML_FILE = possible_paths[0]['yaml_file']
    SETTINGS_YAML = possible_paths[0]['settings_yaml']

logger.info(f"最終使用路徑:")
logger.info(f"  - 資料夾: {FOLDER}")
logger.info(f"  - YAML檔: {YAML_FILE}")
logger.info(f"  - 設定檔: {SETTINGS_YAML}")

# 確保設定檔存在
if not os.path.exists(SETTINGS_YAML):
    logger.warning(f"警告: 設定檔 {SETTINGS_YAML} 不存在，將創建默認設定")
    
    # 確保目錄存在
    settings_dir = os.path.dirname(SETTINGS_YAML)
    if not os.path.exists(settings_dir):
        try:
            os.makedirs(settings_dir)
            logger.info(f"創建目錄: {settings_dir}")
        except Exception as e:
            logger.error(f"錯誤: 無法創建目錄 {settings_dir}: {e}")
    
    try:
        with open(SETTINGS_YAML, 'w', encoding='utf-8') as f:
            yaml.dump(DEFAULT_SETTINGS, f, indent=2, allow_unicode=True)
        logger.info(f"已創建默認設定檔: {SETTINGS_YAML}")
    except Exception as e:
        logger.error(f"錯誤: 無法創建設定檔 {SETTINGS_YAML}: {e}")

# 主應用程式類別
class CoffeeBeanLabeler(QMainWindow):
    """主應用程式類別，處理主界面和標記邏輯"""
    
    def __init__(self):
        super().__init__()
        
        # 標記變更狀態
        self.has_changes = False
        self.img_path = None
        
        # 檢查資料夾是否存在
        if not os.path.exists(FOLDER):
            reply = QMessageBox.critical(
                self, "錯誤", 
                f"找不到資料夾: {FOLDER}\n\n是否要創建此資料夾？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    os.makedirs(FOLDER, exist_ok=True)
                    logger.info(f"已創建資料夾: {FOLDER}")
                except Exception as e:
                    logger.error(f"無法創建資料夾: {e}")
                    QMessageBox.critical(self, "錯誤", f"無法創建資料夾: {e}")
                    sys.exit(1)
            else:
                QMessageBox.information(
                    self, "提示", 
                    "請修改程式設定中的路徑或確保數據集存在後再啟動程式。"
                )
                sys.exit(1)
        
        # 載入設定與資料
        try:
            self.settings = load_settings(SETTINGS_YAML)
            self.labels = self.settings['labels']
            logger.info("設定已成功載入")
        except Exception as e:
            logger.error(f"載入設定檔時出錯: {e}")
            QMessageBox.critical(self, "錯誤", f"載入設定檔時出錯: {e}")
            sys.exit(1)
            
        try:
            self.data = load_dataset(YAML_FILE, WORKING_DIR)
            
            # 清理資料集中的重複路徑
            cleaned, cleaned_data = clean_dataset(YAML_FILE, self.data, WORKING_DIR)
            if cleaned:
                self.data = cleaned_data
                # 立即保存清理後的資料集
                save_dataset(YAML_FILE, self.data, WORKING_DIR)
                logger.info("已自動清理並保存更新後的資料集")
                
        except Exception as e:
            logger.error(f"載入資料集檔案時出錯: {e}")
            reply = QMessageBox.warning(
                self, "警告", 
                f"載入資料集檔案時出錯: {e}\n\n是否要創建新的資料集檔案？",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.data = {'dataset': {}}
                logger.info("已創建新的資料集")
            else:
                sys.exit(1)
        
        # 獲取圖片列表
        try:
            # 使用工具函數獲取圖片列表
            self.image_paths = get_image_list(FOLDER)
            logger.info(f"已加載 {len(self.image_paths)} 張圖片")
        except Exception as e:
            logger.error(f"讀取圖片列表時出錯: {e}")
            QMessageBox.critical(self, "錯誤", f"讀取圖片列表時出錯: {e}")
            sys.exit(1)
        
        if not self.image_paths:
            logger.error(f"在資料夾 {FOLDER} 中沒有找到任何圖片")
            reply = QMessageBox.critical(
                self, "錯誤", 
                f"在資料夾 {FOLDER} 中沒有找到任何圖片。\n\n請確保路徑正確並包含圖片檔案。",
                QMessageBox.Ok
            )
            sys.exit(1)
            
        # 從上次的位置開始
        self.current_index = self.settings['last_index']
        
        # 確保索引在有效範圍內
        if self.current_index >= len(self.image_paths):
            self.current_index = len(self.image_paths) - 1
        elif self.current_index < 0:
            self.current_index = 0
            
        # 設定UI
        self.setup_ui()
        
        # 顯示起始資訊
        logger.info(f"從第 {self.current_index + 1} 張圖片開始標記（共 {len(self.image_paths)} 張）")
        logger.info(f"資料集中共有 {len(self.data['dataset'])} 張圖片的標記")
        self.print_help()
        
        # 註冊退出時的儲存函數
        atexit.register(self.save_on_exit)
        
        # 更新顯示
        self.update_display()
        
        # 檢查資料集中的路徑是否所有圖片都能找到
        self.check_dataset_paths()
        
        # 顯示歡迎訊息
        #self.show_welcome_message()
    
    def setup_ui(self):
        """設置使用者界面"""
        logger.debug("設置使用者界面")
        self.setWindowTitle("咖啡豆標籤標記工具")
        self.resize(1000, 800)
        
        # 主要部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 圖片顯示區
        self.image_container = QWidget()
        image_layout = QVBoxLayout(self.image_container)
        image_layout.setContentsMargins(10, 10, 10, 30)  # 底部留出更多空間
        
        # 圖片標籤和滾動區域設置
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(400)  # 減小最小高度，使布局更靈活
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 讓圖片區域可以擴展
        self.image_label.setScaledContents(False)  # 不使用自動縮放，我們會手動控制
        
        # 創建滾動區域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 確保滾動區域可以根據內容自動調整大小
        scroll_area.setWidget(self.image_label)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 滾動區域也可以擴展
        
        image_layout.addWidget(scroll_area)
        
        # 標籤顯示區 - 增加空間和樣式
        self.label_info = QLabel()
        self.label_info.setAlignment(Qt.AlignCenter)
        self.label_info.setStyleSheet("margin: 15px 0; font-size: 14px; min-height: 40px;")
        
        # 導航欄
        nav_layout = QHBoxLayout()
        
        prev_btn = QPushButton("上一張 (←)")
        prev_btn.clicked.connect(self.prev_image)
        
        next_btn = QPushButton("下一張 (→)")
        next_btn.clicked.connect(self.next_image)
        
        overview_btn = QPushButton("總覽模式 (W)")
        overview_btn.clicked.connect(self.show_overview)
        
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        nav_layout.addWidget(overview_btn)
        
        # 標籤按鈕
        label_layout = QGridLayout()
        self.label_buttons = {}
        
        row, col = 0, 0
        max_cols = 5
        
        for key, label in self.labels.items():
            btn = QPushButton(f"{key}: {label}")
            btn.clicked.connect(lambda checked, lbl=label: self.toggle_label(lbl))
            label_layout.addWidget(btn, row, col)
            self.label_buttons[label] = btn
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # 更多操作按鈕
        more_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清除全部標籤 (Shift+C)")
        clear_btn.clicked.connect(self.clear_labels)
        
        save_btn = QPushButton("儲存並退出 (Q)")
        save_btn.clicked.connect(self.close)
        
        more_layout.addWidget(clear_btn)
        more_layout.addWidget(save_btn)
        
        # 狀態欄
        self.statusBar().showMessage(f"圖片 {self.current_index + 1}/{len(self.image_paths)}")
        
        # 整體佈局
        layout.addWidget(self.image_container, 3)  # 給圖片區域分配更大的伸展因子
        layout.addWidget(self.label_info)
        layout.addLayout(nav_layout)
        layout.addLayout(label_layout)
        layout.addLayout(more_layout)
        
        # 設置鍵盤快捷鍵
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """設置鍵盤快捷鍵"""
        logger.debug("設置快捷鍵")
        
        # 換圖快捷鍵
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.prev_image)
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.next_image)
        QShortcut(QKeySequence(Qt.Key_Home), self).activated.connect(self.first_image)
        QShortcut(QKeySequence(Qt.Key_End), self).activated.connect(self.last_image)
        QShortcut(QKeySequence(Qt.Key_PageUp), self).activated.connect(self.page_up)
        QShortcut(QKeySequence(Qt.Key_PageDown), self).activated.connect(self.page_down)
        
        # 標籤快捷鍵
        for key, label in self.labels.items():
            try:
                # 直接使用字符串鍵值設置快捷鍵
                shortcut = QShortcut(QKeySequence(key), self)
                # 使用函數工廠方式創建連接，避免閉包問題
                def create_callback(target_label):
                    return lambda: self.toggle_label(target_label)
                
                shortcut.activated.connect(create_callback(label))
                logger.info(f"設置快捷鍵: '{key}' 對應標籤 '{label}'")
            except Exception as e:
                logger.warning(f"設置鍵值 '{key}' 的快捷鍵時出錯: {e}")
        
        # 特殊功能快捷鍵
        QShortcut(QKeySequence("Shift+C"), self).activated.connect(self.clear_labels)  # 清除標籤
        QShortcut(QKeySequence("W"), self).activated.connect(self.show_overview)  # 切換到總覽模式
        QShortcut(QKeySequence("Q"), self).activated.connect(self.close)  # 保存並退出
        
        # 快速導航快捷鍵
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(self.find_prev_not_ok)  # 上一個非OK
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(self.find_next_not_ok)  # 下一個非OK
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(self.find_prev_whitelist)  # 上一個白名單
        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(self.find_next_whitelist)  # 下一個白名單
        QShortcut(QKeySequence("Shift+Left"), self).activated.connect(self.find_prev_multi_label)  # 上一個多標籤
        QShortcut(QKeySequence("Shift+Right"), self).activated.connect(self.find_next_multi_label)  # 下一個多標籤

    def check_dataset_paths(self):
        """檢查資料集中的路徑是否都能找到對應的圖片"""
        logger.debug("檢查資料集路徑")
        found_images = 0
        missing_images = 0
        missing_paths = []
        image_paths_set = set(self.image_paths)
        
        # 使用WORKING_DIR作為專案根目錄
        project_root = WORKING_DIR
        
        for path in self.data['dataset'].keys():
            # 檢查絕對路徑或轉換後的絕對路徑是否在圖片列表中
            if path in image_paths_set:
                found_images += 1
            else:
                # 嘗試將數據集中可能使用的相對路徑轉換為絕對路徑再比較
                if not os.path.isabs(path):
                    abs_path = normalize_path(os.path.abspath(os.path.join(project_root, path)))
                    if abs_path in image_paths_set:
                        found_images += 1
                        continue
                
                # 反過來，嘗試將圖片路徑轉換為相對路徑比較
                rel_path_found = False
                try:
                    for img_path in self.image_paths:
                        rel_path = normalize_path(os.path.relpath(img_path, project_root))
                        data_rel_path = normalize_path(path)
                        if rel_path.endswith(data_rel_path) or data_rel_path.endswith(rel_path):
                            found_images += 1
                            rel_path_found = True
                            break
                except:
                    pass
                
                if not rel_path_found:
                    missing_images += 1
                    missing_paths.append(path)
        
        if missing_images > 0:
            logger.warning(f"資料集中有 {missing_images} 張圖片路徑無法找到")
            # 最多顯示5個錯誤路徑
            for i, path in enumerate(missing_paths[:5]):
                logger.warning(f"  找不到: {path}")
            if len(missing_paths) > 5:
                logger.warning(f"  還有 {len(missing_paths) - 5} 個路徑未顯示...")

    def show_welcome_message(self):
        """顯示歡迎訊息"""
        logger.debug("顯示歡迎訊息")
        
        welcome_text = (
            f"咖啡豆標籤工具已成功啟動！\n\n"
            f"資料夾: {FOLDER}\n"
            f"共有 {len(self.image_paths)} 張圖片\n"
            f"資料集中已有 {len(self.data['dataset'])} 張圖片的標記\n"
        )
        
        # 檢查是否有找不到的路徑，如果有就顯示警告
        found_images = 0
        missing_images = 0
        missing_paths = []
        image_paths_set = set(self.image_paths)
        
        for path in self.data['dataset'].keys():
            if path in image_paths_set:
                found_images += 1
            else:
                missing_images += 1
                missing_paths.append(path)
        
        if missing_images > 0:
            welcome_text += f"\n警告: 資料集中有 {missing_images} 張圖片路徑無法找到"
        
        welcome_text += "\n\n按確定開始標記工作。"
        
        QMessageBox.information(
            self, "歡迎", welcome_text
        )
    
    def print_help(self):
        """顯示使用說明"""
        logger.debug("顯示使用說明")
        logger.info("操作說明：")
        logger.info("- 左右方向鍵：切換圖片")
        logger.info("- 數字鍵：切換標籤")
        logger.info("- Q 鍵：儲存並退出")
        logger.info("- Home 鍵：跳到第一張圖片")
        logger.info("- End 鍵：跳到最後一張圖片")
        logger.info("- PageUp/PageDown：快速前後翻頁（10張）")
        logger.info("- Shift+C：清除該圖片的所有標籤")
        logger.info("- W 鍵：切換到總覽模式")

    def update_display(self):
        """更新圖片和標籤顯示"""
        # 檢查索引範圍
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return
            
        current_path = self.image_paths[self.current_index]
        self.img_path = current_path  # 確保img_path是當前路徑
        
        # 確保圖片路徑在資料集中
        if current_path not in self.data['dataset']:
            self.data['dataset'][current_path] = []
            
        # 載入圖片
        try:
            img = load_image(current_path)
            
            # 取得視窗可用大小
            image_container_size = self.image_container.size()
            container_width = image_container_size.width() - 40  # 考慮邊距
            container_height = image_container_size.height() - 60  # 考慮邊距和底部空間
            
            # 獲取原始圖片尺寸
            orig_width, orig_height = img.size
            
            # 計算最佳顯示尺寸
            if orig_width > 0 and orig_height > 0:
                # 計算縮放比例
                width_ratio = container_width / orig_width
                height_ratio = container_height / orig_height
                
                # 使用較小的比例，確保完整顯示圖片
                scale_ratio = min(width_ratio, height_ratio)
                
                # 確保比例不小於1，如果圖片小於容器，則放大到適合的大小
                if scale_ratio < 1.0 or scale_ratio > 1.0:
                    # 計算新尺寸
                    new_width = int(orig_width * scale_ratio)
                    new_height = int(orig_height * scale_ratio)
                    
                    # 確保至少有最小尺寸
                    new_width = max(new_width, 100)
                    new_height = max(new_height, 100)
                    
                    # 調整圖片大小
                    img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 轉換為QPixmap並顯示
            qimg = ImageLoader.pil_to_qimage(img)
            pixmap = QPixmap.fromImage(qimg)
            
            # 設置圖片到標籤
            self.image_label.setPixmap(pixmap)
            self.image_label.setMinimumSize(pixmap.width(), pixmap.height())
            
            # 更新視窗標題
            self.setWindowTitle(f"咖啡豆標籤標記工具 - {os.path.basename(current_path)}")
            
        except Exception as e:
            logger.error(f"無法載入圖片: {e}")
            self.image_label.setText(f"無法載入圖片: {e}")
            
        # 更新標籤顯示
        current_labels = self.data['dataset'].get(current_path, [])
        self.label_info.setText(f"當前標籤: {current_labels}")
        
        # 更新按鈕狀態
        for label, btn in self.label_buttons.items():
            if label in current_labels:
                btn.setStyleSheet(STYLES["highlighted_button"])
            else:
                btn.setStyleSheet(STYLES["button"])
                
        # 更新狀態欄
        self.statusBar().showMessage(f"圖片 {self.current_index + 1}/{len(self.image_paths)} | {os.path.basename(current_path)}")

    def save_on_exit(self):
        """退出時保存數據"""
        logger.info("保存資料並退出")
        save_dataset(YAML_FILE, self.data, WORKING_DIR)
        save_settings(SETTINGS_YAML, self.settings, self.current_index)
        logger.info("資料已保存")

    def show_overview(self):
        """顯示總覽模式"""
        logger.info("開啟總覽模式")
        # 先創建並顯示加載對話框
        loading_dialog = LoadingDialog(parent=self)
        loading_dialog.show()
        
        # 創建總覽視窗但不立即顯示
        try:
            self.overview_window = OverviewWindow(self.image_paths, self.data, self)
            self.overview_window.view_image.connect(self.on_view_image_from_overview)
            
            # 連接進度更新信號
            if hasattr(self.overview_window, 'loader_thread'):
                # 將進度更新連接到對話框
                self.overview_window.loader_thread.progress_updated.connect(
                    lambda current, total: loading_dialog.update_progress(current, total)
                )
                
                # 當載入完成時，關閉對話框並顯示總覽視窗
                self.overview_window.loader_thread.loading_finished.connect(
                    lambda: self._show_overview_window(loading_dialog)
                )
            else:
                # 如果沒有載入線程，直接顯示總覽視窗
                loading_dialog.close()
                self.overview_window.show()
        except Exception as e:
            logger.error(f"創建總覽視窗時出錯: {e}")
            loading_dialog.close()
            QMessageBox.critical(self, "錯誤", f"創建總覽視窗時出錯: {e}")
    
    def _show_overview_window(self, loading_dialog):
        """關閉加載對話框並顯示總覽視窗"""
        try:
            # 先確保對話框已關閉
            loading_dialog.close()
            loading_dialog.deleteLater()
            
            # 顯示總覽視窗
            self.overview_window.show()
            logger.info("總覽視窗已顯示")
        except Exception as e:
            logger.error(f"顯示總覽視窗時出錯: {e}")
            # 確保即使出錯也關閉加載對話框
            try:
                loading_dialog.close()
                loading_dialog.deleteLater()
            except:
                pass
    
    def on_view_image_from_overview(self, img_path):
        """從總覽模式選擇圖片進行標記"""
        logger.info(f"從總覽模式選擇圖片: {img_path}")
        labeling_window = LabelingWindow(img_path, self.data, self.labels, self.image_paths, self.current_index, self)
        labeling_window.labels_changed.connect(self.on_labels_changed)
        labeling_window.show()
    
    def on_labels_changed(self, img_path, new_labels):
        """標籤變更時更新總覽視窗"""
        logger.debug(f"標籤已變更: {img_path}, 新標籤: {new_labels}")
        if hasattr(self, 'overview_window') and self.overview_window.isVisible():
            self.overview_window.update_thumbnail_label(img_path, new_labels)
            self.overview_window.refresh_data()

    # 導航方法
    def prev_image(self):
        """上一張圖片"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
    
    def next_image(self):
        """下一張圖片"""
        if self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.update_display()
    
    def first_image(self):
        """跳到第一張圖片"""
        self.current_index = 0
        self.update_display()
    
    def last_image(self):
        """跳到最後一張圖片"""
        self.current_index = len(self.image_paths) - 1
        self.update_display()
    
    def page_up(self):
        """向前10張圖片"""
        self.current_index = max(0, self.current_index - 10)
        self.update_display()
    
    def page_down(self):
        """向後10張圖片"""
        self.current_index = min(len(self.image_paths) - 1, self.current_index + 10)
        self.update_display()
    
    # 标签操作方法
    def toggle_label(self, label):
        """切換標籤狀態"""
        if not self.image_paths:
            return
            
        current_path = self.image_paths[self.current_index]
        
        if current_path not in self.data['dataset']:
            self.data['dataset'][current_path] = []
            
        current_labels = self.data['dataset'][current_path]
        
        if label in current_labels:
            current_labels.remove(label)
        else:
            current_labels.append(label)
            
        self.data['dataset'][current_path] = current_labels
        self.update_label_display()
    
    def clear_labels(self):
        """清除所有標籤"""
        if not self.image_paths:
            return
            
        current_path = self.image_paths[self.current_index]
        
        if current_path in self.data['dataset']:
            self.data['dataset'][current_path] = []
            self.update_label_display()
    
    def update_label_display(self):
        """更新標籤顯示"""
        if not self.image_paths:
            return
            
        current_path = self.image_paths[self.current_index]
        current_labels = self.data['dataset'].get(current_path, [])
        
        self.label_info.setText(f"當前標籤: {current_labels}")
        
        # 更新按鈕狀態
        for label, btn in self.label_buttons.items():
            if label in current_labels:
                btn.setStyleSheet(STYLES["highlighted_button"])
            else:
                btn.setStyleSheet(STYLES["button"])
    
    # 快速導航功能
    def find_prev_not_ok(self):
        """查找前一張不是OK的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index - 1
        while index >= 0:
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if labels and "OK" not in labels:
                self.current_index = index
                self.update_display()
                return
            index -= 1
            
        QMessageBox.information(self, "提示", "已經是第一張非OK圖片")
    
    def find_next_not_ok(self):
        """查找下一張不是OK的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index + 1
        while index < len(self.image_paths):
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if labels and "OK" not in labels:
                self.current_index = index
                self.update_display()
                return
            index += 1
            
        QMessageBox.information(self, "提示", "已經是最後一張非OK圖片")
    
    def find_prev_whitelist(self):
        """查找前一張含有白名單標籤的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index - 1
        while index >= 0:
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if any(label in WHITE_LIST for label in labels):
                self.current_index = index
                self.update_display()
                return
            index -= 1
            
        QMessageBox.information(self, "提示", "已經是第一張含有白名單標籤的圖片")
    
    def find_next_whitelist(self):
        """查找下一張含有白名單標籤的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index + 1
        while index < len(self.image_paths):
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if any(label in WHITE_LIST for label in labels):
                self.current_index = index
                self.update_display()
                return
            index += 1
            
        QMessageBox.information(self, "提示", "已經是最後一張含有白名單標籤的圖片")
    
    def find_prev_multi_label(self):
        """查找前一張有多個標籤的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index - 1
        while index >= 0:
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if len(labels) > 1:
                self.current_index = index
                self.update_display()
                return
            index -= 1
            
        QMessageBox.information(self, "提示", "已經是第一張有多個標籤的圖片")
    
    def find_next_multi_label(self):
        """查找下一張有多個標籤的圖片"""
        if not self.image_paths:
            return
            
        index = self.current_index + 1
        while index < len(self.image_paths):
            path = self.image_paths[index]
            labels = self.data['dataset'].get(path, [])
            if len(labels) > 1:
                self.current_index = index
                self.update_display()
                return
            index += 1
            
        QMessageBox.information(self, "提示", "已經是最後一張有多個標籤的圖片")

def main():
    """主函數"""
    try:
        # 設置全局日誌級別（可根據需要更改）
        set_global_log_level('INFO')
        
        app = QApplication(sys.argv)
        
        # 設置應用程式風格
        app.setStyle('Fusion')
        
        # 創建主視窗
        window = CoffeeBeanLabeler()
        window.show()
        
        # 運行應用程式
        sys.exit(app.exec_())
    except Exception as e:
        # 在控制台打印詳細錯誤
        import traceback
        logger.critical(f"程式發生嚴重錯誤: {e}")
        logger.critical(traceback.format_exc())
        
        # 嘗試創建錯誤對話框
        try:
            from PyQt5.QtWidgets import QMessageBox
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("程式錯誤")
            error_box.setText(f"程式發生嚴重錯誤:\n{str(e)}")
            error_box.setDetailedText(traceback.format_exc())
            error_box.exec_()
        except:
            logger.error("無法顯示錯誤對話框")
        
        sys.exit(1)

if __name__ == "__main__":
    main() 