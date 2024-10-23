Tesseract 自定义训练流水线
一个全面的 Python 脚本，用于使用您自己的地面真实数据训练自定义 Tesseract OCR 模型。该流水线自动化了从数据准备到模型训练的整个过程，利用并行处理提高效率，并确保日志记录的稳健性。

目录
概述
功能特性
前提条件
安装步骤
使用方法
项目结构
日志记录
清理临时文件
故障排除
贡献指南
许可证
概述
本项目提供了一个基于 Python 的 Tesseract OCR 模型训练流水线。它处理以下内容：

依赖检查：确保所有必要的工具已安装。
字体管理：检查所需字体是否存在，并在需要时查找替代字体。
并行处理：利用多核 CPU 加速数据生成和处理。
稳健的日志记录：实现多进程安全的日志记录，跟踪训练过程。
错误处理：包含重试机制和详细的错误日志记录。
灵活的配置：轻松调整路径、字体名称和样本数量等参数。
通过自动化这些步骤，流水线简化了创建适合您特定数据的定制 OCR 模型的过程。

功能特性
依赖验证：确保所有必要的工具已安装。
字体管理：检查所需字体是否存在，并在需要时查找替代字体。
并行数据生成：利用多核 CPU 高效生成训练样本。
稳健的日志记录：实现线程安全的日志记录，处理来自多个进程的日志。
错误处理：结合重试机制和详细的错误日志记录。
灵活的配置：轻松调整路径、字体名称和样本数量等参数。
前提条件
在运行脚本之前，请确保已安装以下内容：

Python 3.6+
Git
Tesseract OCR（推荐版本 5.4.1）
Tesseract 训练工具：
text2image
tesseract
lstmtraining
combine_tessdata
字体配置工具：
fc-cache
fc-list
fc-match
安装步骤
1. 克隆仓库
bash
Copy code
git clone https://github.com/your_username/tesseract-training.git
cd tesseract-training
2. 设置 Python 环境
建议使用虚拟环境：

bash
Copy code
python3 -m venv venv
source venv/bin/activate
3. 安装所需的 Python 包
如果有任何依赖（脚本主要使用标准库），可以安装。否则，跳过此步骤。

bash
Copy code
pip install -r requirements.txt
4. 确保已安装 Tesseract 工具
在 Ubuntu/Debian 上：

bash
Copy code
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
sudo apt-get install libtesseract-dev
在 macOS 上（使用 Homebrew）：

bash
Copy code
brew install tesseract
brew install tesseract-lang
在 Windows 上：

从 UB Mannheim 的 Tesseract 下载并安装。

使用方法
1. 准备发票数据
将您的发票文本放在 data/generated_invoices.txt 中。每行应代表一个独立的发票。
2. 配置路径和参数
打开 scripts/train_tesseract_model.py，根据需要调整顶部的配置参数，如路径和字体名称。
3. 运行训练脚本
bash
Copy code
python scripts/train_tesseract_model.py
4. 监控训练过程
日志将同时输出到 logs/training.log 和控制台。
5. 获取训练好的模型
训练成功后，训练好的模型将位于 output/my_model.traineddata。
项目结构
bash
Copy code
tesseract-training/
├── data/
│   └── generated_invoices.txt        # 输入的发票数据
├── logs/
│   └── training.log                  # 日志文件
├── scripts/
│   └── train_tesseract_model.py       # 训练脚本
├── output/
│   └── my_model.traineddata           # 训练好的 Tesseract 模型
├── model/
│   ├── chi_sim.lstm                   # 提取的 LSTM 模型
│   └── my_model.checkpoint            # 检查点文件
├── .gitignore                         # Git 忽略文件
├── README.md                          # 项目文档
└── requirements.txt                   # Python 依赖（如果有）
日志记录
训练过程的日志同时记录到控制台和 logs/training.log。日志系统设计为适用于多进程环境，确保来自并行任务的日志能够正确记录而不会冲突。

清理临时文件
要删除训练过程中生成的临时文件，您可以在 scripts/train_tesseract_model.py 的 train_model() 函数中取消注释 clean_up() 调用：

python
Copy code
def train_model():
    generate_training_data()
    generate_lstmf_files()
    generate_lstmf_training_list()
    extract_lstm_from_traineddata()
    train_lstm()
    clean_up()  # 取消注释以启用清理
故障排除
缺少依赖：确保所有必需的工具（如 text2image、tesseract 等）已安装并且在系统的 PATH 中可访问。
字体问题：如果找不到指定字体，脚本将尝试查找并使用替代字体。确保您的系统已安装必要的字体。
权限错误：确保脚本具有在指定目录中读写的必要权限。
日志文件：检查 logs/training.log 以获取详细的错误信息和调试信息。
贡献指南
欢迎贡献！请为任何改进或错误修复提交 issue 或 pull request。

许可证
本项目采用 MIT 许可证。详见 LICENSE 文件。

其他详细信息
1. 配置 Git
在将项目上传到 GitHub 之前，请确保您的系统上已正确配置 Git：

bash
Copy code
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
2. 创建 .gitignore 文件
确保您有一个 .gitignore 文件，以排除不必要的文件被 Git 跟踪。项目中已包含一个示例 .gitignore：

gitignore
Copy code
# 日志文件
logs/
*.log

# 输出目录
output/

# 模型检查点
model/*.checkpoint

# 临时文件
*.tmp
*.temp

# Python 字节码
__pycache__/
*.pyc

# 操作系统生成的文件
.DS_Store
Thumbs.db
3. 推送到 GitHub
在设置好仓库并配置 Git 后，将您的项目推送到 GitHub：

bash
Copy code
git add .
git commit -m "初始提交：添加训练脚本和项目结构"
git remote add origin https://github.com/your_username/tesseract-training.git
git push -u origin main
将 https://github.com/your_username/tesseract-training.git 替换为您的实际仓库 URL。

4. 使用 SSH 与 GitHub（可选）
为了更安全和便捷的设置，建议使用 SSH 密钥与 GitHub 进行交互：

生成 SSH 密钥：

bash
Copy code
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"
将 SSH 密钥添加到 GitHub：

将 SSH 密钥复制到剪贴板：

bash
Copy code
cat ~/.ssh/id_rsa.pub
登录 GitHub，点击右上角头像，选择 Settings。

在左侧菜单中选择 SSH and GPG keys。

点击 New SSH key，填写标题并粘贴公钥内容，点击 Add SSH key。

验证 SSH 连接：

bash
Copy code
ssh -T git@github.com
您应该会看到类似以下的欢迎信息：

vbnet
Copy code
Hi your_username! You've successfully authenticated, but GitHub does not provide shell access.
使用 SSH URL 连接仓库：

在 GitHub 仓库页面，找到仓库的 SSH URL。例如：

scss
Copy code
git@github.com:your_username/tesseract-training.git
将本地仓库连接到 GitHub 仓库：

bash
Copy code
git remote set-url origin git@github.com:your_username/tesseract-training.git
git push -u origin main
联系方式
如有任何问题或需要支持，请随时在 GitHub 仓库 上提交 issue，或通过 your.email@example.com 联系我们。


