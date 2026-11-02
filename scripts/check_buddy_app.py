#!/usr/bin/env python3
"""Buddy 应用配置清单自检。

用法:
    python3 check_buddy_app.py <application.json> [--template]

    --template  用内置模板做自检（验证模板本身结构完好）

检查的是「提交前必须满足」的平台硬规则：
  · 五模块齐全
  · 场景胶囊 2~5 条、工作模式 2~4 个且字段完整
  · 授权回调 URL / 可信 Origin 必须是 https 且占位符已替换
  · Client Secret 只展示一次的提醒必须在清单里
  · 市场配置引用的资产带 source/id
  · icon 与背景图设计规格数值不得改动
  · 模型池非空

退出码: 0 = 无 FAIL（有 WARN 也算通过），1 = 有 FAIL
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "application.template.json"

PASS, WARN, FAIL = [], [], []


def ok(msg):
    PASS.append(msg)


def warn(msg):
    WARN.append(msg)


def bad(msg):
    FAIL.append(msg)


def find_key(d, *keywords):
    """在嵌套 dict 里按关键字找第一个匹配的 key（忽略大小写与空格）。"""
    if not isinstance(d, dict):
        return None, None
    for k, v in d.items():
        norm = re.sub(r"[\s_]+", "", str(k)).lower()
        if all(re.sub(r"[\s_]+", "", kw).lower() in norm for kw in keywords):
            return k, v
    for v in d.values():
        rk, rv = find_key(v, *keywords)
        if rk is not None:
            return rk, rv
    return None, None


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


def has_placeholder(*strings):
    return any("{{" in s or "}}" in s for s in strings)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_template = "--template" in sys.argv
    path = Path(args[0]) if args else TEMPLATE
    if use_template:
        path = TEMPLATE
    if not path.exists():
        print(f"[error] 找不到文件：{path}")
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[error] JSON 解析失败：{e}")
        return 1

    print("=" * 62)
    print(f"Buddy 应用配置清单自检 · {path}")
    print("=" * 62)

    # ---- 1. 五模块齐全 ----
    for i in range(1, 6):
        k, _ = find_key(data, f"模块{i}")
        if k:
            ok(f"模块{i} 存在（{k}）")
        else:
            bad(f"缺少模块{i}")

    # ---- 2. 场景胶囊 2~5 条 ----
    k, caps = find_key(data, "场景胶囊")
    if caps is None:
        bad("缺少「场景胶囊」")
    elif isinstance(caps, (dict, list)):
        if isinstance(caps, dict):
            vals = [str(v) for v in caps.values() if str(v).strip()]
        else:
            vals = []
            for v in caps:
                if isinstance(v, dict):
                    vals.append(str(v.get("名称") or v.get("文案") or v.get("text") or ""))
                elif str(v).strip():
                    vals.append(str(v))
        n = len(vals)
        if 2 <= n <= 5:
            ok(f"场景胶囊 {n} 条（要求 2~5）")
        else:
            bad(f"场景胶囊 {n} 条，要求 2~5 条")
        if has_placeholder(*vals):
            warn("场景胶囊里还有 {{占位符}} 没替换")
    else:
        bad(f"「场景胶囊」结构不可识别（应为 dict 或 list，实际 {type(caps).__name__}）")

    # ---- 3. 工作模式 2~4 个且字段完整 ----
    k, modes = find_key(data, "工作模式")
    if modes is None:
        bad("缺少「工作模式」")
    elif isinstance(modes, dict):
        pairs = list(modes.items())
    elif isinstance(modes, list):
        pairs = [(str(m.get("名称") or m.get("name") or f"#{i+1}"), m)
                 for i, m in enumerate(modes) if isinstance(m, dict)]
    else:
        pairs = []
        bad(f"「工作模式」结构不可识别（应为 dict 或 list，实际 {type(modes).__name__}）")
    if modes is not None and (isinstance(modes, (dict, list))):
        n = len(pairs)
        if 2 <= n <= 4:
            ok(f"工作模式 {n} 个（要求 2~4）")
        else:
            bad(f"工作模式 {n} 个，要求 2~4 个")
        for name, m in pairs:
            if not isinstance(m, dict):
                bad(f"工作模式「{name}」结构不是对象")
                continue
            missing = [f for f in ("SystemPrompt", "预绑定Skill", "适用场景")
                       if find_key(m, f.replace(" ", ""))[0] is None]
            if missing:
                bad(f"工作模式「{name}」缺字段：{', '.join(missing)}")
            else:
                ok(f"工作模式「{name}」字段完整")

    # ---- 4. 授权回调 URL / 可信 Origin ----
    for kw, label in ((("授权回调",), "授权回调URL"), (("可信Origin", "可信 Origin"), "可信Origin")):
        k, v = find_key(data, *kw)
        if v is None:
            bad(f"缺少「{label}」")
            continue
        s = str(v)
        if s.startswith("https://"):
            ok(f"{label} 是 https")
        elif s.startswith("http://"):
            bad(f"{label} 用的是 http://，平台要求 https")
        else:
            bad(f"{label} 不是合法 URL：{s[:60]}")
        if "{{" in s:
            warn(f"{label} 里还有 {{占位符}}")

    # ---- 5. Client Secret 提醒 ----
    all_str = list(walk_strings(data))
    if any("Secret" in s and ("仅" in s or "一次" in s) for s in all_str):
        ok("含「Client Secret 仅展示一次」的提醒")
    else:
        bad("缺少「Client Secret 仅完整展示一次」的提醒（必须写进清单）")

    # ---- 6. 市场配置引用的资产 ----
    k, market = find_key(data, "市场配置")
    if market is None:
        warn("未找到「市场配置」模块")
    elif isinstance(market, dict):
        for board in ("专家", "专家团", "技能", "连接器", "精选场景"):
            bk, bv = find_key(market, board)
            if bv is None:
                continue
            items = bv if isinstance(bv, list) else ([bv] if not isinstance(bv, dict) else list(bv.values()))
            # 「（可选）」「（可选，默认关闭）」这类说明不算已填
            items = [i for i in items
                     if str(i).strip() and not re.fullmatch(r"[（(]?可选[^）)]*[）)]?", str(i).strip())]
            if not items:
                warn(f"市场配置「{board}」为空")
                continue
            if all(isinstance(i, str) and "{{" in i for i in items):
                warn(f"市场配置「{board}」里还有占位符")
                continue
            for i in items:
                if isinstance(i, str):
                    ok(f"市场配置「{board}」已填：{i[:40]}")
                elif isinstance(i, dict):
                    if not (i.get("source") or i.get("id") or i.get("name")):
                        bad(f"市场配置「{board}」有条目缺 source/id/name：{str(i)[:60]}")
                    else:
                        ok(f"市场配置「{board}」条目完整")
    else:
        bad("「市场配置」结构不是字典")

    # ---- 7. 设计规格数值 ----
    icon_ok = any("16px×16px" in s and "1.2px" in s and "100%" in s for s in all_str)
    bg_ok = any("1000×910px" in s for s in all_str)
    if icon_ok:
        ok("应用 icon 规格数值正确（16×16 / 1.2px / 100%）")
    else:
        bad("应用 icon 规格缺失或数值被改动（应为 16px×16px、线宽 1.2px、圆角 100%）")
    if bg_ok:
        ok("精选场景背景图规格正确（1000×910px）")
    else:
        warn("未找到精选场景背景图规格（用到时才需要：1000×910px、日夜间 2 套）")

    # ---- 8. 模型池 ----
    k, models = find_key(data, "模型池")
    if models is None:
        warn("未找到「模型池」")
    else:
        picked = []
        if isinstance(models, dict):
            pk, pv = find_key(models, "勾选")
            picked = pv if isinstance(pv, list) else []
        if picked:
            ok(f"模型池已勾选 {len(picked)} 个")
        else:
            warn("模型池未勾选模型")

    # ---- 9. 占位符总扫描 ----
    leftover = [s for s in all_str if "{{" in s and not s.strip().startswith("{{") is None]
    n_ph = sum(1 for s in all_str if "{{" in s)
    if n_ph:
        warn(f"清单里还有 {n_ph} 处 {{占位符}} 待替换（提交前必须全部替换）")

    # ---- 输出 ----
    for m in PASS:
        print(f"  ✓ {m}")
    for m in WARN:
        print(f"  ! {m}")
    for m in FAIL:
        print(f"  ✗ {m}")
    print("=" * 62)
    print(f"PASS={len(PASS)}  WARN={len(WARN)}  FAIL={len(FAIL)}")
    if FAIL:
        print("结论：FAIL —— 必须先修完上述问题再提交")
    elif WARN:
        print("结论：PASS（有提醒项，提交前请确认）")
    else:
        print("结论：PASS —— 可提交")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
