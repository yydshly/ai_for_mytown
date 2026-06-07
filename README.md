# AI 助农（陕西桃树 MVP）

帮助家在陕西、以桃树种植为主的果农父母，借助 AI 完成全流程指导：拍照病虫害诊断、按物候期的农事日历、天气与灾害预警、自然语言（含语音）问答。

形态：**Web 优先**（移动端 H5，父母在手机微信或浏览器扫码即用），后期再考虑微信小程序/App。

定位：**这不是农业 SaaS，是"子女远程协助父母种地"的家庭产品**——子女配置兜底，父母被动接收推送与语音。

## 文档（SSOT — 开发前先读）

所有产品范围、知识规则、架构决策、风险都以 `docs/` 为单一信息源，改范围先改文档再改代码：

- [docs/product-ia.md](docs/product-ia.md) — 模块地图 + 移动端 IA + 双角色 + P0 范围
- [docs/knowledge-governance.md](docs/knowledge-governance.md) — 三层知识来源 + 校验 + 溯源 schema + **用药硬规则**
- [docs/adr.md](docs/adr.md) — 架构决策记录（部署/存储/账户/多作物/语音/方言…）
- [docs/risks.md](docs/risks.md) — 风险登记（用药错误、漏报、单点维护、成本…）

完整初版方案另见计划文件：`C:\Users\yun68\.claude\plans\ai-wiggly-lerdorf.md`。

---

## 当前状态：Phase 2（拍照诊断闭环已通）

Phase 1（骨架 + 知识库种子）✅
- FastAPI 后端骨架（routes/services/infra 分层）
- AI provider 抽象（复制 `src/ai/`）：MiniMax / MiMo / minimax_anthropic
- 农业领域任务函数 `src/ai/tasks.py`：诊断 / 日历 / 预警 / 问答
- 关中桃树物候期 + 农事日历种子数据，物候期推算服务
- 移动端首页线框壳（适老化，接真实日历数据）
- 路由 `/api/health`、`/api/calendar/today`、`/api/calendar/all`

Phase 2（拍照诊断）✅
- 病虫害知识库 `peach_pests.jsonl`（6 种关中常见病虫，带溯源元数据）
- **已登记农药表** `pesticide_kb.jsonl`（verified=false，遵 ADR-010 用药护栏）
- `knowledge_base.py` 零依赖关键词检索（语料增大后可换 chromadb）
- `diagnose.py` 诊断编排：识别 → 对齐知识 → 用药护栏 → 结构化结果
- `POST /api/diagnose`（multipart，`?mock=1` 可无 key 联调，默认不留存图片）
- 前端拍照 → 上传 → 结果浮层（识别/农业措施/用药护栏/免责）

> **用药护栏**：诊断只给病虫识别和农业/物理措施；化学用药一律查表，未经
> 农技审核的不展示药剂剂量，导向农技员（详见 docs/knowledge-governance.md §4）。

Phase 3a（语音播报）✅
- AI 配置全部打通：文字=minimax(MiniMax-Text-01)、vision=minimax(abab7-chat-preview)、
  TTS=mimo(Token Plan 专属地址)。详见 docs/adr.md ADR-008。
- `tts_service.py` 语音合成 + 磁盘缓存（同文本秒回，省成本）
- `POST /api/tts`、`GET /api/tts/available`
- 前端"🔊 听"按钮：物候概述、每条农事、拍照诊断结果均可一键朗读（适老化关键）

Phase 3b（天气灾害预警）✅
- `disaster_playbooks.json` 五类灾害应对手册：霜冻/冰雹/大风/高温日灼/连阴雨（来之前/发生时/过后补救）
- `weather.py` 天气客户端：未配 key 走 mock（`?scenario=` 注入场景），配 key 走和风天气
- `alerts.py` **硬规则引擎**（R-02 不依赖 LLM）：天气阈值 × 当前物候期触发，物候不匹配自动降级
- `GET /api/alerts?scenario=`，前端预警横幅（severe 红/warning 橙）+ 详情浮层 + 听
- 演示：浏览器访问 `/?scenario=frost|hail|wind|heat|rain` 看不同预警

> 申请和风天气 key 后填入 `config.json` 的 `weather.api_key` 即走真实天气。

Phase 3c（语音问答）✅
- `chat_service.py` 问答 + RAG（病虫害检索 + 当前物候期 + 本周农事 作为上下文）
- `POST /api/chat`（带对话历史），用药相关遵 prompt 护栏
- 前端"问问 AI"语音浮层：浏览器 Web Speech API 语音输入（ADR-006）+ 打字兜底，
  回答自动 TTS 朗读，保留对话历史
- 实测：问"现在该施什么肥" → 答案精准命中当前物候期 + 农事数据

### 四大核心 AI 能力已全部打通 🎉
| 能力 | 入口 | 状态 |
|---|---|---|
| 拍照诊断病虫害 | 首页"拍照诊断" | ✅（真实 vision + 用药护栏）|
| 物候农事日历 | 首页"今日农事" | ✅ |
| 天气灾害预警 | 首页预警横幅 | ✅（硬规则）|
| 语音/文字问答 | 首页"问问 AI" | ✅（RAG + 朗读）|

真机就绪（PWA + 部署）✅
- PWA：`manifest.webmanifest` + 桃图标 + `sw.js` 离线壳，可"添加到主屏幕"像 App 打开
- 服务启动打印可访问地址；`--host 0.0.0.0` 支持局域网直连
- **部署与父母走查清单见 [docs/deploy-mobile.md](docs/deploy-mobile.md)**

> ⚠️ 手机上**语音输入(ASR)和"添加到主屏幕"需要 HTTPS**，纯局域网 http 不行。
> 用带 https 的内网穿透（cpolar 等）一并解决可达性与安全环境。

Phase 16-17（多用户 + 数据隔离 · 产品化地基）✅
- **身份层**：users/sessions 表，pbkdf2 加盐哈希 + token 会话；register/login/me/logout；身份与业务解耦（日后可插微信登录）
- **数据隔离**：plots/contacts 加 owner_id，仓储全部按 owner 过滤；日志/账本通过地块归属继承；删除走 owner 校验子查询
- **鉴权**：infra/auth_dep 依赖；plots/logs/账本/contacts 需登录，越权返回 404；诊断/问答可匿名，地块上下文仅在登录且拥有时注入；定时推送走 list_all（系统视角）
- **前端**：全屏登录/注册门 + fetch 自动带 token + 退出登录；"我"显示当前账号
- 验证：匿名→401、A 的地块对 B 不可见(404)、跨用户隔离单测；38 测试通过

Phase 12（"我"标签页 + 通讯录 F4）✅
- 联系人实体：domain/contact + repositories/contact_repository + routes/contact_routes（CRUD）
- "我"标签：**通讯录一键拨号**（tel: 链接，农技员/子女/邻居）—— 老人无障碍兜底（AI 答不出→直接打电话）
- 快捷入口（图鉴/园子）+ 关于（推送/AI 状态 + 免责声明）

Phase 11（诊断安全上下文）✅
- 拍照诊断带当前地块 plot_id，结果显示"这块地距上次打药 N 天，注意安全间隔期"（农事日志反哺用药安全）

Phase 10（病虫害图鉴 E3）✅
- KnowledgeBase.list_all + GET /api/pests；首页"📖 病虫害图鉴"可展开 + 听，父母可主动查病

Phase 9（闭环整合）✅
- 一键"记一笔"（诊断/日历→当前园子）；首页"距上次打药 N 天"；GET /api/plots/{id}/summary

Phase 8（回归测试 pytest）✅
- `tests/` 28+ 个用例，覆盖纯逻辑层与仓储层（分层让各层可独立单测）：
  物候期（跨年休眠/多作物差异）、作物注册表（解析/回退）、知识库检索+**用药护栏**、
  灾害规则（霜冻按物候分级/冰雹/措施）、地块/日志/去重仓储（含级联删除）、诊断 mock
- 仓储测试用 tmp_path 独立 SQLite，不碰真实数据；异步用例用 asyncio.run（免 pytest-asyncio）
- 运行：`python -m pytest`（见 pytest.ini）

Phase 7（主动推送 F1 · 老人产品命脉）✅
- **推送通道抽象** `services/notify/`（base/factory/log/serverchan），模式同 AI provider
  - `log` 通道默认、免配置（写日志）；`serverchan`（方糖）推到父母微信
- 去重表 `notifications_sent`（同地块/同灾害/同天只推一次，防刷屏）
- `alert_scheduler.py`：`run_alert_check` 遍历地块→按作物/位置评估→推新预警；
  `AlertScheduler` 用 APScheduler 定时（默认 6/12/18 时），随应用启停、缺库优雅降级
- `routes/notify_routes.py`：`GET /api/notify/status`、`POST /api/notify/check-now?scenario=&force=`
- 验证：check-now 推送 severe 预警 + 二次去重；推送文案即父母微信所见
- 启用真实微信推送：① `pip install apscheduler` ② 父母关注「方糖」服务号取 SendKey
  ③ config.notify.channel 改 serverchan 并填 sendkey

Phase 6（农事日志 D2）✅
- `domain/activity_log.py` + `repositories/activity_log_repository.py`（复用 repository 分层）
- `activity_logs` 表（外键→plots，**级联删除**）；`routes/log_routes.py`
  `GET/POST /api/plots/{id}/logs`、`DELETE /api/logs/{id}`、`GET /api/log-categories`
- 前端"我的园子→农事记录"：按地块记录施肥/打药/修剪等，倒序列表 + 记一笔
- 价值：构成"建议→执行→记录→复盘"闭环，是知识沉淀（L3）与安全间隔期计算的数据源
- `latest_by_category` 已备好（供后续"距上次打药N天"提示）

Phase 5（持久化 + 地块档案 D1）✅
- **SQLite 持久化层**（ADR-002）：`infra/db.py`（连接/schema/迁移），数据在 `data/app.db`（gitignore）
- **新增 `repositories/` 数据访问层**：SQL 隔离在此，routes/services 不直接写 SQL
- `domain/plot.py` 地块模型 + `repositories/plot_repository.py` CRUD
- `routes/plot_routes.py`：`GET/POST/PUT/DELETE /api/plots`，crop 经注册表校验
- 前端"我的园子"：增删改地块、设为当前；**当前地块驱动首页作物**，经纬度喂给天气预警
- 验证：CRUD + 重启持久化 + 非法作物拒绝 + 前端"设为当前→首页切作物"全通

Phase 4（多作物架构）✅
- 知识按作物分目录 `data/knowledge/<crop>/`，`crops.json` 注册表
- `CropRegistry`（domain）+ `KnowledgeManager`（按作物缓存）；所有接口支持 `?crop=`
- 已加**苹果**验证可扩展：加作物 = 丢数据文件夹 + 注册一行，零业务代码改动
- 前端顶部作物切换（桃/苹果），选择持久化；详见 docs/adr.md ADR-011
- 扩展梨/樱桃：建 `data/knowledge/<id>/` + 在 crops.json 登记即可

### 下一步（真机验证后按需扩展）
- [ ] 跑 docs/deploy-mobile.md：穿透部署 → 本人扮父母走一遍 → 记录卡点
- [ ] 主动推送（微信 Server酱）：预警主动找父母（F1，老人产品命脉）
- [ ] 双账户（父母/子女）+ 地块档案 D1
- [ ] 申请和风天气 key / 找农技员校对知识库
- [ ] Phase 3：天气 API + 灾害预警（硬规则）+ 语音问答（ASR→chat→TTS）
- [ ] Phase 4：父母实测 → 字体/按钮/语速优化 → 扩展苹果/梨/樱桃

---

## 目录结构

```
server.py                      入口装配
config/                        config.example.json（提交）/ config.json（gitignore）
data/
  knowledge/
    crops.json                 作物注册表
    <crop>/                    每作物：phenology/calendar/pests/pesticide/playbooks
  app.db                       SQLite（地块等，gitignore）
src/ai/                        provider 抽象 + 任务函数
src/backend/
  app_context.py               AppContext 装配（crops/knowledge/db）
  routes/                      HTTP 薄层（按职责拆分，每个 register(app, ctx)）
  services/                    编排（diagnose/chat/tts/weather/alerts/knowledge_manager）
  repositories/                数据访问层（SQL 隔离，如 plot_repository）
  domain/                      纯模型与规则（crops/plot/app_metadata）
  infra/                       基础设施（db/logging/safeio）
```

> 分层原则：routes(HTTP) → services(编排) → repositories(数据) → infra；domain 为无 IO 的纯模型。
> 新作物 = 加 `data/knowledge/<id>/` + crops.json 一行；新实体 = domain + repository + routes 各一。

---

## 安装与启动

```powershell
python -m pip install -r requirements.txt

# 复制配置模板，填入 API key（或用环境变量）
copy config\config.example.json config\config.json

# 启动开发服务
python server.py
# → http://127.0.0.1:8770/api/health
# → http://127.0.0.1:8770/api/calendar/today
# → http://127.0.0.1:8770/docs   （自动 Swagger）
```

## 配置 AI（推荐：直接改配置文件）

把 key 直接粘进 `config/config.json`（已在 .gitignore，不进 Git/发布包）：

```jsonc
"ai": {
  "active": "minimax",            // 文字模型（原生 minimax，快、即出正文）
  "vision_provider": "minimax",   // 拍照诊断
  "tts_provider": "mimo",         // 朗读（需有效 MiMo key）
  "providers": {
    "minimax": {
      "type": "minimax",
      "api_key": "粘贴你的MiniMax-Key",
      "enable_vision": true,
      "models": { "text": "MiniMax-Text-01", "vision": "abab7-chat-preview" }
    },
    "mimo": { "type": "mimo", "api_key": "粘贴你的MiMo-Key" }
  }
}
```

> **粘 key 时注意别粘进占位串中间**（如 `PASTE_MINIMAX_KEY_HERE`），要把整个占位串替换掉。

也支持 `${ENV_VAR}` 形式读环境变量（如 `"api_key": "${MINIMAX_API_KEY}"`）。

### 填完自检（不泄露完整 key）

```powershell
# 1) 看配置状态（不发网络请求）
python scripts/check_ai.py

# 2) 真实调用验证
python scripts/check_ai.py --text                 # 文字对话
python scripts/check_ai.py --vision 某张照片.jpg   # 拍照诊断识别
python scripts/check_ai.py --tts                  # 语音合成

# 3) 服务启动后看 HTTP 状态
curl http://127.0.0.1:8770/api/ai/status
```

`vision_ready: true` 即可走真实拍照诊断。前端 `frontend/index.html` 的 `useMock`
已设为 `false`（走真实识别）；无 key 联调时可临时改回 `true` 走后端 mock。

> **关键模型名坑（已验证）**：vision 正确模型是 `abab7-chat-preview`，旧名
> `MiniMax-VL-01` 已失效。详见 docs/adr.md ADR-008。

---

## Phase 1 验证

```powershell
# 物候期匹配
python -c "from src.backend.app_context import build_context; from pathlib import Path; from src.backend.services.phenology import load_stages, current_stage; from datetime import date; ctx = build_context(Path('.').resolve()); print(current_stage(load_stages(ctx.phenology_path), date.today()))"

# 路由装配
python -c "from server import create_app; app, ctx = create_app(); print(sorted({r.path for r in app.routes if hasattr(r,'path')}))"

# 启动后用浏览器或 curl
curl http://127.0.0.1:8770/api/calendar/today
```

---

## 已知未决

- **MiniMax vision** 在 `minimax.py` 中已支持但默认关闭，需在 `config.json` 把 `providers.minimax.enable_vision = true`，并验证账号下 `MiniMax-VL-01` 可用。
- **ASR 缺失**：现有 provider 没人实现 ASR。Phase 3 准备走"前端浏览器 Web Speech API → 文本"路径，绕过这一缺口；后续再考虑加 ASR provider。
- **农药/物候数据**为 MVP 种子，**用药建议必须经农技资料/农技员二次校对**再放给父母用，避免错误用药。

---

## 关联项目

姊妹项目 `资料浏览器`（`D:\claude_code\20260530_资料转换为个人技能\浏览呢能力`）提供了：

- `src/ai/` provider 抽象（本项目复制使用，不改接口）
- FastAPI routes/services/infra 分层模式（本项目沿用）

本项目暂不与姊妹项目共享代码，先用 **复制** 方式独立演进，避免相互绑死。后期如有共享需求再抽公共包。
