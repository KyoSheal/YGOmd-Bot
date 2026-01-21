# Tesseract OCR 安装指南

Tesseract OCR 是卡片文字识别的核心组件，必须单独安装。

## Windows系统安装

### 方法1：使用安装包（推荐）

1. **下载安装包**
   - 访问: https://github.com/UB-Mannheim/tesseract/wiki
   - 下载最新的 `tesseract-ocr-w64-setup-v5.x.x.exe` (64位)

2. **安装**
   - 双击运行安装程序
   - **重要**: 安装时勾选 "Additional language data" 选项
   - 选择中文简体 (Chinese Simplified) 语言包
   - 记住安装路径，默认是：`C:\Program Files\Tesseract-OCR`

3. **配置环境变量**
   - 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
   - 在"系统变量"中找到"Path"
   - 点击"编辑" → "新建"
   - 添加：`C:\Program Files\Tesseract-OCR`
   - 确定保存

4. **验证安装**
   打开新的命令行窗口，运行：
   ```bash
   tesseract --version
   ```
   应该看到版本信息（如 tesseract v5.x.x）

### 方法2：使用包管理器

如果你安装了 Chocolatey：
```bash
choco install tesseract
```

## 配置YGO Bot

安装完成后，有两种方式让bot找到Tesseract：

### 选项1：使用环境变量（推荐）
已添加到PATH，无需额外配置

### 选项2：在代码中指定路径
如果没有添加到PATH，需要修改配置。

创建文件 `config/tesseract.yaml`:
```yaml
tesseract_cmd: "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
tessdata_dir: "C:\\Program Files\\Tesseract-OCR\\tessdata"
```

## macOS系统安装

使用Homebrew：
```bash
brew install tesseract
brew install tesseract-lang  # 语言包
```

## Linux系统安装

Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-chi-sim  # 中文简体
```

Fedora/RHEL:
```bash
sudo dnf install tesseract
sudo dnf install tesseract-langpack-chi_sim
```

## 验证完整安装

运行检查脚本：
```bash
python setup_check.py
```

如果看到"✅ Tesseract已安装"，说明配置成功！

## 常见问题

### Q: 运行时提示找不到tesseract

**A**: 确保已添加到PATH环境变量，或重启命令行窗口

### Q: 识别中文时出错

**A**: 确保安装时选择了中文语言包，或手动下载：
- 下载 `chi_sim.traineddata` 从 https://github.com/tesseract-ocr/tessdata
- 放到 `C:\Program Files\Tesseract-OCR\tessdata\`

### Q: 仍然无法识别

**A**: 在代码中明确指定路径（见上方选项2）

## 下一步

安装完成后，再次运行：
```bash
python setup_check.py
```

确认所有检查通过后，可以开始使用bot：
```bash
python main.py
```
