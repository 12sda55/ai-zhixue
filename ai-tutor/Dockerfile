FROM python:3.11-slim

WORKDIR /app

# Manim 系统依赖（Cairo + Pango + ffmpeg + 中文字体）
# 注意：不装 texlive（项目禁用 Tex/MathTex，改用 Text/MarkupText），避免镜像过大
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# ★ 创建字体别名：让 "Microsoft YaHei" 映射到 "Noto Sans CJK SC"
# 原因：代码中 Manim prompt 和字幕样式硬编码了 font="Microsoft YaHei"
# Linux 容器没有 Microsoft YaHei，需要 fontconfig 别名让 Manim/Pango 能找到中文字体
RUN mkdir -p /etc/fonts/conf.d && \
    echo '<?xml version="1.0" encoding="UTF-8"?>' > /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '<fontconfig>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '  <alias><family>Microsoft YaHei</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '  <alias><family>微软雅黑</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '  <alias><family>SimHei</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '  <alias><family>SimSun</family><prefer><family>Noto Sans CJK SC</family></prefer></alias>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    echo '</fontconfig>' >> /etc/fonts/conf.d/99-microsoft-yahei-alias.conf && \
    fc-cache -f

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 ChromaDB embedding 模型（独立 layer，代码改动不触发重新下载）
#
# 为什么不能用 chromadb 默认下载：
#   chromadb 0.4.22 ONNXMiniLM_L6_V2 默认从 S3 下载 onnx.tar.gz:
#     https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz
#   该 S3 在国内访问极慢（Sealos pod 实测 40k/s，83MB 下载 6+ 小时）
#   Sealos pod 出口无法走代理，导致容器一直卡在下载
#
# 解决方案：
#   国内 HuggingFace 镜像 hf-mirror.com 上的
#   sentence-transformers/all-MiniLM-L6-v2 仓库内的 onnx/model.onnx
#   与 chromadb 期望的 model.onnx 字节完全一致 (90405214 bytes)
#   构建时用 Python urllib 把 6 个文件放到 chromadb 默认查找路径
#   /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/
#   chromadb 启动时发现文件全部存在则跳过下载
ENV HF_ENDPOINT=https://hf-mirror.com
COPY scripts/download_chromadb_model.py /tmp/download_chromadb_model.py
RUN python /tmp/download_chromadb_model.py || \
    echo "[WARN] ChromaDB model pre-download failed, will fall back to slow S3 download at startup"

# 应用代码
COPY . .

# 持久化目录
RUN mkdir -p data/videos data/chroma_db

# 端口
ENV PORT=8000
EXPOSE 8000

# 直接用 uvicorn 启动
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
