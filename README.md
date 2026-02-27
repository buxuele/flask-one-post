# Echo

简洁的社交媒体内容编辑器，一键发布到 X (Twitter) 和知乎。

## 功能

- 文本编辑（140 字符限制）
- 图片上传、预览和拖拽排序（自动压缩至 1080p）
- AI 话题标签建议 (Groq)
- 实时发布进度（悬浮抽屉）
- 草稿自动保存（本地存储，支持多草稿管理）
- 键盘快捷键（Ctrl+Enter 发布、Ctrl+S 保存、Ctrl+L AI润色、Ctrl+P 预览）
- 发布预览（模拟 X/知乎 显示效果，检查字符限制）
- 定时发布（排期列表，后台自动执行）
- 发布历史记录（瀑布流，支持单条删除、批量删除、按平台/日期筛选）
- 本地图标资源（无需联网加载）
- 内容质量自检提示（可拖拽悬浮面板）
- 一键发布到 X (Twitter) 和知乎

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv venv
```

### 2. 激活虚拟环境

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `.env` 文件：

```env
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_secret_key

# X (Twitter) API
X_API_KEY=your_api_key
X_API_KEY_SECRET=your_api_key_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

### 5. 运行应用

```bash
python app.py
```

访问 http://localhost:5000

## 使用方法

### 基本发布
1. 在编辑器中输入内容（支持 140 字符）
2. 点击"添加图片"上传图片（支持拖拽排序）
3. 点击"AI 润色"自动生成话题标签
4. 点击"立即发布"

### 草稿管理
- 内容会自动保存到草稿箱
- 可创建多个草稿并切换
- 点击"新建"按钮创建新草稿
- 发布后自动清除当前草稿

### 键盘快捷键
- `Ctrl/Cmd + Enter` - 立即发布
- `Ctrl/Cmd + S` - 保存草稿
- `Ctrl/Cmd + L` - AI 润色
- `Ctrl/Cmd + P` - 预览

### 定时发布
1. 编辑好内容和图片
2. 点击"定时发布"按钮
3. 选择发布时间
4. 点击"确认定时发布"
5. 在"排期"页面查看和管理待发布的任务

### 历史记录管理
- 按平台筛选（X/知乎）
- 按日期筛选（今天/本周/本月）
- 点击"多选"按钮进入批量模式
- 支持批量删除历史记录

## 项目结构

```
flask-one-post/
├── app.py                      # Flask 主应用
├── models.py                   # 数据库模型
├── requirements.txt            # 依赖列表
├── .env                        # 环境变量（需创建）
├── .gitignore                  # Git 忽略规则
├── services/
│   ├── __init__.py
│   ├── gemini_service.py       # AI 服务
│   └── publisher_service.py    # 发布服务
├── templates/
│   ├── base.html               # 基础模板
│   ├── index.html              # 发布页面
│   ├── history.html            # 历史记录
│   ├── scheduled.html          # 排期列表
│   └── about.html              # 关于页面
├── static/
│   ├── uploads/                # 图片上传目录
│   ├── icons/                  # 本地图标资源
│   └── favicon.svg             # 网站图标
└── instance/posts.db           # SQLite 数据库
```

## 关于

Echo 由以下开发者创建：

- **X (Twitter)**: [@fanchuangwater](https://x.com/fanchuangwater)
- **GitHub**: [buxuele](https://github.com/buxuele)
- **知乎**: [fanchaung](https://www.zhihu.com/people/fanchaung)

访问应用内的「关于」页面查看更多详情。

## 依赖

- Flask 2.3.3
- Flask-SQLAlchemy 3.0.5
- groq 0.20.0
- xdk 0.5.0
- python-dotenv 1.2.1
- Pillow 11.3.0
- playwright 1.54.0

## License

MIT
# flask-one-post
