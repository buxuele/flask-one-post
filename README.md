# Zenith Social Publisher

基于 Flask 的社交媒体内容编辑器，支持一键发布到 X (Twitter)。

## 功能

- 文本编辑（140 字符限制）
- 图片上传、预览和拖拽排序
- AI 话题标签建议 (Groq)
- 实时发布进度（悬浮抽屉）
- 发布历史记录（瀑布流）

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

1. 在编辑器中输入内容（支持 140 字符）
2. 点击"添加图片"上传图片（支持拖拽排序）
3. 点击"AI 润色"自动生成话题标签
4. 点击"立即发布"

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
│   └── history.html            # 历史记录
└── static/uploads/             # 图片上传目录
```

## 依赖

- Flask 2.3.3
- Flask-SQLAlchemy 3.0.5
- groq 0.20.0
- xdk 0.5.0
- python-dotenv 1.2.1

## License

MIT
# flask-one-post
