# AI 助农 · 容器镜像
# 构建： docker build -t ai-nong .
# 运行： docker run -d -p 8770:8770 --env-file .env -v $PWD/data:/app/data ai-nong
#   -v 把 data/ 挂成持久卷（SQLite 库 + 上传图片 + 语料），容器重建数据不丢。
#   密钥通过 --env-file .env 注入；config.example.json 的 ${ENV} 会自动展开。

FROM python:3.11-slim

WORKDIR /app

# 系统依赖（如需 PDF/图像处理可在此加；当前保持精简）
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 注：当前用关键词检索，未用 chromadb。若想精简镜像，可先从 requirements 去掉 chromadb。
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8770

# 0.0.0.0 让容器外可访问；端口与 config/server 一致
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8770"]
