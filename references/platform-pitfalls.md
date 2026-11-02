# 平台实测踩坑清单

每一条都是真实上架时撞到并解决的。**备料时逐条对照**，别等平台报错再回头查。

---

## A. 包结构与解析（上传阶段就会挂）

### A1 · `token-schema.json` 必须放**包根目录**
- **现象**：`解析失败：invalid mcp.json: invalid field [mcpServers.xxx.url] 原因=URL 变量 ${TOKEN} 未在 token-schema.json 的 fields 中声明`
- **原因**：平台在包根目录找 `token-schema.json`；放在 `ai.workbuddy/` 会被当成不存在。
- **解法**：包根目录放一份 `token-schema.json`（`ai.workbuddy/` 可保留副本），
  **并确认打包脚本的白名单包含它** —— 白名单漏了这个文件，zip 里就没有它（症状完全一样，极易误判成路径问题）。

### A2 · 传输类型写 `streamableHttp`，不是 `streamable-http`
- 官方校验器会直接给这条建议。照做。

### A3 · zip 顶层必须是 `<connector-id>/`
- 例如 `dispatch-board/mcp.json`，不能直接是 `mcp.json`。
- `.md` / `.json` 用 **CRLF** 行尾。

### A4 · 技能 frontmatter 必填 8 字段
`name` / `display_name` / `display_name_en` / `description` / `description_zh` / `description_en` / `version` / `author`

### A5 · frontmatter 里出现「ASCII 冒号 + 空格」→ YAML 解析失败
- **现象**：`解析失败：…` 且不指出具体行
- **真实案例**：`description_en: "… task dispatch board: filter tasks …"`
  —— YAML 把它当成嵌套映射，直接解析失败。
- **解法**：所有值加引号 + 把冒号换成破折号/全角冒号。

### A6 · `examples_zh` / `examples_en` **最多 3 条**
- **现象**：`解析失败：examples_zh 最多 3 个示例，当前 4 个`
- **注意**：这是**技能**的限制；连接器的 `connector-meta.json` 可以放 4 条。
- 这两个字段就是市场详情页的「**试试这样问我**」，所以填上才有展示价值。

---

## B. 表单交互（平台是 Tailwind + Radix，JS 点击无效）

### B1 · 类目是「一级 → 二级」级联
- 一级 9 个：物流 / 教育 / 交通 / 生活 / 餐饮 / 旅游 / 工具 / 商业 / 体育
- 工具下的二级 11 个：记账 / 日历 / 天气 / **办公** / 图片处理 / 计算器 / 报价比价 / 信息查询 / 预约报名 / 健康管理 / 备忘录
- **必须先真实鼠标事件展开一级，再点二级**。JS `.click()` 对这类组件**无效**。
- 用 `Input.dispatchMouseEvent`（发布器的 `Browser.real_click` 已封装）。

### B2 · 技能页有两个必填下拉
「市场展示分类」+「服务类目」。连接器页只有「服务类目」。

### B3 · 「市场展示分类」是**多选**（13 项扁平）
- 选中的以 **chip** 展示，每个 chip 上有 `aria-label="删除 XXX"` 的删除按钮可取消。
- 下拉选项**不是** `role=option` 节点，要按文字定位 + 真实鼠标事件点。
- 常见取值：办公协同 / 开发工具 / 效率工具 / 内容创作 / 信息资讯 / 教育学习 / 数据分析 /
  网站部署 / 生活服务 / 商业运营 / 知识与学习 / 健康医疗 / 投资理财 / 双十一 / OPC·一人公司

### B4 · 平台可能给**已经填好的下拉**再自动选一个
脚本选完「开发工具」，最终摘要却是「信息资讯」。**每次操作后都要回读摘要页确认实际值**，
不要相信脚本的 "已选择 xxx" 输出。

---

## C. 发布动作与版本

### C1 · 四种动作
`create` / `edit`(仍是 create&step=2) / `republish` / `resubmit`。
带 asset-id 时用 `--action` 指定（发布脚本已支持）。

### C2 · 版本号必须严格递增
驳回后修包重传同理。

### C3 · 发布页字段全是 `readOnly=true`
名称 / 介绍 / 示例 / 版本号**都从能力包解析**，手改表单无效（JS 赋值会被 React 立刻回滚，
`Input.insertText` 也因为 readonly 不生效）。
**唯一改法：重新上传新包 + 提交。**

### C4 · 个人主体提交连接器被后端拦
「个人主体暂不支持创建连接器，请升级为企业主体后使用」。
文案来自后端（前端产物里搜不到），三种动作都拦。→ 主体策略，别重试。

---

## D. 合规红线

- **令牌绝不硬编码进包**。用 `${ENV_VAR}` 占位 + `token-schema.json` 让用户自填，
  `connector-meta.json` 标 `auth_mode: "token"`。
- 包内不留本机绝对路径、个人邮箱、手机号。
- 官方校验器会查「品牌脱钩」，别把腾讯/WorkBuddy 的品牌词塞进自有描述。

---

## E. 自检流程

```bash
bash ~/.workbuddy/skills/open-platform-publisher/scripts/publish.sh check <zip> connector
python3 ~/.workbuddy/skills/wb-open-builder/scripts/validate_asset.py --type connector <包目录>
```

两个校验器**交叉验证**，都 PASS 才上传。

---

## F. 踩坑速查表

| 现象 | 最可能的原因 |
|---|---|
| 解析失败 + 提到 URL 变量未声明 | `token-schema.json` 不在包根 / 没进 zip |
| 解析失败 + 提到 examples | 技能示例超过 3 条 |
| 解析失败但看不出哪行 | frontmatter 里有 ASCII 冒号+空格 |
| 类目下拉点不动 | 用了 JS `.click()`，改真实鼠标事件 |
| 填了市场展示分类但摘要没变 | 点到了 chip 而不是列表项；或平台自动改了值，要回读确认 |
| 表单输入框改不动 | 字段是 `readOnly`，元信息只能靠重新传包 |
| 提交后页面仍显示表单 | 后端返回了错误（主体策略/必填项），读页面上的红字 |
| 个人主体发连接器被拒 | 主体策略，需要企业/组织主体 |
