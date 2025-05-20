import os
import time
import threading
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtGui import QImage
from PIL import Image
import numpy as np

from .logger import get_logger

# 獲取當前模組的 logger
logger = get_logger('image_loader')

class ImageLoader(QThread):
    """圖片加載線程，用於後台載入和處理圖片"""
    image_loaded = pyqtSignal(str, object)  # 圖片路徑和 QImage 對象
    progress_updated = pyqtSignal(int, int)  # 當前進度和總數
    loading_finished = pyqtSignal()  # 加載完成信號
    
    def __init__(self, all_paths, priority_paths=None):
        """
        初始化圖片加載線程
        
        Parameters:
            all_paths (list): 所有需要加載的圖片路徑
            priority_paths (list, optional): 優先加載的圖片路徑
        """
        super().__init__()
        self.all_paths = all_paths
        self.priority_paths = priority_paths or []
        self._stop_requested = threading.Event()
        self.cache = {}  # 線程內部緩存
        
        # 使用較低的線程優先級，以避免阻塞主線程
        self.setPriority(QThread.LowPriority)
        
        logger.debug(f"初始化圖片加載線程: {len(all_paths)} 張圖片，{len(priority_paths or [])} 張優先")
    
    def stop(self):
        """請求停止線程"""
        self._stop_requested.set()
        logger.debug("請求停止加載線程")
    
    def run(self):
        """運行線程"""
        # 重置停止標誌
        self._stop_requested.clear()
        
        try:
            # 首先處理優先路徑
            priority_set = set(self.priority_paths)
            paths_to_load = list(self.priority_paths)  # 複製優先列表
            
            # 添加其餘路徑
            for path in self.all_paths:
                if path not in priority_set:
                    paths_to_load.append(path)
            
            total = len(paths_to_load)
            loaded = 0
            
            # 發送初始進度信號
            self.progress_updated.emit(loaded, total)
            
            # 開始加載
            for path in paths_to_load:
                # 檢查是否請求停止
                if self._stop_requested.is_set():
                    logger.info("加載線程收到停止請求")
                    break
                
                try:
                    # 延遲以避免佔用過多CPU
                    self.msleep(1)  # 使用QThread的毫秒睡眠，更精確
                    
                    # 檢查路徑有效性
                    if not path or not os.path.exists(path):
                        logger.warning(f"圖片路徑無效: {path}")
                        continue
                    
                    # 使用PIL加載圖片
                    img = Image.open(path)
                    # 縮小尺寸以減少內存使用
                    img.thumbnail((800, 800), Image.LANCZOS)
                    
                    # 轉換為QImage
                    qimage = self.pil_to_qimage(img)
                    
                    # 發射信號
                    self.image_loaded.emit(path, qimage)
                    
                    # 更新進度
                    loaded += 1
                    if loaded % 5 == 0 or loaded == total:  # 每5張或最後一張時更新進度
                        self.progress_updated.emit(loaded, total)
                    
                except Exception as e:
                    logger.error(f"載入圖片時出錯 {path}: {e}")
                
                # 釋放資源，避免內存洩漏
                img = None
                qimage = None
            
            # 加載完成
            logger.info(f"圖片加載完成: {loaded}/{total}")
            self.loading_finished.emit()
            
        except Exception as e:
            logger.error(f"圖片加載線程出錯: {e}")
            self.loading_finished.emit()  # 即使出錯也發送完成信號
    
    @staticmethod
    def pil_to_qimage(pil_image):
        """
        將PIL圖像轉換為QImage
        
        Parameters:
            pil_image (PIL.Image): PIL圖像對象
        
        Returns:
            QImage: 轉換後的QImage對象
        """
        try:
            # 確保圖片是RGB模式
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            
            # 轉換為numpy數組
            img_data = np.array(pil_image)
            height, width, channels = img_data.shape
            
            # 創建QImage
            bytes_per_line = channels * width
            qimg = QImage(img_data.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            return qimg
        except Exception as e:
            logger.error(f"轉換PIL圖像到QImage時出錯: {e}")
            # 返回一個1x1的空白QImage作為後備
            return QImage(1, 1, QImage.Format_RGB888)

# 用於直接測試圖片載入器
def load_image(image_path, size=None):
    """
    載入單張圖片並返回PIL Image對象
    
    Parameters:
        image_path (str): 圖片路徑
        size (tuple, optional): 目標尺寸 (寬, 高)
        
    Returns:
        PIL.Image: 載入的PIL Image對象
    """
    try:
        logger.debug(f"直接載入圖片: {image_path}")
        
        # 使用PIL載入圖片
        img = Image.open(image_path)
        
        # 確保圖片模式正確
        if img.mode not in ["RGB", "RGBA"]:
            img = img.convert("RGB")
        
        # 如果需要調整大小
        if size:
            img.thumbnail(size)
        
        return img
    except Exception as e:
        logger.error(f"直接載入圖片失敗 {image_path}: {e}")
        
        # 創建錯誤圖像
        width, height = size or (100, 100)
        # 返回紅色的PIL圖像作為錯誤指示
        error_img = Image.new('RGB', (width, height), color=(255, 0, 0))
        return error_img 