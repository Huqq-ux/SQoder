# SQoder

一个强大的 AI 编程助手，集成了 SOP（标准操作流程）执行能力，支持文件操作、PowerShell 工具调用、知识库检索等功能。

## 🚀 功能特点

- **智能代码助手**：基于 DeepSeek 模型，提供专业的编程支持
- **SOP 执行能力**：支持标准操作流程的执行和管理
- **文件操作工具**：读取、写入、复制、移动、删除文件
- **PowerShell 工具**：执行 PowerShell 命令，管理 PowerShell 进程
- **知识库检索**：基于 FAISS 向量数据库的文档检索
- **Streamlit Web UI**：提供友好的 Web 界面
- **终端模式**：支持命令行交互

## 📦 安装步骤

### 1. 环境要求
- Python 3.14+
- pip 或 uv 包管理器

### 2. 克隆仓库
```bash
git clone https://github.com/Huqq-ux/SQoder.git
cd SQoder
```

### 3. 安装依赖
使用 uv（推荐）：
```bash
uv install
```

或使用 pip：
```bash
pip install -e .
```

### 4. 配置环境变量
需要设置 `DASHSCOPE_API_KEY` 环境变量（用于调用 DeepSeek 模型）：

**Windows**：
```powershell
set DASHSCOPE_API_KEY=your_api_key
```

**Linux/macOS**：
```bash
export DASHSCOPE_API_KEY=your_api_key
```

## 🎯 使用方法

### 1. Streamlit Web UI
```bash
streamlit run Coder/ui/streamlit_app.py
```

### 2. 终端模式
```bash
python main.py
```

### 3. 示例用法

**查询可用工具**：
```
用户: 你有哪些可用工具？
```

**文件操作**：
```
用户: 读取当前目录下的 README.md 文件
```

**执行 PowerShell 命令**：
```
用户: 执行 PowerShell 命令：Get-Process | Select-Object Name, CPU
```

**SOP 执行**：
```
用户: 执行 Python 应用部署流程
```

## 📁 项目结构

```
SQoder/
├── Coder/
│   ├── agent/          # 智能代理实现
│   ├── knowledge/      # 知识库和检索
│   ├── model/          # 模型配置
│   ├── prompts/        # 提示词模板
│   ├── sop/            # SOP 执行系统
│   ├── tools/          # 工具集
│   ├── ui/             # Web 界面
│   ├── MCP/            # 多通道协议工具
│   └── util/           # 工具函数
├── tests/              # 测试文件
├── pyproject.toml      # 项目配置
├── uv.lock             # 依赖锁定
└── README.md           # 项目文档
```

## 🔧 工具列表

### 文件操作工具
- `read_file` - 读取文件内容
- `write_file` - 写入/创建文件
- `copy_file` - 复制文件
- `move_file` - 移动/重命名文件
- `file_delete` - 删除文件
- `file_search` - 按模式搜索文件
- `list_directory` - 列出目录内容

### PowerShell 工具
- `get_powershell_processes` - 获取所有 PowerShell 进程
- `close_powershell_processes` - 关闭 PowerShell 进程
- `open_new_powershell` - 打开新的 PowerShell 窗口
- `run_powershell_script` - 执行 PowerShell 命令

## 📚 知识库

项目包含以下 SOP 文档：
- Python 应用部署流程
- 系统故障排查流程

知识库会自动索引到 FAISS 向量数据库，支持语义检索。

## 🔒 安全注意事项

- PowerShell 工具会拦截危险命令模式，确保安全执行
- 所有文件操作限于项目目录内
- 建议在受控环境中使用

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目！

## 📄 许可证

本项目采用 MIT 许可证。

## 📞 联系方式

- GitHub: [Huqq-ux/SQoder](https://github.com/Huqq-ux/SQoder)
- 邮箱: sqoder@example.com