import yaml
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms
import torch

from collections import defaultdict
from globals.globals import LABELS
YAML_FILE = 'dataset/coffee_bean_dataset/splits/split_8_dataset.yaml'  # 替換為你的 dataset.yaml 路徑

class CoffeeBeanDataset(Dataset):
    def __init__(self, yaml_file, transform=None):
        # 讀取 YAML 檔案
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
            raw_data = data.get('dataset', {})
        
        self.transform = transform
        self.image_paths = []
        self.labels = []
        for path, labels in raw_data.items():
            # 只保留第一個標籤在 LABELS 裡的資料
            if labels and labels[0] in LABELS:
                self.image_paths.append(path)
                self.labels.append(labels)
            # 否則自動忽略
        self.labels_count = len(LABELS)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        # 取得影像路徑和標籤
        img_path = self.image_paths[idx]
        labels = self.labels[idx]  # 這裡是多標籤

        # 使用 os.path.join 來構建完整的路徑
        full_img_path = img_path

        # 開啟影像
        image = Image.open(full_img_path)

        # 如果有提供轉換，則應用轉換
        if self.transform:
            image = self.transform(image)
        else:
            #print("資料集沒有提供transform")
            # 如果沒有transform，至少要將圖像轉換為張量
            transform = transforms.Compose([
                transforms.ToTensor(),
            ])
            image = transform(image)
    
        # 將標籤轉換為單一數字索引（只取第一個標籤）
        try:
            if len(labels) == 0:
                raise ValueError(f"圖片 {img_path} 沒有標籤")
            label_index = LABELS.index(labels[0])  # 只取第一個標籤
            return image, label_index
        except ValueError as e:
            raise ValueError(f"標籤 {labels} 不在標籤列表中: {e}")
    
    def show_dataset_statistics(self):
        import matplotlib.pyplot as plt
        from matplotlib import font_manager

        # 使用系統中支援中文字的字體
        plt.rcParams['font.family'] = 'DFKai-SB'  # 使用系統中預設的中文字體
        plt.rcParams['axes.unicode_minus'] = False  # 顯示負號
        """顯示資料集的類別分布狀況和各類別的範例圖片"""
        # 收集每個類別的圖片索引
        class_distributions = defaultdict(list)
        class_counts = defaultdict(int)
        
        print("\n=== 資料集統計資訊 ===")
        print(f"總圖片數量: {len(self)}")
        
        # 統計每個類別的數量和收集圖片索引
        for idx in range(len(self)):
            try:
                _, label_index = self[idx]
                label_name = LABELS[label_index]
                class_counts[label_name] += 1
                class_distributions[label_name].append(idx)
            except Exception as e:
                print(f"處理索引 {idx} 時發生錯誤: {e}")
                continue
        
        # 顯示類別分布
        print("\n類別分布:")
        for label, count in class_counts.items():
            percentage = (count / len(self)) * 100
            print(f"{label}: {count} 張 ({percentage:.1f}%)")
        
        # 繪製類別分布長條圖
        plt.figure(figsize=(15, 5))
        plt.subplot(1, 2, 1)
        plt.bar(class_counts.keys(), class_counts.values())
        plt.xticks(rotation=45, ha='right')
        plt.title("類別分布")
        plt.ylabel("圖片數量")
        
        # 顯示每個類別的第一張圖片
        num_classes = len(class_distributions)
        cols = 4
        rows = (num_classes + cols - 1) // cols
        plt.figure(figsize=(15, 3*rows))
        
        for idx, (label_name, image_indices) in enumerate(class_distributions.items()):
            if image_indices:  # 確保該類別有圖片
                # 獲取該類別的第一張圖片
                image, _ = self[image_indices[0]]
                
                # 如果是 tensor，轉換為 numpy array
                if isinstance(image, torch.Tensor):
                    image = image.permute(1, 2, 0).numpy()
                    
                    # 如果是單通道圖片，移除通道維度
                    if image.shape[2] == 1:
                        image = image[:, :, 0]
                    
                    # 正規化到 [0, 1] 範圍
                    image = (image - image.min()) / (image.max() - image.min())
                
                plt.subplot(rows, cols, idx + 1)
                plt.imshow(image)
                plt.title(f"{label_name}\n({class_counts[label_name]} 張)")
                plt.axis('off')
        
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    # 測試代碼
    dataset = CoffeeBeanDataset(YAML_FILE)

    # 測試數據集長度
    print(f"Dataset length: {len(dataset)}")

    print("LABELS: ", LABELS)
    # 測試訪問數據集項目
    for i in range(len(dataset)):
        try:
            image, label_index = dataset[i]
            print(f"Image {i}: Label index {label_index}")
        except Exception as e:
            print(f"Error accessing item {i}: {e}")
            break

    # 顯示資料集統計資訊
    dataset.show_dataset_statistics()