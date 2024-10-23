import os
import subprocess
import logging
import shutil
import glob
import time
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count, Queue
from logging.handlers import QueueHandler, QueueListener

# =======================
# 配置参数
# =======================

# 日志配置
LOG_FILE = "training.log"

# 字体配置
DEFAULT_FONTS_DIR = "/usr/share/fonts"  # 默认字体目录，可根据需要修改

# 其他配置
INVOICE_FILE_PATH = "generated_invoices.txt"  # 发票数据文件路径
NUM_SAMPLES = 100  # 样本数量
FONT_NAMES = ["Microsoft YaHei"]  # 支持的字体列表
LANGUAGES = ["chi_sim"]  # 支持的语言列表

# 路径配置
HOME_DIR = Path.home()
TESSDATA_PREFIX = HOME_DIR / "Desktop" / "trainingdata" / "tesseract-5.4.1"
TESSDATA_PATH = TESSDATA_PREFIX / "tessdata"
TESSTRAIN_DIR = HOME_DIR / "Desktop" / "trainingdata" / "tesstrain"
TRAINING_DATA_DIR = TESSTRAIN_DIR / "data" / "my_model-ground-truth"
LANGDATA_DIR = TESSTRAIN_DIR / "langdata"
OUTPUT_DIR = TESSTRAIN_DIR / "output"
MODEL_DIR = TESSTRAIN_DIR / "model"  # 用于存放中间模型文件

# 环境变量设置
os.environ["TESSDATA_PREFIX"] = str(TESSDATA_PATH)
os.environ['OMP_NUM_THREADS'] = str(cpu_count())

# 创建必要的目录
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
(LANGDATA_DIR / "my_model").mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# =======================
# 日志配置（多进程安全）
# =======================

def configure_logging(log_queue):
    """配置主进程的日志监听器"""
    handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    listener = QueueListener(log_queue, handler, stream_handler)
    listener.start()
    return listener

def worker_configure_logger(log_queue):
    """配置子进程的日志处理器"""
    queue_handler = QueueHandler(log_queue)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(queue_handler)
    # 移除其他处理器以避免重复日志
    for handler in logger.handlers:
        if not isinstance(handler, QueueHandler):
            logger.removeHandler(handler)

# =======================
# 函数定义
# =======================

def check_dependencies():
    """检查所有必需的外部命令是否可用"""
    commands = ['text2image', 'tesseract', 'lstmtraining', 'combine_tessdata', 'fc-cache', 'fc-list', 'fc-match']
    missing = []
    for cmd in commands:
        if shutil.which(cmd) is None:
            missing.append(cmd)
    if missing:
        logging.error(f"缺少必需的命令：{', '.join(missing)}。请确保已安装并在系统路径中。")
        return False
    logging.info("所有必需的外部命令均已安装。")
    return True

def refresh_fonts_cache():
    """刷新字体缓存"""
    try:
        logging.info("刷新字体缓存...")
        subprocess.run(['fc-cache', '-fv'], check=True)
        logging.info("字体缓存刷新成功。")
    except subprocess.CalledProcessError as e:
        logging.error(f"刷新字体缓存时发生错误：{e}")

def check_font_installed(font_name):
    """检查字体是否安装"""
    command = ['fc-list', ':family']
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        installed_fonts = result.stdout.lower().splitlines()
        for line in installed_fonts:
            if font_name.lower() in line:
                logging.info(f"已安装字体：{font_name}")
                return True
        logging.error(f"字体未找到：{font_name}")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"检查字体时发生错误：{e}")
        return False

def find_alternative_font(font_name):
    """如果找不到指定字体，返回系统中已安装的替代字体"""
    try:
        result = subprocess.run(['fc-match', font_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if result.returncode == 0:
            alternative_font = result.stdout.split(':')[0].strip()
            logging.info(f"找不到字体 '{font_name}'，使用替代字体：{alternative_font}")
            return alternative_font
        else:
            logging.error(f"fc-match 命令失败，无法找到替代字体。错误信息：{result.stderr}")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"fc-match 命令执行失败，无法找到替代字体。错误信息：{e}")
        return None

def generate_single_training_sample(args):
    """生成单个训练样本，args 是一个包含 (invoice_text, output_base, i, font_name) 的元组"""
    invoice_text, output_base, i, font_name = args
    retries = 3
    try:
        logging.info(f"正在处理的发票文本 (编号: {i}):\n{invoice_text}\n")

        # 将发票内容写入文本文件
        text_line_path = f"{output_base}.txt"
        with open(text_line_path, 'w', encoding='utf-8') as f:
            f.write(invoice_text)
        logging.debug(f"写入文本文件：{text_line_path}，内容：{invoice_text}")

        for attempt in range(retries):
            command = [
                'text2image',
                '--font', font_name,          # 使用指定的字体
                '--outputbase', output_base,
                '--text', text_line_path,
                '--fonts_dir', str(DEFAULT_FONTS_DIR),  # 确保字体目录正确
                '--ptsize', '40',
                '--char_spacing', '0.0',
                '--exposure', '0'
            ]

            logging.debug(f"执行命令：{' '.join(command)} (尝试 {attempt + 1}/{retries})")
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode == 0:
                logging.info(f"text2image 生成训练数据成功，文件：{output_base}.tif")
                gt_text_path = f"{output_base}.gt.txt"
                with open(gt_text_path, 'w', encoding='utf-8') as f:
                    f.write(invoice_text)
                logging.debug(f"写入 GT 文本文件：{gt_text_path}，内容：{invoice_text}")

                # 检查文件是否生成
                if Path(f"{output_base}.tif").exists():
                    logging.info(f"成功生成 .tif 文件：{output_base}.tif")
                else:
                    logging.error(f"没有找到生成的 .tif 文件：{output_base}.tif")
                break
            else:
                logging.error(f"text2image 生成训练数据失败，错误信息：{result.stderr}")
                time.sleep(2)
        else:
            logging.error(f"多次尝试后，仍无法生成训练样本，样本编号：{i}")

        # 删除临时文本文件
        try:
            Path(text_line_path).unlink()
            logging.debug(f"已删除临时文本文件：{text_line_path}")
        except OSError as e:
            logging.error(f"删除临时文本文件失败：{text_line_path}，错误信息：{e}")

    except Exception as e:
        logging.error(f"生成训练样本时发生异常，样本编号：{i}，错误信息：{e}")

def generate_training_samples_in_parallel(invoice_texts, output_bases):
    """并行生成多个训练样本"""
    logging.info("开始并行生成训练样本...")
    max_workers = min(cpu_count() * 2, 32)  # 根据实际情况调整
    args_list = [(text, base, idx + 1, FONT_NAMES[0]) for idx, (text, base) in enumerate(zip(invoice_texts, output_bases))]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generate_single_training_sample, args) for args in args_list]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logging.error(f"任务运行时出错: {exc}")
    logging.info("所有训练样本生成完成。")

def generate_training_samples_from_invoices():
    logging.info(f"从文件 {INVOICE_FILE_PATH} 读取发票数据并生成训练样本...")
    try:
        with open(INVOICE_FILE_PATH, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        logging.error(f"发票文件未找到：{INVOICE_FILE_PATH}")
        return

    # 过滤有效的发票数据行
    # 替换 '￥' 为 '¥' 并将文本转换为小写
    invoice_texts = [line.strip().replace('￥', '¥').lower() for line in lines if line.strip() and not line.startswith("=")]

    # 应用样本数量限制
    if NUM_SAMPLES > 0:
        invoice_texts = invoice_texts[:NUM_SAMPLES]

    if not invoice_texts:
        logging.warning("没有找到有效的发票数据。")
        return

    output_bases = [TRAINING_DATA_DIR / f"invoice_{idx}" for idx in range(1, len(invoice_texts) + 1)]

    # 并行生成训练样本
    generate_training_samples_in_parallel(invoice_texts, output_bases)

def find_best_checkpoint():
    """查找损失率最低的检查点文件"""
    logging.info("开始查找损失率最小的检查点文件...")
    checkpoint_files = list(MODEL_DIR.glob('*.checkpoint'))
    if not checkpoint_files:
        logging.error("未找到任何检查点文件。")
        return None

    min_loss = float('inf')
    best_checkpoint = None

    # 使用正则表达式从文件名中提取损失率
    def get_loss_from_filename(filename):
        match = re.search(r'_([0-9.]+)_\d+_\d+\.checkpoint', filename.name)
        if match:
            return float(match.group(1))
        return None

    for checkpoint in checkpoint_files:
        loss = get_loss_from_filename(checkpoint)
        if loss is not None and loss < min_loss:
            min_loss = loss
            best_checkpoint = checkpoint

    if best_checkpoint:
        logging.info(f"找到最优检查点文件：{best_checkpoint} (损失率：{min_loss})")
    else:
        logging.error("未找到任何有效的检查点文件。")

    return best_checkpoint

def generate_single_lstmf(tif_file):
    """单个 .tif 文件生成 .lstmf 文件的处理函数"""
    try:
        base = tif_file.with_suffix('')  # 去除 .tif 后缀
        lstmf_file = base.with_suffix('.lstmf')
        gt_file = base.with_suffix('.gt.txt')

        # 检查 .gt.txt 文件是否存在
        if not gt_file.exists():
            logging.error(f"缺少对应的 .gt.txt 文件：{gt_file}，跳过生成 .lstmf 文件。")
            return

        command = [
            'tesseract',
            str(tif_file),
            str(base),
            '-l', 'chi_sim',  # 仅使用简体中文
            '--psm', '6',
            '--tessdata-dir', str(TESSDATA_PATH),
            'lstm.train'
        ]

        logging.debug(f"执行命令：{' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logging.error(f"生成 .lstmf 文件失败，文件：{tif_file}，错误信息：{result.stderr}")
            logging.debug(f"Tesseract 输出（stdout）：{result.stdout}")
            logging.debug(f"Tesseract 输出（stderr）：{result.stderr}")
        else:
            # 检查文件是否实际生成
            if lstmf_file.exists():
                logging.info(f"成功生成 .lstmf 文件：{lstmf_file}")
            else:
                logging.error(f"命令返回成功，但未找到 .lstmf 文件：{lstmf_file}")
                logging.debug(f"Tesseract 输出（stdout）：{result.stdout}")
                logging.debug(f"Tesseract 输出（stderr）：{result.stderr}")

    except Exception as e:
        logging.error(f"生成 .lstmf 文件时发生异常，文件：{tif_file}，错误信息：{e}")

def generate_lstmf_files():
    """使用 Tesseract 生成 .lstmf 文件，使用多进程加速"""
    logging.info("开始生成 .lstmf 文件...")
    tif_files = list(TRAINING_DATA_DIR.glob("*.tif"))
    logging.info(f"找到 {len(tif_files)} 个 .tif 文件需要转换为 .lstmf 文件。")

    if not tif_files:
        logging.warning("未找到任何 .tif 文件，请检查生成步骤。")
        return

    max_workers = min(cpu_count() * 2, 32)  # 根据实际情况调整
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generate_single_lstmf, tif_file) for tif_file in tif_files]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                logging.error(f"任务运行时出错: {exc}")
    logging.info("所有 .lstmf 文件生成完成。")

def generate_lstmf_training_list():
    """生成 lstmf.training_list 文件，使用绝对路径"""
    logging.info("开始生成 lstmf.training_list 文件...")
    training_list_path = TRAINING_DATA_DIR / "lstmf.training_list"

    try:
        lstmf_files = list(TRAINING_DATA_DIR.glob("*.lstmf"))
        logging.info(f"找到 {len(lstmf_files)} 个 .lstmf 文件")

        if not lstmf_files:
            logging.warning("未找到任何 .lstmf 文件，请检查生成步骤。")

        with open(training_list_path, 'w', encoding='utf-8') as f:
            for lstmf_file in lstmf_files:
                absolute_path = lstmf_file.resolve()
                f.write(f"{absolute_path}\n")

        logging.info(f"成功生成 lstmf.training_list 文件：{training_list_path}")
    except Exception as e:
        logging.error(f"生成 lstmf.training_list 文件失败，错误信息：{e}")

def extract_lstm_from_traineddata(retries=3):
    """从预训练的 traineddata 文件中提取 lstm 文件，并添加重试机制"""
    logging.info("开始提取 LSTM 文件...")
    base_model = TESSDATA_PATH / "chi_sim.traineddata"
    output_lstm = MODEL_DIR / "chi_sim.lstm"
    if not base_model.exists():
        logging.error(f"基础模型文件未找到：{base_model}")
        return

    command = [
        'combine_tessdata', '-e', str(base_model), str(output_lstm)
    ]

    for attempt in range(1, retries + 1):
        logging.debug(f"执行命令：{' '.join(command)} (尝试 {attempt}/{retries})")
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            logging.info(f"成功提取 LSTM 文件：{output_lstm}")
            return
        except subprocess.CalledProcessError as e:
            logging.error(f"提取 LSTM 文件失败，错误信息：{e.stderr}")
            if attempt < retries:
                logging.info("等待 5 秒后重试...")
                time.sleep(5)
            else:
                logging.error("达到最大重试次数，提取 LSTM 文件失败。")

def package_traineddata():
    """打包 .traineddata 文件"""
    logging.info("开始打包 .traineddata 文件...")
    best_checkpoint = find_best_checkpoint()

    if not best_checkpoint:
        logging.error("无法打包 .traineddata 文件，因为未找到最佳检查点。")
        return

    final_traineddata_path = OUTPUT_DIR / "my_model.traineddata"
    package_cmd = [
        'lstmtraining',
        '--stop_training',
        '--continue_from', str(best_checkpoint),
        '--traineddata', str(TESSDATA_PATH / 'chi_sim.traineddata'),  # 仅使用简体中文数据
        '--model_output', str(final_traineddata_path)
    ]

    logging.debug(f"执行命令：{' '.join(package_cmd)}")

    try:
        result = subprocess.run(package_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        logging.info(f"成功生成 .traineddata 文件：{final_traineddata_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"生成 .traineddata 文件失败，错误信息：{e.stderr}")

def train_lstm():
    """使用 lstmtraining 进行训练，并实时显示输出"""
    logging.info("开始进行 LSTM 模型训练...")
    lstm_model_path = MODEL_DIR / 'chi_sim.lstm'

    # 检查 .lstm 文件是否存在
    if not lstm_model_path.exists():
        logging.error(f"LSTM 模型文件未找到：{lstm_model_path}。请确保已成功提取 .lstm 文件。")
        return

    # 训练过程，生成检查点文件
    model_output_prefix = MODEL_DIR / 'my_model'
    init_cmd = [
        'lstmtraining',
        '--model_output', str(model_output_prefix),
        '--continue_from', str(lstm_model_path),
        '--traineddata', str(TESSDATA_PATH / 'chi_sim.traineddata'),  # 仅使用简体中文数据
        '--train_listfile', str(TRAINING_DATA_DIR / 'lstmf.training_list'),
        '--max_iterations', '4000'
    ]

    logging.debug(f"执行命令：{' '.join(init_cmd)}")

    try:
        # 使用 Popen 启动子进程，并将输出写入日志文件
        with open(MODEL_DIR / "lstmtraining_output.log", "w", encoding='utf-8') as logfile:
            process = subprocess.Popen(init_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # 实时读取子进程的输出并打印
            for line in iter(process.stdout.readline, ''):
                # 将输出转换为小写并写入日志
                processed_line = line.lower()
                logfile.write(processed_line)
                logging.debug(processed_line.strip())

            process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                logging.error(f"LSTM 训练过程中出现错误，返回码：{return_code}")
                logging.error(f"查看详细错误信息：{MODEL_DIR / 'lstmtraining_output.log'}")
                return
            else:
                logging.info("LSTM 训练完成。")
    except Exception as e:
        logging.error(f"运行 lstmtraining 时发生异常：{e}")
        return

    # 训练完成后，开始打包 traineddata 文件
    logging.info("开始打包 .traineddata 文件...")
    package_traineddata()

def clean_up():
    """清理临时文件（可选）"""
    logging.info("开始清理临时文件...")
    try:
        files_to_delete = list(TRAINING_DATA_DIR.glob("*.tif")) + \
                          list(TRAINING_DATA_DIR.glob("*.gt.txt")) + \
                          list(TRAINING_DATA_DIR.glob("*.box")) + \
                          list(TRAINING_DATA_DIR.glob("*.tr")) + \
                          list(TRAINING_DATA_DIR.glob("*.lstmf"))

        for file in files_to_delete:
            if file.exists():
                file.unlink()
                logging.debug(f"已删除文件：{file}")
            else:
                logging.warning(f"文件未找到，跳过删除：{file}")

        logging.info("已删除临时训练数据文件。")
    except Exception as e:
        logging.error(f"清理过程中发生错误：{e}")

def generate_training_data():
    """生成训练数据，使用多进程加速"""
    logging.info("开始生成训练数据...")
    refresh_fonts_cache()

    # 检查并确保所需字体已安装
    for font in FONT_NAMES.copy():  # 使用 copy 以安全地修改列表
        if not check_font_installed(font):
            alternative = find_alternative_font(font)
            if alternative:
                logging.info(f"将字体 '{font}' 替换为 '{alternative}'")
                FONT_NAMES[FONT_NAMES.index(font)] = alternative
            else:
                logging.error(f"字体 '{font}' 未安装，无法继续生成训练数据。")
                return

    generate_training_samples_from_invoices()
    logging.info("训练数据生成完成。")

def train_model():
    """完整的训练流程"""
    generate_training_data()
    generate_lstmf_files()
    generate_lstmf_training_list()
    extract_lstm_from_traineddata()
    train_lstm()
    # clean_up()  # 根据需要开启或关闭清理

def main():
    """主函数"""
    log_queue = Queue()
    listener = configure_logging(log_queue)
    try:
        if not check_dependencies():
            logging.error("依赖检查失败，终止训练。")
            return
        train_model()
    finally:
        listener.stop()

if __name__ == "__main__":
    main()
