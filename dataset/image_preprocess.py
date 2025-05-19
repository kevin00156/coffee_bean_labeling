import os  
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import cv2
import numpy as np
import glob
import os
import yaml
import logging  # 新增
import multiprocessing
from globals.globals import dataset_settings

# 設定 logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

"""
這支程式是用來處理影像的
這支程式會將原始影像的每個咖啡豆都逐個摳下來，並且儲存成單獨的影像
你可以在coffee_bean_dataset/OK/result中看到框出咖啡豆的影像，在coffee_bean_dataset/OK/coffee_beans中看到摳下的咖啡豆影像
"""

BASE_PATH = "dataset/coffee_bean_dataset_2/full_insect_damage"

pixel_threshold_lower = dataset_settings['coffee_bean_pixel_threshold']['lower']  # 獲取像素下限
pixel_threshold_upper = dataset_settings['coffee_bean_pixel_threshold']['upper']  # 獲取像素上限

def save_image(image_folder, image, namespace):
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        logger.info(f"建立資料夾: {image_folder}")
    
    # 找到images資料夾中最大的號碼
    existing_images = glob.glob(os.path.join(image_folder, f'{namespace}_*.jpg'))
    if existing_images:
        latest_image = max(existing_images, key=os.path.getctime)
        latest_image_number = int(os.path.basename(latest_image).split('_')[-1].split('.')[0])
    else:
        latest_image_number = 0
    
    # 將圖像寫入到images資料夾中，命名是namespace_{i}.jpg
    image_path = os.path.join(image_folder, f'{namespace}_{latest_image_number + 1}.jpg')
    cv2.imwrite(image_path, image)
    logger.info(f"儲存影像到 {image_path}")

def process_coffee_beans(image, show_image=False, pixel_threshold_lower=10000, pixel_threshold_upper=50000):
    logger.info("開始處理影像：灰階轉換")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if show_image:
        cv2.imshow('灰度圖', gray)
        cv2.waitKey(0)
    
    logger.info("進行高斯模糊降噪")
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    if show_image:
        cv2.imshow('高斯模糊', blurred)
        cv2.waitKey(0)
    
    logger.info("進行Otsu二值化")
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if show_image:
        cv2.imshow('二值化', binary)
        cv2.waitKey(0)
    
    logger.info("進行形態學開運算去除雜訊")
    kernel = np.ones((3,3), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
    if show_image:
        cv2.imshow('開運算', opening)
        cv2.waitKey(0)
    
    logger.info("尋找輪廓")
    contours, _ = cv2.findContours(opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    logger.info(f"總共找到 {len(contours)} 個輪廓")
    result = image.copy()
    
    filtered_contours = [
        contour for contour in contours 
        if pixel_threshold_lower < cv2.contourArea(contour) < pixel_threshold_upper]
    logger.info(f"經過面積篩選後剩下 {len(filtered_contours)} 個輪廓")
        
    rotated_beans = []
    logger.info("開始旋轉每顆咖啡豆的邊界並記錄區域")
    for idx, contour in enumerate(filtered_contours):
        area = cv2.contourArea(contour)
        if area > pixel_threshold_lower and area < pixel_threshold_upper:
            # 1. 取得最小外接旋轉矩形
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            # === 新增：在 result 上畫出旋轉外接矩形 ===
            cv2.drawContours(result, [box], 0, (0, 255, 0), 2)
            cv2.putText(result, str(idx+1), (box[0][0], box[0][1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            width = int(rect[1][0])
            height = int(rect[1][1])
            angle = rect[2]
            # 讓長邊對齊X軸
            if width < height:
                angle = angle + 90
                width, height = height, width
            center = rect[0]
            # 2. 取得仿射變換矩陣，將原圖旋正
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (image.shape[1], image.shape[0]))
            # 3. 以旋轉後的中心、寬高為基準，擴展3像素後裁切
            expand = 3
            x_rot = int(center[0] - width // 2 - expand)
            y_rot = int(center[1] - height // 2 - expand)
            w_rot = width + expand * 2
            h_rot = height + expand * 2
            # 邊界檢查
            x_rot = max(0, x_rot)
            y_rot = max(0, y_rot)
            x_end = min(rotated.shape[1], x_rot + w_rot)
            y_end = min(rotated.shape[0], y_rot + h_rot)
            crop = rotated[y_rot:y_end, x_rot:x_end]
            if crop.size == 0 or crop.shape[0] == 0 or crop.shape[1] == 0:
                logger.warning(f"咖啡豆 #{idx+1} 裁切範圍無效，已跳過")
                continue
            rotated_beans.append({
                "image": crop,
                "rect": rect,
                "box": box,
                "angle": angle,
                "center": center,
                "width": width,
                "height": height,
                "idx": idx
            })
            logger.info(f"咖啡豆 #{idx+1} 旋轉並擴展區域: center={center}, w={width}, h={height}, angle={angle}")
    logger.info("影像處理階段結束")
    return result, rotated_beans

def worker(image_queue, processed_image_folder, coffee_beans_image_folder, pixel_threshold_lower, pixel_threshold_upper):
    while True:
        image_path = image_queue.get()
        if image_path is None:
            break
        logger.info(f"[Worker {multiprocessing.current_process().name}] 開始處理影像: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            logger.warning(f"[Worker {multiprocessing.current_process().name}] 讀取失敗: {image_path}")
            continue
        processed_image, rotated_beans = process_coffee_beans(
            image, show_image=False, 
            pixel_threshold_lower=pixel_threshold_lower, 
            pixel_threshold_upper=pixel_threshold_upper
        )
        result_path = f"{processed_image_folder}/{os.path.basename(image_path)}"
        cv2.imwrite(result_path, processed_image)
        logger.info(f"[Worker {multiprocessing.current_process().name}] 儲存框出咖啡豆的影像到 {result_path}")
        for bean in rotated_beans:
            crop_image = bean["image"]
            save_image(coffee_beans_image_folder, crop_image, f"{os.path.basename(image_path).split('.')[0]}_coffee_bean")
        logger.info(f"[Worker {multiprocessing.current_process().name}] 完成 {image_path} 的所有咖啡豆裁切與儲存")

def main(original_image_folder, processed_image_folder, coffee_beans_image_folder, show_image=False, pixel_threshold_lower=10000, pixel_threshold_upper=50000):
    if not os.path.exists(original_image_folder):
        logger.error(f"資料夾 {original_image_folder} 不存在")
        return
    if not os.path.exists(processed_image_folder):
        os.makedirs(processed_image_folder)
        logger.info(f"建立資料夾: {processed_image_folder}")
    if not os.path.exists(coffee_beans_image_folder):
        os.makedirs(coffee_beans_image_folder)
        logger.info(f"建立資料夾: {coffee_beans_image_folder}")
    
    image_files = (
        glob.glob(f"{original_image_folder}/*.[jJ][pP][gG]") +
        glob.glob(f"{original_image_folder}/*.[jJ][pP][eE][gG]") +
        glob.glob(f"{original_image_folder}/*.[pP][nN][gG]")
    )
    logger.info(f"共找到 {len(image_files)} 張影像進行處理")

    # 建立 multiprocessing queue
    image_queue = multiprocessing.Queue(maxsize=16)
    num_workers = 4
    workers = []
    for _ in range(num_workers):
        p = multiprocessing.Process(
            target=worker, 
            args=(image_queue, processed_image_folder, coffee_beans_image_folder, pixel_threshold_lower, pixel_threshold_upper)
        )
        p.start()
        workers.append(p)
    
    # 將所有圖片路徑放進 queue
    for image_path in image_files:
        image_queue.put(image_path)
    # 放入結束訊號
    for _ in range(num_workers):
        image_queue.put(None)
    # 等待所有 worker 結束
    for p in workers:
        p.join()
    logger.info("所有圖片處理完成")

if __name__ == '__main__':  
    """
    main(
        original_image_folder=f"{BASE_PATH}/OK", 
        processed_image_folder=f"{BASE_PATH}/OK/result", 
        coffee_beans_image_folder=f"{BASE_PATH}/OK/coffee_beans", 
        show_image=False, 
        pixel_threshold_lower=pixel_threshold_lower, 
        pixel_threshold_upper=pixel_threshold_upper
    )
    main(
        original_image_folder=f"{BASE_PATH}/NG", 
        processed_image_folder=f"{BASE_PATH}/NG/result", 
        coffee_beans_image_folder=f"{BASE_PATH}/NG/coffee_beans", 
        show_image=False, 
        pixel_threshold_lower=pixel_threshold_lower, 
        pixel_threshold_upper=pixel_threshold_upper
    )
    """
    main(
        original_image_folder=f"{BASE_PATH}", 
        processed_image_folder=f"{BASE_PATH}/result", 
        coffee_beans_image_folder=f"{BASE_PATH}/coffee_beans", 
        show_image=False, 
        pixel_threshold_lower=pixel_threshold_lower, 
        pixel_threshold_upper=pixel_threshold_upper
    )
