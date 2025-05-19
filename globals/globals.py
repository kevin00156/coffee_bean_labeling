import yaml
import os
from kevins_torch.utils import load_config

DATASET_SETTINGS_PATH = "dataset/settings.yaml"
TRAINING_CONFIGS_PATH = "configs/train_configs"
TRAINING_SETTINGS_PATH = "configs/settings.yaml"

with open(TRAINING_SETTINGS_PATH, 'r') as file:
    training_settings = yaml.safe_load(file)  # 讀取配置文件

# 讀取 settings.yaml 並將 LABELS 設置為字典
with open(DATASET_SETTINGS_PATH, 'r') as file:
    dataset_settings = yaml.safe_load(file)
    LABELS: list[str] = list(dataset_settings['labels'].values())

config_filenames = [path for path in os.listdir(TRAINING_CONFIGS_PATH) if path.endswith(".yaml")]
# 根據配置文件名中的數字進行排序
config_filenames.sort(key=lambda x: int(x.split('_')[2].split('.')[0]))

#print(f"找到的配置文件: {config_filenames}")
# 加載所有配置
training_configs = [load_config(TRAINING_CONFIGS_PATH + "/" + config_filename) for config_filename in config_filenames]

#import kevins_torch.utils.load_parameters as load_parameters
#print(load_parameters.get_optimizer_classes())
