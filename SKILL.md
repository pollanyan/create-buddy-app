---
name: create-buddy-app
description: "在 WorkBuddy 开放平台（open.workbuddy.cn）开发并上架 Buddy 应用、连接器、技能、专家的操作手册。当用户说「创建Buddy应用」「做个应用放进发现应用」「发布连接器到市场」「上架技能」「让本地 MCP 出现在连接器列表」时使用。内含主体门槛判定、Buddy 应用五模块配置清单、平台实测踩坑清单、桌面端本地插件挂载门禁，以及已验证可用的 CDP 发布脚本用法。"
description_zh: "在 WorkBuddy 开放平台开发并上架 Buddy 应用、连接器、技能、专家资产的操作手册：主体门槛判定、五模块配置清单、平台实测坑、桌面端插件挂载门禁、CDP 发布脚本用法。"
description_en: "An operating playbook for building and publishing Buddy apps, connectors, skills and experts on the WorkBuddy open platform — subject gates, the five-module app checklist, platform pitfalls, desktop plugin mounting rules, and the CDP publishing workflow."
display_name: "创建Buddy应用"
display_name_en: "Create Buddy App"
examples_zh:
  - "帮我创建一个任务派工台 Buddy 应用"
  - "把这个 MCP 发布到开放平台的连接器市场"
  - "技能上架需要准备哪些字段"
examples_en:
  - "Create a task dispatch board Buddy app for me"
  - "Publish this MCP to the connector marketplace"
  - "What fields do I need to prepare for a skill release"
version: 1.0.1
author: "WorkBuddy 开放平台实战手册"
agent_created: true
---

# 创建Buddy应用

在 WorkBuddy 开放平台把能力封装成可上架资产的完整作业手册。**所有内容都来自一次真实上架（任务派工台：连接器 + 技能 + 本地插件）的实测**，不是文档摘抄。

## 第一步永远不是动手，是先查已有技能

平台/生态类任务的正确起点是**搜索并安装现成技能**，而不是反查客户端实现：

```bash
# 用 search_and_install_skills 搜（首选）
action: search, keywords: ["Buddy 应用 生成","开放平台 资产","连接器 开发"]
action: install, skill_names: ["wb-open-builder","open-platform-publisher","workbuddy-connector-authoring"]
```

已装的三兄弟各自负责一段，**本技能不重复它们的内容，只做编排与补充**：

| 技能 | 负责 |
|---|---|
| `wb-open-builder` | 五类资产的生成范本（WB01~WB06）+ 校验器 `scripts/validate_asset.py` |
| `open-platform-publisher` | 上架前合规校验 + CDP 驱动上传（`scripts/publish.sh`） |
| `workbuddy-connector-authoring` | 连接器包规范、本地安装、排障、打包 |

本技能补的是这三者都没覆盖的：**主体门槛的判定顺序、Buddy 应用与连接器的依赖关系、平台实测坑、桌面端插件门禁、踩坑成因**。

## 路由：用户要什么，走哪条路

| 用户诉求 | 路线 | 关键动作 |
|---|---|---|
| 「让我的东西出现在右上角**发现应用**」 | ① 连接器 → ② Buddy 应用 → ③ 审核上架 | Buddy 应用必须**企业/组织主体**；先读 `references/platform-gates.md` |
| 「上架一个**连接器**」 | 打 zip → 校验 → 上传 → 选类目 → 提交 | 读 `references/platform-pitfalls.md` 的坑清单 |
| 「上架一个**技能**」 | 同上，但 frontmatter 字段要求不同 | 技能 frontmatter 必填 8 字段 + examples ≤3 |
| 「让本地 MCP 出现在客户端里」 | 桌面端插件路线 | 读 `references/desktop-plugin.md` 的 **5 道门** |
| 「做一个带界面的 MCP 工具面板」 | MCP App 路线 | 读 `references/desktop-plugin.md` 的 **面板技术要点** |
| 「上架被驳回了 / 要发新版本」 | republish / resubmit | 见下方「版本与动作」 |

## 铁律（违反必踩坑）

1. **先确认主体类型再动手**。个人认证只能发布技能/专家/专家团；**Buddy 应用与硬件接入需要企业或组织主体**。
   连接器在个人主体下提交会被后端拦（"个人主体暂不支持创建连接器"），不是配置问题，别反复试。
2. **Buddy 应用不走 zip 上传**，是网页端逐模块填表单。先用 `assets/application.template.json` 生成
   "填写内容清单"，再逐模块粘贴；提交前用 `scripts/check_buddy_app.py` 自检。
3. **发布页的字段全是 `readOnly=true`**，名称/介绍/示例/版本号都由能力包解析而来。
   想改元信息，唯一路径是**重新上传新包 + 提交**，手改表单无效。
4. **类目是「一级→二级」级联，必须用真实鼠标事件**（`Input.dispatchMouseEvent`）。
   JS 的 `.click()` 对 Tailwind 组件无效。
5. **交付前必须用官方校验器跑一遍**，不靠肉眼判断合规。
6. **能自己做的不要推给用户**：打包、校验、部署、写脚本、查文档、驱动 CDP 全自己做完；
   只把扫码登录、人脸核身、⌘Q 重启、资质认证这类物理上必须人做的交出去。

## 版本与动作（平台只有四种发布动作）

| 动作 | URL 参数 | 用途 |
|---|---|---|
| Create | `?action=create&step=1` | 新建资产 |
| Edit | `?action=create&step=2` | 编辑已有资产（本质仍是 Create） |
| Republish | `?action=republish&step=1` | 已上线资产发新版本 |
| Resubmit | `?action=resubmit&step=1` | 被驳回后修改重提 |

发布脚本已支持 `--action`：

```bash
cd ~/.workbuddy/skills/open-platform-publisher/scripts
bash publish.sh publish <zip> connector --asset-id oc_xxx --action republish --no-submit
```

`--asset-id` 会让平台把新包识别为**既有资产的新版本**，资产 ID 不变、版本号递增。
版本号必须严格递增；驳回后修包重传同理。

## 标准作业流程（连接器 / 技能）

```
1. 读 references/platform-gates.md      →  确认主体类型与资产归属
2. 读 references/platform-pitfalls.md   →  照着 checklist 备料（每个坑都有现象与解法）
3. 组包（连接器：connector-meta.json + mcp.json + icon + skills/）
4. 打包（zip 顶层必须是 <connector-id>/；.md/.json 用 CRLF）
5. bash publish.sh check <zip> connector      → 必须 PASS
6. bash publish.sh publish <zip> connector     → 驱动上传
7. 人工补齐平台必填项（类目 / 市场展示分类）→ 提交审核
8. 回列表页核对状态（https://open.workbuddy.cn/connector/all 与 /skill/all）
```

**Buddy 应用是第 7 步之后的独立一段**：连接器过了审，才能在 Buddy 应用的「市场配置」里选配它。

## 自检与工具

```bash
# Buddy 应用配置清单自检（本文档配套）
python3 ~/.workbuddy/skills/create-buddy-app/scripts/check_buddy_app.py <application.json>

# 上架包官方校验
bash ~/.workbuddy/skills/open-platform-publisher/scripts/publish.sh check <zip> connector|skill

# 开放平台登录（必须本人扫码，Agent 代不了）
bash ~/.workbuddy/skills/open-platform-publisher/scripts/publish.sh login
bash ~/.workbuddy/skills/open-platform-publisher/scripts/publish.sh status
```

## 参考文件

| 文件 | 内容 |
|---|---|
| `references/platform-gates.md` | 主体门槛、五类资产矩阵、Buddy 应用五模块清单、分发路径（公开 / 企业单） |
| `references/platform-pitfalls.md` | 平台实测踩坑 checklist：每个坑的现象、原因、解法 |
| `references/desktop-plugin.md` | 桌面端插件挂载 5 道门、Agent Plugin 严格解析、MCP App 面板技术要点 |
| `references/lessons.md` | 方法论层面的经验与教训（怎么少走弯路） |
| `assets/application.template.json` | Buddy 应用配置清单模板（可直接填写） |

## 来源与更新

本技能由一次真实上架实战沉淀，源码仓库：<https://github.com/pollanyan/create-buddy-app>（MIT 协议）。
平台规则会变 —— 发现文档与本文冲突时，以开放平台实际行为为准，并顺手更新本技能。
