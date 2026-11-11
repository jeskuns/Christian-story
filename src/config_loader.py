"""
源配置加载器

优先用 PyYAML；如果环境里没有（例如较新的 Python 没有对应 wheel），
就用标准库解析本项目 config/sources.yaml 的固定子集，保证采集链路不因
一个可选依赖而完全跑不起来。
"""
import os
import re
import json


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _value(raw: str):
    s = (raw or "").strip()
    if not s:
        return ""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _simple_yaml(text: str) -> dict:
    """解析本项目 sources.yaml 的形态：sources: → 列表 → 键值 → extra 子字典"""
    sources, cur, in_extra = [], None, False
    for raw in text.splitlines():
        line = _strip_comment(raw)
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())

        if stripped.startswith("- ") or stripped == "-":
            if cur:
                sources.append(cur)
            cur, in_extra = {}, False
            rest = stripped[2:].strip() if stripped.startswith("- ") else ""
            if ":" in rest:
                k, v = rest.split(":", 1)
                cur[k.strip()] = _value(v)
            continue

        if cur is None or ":" not in stripped:
            continue
        k, v = stripped.split(":", 1)
        k = k.strip()

        if indent >= 6 and in_extra:
            cur.setdefault("extra", {})[k] = _value(v)
            continue
        if k == "extra" and not v.strip():
            in_extra = True
            cur["extra"] = {}
            continue
        in_extra = False
        cur[k] = _value(v)

    if cur:
        sources.append(cur)
    return {"sources": sources}


def load_sources(path: str) -> dict:
    if not os.path.exists(path):
        return {"sources": []}
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        import yaml
        return yaml.safe_load(text) or {"sources": []}
    except ImportError:
        return _simple_yaml(text)
