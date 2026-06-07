# 云部署指南（让别人也能用）

> 本指南用 Docker + Caddy 把产品部署到云服务器，拿到一个 **https 域名**给果农用。
> 比内网穿透更适合"真用"：稳定、不依赖家里 PC、ASR/PWA 都能用。

---

## 0. 上公网前必读：安全检查清单 ⚠️

| 项 | 状态 / 要做的 |
|---|---|
| 登录隔离 | ✅ 已有：地块/日志/账本/通讯录需登录，各用户数据互不可见 |
| 密钥安全 | ✅ 用环境变量注入，不进镜像/Git |
| **AI 接口防滥用** | ⚠️ 诊断/问答当前**可匿名调用**→ 公网上任何人能烧你的 AI 额度。**上公网前建议二选一**：① 给诊断/问答也加"需登录"；② 或在 Caddy 层加全站 Basic Auth/限流。 |
| HTTPS | ✅ Caddy 自动签证书（需域名） |
| 数据备份 | 定时复制 `data/app.db` 和 `data/images/`（见下） |
| 备案 | 国内服务器用域名跑 80/443 需 **ICP 备案**；香港/海外免备案 |

---

## 1. 选服务器（回顾）

- **快速上线**：香港/海外轻量服务器 + 域名 → **免备案**，1 小时能用。延迟略高但够用。
- **长期最优**：国内轻量服务器（腾讯云/阿里云）+ 域名 + **ICP 备案**（约 1-2 周）→ 延迟最低。
- 建议：**先香港上线拿反馈，国内备案并行办，办好再迁。**

---

## 2. 部署步骤（Docker）

```bash
# 1) 服务器装 Docker（略）。拉代码：
git clone git@github.com:yydshly/ai_for_mytown.git
cd ai_for_mytown

# 2) 配密钥
cp .env.example .env
vim .env        # 填 MINIMAX_API_KEY 等

# 3) 构建 + 运行（data 挂成持久卷，重建不丢数据）
docker build -t ai-nong .
docker run -d --name ai-nong --restart unless-stopped \
  -p 127.0.0.1:8770:8770 \
  --env-file .env \
  -v $PWD/data:/app/data \
  ai-nong

# 4) 灌入资料（首次会自动灌种子；有真实资料时把文件放进 data/corpus/<crop>/ 再跑）
docker exec ai-nong python scripts/ingest_docs.py
```

> 注：定时推送需要 apscheduler（已在 requirements，镜像里有）。父母关注「方糖」服务号取 SendKey
> 填进 `.env` 的 `SERVERCHAN_KEY`，并把 config 的 `notify.channel` 改成 `serverchan` 才会真正推送。

## 3. Caddy 自动 HTTPS

```bash
# 把 Caddyfile 里的 your.domain.com 换成你的域名（先解析到服务器公网 IP）
caddy run --config ./Caddyfile
# 之后访问 https://your.domain.com 即可；手机上语音/添加到主屏幕都可用。
```

## 4. 首次进入

- 打开 https 域名 → **第一个注册的账号自动成为管理员**（你）。
- 管理员能在"我"里看到 👍👎 反馈、上传病虫参考图。
- 让父母/果农各自注册自己的账号（数据互不可见）。

## 5. 数据备份（重要）

```bash
# 简单粗暴：定时复制（crontab 每天一次）
cp data/app.db   backup/app_$(date +%F).db
tar czf backup/images_$(date +%F).tgz data/images
```

## 6. 更新版本

```bash
git pull
docker build -t ai-nong .
docker rm -f ai-nong
docker run -d ... （同上）   # data 卷不动，数据保留
```

---

## 部署后回到正题

部署只是手段，目的是**让真实果农能用上、好拿反馈**。部署完请走
[docs/deploy-mobile.md](deploy-mobile.md) 的"父母走查清单"和
[docs/gtm/用户访谈提纲.md](gtm/用户访谈提纲.md)。
