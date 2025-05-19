import os
import yaml
import time
import shutil
from .logger import get_logger
from .constants import DEFAULT_SETTINGS

# 獲取當前模組的 logger
logger = get_logger('file_utils')

def normalize_path(path):
    """統一路徑格式，將所有路徑轉換為使用正斜線"""
    logger.debug(f"正規化路徑: {path}")
    return path.replace('\\', '/')

def load_settings(yaml_file):
    """載入設定檔，包含標籤和上次的索引"""
    logger.info(f"載入設定檔: {yaml_file}")
    try:
        with open(yaml_file, 'r', encoding='utf-8') as file:
            settings = yaml.safe_load(file)
            result = {
                'labels': settings.get('labels', DEFAULT_SETTINGS['labels']),
                'last_index': settings.get('last_index', 0)
            }
            logger.debug(f"設定檔已載入: {result}")
            return result
    except Exception as e:
        logger.error(f"載入設定檔時發生錯誤: {e}")
        # 返回預設設定
        logger.info("使用預設設定")
        return DEFAULT_SETTINGS.copy()

def save_settings(yaml_file, settings_data, current_index):
    """保存設定檔，更新上次的索引"""
    logger.info(f"保存設定檔: {yaml_file}, 當前索引: {current_index}")
    try:
        # 確保目錄存在
        os.makedirs(os.path.dirname(yaml_file), exist_ok=True)
        
        # 讀取現有設定或創建新的
        if os.path.exists(yaml_file):
            with open(yaml_file, 'r', encoding='utf-8') as file:
                settings = yaml.safe_load(file) or {}
        else:
            settings = {}
        
        # 更新索引
        settings['last_index'] = current_index
        
        # 保存設定
        with open(yaml_file, 'w', encoding='utf-8') as file:
            yaml.dump(settings, file, indent=2, allow_unicode=True)
        
        logger.debug("設定檔已保存")
        return True
    except Exception as e:
        logger.error(f"保存設定檔時發生錯誤: {e}")
        return False

def load_dataset(yaml_file, project_root):
    """載入或創建資料集，並確保所有路徑格式一致"""
    logger.info(f"載入資料集: {yaml_file}")
    
    try:
        if os.path.exists(yaml_file):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {'dataset': {}}
                
                # 統一路徑格式
                normalized_data = {'dataset': {}}
                
                logger.debug(f"載入資料集時的專案根目錄: {project_root}")
                
                for path, labels in data['dataset'].items():
                    # 正規化路徑斜線
                    normalized_path = normalize_path(path)
                    
                    # 如果是相對路徑，則轉換為絕對路徑以便程式內部使用
                    if not os.path.isabs(normalized_path):
                        # 從專案根目錄開始組合路徑
                        abs_path = os.path.abspath(os.path.join(project_root, normalized_path))
                        normalized_path = normalize_path(abs_path)
                    
                    normalized_data['dataset'][normalized_path] = labels
                
                logger.info(f"成功載入資料集，包含 {len(normalized_data['dataset'])} 項記錄")
                return normalized_data
        else:
            logger.warning(f"資料集文件不存在: {yaml_file}，將創建新的資料集")
            return {'dataset': {}}
    except Exception as e:
        logger.error(f"載入資料集時發生錯誤: {e}")
        return {'dataset': {}}

def save_dataset(yaml_file, data, project_root):
    """保存資料集，並自動創建備份"""
    logger.info(f"正在儲存資料集: {yaml_file}")
    
    try:
        # 創建備份目錄
        backup_dir = os.path.join(os.path.dirname(yaml_file), "backups")
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir)
                logger.info(f"已創建備份目錄: {backup_dir}")
            except Exception as e:
                logger.warning(f"無法創建備份目錄 {backup_dir}: {e}")
        
        # 創建帶有時間戳的備份檔名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"{os.path.basename(yaml_file)}.{timestamp}.bak")
        
        # 如果原始檔案存在，先創建備份
        if os.path.exists(yaml_file):
            try:
                shutil.copy2(yaml_file, backup_file)
                logger.info(f"已創建備份: {backup_file}")
            except Exception as e:
                logger.warning(f"備份失敗: {e}")
        
        # 統一路徑格式，確保使用相對路徑
        normalized_data = {'dataset': {}}
        
        logger.debug(f"儲存資料集時的專案根目錄: {project_root}")
        
        for path, labels in data['dataset'].items():
            # 處理絕對路徑轉換為相對路徑
            if os.path.isabs(path):
                try:
                    # 嘗試將絕對路徑轉換為相對於專案根目錄的路徑
                    rel_path = os.path.relpath(path, project_root)
                    # 確保使用正斜線
                    normalized_path = normalize_path(rel_path)
                except ValueError:
                    # 如果無法轉換（例如不同磁碟機），則保留原路徑但仍正規化斜線
                    logger.warning(f"無法將路徑 {path} 轉換為相對路徑")
                    normalized_path = normalize_path(path)
            else:
                # 已經是相對路徑，只需正規化斜線
                normalized_path = normalize_path(path)
            
            normalized_data['dataset'][normalized_path] = labels
        
        # 確保目錄存在
        os.makedirs(os.path.dirname(yaml_file), exist_ok=True)
        
        # 保存新的資料集
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(normalized_data, f, indent=2, allow_unicode=True)
        
        logger.info("儲存完成！")
        return True
    except Exception as e:
        logger.error(f"儲存資料集失敗: {e}")
        return False

def clean_dataset(yaml_file, data, project_root):
    """清理資料集中的重複路徑條目"""
    logger.info("開始清理資料集中的重複路徑")
    
    # 創建一個新的數據集字典
    cleaned_data = {'dataset': {}}
    
    # 用於檢測重複的集合
    unique_paths = set()
    duplicates = []
    
    # 獲取所有路徑的標準形式（絕對路徑）
    path_mapping = {}  # 原始路徑 -> 標準路徑
    
    for path in data['dataset']:
        # 如果是相對路徑，轉換為絕對路徑
        if not os.path.isabs(path):
            abs_path = normalize_path(os.path.abspath(os.path.join(project_root, path)))
        else:
            abs_path = normalize_path(path)
        
        # 檢查是否已經有相同的標準路徑
        if abs_path in unique_paths:
            duplicates.append(path)
            logger.debug(f"發現重複路徑: {path}")
        else:
            unique_paths.add(abs_path)
            path_mapping[path] = abs_path
    
    # 如果沒有重複，直接返回原始數據
    if not duplicates:
        logger.info("沒有發現重複路徑")
        return False, data
    
    # 處理重複項，保留最新的標籤
    for path, labels in data['dataset'].items():
        if path not in duplicates:  # 不是重複項，直接添加
            cleaned_data['dataset'][path] = labels
    
    # 報告清理結果
    logger.info(f"清理了 {len(duplicates)} 個重複的路徑條目")
    
    return True, cleaned_data

def get_image_list(folder_path):
    """獲取指定文件夾中的所有圖片文件路徑"""
    logger.info(f"獲取圖片列表: {folder_path}")
    
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    image_paths = []
    
    try:
        if os.path.exists(folder_path):
            # 使用絕對路徑以確保程式內部操作一致性
            images = [
                normalize_path(os.path.abspath(os.path.join(folder_path, f)))
                for f in os.listdir(folder_path) 
                if f.lower().endswith(image_extensions)
            ]
            
            # 排序保證順序一致
            image_paths = sorted(images)
            
            logger.info(f"找到 {len(image_paths)} 張圖片")
            
            # 記錄一些路徑示例，用於調試
            if image_paths:
                logger.debug(f"圖片路徑示例: {image_paths[0]}")
                if len(image_paths) > 1:
                    logger.debug(f"圖片路徑示例2: {image_paths[1]}")
        else:
            logger.error(f"文件夾不存在: {folder_path}")
    except Exception as e:
        logger.error(f"獲取圖片列表時發生錯誤: {e}")
    
    return image_paths 