# 多格式文档审批、图章与手写签名综合工作台 (DocStampLab) v1.0.0

纯前端高性能、无服务器依赖的多格式文档（PDF / Word / 图片）审批签批与图章印章渲染桌面/Web 工作台。

## ✨ 核心特性

- **多格式文档解析**：
  - 原生支持 PDF 矢量解析渲染与多页翻页浏览（基于 Mozilla PDF.js 核心）
  - 支持 Word 文档 (.docx) 快速解析排版（基于 Mammoth.js）
  - 支持常用图片格式 (.png / .jpg / .jpeg)
- **参数化极坐标图章设计引擎**：
  - 顶部弧形文字排布（支持简化宋体、黑体、楷体、仿宋等多种字体）
  - 弧形字号 `6px ~ 96px` 超宽范围自由调节，防裁切离屏自适应
  - 底部辅助文字（支持向心直立 / 环绕排布、旋转偏角、排布半径调节）
  - 中心几何多角星定制（外径、角数、Y 轴偏置）
  - 双圈/单圈边框与像素脱墨磨损质感模拟
- **手写签名板 (Signature Pad)**：
  - 基于矢量点阵重构，笔触粗细（`1px ~ 18px`）与笔迹颜色（碳素黑/墨水蓝/朱砂红及自定义拾色）实时重绘
  - 智能边缘裁剪与半透明渗透印泥融合
- **双图层独立拖拽与融合**：
  - 支持图章与签名双图层独立拖拽、缩放、旋转
  - 真实物理图层色彩混合（正片叠底 Multiply、颜色加深 Color Burn、暗部优先 Darken 等）
  - 支持快捷一键归位与默认范本快速重置
- **多端与离线高可用**：
  - 移动端 / 手机浏览器自适应与高精度触控映射
  - 纯离线依赖打包，无外网亦可顺畅运行
  - 导出自动生成规范防覆盖时间戳文件名

## 🚀 部署与运行

### 1. 静态 Web 端（Cloudflare Pages / Vercel / GitHub Pages）
根目录下已包含 `index.html` 以及离线解析依赖，构建输出目录设置为 `/` 或 `public` 即可直接上线。

### 2. Windows 桌面客户端
本项目支持使用 PyInstaller 打包为独立的 Windows 单文件免安装客户端：
```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "DocStampLab" --add-data "integrated_doc_stamplab.html;." --add-data "pdf.min.js;." --add-data "mammoth.browser.min.js;." app_launcher.py
```
打包产物位于 `dist/DocStampLab.exe`。

## ⚠️ 免责声明
本系统仅用于内部流转审批、办公电子签批算法研究与技术原型演示。严禁用于任何伪造国家机关公章、企事业单位印章等违法违规行为。
