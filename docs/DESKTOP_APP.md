# RAG 知识库问答系统 - 桌面应用

本文档介绍如何将 RAG 知识库问答系统打包为独立的桌面应用程序。

## 方案对比

| 方案 | 技术栈 | 包大小 | 启动速度 | 跨平台 | 开发难度 |
|------|--------|--------|----------|--------|----------|
| **方案A: PyInstaller** | Python + PyInstaller | ~500MB | 较慢 | Windows/Mac/Linux | ⭐⭐ |
| **方案B: Tauri** | Vue 3 + Rust + Tauri | ~30MB | 很快 | Windows/Mac/Linux | ⭐⭐⭐⭐ |

## 方案A: PyInstaller 打包（快速方案）

### 环境要求
- Python 3.10+
- PyInstaller 6.0+

### 打包步骤

```bash
# 1. 安装 PyInstaller
pip install pyinstaller pyinstaller-versionfile

# 2. 执行打包
cd build
build_windows.bat

# 3. 输出文件
# dist/RAGKnowledgeBase.exe
```

### 手动打包

```bash
pyinstaller build/rag_app.spec --clean --noconfirm
```

### 打包后运行

双击 `RAGKnowledgeBase.exe` 或在命令行运行：

```bash
# 启动 Gradio UI
RAGKnowledgeBase.exe --ui

# 启动 FastAPI 服务
RAGKnowledgeBase.exe --api --port 8000

# 查看帮助
RAGKnowledgeBase.exe --help
```

### 注意事项

1. **Ollama 服务**：打包后的程序仍需要本地运行 Ollama 服务
2. **文件大小**：由于依赖较多，打包文件约 500MB
3. **首次启动**：首次启动可能较慢（解压资源）

---

## 方案B: Tauri 桌面应用（专业方案）

### 环境要求

- Node.js 18+
- Rust 1.70+
- pnpm 或 npm

### 安装 Rust

```bash
# Windows
winget install Rustlang.Rustup

# 或访问 https://rustup.rs
```

### 开发模式

```bash
cd desktop

# 安装依赖
npm install

# 开发模式运行
npm run tauri:dev
```

### 生产构建

```bash
cd desktop

# 构建所有平台
npm run tauri:build

# 输出位置
# Windows: src-tauri/target/release/bundle/msi/
# macOS: src-tauri/target/release/bundle/dmg/
# Linux: src-tauri/target/release/bundle/deb/
```

### 项目结构

```
desktop/
├── src/                    # Vue 前端
│   ├── views/              # 页面组件
│   │   ├── ChatView.vue    # 智能问答
│   │   ├── DocumentsView.vue # 知识库管理
│   │   ├── InterviewView.vue # 模拟面试
│   │   └── SettingsView.vue  # 系统设置
│   ├── layouts/            # 布局组件
│   ├── router/             # 路由配置
│   └── styles/             # 样式文件
├── src-tauri/              # Rust 后端
│   ├── src/
│   │   ├── main.rs         # 入口
│   │   ├── commands/       # Tauri 命令
│   │   ├── models/         # 数据模型
│   │   └── rag/            # RAG 核心逻辑
│   └── tauri.conf.json     # Tauri 配置
└── package.json
```

### 功能特性

- ✅ 智能问答（支持 Markdown 渲染）
- ✅ 知识库管理（文档上传/删除）
- ✅ 模拟面试（题库/评分/报告）
- ✅ 系统设置（模型配置/缓存管理）
- ✅ 原生系统集成（文件对话框/通知）

---

## 对比总结

### 选择方案A（PyInstaller）如果：
- 需要快速打包发布
- 团队熟悉 Python
- 对包大小不敏感
- 需要保持现有 Gradio UI

### 选择方案B（Tauri）如果：
- 追求专业的桌面体验
- 需要小巧的安装包
- 需要更好的性能
- 愿意投入开发时间

---

## 分发建议

### 内部分发
- 使用方案A，快速迭代
- 提供 Ollama 一键安装脚本

### 商业分发
- 使用方案B，更专业
- 添加自动更新功能
- 提供安装向导

---

## 常见问题

### Q: 打包后无法连接 Ollama？
A: 确保 Ollama 服务已启动，检查防火墙设置

### Q: PyInstaller 打包文件过大？
A: 可以尝试：
1. 排除不必要的模块（在 spec 文件中配置 excludes）
2. 使用 UPX 压缩
3. 考虑使用 Tauri 方案

### Q: Tauri 构建失败？
A: 检查：
1. Rust 版本是否 >= 1.70
2. Windows 构建工具是否完整
3. WebView2 是否已安装（Windows）

---

## 相关链接

- [PyInstaller 文档](https://pyinstaller.org/)
- [Tauri 文档](https://tauri.app/)
- [Vue 3 文档](https://vuejs.org/)
