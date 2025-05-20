import os
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSizePolicy, QProgressBar, QDialog, QApplication, QFrame)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRect

from .logger import get_logger
from .constants import THUMBNAIL_SIZE, STYLES, WHITE_LIST

# 獲取當前模組的 logger
logger = get_logger('widgets')

class ThumbnailWidget(QWidget):
    """
    縮略圖小部件，用於顯示圖片縮略圖和標籤
    """
    clicked = pyqtSignal(str)  # 發射被點擊的圖片路徑
    
    def __init__(self, img_path, parent=None):
        """
        初始化縮略圖小部件
        
        Parameters:
            img_path (str): 圖片路徑
            parent (QWidget, optional): 父部件
        """
        super().__init__(parent)
        self.img_path = img_path
        self.image_set = False
        self.labels = []
        self.error_state = False  # 追踪是否圖片顯示出錯
        self.target_class = None  # 目標類別
        
        # 設置固定大小
        self.setFixedSize(160, 180)
        
        # 佈局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        
        # 圖片標籤，用於顯示縮略圖
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setFrameShape(QFrame.Box)
        self.image_label.setFrameShadow(QFrame.Sunken)
        self.image_label.setLineWidth(1)
        self.image_label.setStyleSheet("background-color: #f0f0f0;")
        
        # 標籤信息標籤
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setMaximumHeight(20)
        self.info_label.setStyleSheet("font-size: 10px;")
        
        # 添加到佈局
        layout.addWidget(self.image_label)
        layout.addWidget(self.info_label)
        
        # 顯示加載中文本
        self.image_label.setText("加載中...")
        
        # 處理點擊事件
        self.setCursor(Qt.PointingHandCursor)
        
        # 設置標籤初始顯示
        self.update_label_display()
        
        logger.debug(f"創建縮略圖小部件: {img_path}")
        
    def mousePressEvent(self, event):
        """處理鼠標按下事件，發射點擊信號"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.img_path)
            # 提供點擊反饋
            self.setStyleSheet("background-color: #e0e0e0;")
            QApplication.processEvents()  # 立即更新界面
            # 短暫延遲後恢復樣式
            QApplication.instance().processEvents()
            self.setStyleSheet("")
    
    def set_image(self, qimage):
        """
        設置圖片，確保正確顯示
        
        Parameters:
            qimage (QImage): 要顯示的圖片
        """
        try:
            if qimage is None or qimage.isNull():
                # 如果圖像為空，顯示錯誤指示
                logger.warning(f"圖像無效: {self.img_path}")
                self.error_state = True
                error_img = QImage(100, 100, QImage.Format_RGB888)
                error_img.fill(QColor(255, 200, 0))  # 黃色警告色
                
                # 在圖像上繪製錯誤標記
                painter = QPainter(error_img)
                painter.setPen(QColor(0, 0, 0))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(QRect(10, 10, 80, 80), Qt.AlignCenter, "載入錯誤")
                painter.end()
                
                self.image_label.setPixmap(QPixmap.fromImage(error_img))
            else:
                # 檢查圖像的有效性
                if qimage.width() <= 0 or qimage.height() <= 0:
                    # 無效圖像尺寸
                    logger.warning(f"圖像尺寸無效: {self.img_path} ({qimage.width()}x{qimage.height()})")
                    self.error_state = True
                    error_img = QImage(100, 100, QImage.Format_RGB888)
                    error_img.fill(QColor(255, 100, 100))  # 警告紅色
                    self.image_label.setPixmap(QPixmap.fromImage(error_img))
                else:
                    # 正常設置圖像
                    logger.debug(f"正常設置圖像: {self.img_path}")
                    self.error_state = False
                    self.image_set = True
                    pixmap = QPixmap.fromImage(qimage)
                    # 縮放到合適大小
                    pixmap = pixmap.scaled(
                        self.image_label.width(), 
                        self.image_label.height(),
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(pixmap)
            
            # 如果之前有加載文本，現在清除
            if not self.image_label.pixmap():
                self.image_label.clear()
            
            # 更新標籤顯示
            self.update_label_display()
        except Exception as e:
            logger.error(f"設置圖片時發生錯誤: {self.img_path}, {e}")
            # 如果設置失敗，顯示錯誤圖示
            self.error_state = True
            error_img = QImage(100, 100, QImage.Format_RGB888)
            error_img.fill(QColor(255, 0, 0))  # 紅色
            self.image_label.setPixmap(QPixmap.fromImage(error_img))
    
    def set_target_class(self, target_class):
        """
        設置目標類別
        
        Parameters:
            target_class (str): 目標類別名稱
        """
        self.target_class = target_class
        self.update_label_display()
    
    def update_label_display(self):
        """更新標籤顯示"""
        # 獲取文件名
        filename = os.path.basename(self.img_path)
        
        # 如果有標籤，則顯示標籤
        if self.labels:
            short_labels = str(self.labels)
            if len(short_labels) > 25:
                short_labels = short_labels[:22] + "..."
            self.info_label.setText(short_labels)
            
            # 根據是否包含目標類別決定顏色
            if self.target_class and self.target_class in self.labels:
                self.info_label.setStyleSheet("color: blue; font-size: 10px;")
            else:
                self.info_label.setStyleSheet("color: red; font-size: 10px;")
        else:
            # 如果沒有標籤，則顯示文件名
            if len(filename) > 15:
                filename = filename[:12] + "..."
            self.info_label.setText(f"未標記: {filename}")
            self.info_label.setStyleSheet("color: gray; font-size: 10px;")
    
    def set_labels(self, labels):
        """
        設置標籤文本
        
        Parameters:
            labels (list): 標籤列表
        """
        self.labels = labels
        self.update_label_display()
        
    def resizeEvent(self, event):
        """調整大小事件，重新縮放圖片"""
        if self.image_label.pixmap() and not self.image_label.pixmap().isNull():
            # 重新縮放圖片以適應新的大小
            try:
                self.image_label.setPixmap(self.image_label.pixmap().scaled(
                    self.width(), self.height(),
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
            except Exception as e:
                logger.error(f"重新縮放圖片失敗: {e}")
        super().resizeEvent(event)

class LoadingDialog(QDialog):
    """載入進度對話框，用於顯示載入進度"""
    
    # 類級別變量，記錄當前是否有對話框打開
    _is_open = False
    
    @classmethod
    def is_dialog_open(cls):
        """檢查是否已有加載對話框打開"""
        return cls._is_open
    
    def __init__(self, parent=None):
        """
        初始化載入對話框
        
        Parameters:
            parent (QWidget, optional): 父部件
        """
        super().__init__(parent)
        
        # 如果已有對話框打開，則記錄
        LoadingDialog._is_open = True
        
        self.setWindowTitle("加載中")
        self.setFixedSize(400, 150)
        self.setModal(True)  # 設置為模態對話框
        
        # 佈局
        layout = QVBoxLayout(self)
        
        # 信息標籤
        self.info_label = QLabel("正在索引圖片，請稍候...")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; margin: 10px;")
        
        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m")
        self.progress_bar.setStyleSheet("font-size: 12px;")
        
        # 添加描述標籤
        self.desc_label = QLabel("正在載入圖片資料，並為每張圖片生成縮略圖...")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font-size: 12px; color: #666;")
        
        # 添加取消按鈕
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        # 添加到佈局
        layout.addWidget(self.info_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.cancel_button, 0, Qt.AlignCenter)
        
        # 設置取消按鈕為不可用，避免用戶中斷載入
        # 註意：這可能導致用戶感覺應用程序卡死，請謹慎使用
        self.cancel_button.setEnabled(False)
        
        logger.debug("創建載入對話框")
    
    def update_progress(self, current, total):
        """
        更新進度條
        
        Parameters:
            current (int): 當前進度
            total (int): 總數
        """
        if total > 0:
            # 設置進度條最大值
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
            
            # 更新標籤
            percent = int((current / total) * 100)
            self.info_label.setText(f"圖片載入中... {percent}% ({current}/{total})")
            
            # 根據進度更新描述
            if percent < 25:
                self.desc_label.setText("正在載入圖片資料，這可能需要一些時間...")
            elif percent < 50:
                self.desc_label.setText("正在生成縮略圖，請耐心等待...")
            elif percent < 75:
                self.desc_label.setText("正在分析圖片標籤，即將完成...")
            else:
                self.desc_label.setText("即將完成，正在最終處理...")
                
                # 進度接近完成時，啟用取消按鈕
                if percent > 90:
                    self.cancel_button.setEnabled(True)
            
            # 處理事件循環，確保界面更新
            QApplication.processEvents()
        
        logger.debug(f"更新進度條: {current}/{total}")
    
    def closeEvent(self, event):
        """當對話框關閉時調用"""
        LoadingDialog._is_open = False
        logger.debug("加載對話框已關閉")
        event.accept()
    
    def reject(self):
        """當用戶點擊取消按鈕時調用"""
        LoadingDialog._is_open = False
        logger.debug("用戶取消加載")
        super().reject() 