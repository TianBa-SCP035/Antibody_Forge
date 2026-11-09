# FatFish 桌宠

Antibody Vita 里的鲸鱼娘桌宠「大肥鱼」：闲聊、读当前页、代填表单建议、导出 / 自定义汇总，以及跟着用户打开过的列表页学接口取数。

## 目录

| 路径 | 内容 |
|------|------|
| `bbctg_vita_web/apps/antibody_vita/src/components/fatfish/` | 前端模块（18 个源文件） |
| `bbctg_vita_web/apps/antibody_vita/public/fatfish/` | 动画 webm、头像、光标；署名见目录内 `ATTRIBUTION.txt` |
| `pet-proxy/` | 本机代理（标准库 Python，无第三方依赖） |

`app.vue` 挂载 `<FatFishPet />`（登录页和业务页共用）。`vite.config.ts` / Nginx 把 `/api/pet` 转到 `127.0.0.1:18765`，**必须写在通用 `/api` 之前**。

## 启动

```bash
cd pet-proxy
python server.py
```

健康检查：`GET http://127.0.0.1:18765/api/pet/health`。

模型地址可用环境变量覆盖（缺省为内网 OpenAI 兼容地址）：

- `PET_QWEN_BASE` / `PET_QWEN_MODEL`
- `PET_DEEPSEEK_BASE` / `PET_DEEPSEEK_MODEL`

## 代理接口

| 路径 | 用途 |
|------|------|
| `POST /api/pet/agent` | 数据任务：DeepSeek 选工具；浏览器用当前登录态执行 |
| `POST /api/pet/chat` | 闲聊 / 页面点评（Qwen） |
| `POST /api/pet/compress` | 长期记忆压缩（Qwen） |
| `POST /api/pet/lines` | 即时反应台词（Qwen） |

代理只听 `127.0.0.1`、不发 CORS、只收 JSON（≤ 512 KB）。生产部署时 `/api/pet` 应放在已登录的同源反代后面，不要把无鉴权进程直接暴露到公网。

## 依赖边界

- 只有 `petTools.ts` 引用业务接口（`#/api/serum`、导出、效价结论）。
- 只有 `session.ts` 读宿主登录态和路由（`@vben/stores`、`vue-router`）。
- `reportBuilder.ts` 按需加载宿主已装的 `xlsx`。
- 其余文件只依赖 Vue、DOM 和 `/api/pet/*`。

新业务页一般不用适配：打开过一次列表即可统计 / 联查；Element Plus 带保存类按钮的表单可代填建议。专门业务计算需成对加 `petTools.ts` 执行器与 `pet-proxy/agent_tools.py` 定义。

## 能力摘要

- **两条路径**：闲聊走 Qwen 人设；带业务词 / 实验 ID / 菜单模块名 / 帮填表走 agent（DeepSeek 无人设 + Qwen 一句开场白）。
- **卡片确认**：填表点「应用」、固定导出点「确认导出」、报表点「下载 Excel」、未认识页面点「打开页面」。用户明确要文件且条数够少时，导出可跳过第二张确认卡。
- **跟着页面取数**：同源、像列表、路径无写类词；POST 还要有读类词。重放前再查一遍。菜单里还没打开的页面可出卡请用户打开，加载后自动认识并接着回答。
- **记忆**：按账号存摘要与近史；压缩不记查到的数字；摘要硬上限 800 字。

## 安全边界

- 没有改 / 删 / 提交工具；填表只写到页面控件，由用户点卡片；自动保存页会由页面自己持久化（卡片提前标明）。
- 密码框与敏感字段名不送模型；正文打码邮箱和大陆手机号；焦点字段同样打码。
- `pet-proxy/logs/agent_trace.jsonl` 含业务内容，已在 `.gitignore`；超过约 5 MB 轮转。

素材署名与许可证见 `public/fatfish/ATTRIBUTION.txt`。
