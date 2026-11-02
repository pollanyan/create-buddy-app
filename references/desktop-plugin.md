# 桌面端：本地插件挂载 + MCP App 面板技术

这一篇是**客户端侧**的知识：怎么让一个 MCP 在 WorkBuddy 桌面端里被识别、注册、可调用、可渲染面板。
与开放平台（云端上架）是两套独立机制，别混。

---

## 一、插件被宿主加载的 5 道门（缺一即「重启后仍不出现」）

| # | 条件 | 位置 |
|---|---|---|
| 1 | `known_marketplaces.json` 注册该市场（含 `installLocation`） | `~/.workbuddy/plugins/known_marketplaces.json` |
| 2 | `installed_plugins.json` 有 `<plugin>@<marketplace>` 条目，`installPath` 存在 | `~/.workbuddy/plugins/installed_plugins.json` |
| 3 | **`settings.json` → `enabledPlugins` 里该项为 `true`** | `~/.workbuddy/settings.json` ← **最容易漏** |
| 4 | 插件根目录有 **`.mcp.json`**（不是 `mcp.json`） | 插件目录 |
| 5 | `plugin.json` 有 `extensions.ai.workbuddy.display` + `ai.workbuddy/assets/icon.svg` | `.codebuddy-plugin/plugin.json` |

**第 3 条是硬开关**：宿主读 `enabledPlugins` 字典（键格式 `<插件>@<市场>`）决定启用谁。
只改注册表 = 装上了但没开。

**第 4 条的隐蔽性**：宿主的 `readPluginMcpServerSources` 只扫 `.mcp.json`、`mcp/*.json`
和 plugin.json 里的 `mcpServers`，**不看 `mcp.json`**。
官方连接器能用 `mcp.json` 是因为它们走的是云端市场目录，不是这条路径。

**版本一致性**：把 `installed_plugins.json` 的 `version` 与 plugin.json 保持一致，
否则宿主判 mismatch **直接跳过整个插件**（且不报错，最难查的一种）。
安装脚本应从 plugin.json **动态读版本**，别写死。

**改了插件/MCP 配置必须 ⌘Q 完全重启**：宿主只在启动时快照插件与用户 MCP 配置。

### 市场目录形状
官方形状是 `<marketplace>/connectors/<id>/`（**不是** `plugins/`）。
插件注册三处：`known_marketplaces.json`、`installed_plugins.json`、
实际文件放 `marketplaces/<mp>/connectors/<plugin>` 并复制到 `cache/<mp>/<plugin>/<version>/`。

### 一个常见的假象
`~/.workbuddy/connectors/default/mcp.json`（技能文档里写的本地连接器路径）
**桌面端 0 处引用** —— 那是 CLI 侧路径。桌面端的本地 MCP 一律由**插件**提供。
写了这个文件只会制造一个「看着像配置、实则无效」的假象。

### 插件 MCP 显示在哪
**【连接器 → 自定义连接器】** → 面板标题「MCP 服务器管理」→ 内部分「我的 MCP」，
条目显示 server key + 「来自插件 <插件名>」+ 工具启用数。
【连接器 → 市场】Tab 是**云端目录**，本地插件进不去；【已安装技能】页展示插件卡片。

---

## 二、Agent Plugin 严格解析（"插件加载成功但一个 MCP 都没注册"）

只要 plugin.json 带 `$schema`，宿主就走**严格解析**，读的是 **`mcp.json`**（不是 `.mcp.json`）：

| 规则 | 合法值 |
|---|---|
| stdio 字段白名单 | `type` / `command` / `args` / `env` / `cwd` —— **多一个就整份作废** |
| `command` | 必须是**单个可执行 token**（`node` 可以；`/abs/path/node` 不行，除非以 `./` 开头） |
| `cwd` | 必须是 `./` 或 `${PLUGIN_ROOT}/…` 开头（绝对路径直接判 invalid）；不写则默认插件根目录 |
| `args` | 字符串数组（**绝对路径 args 允许**） |

**结论：插件必须自包含入口**（如 `command: "./bin/xxx"` + 可执行脚本），
指向插件外的绝对路径要藏在 args 或脚本内容里。

**症状极具迷惑性**：插件本身加载成功（技能照常可用），但零个 MCP 服务器注册。
看到技能生效就以为整条链通了 —— **不要**。验证方式：直接调 MCP 工具，
报 "not found in the deferred tools index" 就说明没注册。

---

## 三、MCP App 面板技术要点

### 元数据
- **入口工具**：`registerAppTool` + `_meta.ui.resourceUri`（指向界面资源 URI）
- **交互工具**：`_meta.ui.visibility = ['app']`（模型看不到，只有界面能调），
  且**绝对不能带 `resourceUri`** —— 否则宿主会为它另开一个 App 实例并顶掉当前面板
- **结果**：`_meta['workbuddy.ai/artifact'].stableId`（宿主据此原地更新产物条目，不新增）
- **启动位置**：`_meta.workbuddy.ui.launchSurface` = `inline` / `panel`

### 资源 URI 带内容哈希
`ui://demo/xxx.html?v=<sha1前8位>` —— 界面文件改了哈希就变，宿主自动拉新版；
需要强制刷新时提供 `reload_widget` 工具。

### 幂等：显式传目标值，不要做纯翻牌
交互工具如果写成"再翻一次"，宿主超时重发就会把状态翻回去（用户看到"点了反而变回去了"）。
**设计成"界面明确告诉服务端目标状态"**，重复投递只是把同一个值再写一次。

### 状态建模：用**链**，不用翻牌
三档状态（待办/进行中/已完成）应该建模成 `todo ⇄ doing ⇄ done` 的链：
- 面板：每行渲染**三段式选择器**，点哪一档设哪一档，当前态高亮
- 服务端：不传目标时沿链**相邻步进**一档（todo→doing→done，done→doing 终点回退），
  绝不出现 done⇄todo 的跳跃式回退
- 翻牌式（`done ⇄ todo` 直翻）会把中间档晾成孤岛 —— 这是逻辑 BUG，不是实现细节

### 数据版本号 rev
每次改动 +1，界面只接受 `rev >= 自己当前 rev` 的数据。宿主会回放旧快照，
没有 rev 会出现"点了没反应"。

### 两条结果通道都要能走通
宿主转发界面发起的工具调用时，会把结果裁成短文本（`contentCount:1`、`structuredContent` 为空），
而打开面板时的 bootstrap 结果 `structuredContent` 是完整的。
所以：**同时**写 `structuredContent` 和一段带标记的 JSON 文本，界面两处都读。

### SDK 透传
MCP SDK 的 `ResultSchema` / `RequestMetaSchema` 是 looseObject，
`_meta`（含 `ui.resourceUri`、`workbuddy.ai/artifact`）能透传，HTTP 桥不丢元数据。

---

## 四、MCP 信任凭据

`~/.workbuddy/mcp-approvals.json`：
- key = `<sha256(trustMaterial)>::<serverName>`
- stdio 的 trustMaterial = `command | args排序逗号连 | env键排序逗号连 | cwd`
- hash 与当前 config 一致时**复用旧凭据**；改了 command/args/cwd 就要重新信任

---

## 五、自检脚本的隔离（重要）

自检脚本会跑真实的写操作（新增任务、切状态）。
**绝不能让自检污染用户真实数据** —— 用环境变量把状态文件指向临时文件：

```js
// server 端
const STATE_FILE = process.env.DISPATCH_BOARD_STATE || join(HERE, 'tasks.json');

// 自检端
const STATE_FILE = join(tmpdir(), `verify-${process.pid}.json`);
const transport = new StdioClientTransport({ ..., env: { ...process.env, DISPATCH_BOARD_STATE: STATE_FILE } });
```
自检结束 `rm` 掉临时文件。曾经因为自检先 `rm tasks.json` 再跑，
每跑一次就把用户看板里新增的任务冲掉 —— 这种坑要在脚本设计上根除，而不是靠记得别跑。
