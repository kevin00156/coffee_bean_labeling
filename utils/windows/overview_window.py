import os
import threading
import time
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, 
                            QHBoxLayout, QWidget, QGridLayout, QScrollArea,
                            QPushButton, QApplication)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from ..logger import get_logger
from ..image_loader import ImageLoader
from ..widgets import ThumbnailWidget
from ..constants import WHITE_LIST, MAX_IMAGES

# 獲取當前模組的 logger
logger = get_logger('overview_window')

class OverviewWindow(QMainWindow):
    """總覽視窗類，用於顯示所有圖片的標籤總覽"""
    view_image = pyqtSignal(str)  # 發射被選中查看的圖片路徑
    
    # 單例模式實現
    _instance = None
    _init_done = False
    
    def __new__(cls, *args, **kwargs):
        """確保只創建一個實例"""
        if cls._instance is None:
            logger.debug("創建 OverviewWindow 單例")
            cls._instance = super(OverviewWindow, cls).__new__(cls)
        else:
            logger.debug("返回現有 OverviewWindow 單例")
        return cls._instance
    
    def __init__(self, all_image_paths, data, parent=None):
        """
        初始化總覽視窗
        
        Parameters:
            all_image_paths (list): 所有圖片路徑列表
            data (dict): 數據集字典
            parent (QWidget, optional): 父窗口
        """
        # 確保只進行一次初始化，但始終更新數據
        if not self._init_done:
            super().__init__(parent)
            self._init_ui()
            self._init_done = True
            logger.debug("總覽視窗已完成初始化")
            
        # 每次都更新數據
        self.update_data(all_image_paths, data)
        
    def _init_ui(self):
        """初始化UI元素，只在第一次創建實例時調用"""
        self.all_image_paths = []
        self.data = {}
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
        
        # 初始化標籤和特殊標籤
        self.all_labels = []
        self.special_labels = ["NOT IN WHITELIST", "WHITELIST"]
        self.label_images = {}
        self.label_counts = {}
        
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
        
        # 確保信號連接正常
        # 這一步是關鍵，確保信號連接只發生一次
        self._ensure_signal_connections()
        
    def _ensure_signal_connections(self):
        """確保所有信號連接都正確建立"""
        logger.debug("確保信號連接正確建立")
        
        # 確保縮略圖的點擊信號正確連接
        for img_path, thumbnail in self.thumbnail_widgets.items():
            if thumbnail is not None:
                try:
                    # 先斷開舊的連接
                    thumbnail.clicked.disconnect()
                except:
                    pass  # 如果未連接，則忽略錯誤
                
                # 重新連接信號
                thumbnail.clicked.connect(self.on_thumbnail_clicked)
                logger.debug(f"重新連接縮略圖信號: {img_path}")
        
        # 在這裡可以添加其他需要確保連接的信號
        
    def on_thumbnail_clicked(self, img_path):
        """當縮略圖被點擊時調用"""
        # 增加日誌來調試點擊事件
        logger.debug(f"縮略圖被點擊: {img_path}, 發送檢視信號")
        # 確保信號正確發送
        self.view_image.emit(img_path)
        
        # 使用定時器延遲執行，確保信號有時間被處理
        QTimer.singleShot(50, lambda: self.statusBar().showMessage(f"檢視圖片: {os.path.basename(img_path)}"))
    
    def update_data(self, all_image_paths, data):
        """
        更新數據，當單例已存在時使用此方法刷新數據
        
        Parameters:
            all_image_paths (list): 所有圖片路徑列表
            data (dict): 數據集字典
        """
        logger.debug("更新總覽視窗數據")
        self.all_image_paths = all_image_paths
        self.data = data
        
        # 重新計算標籤分類
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
        
        # 更新圖片分類
        self.label_images = {label: [] for label in self.all_labels}
        for label in self.special_labels:
            self.label_images[label] = []
        
        # 重新處理圖片分類
        all_image_paths_set = set(all_image_paths)
        dataset_paths_set = set(data['dataset'].keys())
        
        unlabeled_paths = all_image_paths_set - dataset_paths_set
        for path in unlabeled_paths:
            self.label_images["None"].append(path)
        
        for path, labels_list in data['dataset'].items():
            if not labels_list:
                self.label_images["None"].append(path)
            else:
                for label in labels_list:
                    if label in self.all_labels:
                        self.label_images[label].append(path)
                
                if any(label in WHITE_LIST for label in labels_list):
                    self.label_images["WHITELIST"].append(path)
                elif labels_list:
                    no_whitelist = True
                    for label in labels_list:
                        if label in WHITE_LIST:
                            no_whitelist = False
                            break
                    if no_whitelist:
                        self.label_images["NOT IN WHITELIST"].append(path)
        
        # 更新計數
        self.label_counts = {label: len(imgs) for label, imgs in self.label_images.items()}
        
        # 每次更新數據後，重新確保信號連接
        self._ensure_signal_connections()
        
        # 更新顯示
        self.update_view()
        
        # 啟動圖片預載入線程
        self.start_image_loader()
    
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
            
            # 先斷開所有可能的舊連接
            try:
                self.loader_thread.image_loaded.disconnect()
                self.loader_thread.progress_updated.disconnect()
                self.loader_thread.loading_finished.disconnect()
            except:
                pass  # 忽略未連接的錯誤
            
            # 重新連接信號
            self.loader_thread.image_loaded.connect(self.on_image_loaded)
            self.loader_thread.progress_updated.connect(self.on_progress_updated)
            self.loader_thread.loading_finished.connect(self.on_loading_finished)
            
            # 啟動線程
            self.loader_thread.start()
            
            # 更新狀態欄
            self.statusBar().showMessage(f"預載入 {len(priority_paths)} 張圖片")
            logger.info(f"開始載入圖片，優先載入 {len(priority_paths)} 張圖片")
            
        except Exception as e:
            logger.error(f"啟動圖片載入線程時出錯: {e}")
            self.statusBar().showMessage(f"圖片載入失敗: {e}")
    
    def on_loading_finished(self):
        """當所有圖片加載完成時調用"""
        logger.info("圖片加載完成")
        self.statusBar().showMessage("所有圖片加載完成")
        
        # 這裡可以添加完成後的其他處理
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()  # 確保界面更新
    
    def on_progress_updated(self, loaded, total):
        """當載入進度更新時調用"""
        self.progress_label.setText(f"載入進度: {loaded}/{total}")
        self.statusBar().showMessage(f"載入進度: {loaded}/{total} 張圖片")
        logger.debug(f"圖片載入進度: {loaded}/{total}")
        
        # 處理事件循環，確保界面響應
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    def get_current_view_images(self):
        """獲取當前視圖的所有圖片路徑列表"""
        current_images = []
        
        if self.current_view_index == 0:
            # 全部標籤模式，只包含標準標籤
            for label in self.all_labels:
                current_images.extend(self.label_images[label])
        else:
            # 特定標籤模式
            if self.current_view_index <= len(self.all_labels):
                label = self.all_labels[self.current_view_index - 1]
                current_images.extend(self.label_images[label])
            elif self.current_view_index <= len(self.all_labels) + len(self.special_labels):
                # 特殊標籤索引
                special_idx = self.current_view_index - len(self.all_labels) - 1
                label = self.special_labels[special_idx]
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
    
    def previous_view(self):
        """切換到上一個檢視索引"""
        if self.current_view_index > 0:
            self.current_view_index -= 1
            self.update_view()
            self.scroll_area.verticalScrollBar().setValue(0)  # 回到頂部
            logger.debug(f"切換到上一個檢視索引: {self.current_view_index}")
    
    def next_view(self):
        """切換到下一個檢視索引"""
        max_index = len(self.all_labels) + len(self.special_labels)
        if self.current_view_index < max_index:
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
            
            # 保存當前滾動條位置
            scroll_position = self.scroll_area.verticalScrollBar().value()
            logger.debug(f"update_view 保存滾動條位置: {scroll_position}")
            
            # 處理事件，確保界面響應
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 清空現有網格
            self.clear_grid()
            
            # 更新界面標題
            if self.current_view_index == 0:
                # 顯示所有標籤
                self.index_label.setText("目前檢視: 全部標籤")
                # 先更新界面再繼續處理
                QApplication.processEvents()
                self.display_all_labels()
            else:
                # 顯示特定標籤
                if self.current_view_index <= len(self.all_labels):
                    label = self.all_labels[self.current_view_index - 1]
                    self.index_label.setText(f"目前檢視: {label}")
                    QApplication.processEvents()
                    self.display_specific_label(label)
                elif self.current_view_index <= len(self.all_labels) + len(self.special_labels):
                    # 特殊標籤索引
                    special_idx = self.current_view_index - len(self.all_labels) - 1
                    label = self.special_labels[special_idx]
                    self.index_label.setText(f"目前檢視: {label}")
                    QApplication.processEvents()
                    self.display_specific_label(label)
                else:
                    # 索引超出範圍，重置
                    self.current_view_index = 0
                    self.index_label.setText("目前檢視: 全部標籤")
                    QApplication.processEvents()
                    self.display_all_labels()
            
            # 確保界面更新
            QApplication.processEvents()
            
            # 更新優先載入的圖片
            if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
                # 先停止當前線程
                try:
                    self.loader_thread.stop()
                    self.loader_thread.wait(200)  # 給予足夠時間讓線程停止
                    
                    # 如果線程仍在運行且無法停止，則強制終止
                    if self.loader_thread.isRunning():
                        logger.warning("載入線程無法停止，強制終止")
                        self.loader_thread.terminate()
                except Exception as e:
                    logger.error(f"停止載入線程出錯: {e}")
                    
            # 啟動新的線程
            self.start_image_loader()
            
            # 恢復滾動條位置
            QTimer.singleShot(50, lambda: self.restore_scroll_position(scroll_position))
            
            logger.debug(f"視圖已更新: 索引={self.current_view_index}")
            
        except Exception as e:
            logger.error(f"更新視圖時發生錯誤: {e}")
        finally:
            self.is_updating = False
    
    def clear_grid(self):
        """清空網格佈局"""
        # 處理事件，確保界面響應
        from PyQt5.QtWidgets import QApplication
        
        # 使用取出計數來分批處理
        count = 0
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                
            # 每清除10個項目處理一次事件
            count += 1
            if count % 10 == 0:
                QApplication.processEvents()
        
        # 重置縮略圖小部件緩存，僅保留已建立的小部件
        self.thumbnail_widgets = {path: widget for path, widget in self.thumbnail_widgets.items() 
                                if widget is not None}
        
        logger.debug("網格已清空")
    
    def display_all_labels(self):
        """顯示所有標籤的縮略圖，確保每列連續顯示，不留空白"""
        # 處理事件，確保界面響應
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # 顯示所有標籤，每個標籤一列
        visible_labels = self.all_labels
        
        # 限制顯示的標籤數量，避免過多標籤導致卡頓
        MAX_LABELS = 20  # 最多顯示20個標籤
        if len(visible_labels) > MAX_LABELS:
            logger.warning(f"標籤數量過多 ({len(visible_labels)}), 僅顯示前 {MAX_LABELS} 個")
            visible_labels = visible_labels[:MAX_LABELS]
        
        # 添加標籤標題（包含數量）
        for col, label in enumerate(visible_labels):
            header = QLabel(f"{label} ({self.label_counts[label]})")
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #f0f0f0;")
            self.grid_layout.addWidget(header, 0, col)
            
            # 每添加5個標籤處理一次事件
            if (col + 1) % 5 == 0:
                QApplication.processEvents()
        
        # 為每列圖片設置單獨的行計數器，確保圖片連續顯示
        row_counters = {label: 1 for label in visible_labels}  # 從1開始，因為第0行是標題
        
        # 顯示每個標籤下的所有圖片
        total_thumbnails = 0
        max_thumbnails_per_label = 20  # 每個標籤最多顯示20張圖片
        
        for col, label in enumerate(visible_labels):
            label_imgs = self.label_images[label]
            
            # 限制每個標籤顯示的圖片數量
            if len(label_imgs) > max_thumbnails_per_label:
                # 如果圖片太多，取最前面的部分
                display_imgs = label_imgs[:max_thumbnails_per_label]
                logger.debug(f"標籤 {label} 有 {len(label_imgs)} 張圖片，僅顯示前 {max_thumbnails_per_label} 張")
            else:
                display_imgs = label_imgs
            
            if display_imgs:  # 確保這個標籤有圖片
                # 連續顯示該標籤的所有圖片，從row=1開始（標題下方）
                for i, img_path in enumerate(display_imgs):
                    self.add_thumbnail(img_path, row_counters[label], col)
                    row_counters[label] += 1  # 遞增該列的行計數器
                    
                    # 計算已添加的縮略圖總數
                    total_thumbnails += 1
                    
                    # 每添加20個縮略圖處理一次事件，保持界面響應
                    if total_thumbnails % 20 == 0:
                        QApplication.processEvents()
                        
                        # 如果已處理了足夠多的縮略圖，顯示提示並退出循環
                        if total_thumbnails >= 200:  # 限制總數，防止過多圖片導致卡頓
                            logger.warning(f"縮略圖過多，顯示前 {total_thumbnails} 張")
                            break
            else:
                # 如果沒有圖片，添加一個空標籤避免佈局問題
                empty_label = QLabel("無圖片")
                empty_label.setAlignment(Qt.AlignCenter)
                self.grid_layout.addWidget(empty_label, 1, col)
            
            # 處理事件，確保界面響應
            QApplication.processEvents()
            
            # 提前退出循環，避免處理過多標籤
            if total_thumbnails >= 200:
                break
        
        # 為每列設置相同的寬度
        for col in range(len(visible_labels)):
            self.grid_layout.setColumnStretch(col, 1)
            
        logger.debug(f"顯示全部標籤模式: {len(visible_labels)} 個標籤, {total_thumbnails} 張縮略圖")
    
    def display_specific_label(self, label):
        """顯示特定標籤的縮略圖"""
        # 處理事件，確保界面響應
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        # 添加標籤標題
        header = QLabel(f"{label} ({self.label_counts[label]})")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.grid_layout.addWidget(header, 0, 0, 1, 10)  # 標題橫跨10列
        
        # 顯示該標籤下的所有圖片，以10張一行的方式排列
        label_imgs = self.label_images[label]
        
        # 如果是特殊標籤，確保數據是最新的
        if label in ["NOT IN WHITELIST", "WHITELIST"]:
            # 清空當前標籤的圖片列表
            self.label_images[label] = []
            
            # 重新計算符合條件的圖片
            for path, labels_list in self.data['dataset'].items():
                if not labels_list:
                    continue
                
                if label == "WHITELIST" and any(l in WHITE_LIST for l in labels_list):
                    self.label_images[label].append(path)
                elif label == "NOT IN WHITELIST" and labels_list:
                    no_whitelist = True
                    for l in labels_list:
                        if l in WHITE_LIST:
                            no_whitelist = False
                            break
                    if no_whitelist:
                        self.label_images[label].append(path)
            
            # 更新數量
            self.label_counts[label] = len(self.label_images[label])
            # 更新標題顯示
            header.setText(f"{label} ({self.label_counts[label]})")
            # 更新圖片列表
            label_imgs = self.label_images[label]
            
            # 處理事件，確保界面響應
            QApplication.processEvents()
        
        # 限制顯示的圖片數量，避免過多圖片導致卡頓
        if len(label_imgs) > MAX_IMAGES:
            logger.warning(f"標籤 {label} 有 {len(label_imgs)} 張圖片，僅顯示前 {MAX_IMAGES} 張")
            label_imgs = label_imgs[:MAX_IMAGES]
        
        if label_imgs:
            for i, img_path in enumerate(label_imgs):
                row = (i // 10) + 1  # 每行10張，第一行是標題
                col = i % 10
                self.add_thumbnail(img_path, row, col)
                
                # 每添加20張圖片處理一次事件，保持界面響應
                if (i + 1) % 20 == 0:
                    QApplication.processEvents()
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
            
            # 設置目標類別
            target_class = None
            if self.current_view_index > 0:
                if self.current_view_index <= len(self.all_labels):
                    target_class = self.all_labels[self.current_view_index - 1]
            thumbnail.set_target_class(target_class)
            
            # 添加到網格
            if row >= 0 and col >= 0:
                self.grid_layout.addWidget(thumbnail, row, col)
        except Exception as e:
            logger.error(f"添加縮略圖時發生錯誤: {e}")
    
    def update_thumbnail_label(self, img_path, new_labels):
        """更新縮略圖的標籤"""
        # 更新內存數據
        if img_path in self.data['dataset']:
            self.data['dataset'][img_path] = new_labels
        
        # 更新縮略圖顯示
        if img_path in self.thumbnail_widgets and self.thumbnail_widgets[img_path] is not None:
            thumbnail = self.thumbnail_widgets[img_path]
            thumbnail.set_labels(new_labels)
            
            # 更新目標類別
            target_class = None
            if self.current_view_index > 0:
                if self.current_view_index <= len(self.all_labels):
                    target_class = self.all_labels[self.current_view_index - 1]
            thumbnail.set_target_class(target_class)
            
            logger.debug(f"更新縮略圖標籤: {img_path} -> {new_labels}")
            
            # 智能更新標籤分類
            self._update_label_classifications(img_path, new_labels)
            
            # 更新計數
            self.label_counts = {label: len(imgs) for label, imgs in self.label_images.items()}
            
            # 不再立即從視圖中移除縮略圖，即使目標類別改變
            # 將在下一次刷新時處理視圖更新
            
            # 更新標題顯示的計數
            self._update_header_counts()
    
    def _update_label_classifications(self, img_path, new_labels):
        """更新圖片的標籤分類"""
        # 先從所有標籤分類中移除此圖片
        for label_imgs in self.label_images.values():
            if img_path in label_imgs:
                label_imgs.remove(img_path)
        
        # 根據新標籤重新分類
        if not new_labels:
            self.label_images["None"].append(img_path)
        else:
            for label in new_labels:
                if label in self.all_labels:
                    self.label_images[label].append(img_path)
            
            # 處理白名單特殊分類
            if any(label in WHITE_LIST for label in new_labels):
                self.label_images["WHITELIST"].append(img_path)
            elif new_labels:  # 確保有標籤且都不在白名單中
                no_whitelist = True
                for label in new_labels:
                    if label in WHITE_LIST:
                        no_whitelist = False
                        break
                if no_whitelist:
                    self.label_images["NOT IN WHITELIST"].append(img_path)
    
    def _update_header_counts(self):
        """更新標題顯示的標籤計數"""
        # 如果是全部標籤視圖，更新所有標籤標題
        if self.current_view_index == 0:
            # 更新每個標籤列的標題
            for col in range(self.grid_layout.columnCount()):
                header_item = self.grid_layout.itemAtPosition(0, col)
                if header_item and header_item.widget():
                    header = header_item.widget()
                    if isinstance(header, QLabel):
                        label_text = header.text().split(" (")[0]  # 獲取標籤名稱
                        if label_text in self.label_counts:
                            # 更新計數
                            header.setText(f"{label_text} ({self.label_counts[label_text]})")
        else:
            # 如果是特定標籤視圖，只更新當前標籤的標題
            header_item = self.grid_layout.itemAtPosition(0, 0)
            if header_item and header_item.widget():
                header = header_item.widget()
                if isinstance(header, QLabel):
                    label_text = header.text().split(" (")[0]  # 獲取標籤名稱
                    if label_text in self.label_counts:
                        # 更新計數
                        header.setText(f"{label_text} ({self.label_counts[label_text]})")
    
    def refresh_data(self):
        """刷新數據並更新顯示"""
        # 保存當前滾動條位置
        scroll_position = self.scroll_area.verticalScrollBar().value()
        logger.debug(f"保存滾動條位置: {scroll_position}")
        
        # 重新計算標籤分類
        self.label_images = {label: [] for label in self.all_labels}
        # 重置特殊標籤的圖片列表
        for label in self.special_labels:
            self.label_images[label] = []
        
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
                # 處理標準標籤
                for label in labels_list:
                    if label in self.all_labels:
                        self.label_images[label].append(path)
                
                # 處理白名單特殊分類
                if any(label in WHITE_LIST for label in labels_list):
                    self.label_images["WHITELIST"].append(path)
                elif labels_list:  # 確保有標籤且都不在白名單中
                    no_whitelist = True
                    for label in labels_list:
                        if label in WHITE_LIST:
                            no_whitelist = False
                            break
                    if no_whitelist:
                        self.label_images["NOT IN WHITELIST"].append(path)
        
        # 更新標籤數量
        self.label_counts = {label: len(imgs) for label, imgs in self.label_images.items()}
        
        # 更新視圖
        self.update_view()
        
        # 恢復滾動條位置
        # 使用 QTimer.singleShot 確保在 UI 完全更新後設置滾動位置
        QTimer.singleShot(10, lambda: self.restore_scroll_position(scroll_position))
        
        logger.info("數據已刷新，視圖已更新")
    
    def restore_scroll_position(self, position):
        """恢復滾動條位置"""
        if position > 0:
            # 確保界面已經完全更新，然後恢復滾動位置
            self.scroll_area.verticalScrollBar().setValue(position)
            logger.debug(f"恢復滾動條位置: {position}")
    
    def closeEvent(self, event):
        """視窗關閉事件"""
        # 停止圖片載入線程
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            logger.debug("關閉視窗，停止載入線程")
            try:
                self.loader_thread.stop()
                self.loader_thread.wait(500)  # 給足足夠的時間停止
                
                # 如果線程仍在運行，則強制結束
                if self.loader_thread.isRunning():
                    logger.warning("線程未能及時停止，強制終止")
                    self.loader_thread.terminate()
                    self.loader_thread.wait()
            except Exception as e:
                logger.error(f"停止載入線程時出錯: {e}")
        
        # 釋放資源
        self.image_cache.clear()
        self.thumbnail_widgets.clear()
        
        event.accept()
        logger.debug("總覽視窗已關閉") 