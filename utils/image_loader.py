import os
import time
import tempfile
from PIL import Image
from PyQt5.QtGui import QImage, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
import numpy as np

from .logger import get_logger
from .constants import THUMBNAIL_SIZE

# 獲取當前模組的 logger
logger = get_logger('image_loader')

class ImageLoader(QThread):
    """圖片載入器線程類，用於異步載入多張圖片"""
    image_loaded = pyqtSignal(str, QImage)  # 當圖片載入完成時發出信號
    progress_updated = pyqtSignal(int, int)  # 進度更新信號
    loading_finished = pyqtSignal()  # 當所有圖片載入完成時發出信號
    
    def __init__(self, image_paths, priority_paths=None):
        """
        初始化圖片載入器
        
        Parameters:
            image_paths (list): 要載入的所有圖片路徑
            priority_paths (list, optional): 優先載入的圖片路徑
        """
        super().__init__()
        self.image_paths = image_paths
        self.priority_paths = priority_paths or []
        self.running = True
        self.max_retries = 2  # 每張圖片的最大重試次數
        logger.debug(f"初始化圖片載入器，共 {len(image_paths)} 張圖片，{len(self.priority_paths)} 張優先圖片")
    
    def run(self):
        """執行圖片載入任務"""
        logger.info("開始載入圖片...")
        total_images = len(self.image_paths)
        loaded_count = 0
        failed_paths = []  # 用於記錄載入失敗的圖片
        
        # 先處理優先級路徑
        if self.priority_paths:
            logger.info(f"處理 {len(self.priority_paths)} 張優先圖片")
            for path in self.priority_paths:
                if not self.running:
                    logger.info("圖片載入器被停止")
                    return
                    
                if path in self.image_paths:
                    success = self.load_single_image(path)
                    if success:
                        loaded_count += 1
                    else:
                        failed_paths.append(path)
                    
                    if loaded_count % 10 == 0:
                        self.progress_updated.emit(loaded_count, total_images)
        
        # 處理其餘路徑
        logger.info("處理其餘圖片")
        for path in self.image_paths:
            if not self.running:
                logger.info("圖片載入器被停止")
                return
                
            if path not in self.priority_paths:
                success = self.load_single_image(path)
                if success:
                    loaded_count += 1
                else:
                    failed_paths.append(path)
                
                if loaded_count % 10 == 0:
                    self.progress_updated.emit(loaded_count, total_images)
                    
                # 短暫休眠，避免佔用太多資源
                time.sleep(0.01)
        
        # 重試載入失敗的圖片
        if failed_paths and self.running:
            logger.warning(f"嘗試重新載入 {len(failed_paths)} 張失敗的圖片...")
            for retry in range(self.max_retries):
                if not self.running:
                    break
                
                still_failed = []
                for path in failed_paths:
                    if self.load_single_image(path, is_retry=True):
                        loaded_count += 1
                    else:
                        still_failed.append(path)
                
                failed_paths = still_failed
                if not failed_paths:
                    break
                
                # 等待短暫時間後重試
                time.sleep(0.5)
            
            if failed_paths:
                logger.error(f"有 {len(failed_paths)} 張圖片載入失敗，創建佔位符圖像")
                # 為最終失敗的圖片創建佔位符圖像
                for path in failed_paths:
                    self.create_placeholder_image(path)
        
        self.progress_updated.emit(loaded_count, total_images)
        logger.info(f"圖片載入完成，成功載入 {loaded_count}/{total_images} 張圖片")
        self.loading_finished.emit()  # 發出加載完成信號
    
    def load_single_image(self, path, is_retry=False):
        """
        載入單張圖片
        
        Parameters:
            path (str): 圖片路徑
            is_retry (bool, optional): 是否為重試載入
            
        Returns:
            bool: 是否成功載入
        """
        try:
            if not is_retry:
                logger.debug(f"載入圖片: {path}")
                
            # 使用更健壯的圖片載入方式
            img = Image.open(path)
            
            # 確保圖片模式正確
            if img.mode not in ["RGB", "RGBA"]:
                img = img.convert("RGB")
                
            # 如果圖片尺寸過大，先調整到合理大小再縮放為縮略圖
            if max(img.size) > 2000:  # 如果圖片任一邊超過2000像素
                # 計算縮放比例，減小到合理大小
                scale = 2000 / max(img.size)
                new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                img = img.resize(new_size, Image.LANCZOS)
            
            # 創建縮略圖
            img.thumbnail(THUMBNAIL_SIZE)
            
            # 在轉換前確保圖片數據是有效的
            img.load()
            
            # 轉換為QImage，使用增強的轉換方法
            qimg = self.enhanced_pil_to_qimage(img)
            
            # 檢查轉換後的QImage是否有效
            if qimg and not qimg.isNull():
                self.image_loaded.emit(path, qimg)
                return True
            else:
                if not is_retry:
                    logger.warning(f"轉換後的QImage無效: {path}")
                return False
                
        except Exception as e:
            if not is_retry:
                logger.error(f"載入圖片失敗 {path}: {e}")
            return False
    
    def create_placeholder_image(self, path):
        """
        為載入失敗的圖片創建佔位符圖像
        
        Parameters:
            path (str): 圖片路徑
        """
        try:
            logger.debug(f"為 {path} 創建佔位符圖像")
            # 建立一個警告色的錯誤圖示
            error_img = QImage(THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1], QImage.Format_RGB888)
            error_img.fill(QColor(255, 200, 0))  # 警告黃色，比紅色更容易辨識
            
            # 在圖像上繪製錯誤標記
            painter = QPainter(error_img)
            painter.setPen(QColor(0, 0, 0))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(QRect(10, 10, THUMBNAIL_SIZE[0]-20, THUMBNAIL_SIZE[1]-20), 
                             Qt.AlignCenter, "載入錯誤")
            painter.end()
            
            self.image_loaded.emit(path, error_img)
        except Exception as e:
            logger.error(f"創建佔位符圖像失敗: {e}")
    
    def stop(self):
        """停止載入線程"""
        logger.info("停止圖片載入器...")
        self.running = False
        self.wait()
        logger.debug("圖片載入器已停止")
    
    @staticmethod
    def enhanced_pil_to_qimage(pil_img):
        """
        改進版的PIL圖片轉換為QImage函數，增加更多錯誤處理和容錯能力
        
        Parameters:
            pil_img (PIL.Image): PIL圖片對象
            
        Returns:
            QImage: 轉換後的QImage對象
        """
        try:
            # 確保圖片模式正確
            if pil_img.mode == "RGB":
                # 方法1: 使用numpy進行轉換，這是最可靠的方法
                import numpy as np
                img_array = np.array(pil_img)
                height, width, channels = img_array.shape
                bytes_per_line = channels * width
                # 創建副本以避免numpy數組被回收導致問題
                qimg = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
                return qimg
            elif pil_img.mode == "RGBA":
                # 透明圖片
                import numpy as np
                img_array = np.array(pil_img)
                height, width, channels = img_array.shape
                bytes_per_line = channels * width
                # 創建副本
                qimg = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGBA8888).copy()
                return qimg
            else:
                # 其他模式都先轉為RGB
                rgb_img = pil_img.convert("RGB")
                return ImageLoader.enhanced_pil_to_qimage(rgb_img)
        except Exception as e:
            logger.warning(f"首選轉換方法失敗: {e}，嘗試替代方法")
            
            try:
                # 方法2: 保存為臨時文件再載入
                temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_filename = temp.name
                temp.close()
                
                # 保存為PNG文件
                pil_img.convert("RGB").save(temp_filename)
                
                # 使用Qt直接載入
                qimg = QImage(temp_filename)
                
                # 刪除臨時文件
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                    
                return qimg
            except Exception as e2:
                logger.error(f"所有轉換方法都失敗: {e2}")
                
                # 返回一個空白的紅色圖像作為錯誤指示
                qimg = QImage(100, 100, QImage.Format_RGB888)
                qimg.fill(Qt.red)
                return qimg
    
    @staticmethod
    def pil_to_qimage(pil_img):
        """將PIL圖片轉換為QImage，正確處理各種圖片模式，使用增強版本"""
        return ImageLoader.enhanced_pil_to_qimage(pil_img)

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