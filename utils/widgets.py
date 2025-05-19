from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QRect

from .logger import get_logger
from .constants import THUMBNAIL_SIZE, STYLES

# 獲取當前模組的 logger
logger = get_logger('widgets')

class ThumbnailWidget(QWidget):
    """
    縮略圖小部件，用於顯示圖片縮略圖和標籤
    """
    clicked = pyqtSignal(str)  # 發射被點擊的圖片路徑
    
    def __init__(self, path="", parent=None):
        """
        初始化縮略圖小部件
        
        Parameters:
            path (str, optional): 圖片路徑
            parent (QWidget, optional): 父部件
        """
        super().__init__(parent)
        self.path = path
        self.pixmap = None
        self.labels = []
        self.error_state = False  # 追踪是否圖片顯示出錯
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(100, 100)
        self.image_label.setMaximumSize(200, 200)
        # 設置為非自動縮放，讓我們手動處理縮放
        self.image_label.setScaledContents(False)
        
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setMaximumHeight(40)
        
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.text_label)
        
        # 設置樣式
        self.setStyleSheet(STYLES["widget"])
        
        # 如果路徑存在，顯示一個佔位符
        if path:
            self.show_placeholder()
            logger.debug(f"創建縮略圖小部件: {path}")
        
    def show_placeholder(self):
        """顯示佔位符圖像，表示正在載入"""
        placeholder = QImage(100, 100, QImage.Format_RGB888)
        placeholder.fill(Qt.lightGray)
        self.image_label.setPixmap(QPixmap.fromImage(placeholder))
        
    def set_image(self, qimage):
        """
        設置圖片，確保正確顯示
        
        Parameters:
            qimage (QImage): 要顯示的圖片
        """
        try:
            if qimage is None or qimage.isNull():
                # 如果圖像為空，顯示錯誤指示
                logger.warning(f"圖像無效: {self.path}")
                self.error_state = True
                error_img = QImage(100, 100, QImage.Format_RGB888)
                error_img.fill(QColor(255, 200, 0))  # 黃色警告色
                
                # 在圖像上繪製錯誤標記
                painter = QPainter(error_img)
                painter.setPen(QColor(0, 0, 0))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(QRect(10, 10, 80, 80), Qt.AlignCenter, "載入錯誤")
                painter.end()
                
                self.pixmap = QPixmap.fromImage(error_img)
            else:
                # 檢查圖像的有效性
                if qimage.width() <= 0 or qimage.height() <= 0:
                    # 無效圖像尺寸
                    logger.warning(f"圖像尺寸無效: {self.path} ({qimage.width()}x{qimage.height()})")
                    self.error_state = True
                    error_img = QImage(100, 100, QImage.Format_RGB888)
                    error_img.fill(QColor(255, 100, 100))  # 警告紅色
                    self.pixmap = QPixmap.fromImage(error_img)
                else:
                    # 正常設置圖像
                    logger.debug(f"正常設置圖像: {self.path}")
                    self.error_state = False
                    self.pixmap = QPixmap.fromImage(qimage)
            
            # 縮放圖片以適應標籤大小，保持比例
            self._scale_and_set_pixmap()
        except Exception as e:
            logger.error(f"設置圖片時發生錯誤: {self.path}, {e}")
            # 如果設置失敗，顯示錯誤圖示
            self.error_state = True
            error_img = QImage(100, 100, QImage.Format_RGB888)
            error_img.fill(QColor(255, 0, 0))  # 紅色
            self.image_label.setPixmap(QPixmap.fromImage(error_img))
    
    def _scale_and_set_pixmap(self):
        """處理圖片縮放和設置到標籤"""
        try:
            scaled_pixmap = self.pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"縮放圖片失敗: {e}")
            # 嘗試使用不同的縮放方法
            try:
                scaled_pixmap = self.pixmap.scaled(
                    self.image_label.width(), 
                    self.image_label.height(),
                    Qt.KeepAspectRatio
                )
                self.image_label.setPixmap(scaled_pixmap)
            except:
                # 最後嘗試：直接設置原始pixmap
                try:
                    self.image_label.setPixmap(self.pixmap)
                except Exception as e2:
                    logger.error(f"所有顯示方法都失敗: {e2}")
                    # 創建最基本的錯誤圖示
                    error_pixmap = QPixmap(100, 100)
                    error_pixmap.fill(Qt.red)
                    self.image_label.setPixmap(error_pixmap)
        
    def set_labels(self, labels):
        """
        設置標籤文本
        
        Parameters:
            labels (list): 標籤列表
        """
        self.labels = labels
        if not labels:
            self.text_label.setText("無標籤")
        elif len(labels) > 2:
            self.text_label.setText(", ".join(labels[:2]) + "...")
        else:
            self.text_label.setText(", ".join(labels))
            
    def mouseReleaseEvent(self, event):
        """滑鼠釋放事件，發出點擊信號"""
        self.clicked.emit(self.path)
        super().mouseReleaseEvent(event)
        
    def resizeEvent(self, event):
        """調整大小事件，重新縮放圖片"""
        if self.pixmap and not self.pixmap.isNull():
            # 重新縮放圖片以適應新的大小
            try:
                self._scale_and_set_pixmap()
            except Exception as e:
                logger.error(f"重新縮放圖片失敗: {e}")
        super().resizeEvent(event)

class LoadingDialog(QWidget):
    """載入進度對話框，用於顯示載入進度"""
    def __init__(self, title="請稍候", message="正在載入圖片索引...", parent=None):
        """
        初始化載入對話框
        
        Parameters:
            title (str, optional): 對話框標題
            message (str, optional): 載入訊息
            parent (QWidget, optional): 父部件
        """
        super().__init__(parent, Qt.Dialog)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(400, 150)
        
        # 設置視窗樣式
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        # 創建佈局
        layout = QVBoxLayout()
        
        # 添加訊息標籤
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(self.message_label)
        
        # 添加進度條
        from PyQt5.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # 添加進度文字標籤
        self.progress_label = QLabel("0/0")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
        
        # 設置視窗居中
        self.center_on_screen()
        
        logger.debug("創建載入對話框")
    
    def center_on_screen(self):
        """將視窗置於螢幕中央"""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, 
                 (screen.height() - size.height()) // 2)
    
    def update_progress(self, current, total):
        """
        更新進度條和標籤
        
        Parameters:
            current (int): 當前進度值
            total (int): 總進度值
        """
        if total <= 0:
            percent = 0
        else:
            percent = int(current / total * 100)
        
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"{current}/{total}")
        self.message_label.setText(f"正在載入圖片索引... ({percent}%)")
        
        # 強制更新介面
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        logger.debug(f"更新進度: {current}/{total} ({percent}%)")
        
    def closeEvent(self, event):
        """關閉事件處理"""
        logger.debug("關閉載入對話框")
        super().closeEvent(event) 