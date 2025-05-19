import os
import logging
import time
from logging.handlers import RotatingFileHandler

# 創建日誌目錄
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日誌文件名使用時間戳，確保唯一性
LOG_FILE = os.path.join(LOG_DIR, f"app_{time.strftime('%Y%m%d_%H%M%S')}.log")

# 設置全局日誌格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

# 創建文件處理器，使用RotatingFileHandler限制日誌大小和數量
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
)
file_handler.setFormatter(formatter)

# 創建控制台處理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 全局日誌級別字典，方便外部設置
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def get_logger(name, level='INFO'):
    """
    獲取指定名稱的 logger 實例
    
    Parameters:
        name (str): logger 名稱，通常使用模組名稱
        level (str): 日誌級別，可選值: DEBUG, INFO, WARNING, ERROR, CRITICAL
        
    Returns:
        logging.Logger: 配置好的 logger 實例
    """
    # 獲取 logger 實例
    logger = logging.getLogger(name)
    
    # 設置日誌級別
    logger.setLevel(LOG_LEVELS.get(level, logging.INFO))
    
    # 避免重複添加處理器
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    # 避免日誌傳播到上層 logger
    logger.propagate = False
    
    return logger

# 創建一個名為 'app' 的全局 logger
app_logger = get_logger('app')

# 函數用於更改全局日誌級別
def set_global_log_level(level):
    """
    設置全局日誌級別
    
    Parameters:
        level (str): 日誌級別，可選值: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    if level in LOG_LEVELS:
        # 更新根日誌級別
        logging.getLogger().setLevel(LOG_LEVELS[level])
        app_logger.setLevel(LOG_LEVELS[level])
        app_logger.info(f"全局日誌級別已設置為 {level}")
    else:
        app_logger.warning(f"無效的日誌級別: {level}，使用預設值 INFO")
        
# 函數用於獲取有關日誌的信息
def get_log_info():
    """
    獲取當前日誌配置信息
    
    Returns:
        dict: 包含日誌配置信息的字典
    """
    return {
        'log_file': LOG_FILE,
        'log_dir': LOG_DIR,
        'app_level': logging.getLevelName(app_logger.level)
    } 