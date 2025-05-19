import os
import threading
import time
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QGridLayout, QScrollArea,
                            QPushButton, QApplication)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal

from ..logger import get_logger
from ..image_loader import ImageLoader
from ..widgets import ThumbnailWidget

# 獲取當前模組的 logger
logger = get_logger('overview_window')

class OverviewWindow(QMainWindow):
    """總覽視窗類，用於顯示所有圖片的標籤總覽"""
    view_image = pyqtSignal(str)  # 發射被選中查看的圖片路徑
    
    def __init__(self, all_image_paths, data, parent=None):
        """
        初始化總覽視窗
        
        Parameters:
            all_image_paths (list): 所有圖片路徑列表
            data (dict): 數據集字典
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.all_image_paths = all_image_paths
        self.data = data
        self.image_cache = {}  # 圖片緩存
        self.thumbnail_widgets = {}  # 縮略圖小部件緩存
        
        # 添加鎖以防止並發更新
        self.update_lock = threading.Lock()
        self.is_updating = False
        
        self.setWindowTitle("咖啡豆標籤總覽")
        self.resize(1200, 800)
        
        # 主要部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 標籤分類
        self.all_labels = set()
        for labels_list in data['dataset'].values():
            if not labels_list:
                self.all_labels.add("None")
            else:
                self.all_labels.update(labels_list)
        
        self.all_labels.add("None")  # 確保有無標籤類別
        
        # 轉換為排序列表，None放在最前
        self.all_labels = sorted(list(self.all_labels))
        if "None" in self.all_labels:
            self.all_labels.remove("None")
            self.all_labels = ["None"] + self.all_labels
        
        # 為每個標籤收集圖片，確保所有相關圖片都列出
        self.label_images = {label: [] for label in self.all_labels}
        
        # 查找所有圖片路徑，包括尚未在數據集中的圖片
        all_image_paths_set = set(all_image_paths)
        dataset_paths_set = set(data['dataset'].keys())
        
        # 處理尚未在數據集中的圖片
        unlabeled_paths = all_image_paths_set - dataset_paths_set
        for path in unlabeled_paths:
            self.label_images["None"].append(path)
        
        # 處理已在數據集中的圖片，確保每張圖片在每個相關標籤下都顯示
        for path, labels_list in data['dataset'].items():
            if not labels_list:
                self.label_images["None"].append(path)
            else:
                for label in labels_list:
                    if label in self.all_labels:
                        self.label_images[label].append(path)
        
        # 計算每個標籤的圖片數量
        self.label_counts = {label: len(imgs) for label, imgs in self.label_images.items()}
        
        # 建立UI
        # 顯示模式選擇
        mode_layout = QHBoxLayout()
        
        # 索引顯示
        self.current_view_index = 0  # 0: 全部標籤, 1~N: 對應all_labels的索引
        self.index_label = QLabel("目前檢視: 全部標籤")
        mode_layout.addWidget(self.index_label)
        
        # 建立導航按鈕
        prev_btn = QPushButton("←")
        prev_btn.clicked.connect(self.previous_view)
        
        next_btn = QPushButton("→")
        next_btn.clicked.connect(self.next_view)
        
        mode_layout.addWidget(prev_btn)
        mode_layout.addWidget(next_btn)
        
        # 進度條
        self.progress_label = QLabel("載入中: 0/0")
        mode_layout.addWidget(self.progress_label)
        
        main_layout.addLayout(mode_layout)
        
        # 縮略圖顯示區域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        # 設置網格間距，減少無用空間
        self.grid_layout.setHorizontalSpacing(5)
        self.grid_layout.setVerticalSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        self.scroll_area.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll_area)
        
        # 狀態欄
        self.statusBar().showMessage("準備就緒")
        
        # 設置鍵盤快捷鍵
        self.setup_shortcuts()
        
        # 初始化顯示
        self.update_view()
        
        # 啟動圖片預載入線程
        self.start_image_loader()
        
        logger.debug("總覽視窗已初始化")
    
    def setup_shortcuts(self):
        """設置鍵盤快捷鍵"""
        # 退出快捷鍵
        from PyQt5.QtWidgets import QAction
        from PyQt5.QtGui import QKeySequence
        
        quit_action = QAction("關閉", self)
        quit_action.setShortcut(QKeySequence("Q"))
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)
        
        # 導航快捷鍵
        left_action = QAction("上一個檢視", self)
        left_action.setShortcut(QKeySequence(Qt.Key_Left))
        left_action.triggered.connect(self.previous_view)
        self.addAction(left_action)
        
        right_action = QAction("下一個檢視", self)
        right_action.setShortcut(QKeySequence(Qt.Key_Right))
        right_action.triggered.connect(self.next_view)
        self.addAction(right_action)
    
    def start_image_loader(self):
        """啟動圖片預載入線程"""
        # 確保之前的線程已停止
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            try:
                self.loader_thread.stop()
                self.loader_thread.wait(200)  # 給足時間停止
            except Exception as e:
                logger.error(f"停止之前的載入線程時出錯: {e}")
        
        # 收集當前視圖的所有圖片作為優先加載
        try:
            priority_paths = self.get_current_view_images()
            
            # 收集所有需要載入的圖片路徑
            all_paths = []
            for paths in self.label_images.values():
                all_paths.extend(paths)
            
            # 創建新線程
            self.loader_thread = ImageLoader(all_paths, priority_paths)
            self.loader_thread.image_loaded.connect(self.on_image_loaded)
            self.loader_thread.progress_updated.connect(self.on_progress_updated)
            self.loader_thread.start()
            
            # 更新狀態欄
            self.statusBar().showMessage(f"預載入 {len(priority_paths)} 張圖片")
            logger.info(f"開始載入圖片，優先載入 {len(priority_paths)} 張圖片")
            
        except Exception as e:
            logger.error(f"啟動圖片載入線程時出錯: {e}")
            self.statusBar().showMessage(f"圖片載入失敗: {e}")
    
    def get_current_view_images(self):
        """獲取當前視圖的所有圖片路徑列表"""
        current_images = []
        
        if self.current_view_index == 0:
            # 全部標籤模式
            for label in self.all_labels:
                current_images.extend(self.label_images[label])
        else:
            # 特定標籤模式
            if self.current_view_index <= len(self.all_labels):
                label = self.all_labels[self.current_view_index - 1]
                current_images.extend(self.label_images[label])
        
        return current_images
    
    def on_image_loaded(self, path, qimage):
        """當圖片載入完成時調用"""
        try:
            # 檢查路徑和圖片是否有效
            if not path or qimage is None or qimage.isNull():
                logger.warning(f"載入的圖片無效: {path}")
                return
                
            # 保存到緩存
            self.image_cache[path] = qimage
            
            # 更新縮略圖
            if path in self.thumbnail_widgets and self.thumbnail_widgets[path] is not None:
                try:
                    self.thumbnail_widgets[path].set_image(qimage)
                except Exception as e:
                    logger.error(f"更新縮略圖時發生錯誤: {path}, {e}")
        except Exception as e:
            logger.error(f"處理已載入圖片時發生錯誤: {e}")
    
    def on_progress_updated(self, loaded, total):
        """當載入進度更新時調用"""
        self.progress_label.setText(f"載入進度: {loaded}/{total}")
        logger.debug(f"圖片載入進度: {loaded}/{total}")
    
    def previous_view(self):
        """切換到上一個檢視索引"""
        if self.current_view_index > 0:
            self.current_view_index -= 1
            self.update_view()
            self.scroll_area.verticalScrollBar().setValue(0)  # 回到頂部
            logger.debug(f"切換到上一個檢視索引: {self.current_view_index}")
    
    def next_view(self):
        """切換到下一個檢視索引"""
        if self.current_view_index < len(self.all_labels):
            self.current_view_index += 1
            self.update_view()
            self.scroll_area.verticalScrollBar().setValue(0)  # 回到頂部
            logger.debug(f"切換到下一個檢視索引: {self.current_view_index}")
    
    def update_view(self):
        """更新當前視圖"""
        # 防止並發更新導致的崩潰
        if self.is_updating:
            logger.warning("正在更新中，請稍候...")
            return
            
        try:
            self.is_updating = True
            
            # 清空現有網格
            self.clear_grid()
            
            if self.current_view_index == 0:
                # 顯示所有標籤
                self.index_label.setText("目前檢視: 全部標籤")
                self.display_all_labels()
            else:
                # 顯示特定標籤
                if self.current_view_index <= len(self.all_labels):
                    label = self.all_labels[self.current_view_index - 1]
                    self.index_label.setText(f"目前檢視: {label}")
                    self.display_specific_label(label)
                else:
                    # 索引超出範圍，重置
                    self.current_view_index = 0
                    self.index_label.setText("目前檢視: 全部標籤")
                    self.display_all_labels()
            
            # 更新優先載入的圖片
            if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
                # 先停止當前線程
                try:
                    self.loader_thread.stop()
                    self.loader_thread.wait(100)  # 等待100毫秒讓線程結束
                except:
                    pass
                    
                # 啟動新的線程
                self.start_image_loader()
            
            logger.debug(f"視圖已更新: 索引={self.current_view_index}")
            
        except Exception as e:
            logger.error(f"更新視圖時發生錯誤: {e}")
        finally:
            self.is_updating = False
    
    def clear_grid(self):
        """清空網格佈局"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        # 重置縮略圖小部件緩存，僅保留已建立的小部件
        self.thumbnail_widgets = {path: widget for path, widget in self.thumbnail_widgets.items() 
                                if widget is not None}
        
        logger.debug("網格已清空")
    
    def display_all_labels(self):
        """顯示所有標籤的縮略圖，確保每列連續顯示，不留空白"""
        # 顯示所有標籤，每個標籤一列
        visible_labels = self.all_labels
        
        # 添加標籤標題（包含數量）
        for col, label in enumerate(visible_labels):
            header = QLabel(f"{label} ({self.label_counts[label]})")
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #f0f0f0;")
            self.grid_layout.addWidget(header, 0, col)
        
        # 為每列圖片設置單獨的行計數器，確保圖片連續顯示
        row_counters = {label: 1 for label in visible_labels}  # 從1開始，因為第0行是標題
        
        # 顯示每個標籤下的所有圖片
        for col, label in enumerate(visible_labels):
            label_imgs = self.label_images[label]
            if label_imgs:  # 確保這個標籤有圖片
                # 連續顯示該標籤的所有圖片，從row=1開始（標題下方）
                for img_path in label_imgs:
                    self.add_thumbnail(img_path, row_counters[label], col)
                    row_counters[label] += 1  # 遞增該列的行計數器
            else:
                # 如果沒有圖片，添加一個空標籤避免佈局問題
                empty_label = QLabel("無圖片")
                empty_label.setAlignment(Qt.AlignCenter)
                self.grid_layout.addWidget(empty_label, 1, col)
        
        # 為每列設置相同的寬度
        for col in range(len(visible_labels)):
            self.grid_layout.setColumnStretch(col, 1)
            
        logger.debug(f"顯示全部標籤模式: {len(visible_labels)} 個標籤")
    
    def display_specific_label(self, label):
        """顯示特定標籤的縮略圖"""
        # 添加標籤標題
        header = QLabel(f"{label} ({self.label_counts[label]})")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.grid_layout.addWidget(header, 0, 0, 1, 10)  # 標題橫跨10列
        
        # 顯示該標籤下的所有圖片，以10張一行的方式排列
        label_imgs = self.label_images[label]
        if label_imgs:
            for i, img_path in enumerate(label_imgs):
                row = (i // 10) + 1  # 每行10張，第一行是標題
                col = i % 10
                self.add_thumbnail(img_path, row, col)
        else:
            # 沒有圖片時顯示提示
            empty_label = QLabel("此類別無圖片")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 1, 0, 1, 10)
        
        logger.debug(f"顯示特定標籤模式: {label}, {len(label_imgs)} 張圖片")
    
    def add_thumbnail(self, img_path, row, col):
        """添加縮略圖到網格"""
        try:
            # 檢查路徑有效性
            if not img_path or not os.path.exists(img_path):
                logger.warning(f"警告: 圖片路徑無效或不存在: {img_path}")
                
            # 檢查是否已有此圖片的縮略圖小部件
            if img_path in self.thumbnail_widgets and self.thumbnail_widgets[img_path] is not None:
                thumbnail = self.thumbnail_widgets[img_path]
            else:
                # 創建新的縮略圖小部件
                thumbnail = ThumbnailWidget(img_path)
                thumbnail.clicked.connect(self.on_thumbnail_clicked)
                self.thumbnail_widgets[img_path] = thumbnail
                
                # 設置標籤
                img_labels = self.data['dataset'].get(img_path, [])
                thumbnail.set_labels(img_labels)
                
                # 如果圖片已在緩存中，設置圖片
                if img_path in self.image_cache:
                    try:
                        thumbnail.set_image(self.image_cache[img_path])
                    except Exception as e:
                        logger.error(f"從緩存設置圖片時出錯: {e}")
            
            # 添加到網格
            if row >= 0 and col >= 0:
                self.grid_layout.addWidget(thumbnail, row, col)
        except Exception as e:
            logger.error(f"添加縮略圖時發生錯誤: {e}")
    
    def on_thumbnail_clicked(self, img_path):
        """當縮略圖被點擊時調用"""
        self.view_image.emit(img_path)
        logger.debug(f"縮略圖被點擊: {img_path}")
    
    def update_thumbnail_label(self, img_path, new_labels):
        """更新縮略圖的標籤"""
        if img_path in self.thumbnail_widgets and self.thumbnail_widgets[img_path] is not None:
            self.thumbnail_widgets[img_path].set_labels(new_labels)
            logger.debug(f"更新縮略圖標籤: {img_path} -> {new_labels}")
    
    def refresh_data(self):
        """刷新數據並更新顯示"""
        # 重新計算標籤分類
        self.label_images = {label: [] for label in self.all_labels}
        
        # 查找所有圖片路徑，包括尚未在數據集中的圖片
        all_image_paths_set = set(self.all_image_paths)
        dataset_paths_set = set(self.data['dataset'].keys())
        
        # 處理尚未在數據集中的圖片
        unlabeled_paths = all_image_paths_set - dataset_paths_set
        for path in unlabeled_paths:
            self.label_images["None"].append(path)
        
        # 處理已在數據集中的圖片
        for path, labels_list in self.data['dataset'].items():
            if not labels_list:
                self.label_images["None"].append(path)
            else:
                for label in labels_list:
                    if label in self.all_labels:
                        self.label_images[label].append(path)
        
        # 更新標籤數量
        self.label_counts = {label: len(imgs) for label, imgs in self.label_images.items()}
        
        # 更新視圖
        self.update_view()
        logger.info("數據已刷新，視圖已更新")
    
    def closeEvent(self, event):
        """視窗關閉事件"""
        # 停止圖片載入線程
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.stop()
        event.accept()
        logger.debug("總覽視窗已關閉") 