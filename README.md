# 创建Buddy应用

> 在 WorkBuddy 开放平台把能力封装成可上架资产的完整作业手册。
> 全部内容来自一次真实上架（任务派工台：连接器 + 技能 + 本地插件）的实测，不是文档摘抄。

**An operating playbook for building and publishing Buddy apps, connectors, skills and experts on the WorkBuddy open platform — subject gates, the five-module app checklist, platform pitfalls, desktop plugin mounting rules, and the CDP publishing workflow.**

---

## 这个技能解决什么

想在 WorkBuddy 上「发布自己的东西」，会连着一串坑：

- 个人认证到底能发布什么？Buddy 应用为什么建不了？
- 右上角「发现应用」里的条目是本地装的吗？（不是）
- 包怎么组织？zip 顶层目录、CRLF、token-schema 放哪？
- 平台表单为什么点不动、为什么发布页字段改不了？
- 发布包本地校验过了，平台还是说解析失败？
- 提交后到底进没进评审？

这个技能把上面每一条的**现象、原因、解法**都写清楚了，并给出可执行的脚本。

## 目录结构

```
create-buddy-app/
├── SKILL.md                          入口：路由表 + 6 条铁律 + 作业流程
├── references/
│   ├── platform-gates.md              主体门槛矩阵、五类资产关系、Buddy 应用五模块清单、分发路径
│   ├── platform-pitfalls.md           实战踩坑 checklist（现象 → 原因 → 解法）
│   ├── desktop-plugin.md              桌面端插件挂载 5 道门、Agent Plugin 严格解析、MCP App 面板技术
│   └── lessons.md                     方法论八条教训
├── scripts/
│   └── check_buddy_app.py            Buddy 应用配置清单自检（PASS / WARN / FAIL）
└── assets/
    └── application.template.json      Buddy 应用配置清单模板（可直接填写）
```

## 安装

### 方式一 · `npx skills add`（推荐，一条命令）

```bash
npx skills add pollanyan/create-buddy-app --skill create-buddy-app -g -y; \
mkdir -p ~/.workbuddy/skills && \
cp -R ~/.agents/skills/create-buddy-app ~/.workbuddy/skills/
```

用 [skills CLI](https://github.com/vercel-labs/skills)（开放 Agent 技能生态）安装。
需要 **Node.js ≥ 22.20**，在普通终端里跑（它会渲染一个交互式选择界面）。

**后面为什么还要两步**：`skills` CLI 装到的是通用全局目录 `~/.agents/skills/create-buddy-app/`
（并写 `~/.agents/.skill-lock.json` 便于后续 `npx skills update` 升级），
而 **WorkBuddy 只读 `~/.workbuddy/skills/`** —— CLI 目前还没有 `workbuddy` 这个 agent 目标，
所以要手动挪到位。

> ⚠️ 这里用 `;` 而不是 `&&`：CLI 在全局模式下可能以非 0 退出
> （个别 agent 不支持全局安装时会报 `does not support global skill installation`），
> **但技能其实已经装好了**。用 `&&` 会导致后面的复制不执行。

CLI 常用参数：

| 参数 | 作用 |
|---|---|
| `-g, --global` | 装到全局（默认装到当前项目） |
| `-s, --skill <name>` | 只装指定技能（本仓库只有一个技能时可省略） |
| `-a, --agent <agents>` | 指定装到哪些 agent，`*` 表示全部 |
| `--copy` | 复制文件而不是建软链 |
| `-l, --list` | 只列出仓库里可装的技能，不安装 |
| `-y, --yes` | 跳过交互确认 |

`<package>` 除了 `owner/repo`，也接受**技能名**或**任意技能页 URL**
（如 `https://github.com/vercel-labs/agent-skills`）。

装好之后：

```bash
npx skills list              # 看已装技能
npx skills update            # 按 lock 文件升级
```

### 方式二 · 直接 clone（零依赖）

```bash
git clone https://github.com/pollanyan/create-buddy-app.git \
  ~/.workbuddy/skills/create-buddy-app
```

### 方式三 · 下载 zip

从 [Releases](https://github.com/pollanyan/create-buddy-app/releases) 下载
`create-buddy-app.zip`，解压后把 `create-buddy-app/` 整个目录放进 `~/.workbuddy/skills/`。

> **三种方式都适用的两点**
>
> 1. 装到 `~/.workbuddy/skills/` 后，WorkBuddy 会在**下次启动**时扫描到它。
> 2. 想让它在「已安装技能」里显示中文名「创建Buddy应用」，在技能目录下放一个 `_skillhub_meta.json`：
>    ```json
>    { "name": "创建Buddy应用", "source": "local", "version": "1.0.0" }
>    ```

## 使用

装好后直接说人话即可触发，比如：

- 「帮我创建一个任务派工台 Buddy 应用」
- 「把这个 MCP 发布到开放平台的连接器市场」
- 「技能上架需要准备哪些字段」

也可以直接跑配套的自检脚本：

```bash
python3 scripts/check_buddy_app.py <你的 application.json>
python3 scripts/check_buddy_app.py --template     # 校验模板本身
```

输出示例：

```
PASS=17  WARN=4  FAIL=0
结论：PASS（有提醒项，提交前请确认）
```

## 三条最该先记住的

**1. 先确认主体类型，再动手**

| 资产 | 个人主体 | 企业/组织主体 |
|---|---|---|
| 技能 / 专家 / 专家团 | ✅ | ✅ |
| 连接器 | ⚠️ 后端会拦（"个人主体暂不支持创建连接器"） | ✅ |
| **Buddy 应用** | ❌ | ✅ |

Buddy 应用与硬件接入需要**企业或组织主体**。企业认证含**个体工商户**（有营业执照即可）；
无营业执照可走「其他组织机构认证」，能力等同企业主体。
详见 `references/platform-gates.md`。

**2. Buddy 应用不走 zip 上传**

它是网页端逐模块填表单：创建应用 → 首页配置 → 市场配置 → 其他配置 → 预览调试。
先用 `assets/application.template.json` 写出「填写内容清单」，再逐模块粘贴。

**3. 发布页字段全是 `readOnly=true`**

名称/介绍/示例/版本号都由能力包解析而来，**手改表单无效** —— 唯一改法是重新上传新包再提交。

## 依赖的兄弟技能

本技能不重复它们的内容，只做编排与补充：

| 技能 | 负责 |
|---|---|
| `open-platform-publisher` | 上架前合规校验 + CDP 驱动上传 |
| `wb-open-builder` | 五类资产的生成范本 + 校验器 |
| `workbuddy-connector-authoring` | 连接器包规范、本地安装、排障、打包 |

## 官方文档

开放平台 <https://open.workbuddy.cn> ·
文档 `/docs/buddy-app`、`/docs/connector`、`/docs/skill`、`/docs/expert`、`/docs/onboarding`

## License

MIT
