from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, 
                        QHBoxLayout, QWidget, QGridLayout, QScrollArea,
                        QPushButton, QSizePolicy)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import os
from PIL import Image

from ..logger import get_logger
from ..image_loader import ImageLoader

# 獲取當前模組的 logger
logger = get_logger('labeling_window')

class LabelingWindow(QMainWindow):
    """標記視窗類，用於標記單張圖片"""
    labels_changed = pyqtSignal(str, list)  # 路徑和新標籤列表
    image_changed = pyqtSignal(str)  # 當切換到新圖片時發出信號
    
    def __init__(self, img_path, data, labels_dict, all_image_paths=None, current_index=None, parent=None):
        """
        初始化標記視窗
        
        Parameters:
            img_path (str): 圖片路徑
            data (dict): 數據集字典
            labels_dict (dict): 標籤字典
            all_image_paths (list, optional): 所有圖片路徑列表
            current_index (int, optional): 當前圖片索引
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.img_path = img_path
        self.data = data
        self.labels_dict = labels_dict
        self.has_changes = False
        self.original_image = None  # 保存原始圖片以便於調整大小
        
        # 保存所有圖片路徑和當前索引，以便導航
        self.all_image_paths = all_image_paths or []
        if self.all_image_paths and img_path in self.all_image_paths:
            self.current_index = self.all_image_paths.index(img_path)
        else:
            self.current_index = current_index or 0
        
        self.setWindowTitle(f"標記視窗 - {os.path.basename(img_path)}")
        self.resize(800, 800)
        
        # 主要部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 圖片顯示區
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setScaledContents(False)  # 不使用自動縮放，我們會手動控制
        
        self.scroll_area.setWidget(self.image_label)
        
        # 標籤顯示區
        self.label_info = QLabel()
        self.label_info.setAlignment(Qt.AlignCenter)
        self.label_info.setStyleSheet("margin: 15px 0; font-size: 14px; min-height: 30px;")
        
        # 加載圖片
        try:
            self.original_image = Image.open(img_path)
            self.update_image_display()
        except Exception as e:
            logger.error(f"無法載入圖片: {e}")
            self.image_label.setText(f"無法載入圖片: {e}")
        
        # 創建標籤按鈕
        button_layout = QGridLayout()
        self.label_buttons = {}
        
        row, col = 0, 0
        max_cols = 4
        
        for key, label in labels_dict.items():
            btn = QPushButton(f"{key}: {label}")
            
            # 檢查是否已有此標籤
            if img_path in data['dataset'] and label in data['dataset'][img_path]:
                btn.setStyleSheet("background-color: #a3c2c2;")
            
            btn.clicked.connect(lambda checked, lbl=label: self.toggle_label(lbl))
            button_layout.addWidget(btn, row, col)
            self.label_buttons[label] = btn
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # 清除標籤按鈕
        clear_btn = QPushButton("清除全部標籤 (Shift+C)")
        clear_btn.clicked.connect(self.clear_labels)
        
        # 更新顯示標籤資訊
        self.update_label_display()
        
        # 佈局
        layout.addWidget(self.scroll_area, 1)
        layout.addWidget(self.label_info)
        layout.addLayout(button_layout)
        layout.addWidget(clear_btn)
        
        # 設置鍵盤快捷鍵
        self.setup_shortcuts()
        
        logger.debug(f"標記視窗已初始化: {img_path}")
    
    def update_image_display(self):
        """根據視窗大小更新圖片顯示"""
        if self.original_image is None:
            return
            
        # 取得視窗可用大小
        scroll_area_size = self.scroll_area.size()
        view_width = scroll_area_size.width() - 30  # 減去滾動條
        view_height = scroll_area_size.height() - 30  # 減去滾動條
        
        # 獲取原始圖片尺寸
        orig_width, orig_height = self.original_image.size
        
        # 計算最佳顯示尺寸
        if orig_width > 0 and orig_height > 0:
            # 計算縮放比例
            width_ratio = view_width / orig_width
            height_ratio = view_height / orig_height
            
            # 使用較小的比例，確保完整顯示圖片
            scale_ratio = min(width_ratio, height_ratio)
            
            # 計算新尺寸
            new_width = int(orig_width * scale_ratio)
            new_height = int(orig_height * scale_ratio)
            
            # 確保至少有最小尺寸
            new_width = max(new_width, 100)
            new_height = max(new_height, 100)
            
            # 調整圖片大小（不論放大還是縮小）
            if new_width != orig_width or new_height != orig_height:
                resized_img = self.original_image.resize((new_width, new_height), Image.LANCZOS)
            else:
                resized_img = self.original_image
            
            # 轉換為QPixmap並顯示
            qimg = ImageLoader.pil_to_qimage(resized_img)
            pixmap = QPixmap.fromImage(qimg)
            self.image_label.setPixmap(pixmap)
            
            logger.debug(f"圖片已調整大小並顯示: {new_width}x{new_height}")
    
    def resizeEvent(self, event):
        """處理視窗大小變化事件"""
        super().resizeEvent(event)
        # 使用延遲更新避免頻繁重繪
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        else:
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self.update_image_display)
        
        self._resize_timer.start(150)  # 150毫秒延遲
    
    def setup_shortcuts(self):
        """設置鍵盤快捷鍵"""
        # 標籤快捷鍵
        from PyQt5.QtWidgets import QAction, QShortcut
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtCore import Qt
        
        # 為每個標籤創建快捷鍵
        for key, label in self.labels_dict.items():
            # 使用QShortcut而不是QAction，直接綁定單個按鍵
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda lbl=label: self.toggle_label(lbl))
            logger.debug(f"創建快捷鍵: {key} 對應標籤 {label}")
        
        # 清除標籤快捷鍵
        clear_shortcut = QShortcut(QKeySequence("Shift+C"), self)
        clear_shortcut.activated.connect(self.clear_labels)
        
        # 退出快捷鍵
        quit_shortcut = QShortcut(QKeySequence("Q"), self)
        quit_shortcut.activated.connect(self.close)
        
        # 只有當有完整圖片集時才添加導航快捷鍵
        if self.all_image_paths:
            # 左右方向鍵 - 上一張/下一張圖片
            prev_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
            prev_shortcut.activated.connect(self.prev_image)
            
            next_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
            next_shortcut.activated.connect(self.next_image)
            
            # Home/End - 第一張/最後一張圖片
            home_shortcut = QShortcut(QKeySequence(Qt.Key_Home), self)
            home_shortcut.activated.connect(self.first_image)
            
            end_shortcut = QShortcut(QKeySequence(Qt.Key_End), self)
            end_shortcut.activated.connect(self.last_image)
            
            # PageUp/PageDown - 向前/向後10張
            page_up_shortcut = QShortcut(QKeySequence(Qt.Key_PageUp), self)
            page_up_shortcut.activated.connect(self.page_up)
            
            page_down_shortcut = QShortcut(QKeySequence(Qt.Key_PageDown), self)
            page_down_shortcut.activated.connect(self.page_down)
    
    def change_image(self, new_img_path):
        """切換到新圖片"""
        # 先保存當前圖片的更改
        if self.has_changes:
            current_labels = self.data['dataset'].get(self.img_path, [])
            self.labels_changed.emit(self.img_path, current_labels)
            self.has_changes = False
        
        # 更新路徑和窗口標題
        self.img_path = new_img_path
        self.setWindowTitle(f"標記視窗 - {os.path.basename(new_img_path)}")
        
        # 載入新圖片
        try:
            self.original_image = Image.open(new_img_path)
            self.update_image_display()
        except Exception as e:
            logger.error(f"無法載入圖片: {e}")
            self.image_label.setText(f"無法載入圖片: {e}")
        
        # 更新按鈕狀態
        for label, btn in self.label_buttons.items():
            if new_img_path in self.data['dataset'] and label in self.data['dataset'][new_img_path]:
                btn.setStyleSheet("background-color: #a3c2c2;")
            else:
                btn.setStyleSheet("")
        
        # 更新標籤顯示
        self.update_label_display()
        
        # 發送圖片變更信號
        self.image_changed.emit(new_img_path)
        
        logger.debug(f"已切換到新圖片: {new_img_path}")
    
    def prev_image(self):
        """上一張圖片"""
        if self.all_image_paths and self.current_index > 0:
            self.current_index -= 1
            self.change_image(self.all_image_paths[self.current_index])
    
    def next_image(self):
        """下一張圖片"""
        if self.all_image_paths and self.current_index < len(self.all_image_paths) - 1:
            self.current_index += 1
            self.change_image(self.all_image_paths[self.current_index])
    
    def first_image(self):
        """跳到第一張圖片"""
        if self.all_image_paths and self.current_index != 0:
            self.current_index = 0
            self.change_image(self.all_image_paths[self.current_index])
    
    def last_image(self):
        """跳到最後一張圖片"""
        if self.all_image_paths and self.current_index != len(self.all_image_paths) - 1:
            self.current_index = len(self.all_image_paths) - 1
            self.change_image(self.all_image_paths[self.current_index])
    
    def page_up(self):
        """向前10張圖片"""
        if self.all_image_paths:
            new_index = max(0, self.current_index - 10)
            if new_index != self.current_index:
                self.current_index = new_index
                self.change_image(self.all_image_paths[self.current_index])
    
    def page_down(self):
        """向後10張圖片"""
        if self.all_image_paths:
            new_index = min(len(self.all_image_paths) - 1, self.current_index + 10)
            if new_index != self.current_index:
                self.current_index = new_index
                self.change_image(self.all_image_paths[self.current_index])
    
    def toggle_label(self, label):
        """切換標籤狀態"""
        current_path = self.img_path
        
        # 切換標籤
        if label in self.data['dataset'][current_path]:
            self.data['dataset'][current_path].remove(label)
            logger.debug(f"移除標籤: {label}")
            self.label_buttons[label].setStyleSheet("")
        else:
            self.data['dataset'][current_path].append(label)
            logger.debug(f"添加標籤: {label}")
            self.label_buttons[label].setStyleSheet("background-color: #a3c2c2;")
        
        # 更新標籤顯示
        self.update_label_display()
        self.has_changes = True
    
    def clear_labels(self):
        """清除所有標籤"""
        if self.img_path in self.data['dataset']:
            self.data['dataset'][self.img_path] = []
            
            # 更新按鈕樣式
            for btn in self.label_buttons.values():
                btn.setStyleSheet("")
            
            self.update_label_display()
            self.has_changes = True
            logger.debug(f"清除圖片的所有標籤: {self.img_path}")
    
    def update_label_display(self):
        """更新標籤顯示"""
        current_labels = self.data['dataset'].get(self.img_path, [])
        self.label_info.setText(f"當前標籤: {current_labels}")
    
    def closeEvent(self, event):
        """窗口關閉事件"""
        if self.has_changes:
            current_labels = self.data['dataset'].get(self.img_path, [])
            self.labels_changed.emit(self.img_path, current_labels)
        event.accept()
        logger.debug("標記視窗已關閉") 