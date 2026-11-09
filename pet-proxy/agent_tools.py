"""Tool schemas the agent model sees, page-based gating, and argument normalization.

Tools are executed in the browser (bbctg_vita_web .../fatfish/petTools.ts) with the user's own
session, so the business backend still enforces permissions. Names here must match that file.
`propose_*` tools never act: they only create a card the user has to confirm.
"""
from __future__ import annotations

import re

S = {"type": "string"}
PROJECT_REF = {"type": "string", "description": "实验ID、项目编号、项目名或靶点名，原样传用户说的即可"}


def _fn(name: str, desc: str, props: dict | None = None, required: list | None = None) -> dict:
    params = {"type": "object", "properties": props or {}}
    if required:
        params["required"] = required
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": params}}


TOOLS = {
    "search_projects": _fn(
        "search_projects",
        "搜索/统计免疫项目列表。用于：找项目、某人负责的项目、某靶点有哪些项目、有几个项目在进行中。"
        "返回 total（后端精确计数）和最多 limit 条摘要。",
        {
            "keyword": {"type": "string", "description": "项目编号/实验ID/项目名/靶点的关键词"},
            "target_name": S,
            "owner": {"type": "string", "description": "负责人姓名"},
            "status": {"type": "string", "description": "ongoing=进行中（待X/已X/加免中）, completed=已结题（结题+无效价处死）, 或具体状态文字如 待三免"},
            "mine": {"type": "boolean", "description": "只看当前登录用户负责的"},
            "limit": {"type": "integer", "description": "1-20，默认 8"},
        },
    ),
    "get_project_progress": _fn(
        "get_project_progress",
        "查询某个免疫项目的进度：项目状态、各免疫/采血步骤的计划日期、哪些计划日期已过、下一步及距今天数（只有计划日期，没有执行记录）。",
        {"project": PROJECT_REF},
        ["project"],
    ),
    "get_project_detail": _fn(
        "get_project_detail",
        "查询某个免疫项目的完整方案：负责人、PM、靶点、课题类型、免疫间隔、小鼠分组（品系/只数/周龄/性别）、"
        "抗原（名称/种属/类型/货号/佐剂）、免疫步骤（阶段/相对天数/剂量/佐剂/途径/部位）。参考以前的项目来填表时用它。",
        {"project": PROJECT_REF},
        ["project"],
    ),
    "get_titer_summary": _fn(
        "get_titer_summary",
        "查询某个项目的血清效价结论（系统已按板数据算好每只鼠的最高阳性稀释度：ELISA 为稀释倍数，FACS 为 10^n），"
        "并附带各阶段最高值、阶段间倍数变化等统计。分析效价时必须用它，不要自己推算。",
        {
            "project": PROJECT_REF,
            "immune_stage": {"type": "string", "description": "只看某个免疫阶段，如 三免；不填返回全部"},
            "method": {"type": "string", "enum": ["ELISA", "FACS"]},
        },
        ["project"],
    ),
    "check_current_form": _fn(
        "check_current_form",
        "读取用户当前页面的表单和可编辑表格：字段标签、当前值、控件类型、下拉可选项(options)、是否必填、校验错误；"
        "表格给出列、已有行和能否自动加行；parts 是建议的分批顺序。editable=false 表示页面不支持代填。填表、检查表单前必须先调用。",
    ),
    "propose_form_fill": _fn(
        "propose_form_fill",
        "把填写建议提交成确认卡片（用户点“应用”后才写入页面，不会替用户点提交/保存；auto_save 页面除外，见 check_current_form）。用户要填表/补全/新建/参考某项目填时必须用它，"
        "不要只在回答里列建议值。按 parts 分批，每步只调用一次：一次填基本信息（fields），或一次填一张表（table+rows）。"
        "同一轮里多次调用会合并到同一张卡片，同一格后提交的覆盖先提交的。"
        "值的规则：下拉从 options 里选（allow_custom 时可自填）；多选用、分隔；日期 YYYY-MM-DD。",
        {
            "fields": {
                "type": "object",
                "description": "基本信息：{字段标签: 值}，标签必须来自 check_current_form 的 fields",
                "additionalProperties": {"type": "string"},
            },
            "table": {"type": "string", "description": "要填的表格名（check_current_form 的 table）"},
            "start_row": {"type": "integer", "description": "rows 第一项对应的行号，默认 1；超过现有行数且 can_add_rows=true 会自动加行"},
            "rows": {
                "type": "array",
                "description": "表格行：每行一个 {列名: 值}，只写要填的列",
                "items": {"type": "object", "additionalProperties": {"type": "string"}},
            },
            "reason": {"type": "string", "description": "这一批的共同依据（10 字内），如「参考 BJ240301」「常规建议」「示例，请改」"},
            "reasons": {
                "type": "object",
                "description": "个别字段依据和 reason 不同时才写：{字段或列名: 依据}",
                "additionalProperties": {"type": "string"},
            },
        },
    ),
    "propose_export": _fn(
        "propose_export",
        "导出 Excel：用户说导出、下载、拉个表、给我个Excel/表格、出个清单时用它。直接把用户说的条件放进过滤参数，"
        "不需要先 search_projects。带筛选且结果不超过 40 条、或单个项目的方案时，结果里 auto=true 表示允许跳过确认；"
        "只有 note 写明「已开始下载」时才告诉用户已经开始，否则一律说请点「确认导出」。"
        "kind: project_list=免疫项目列表; mouse_list=小鼠免疫明细（每只鼠的分组/免疫信息）; scheme=某个项目的免疫方案。",
        {
            "kind": {"type": "string", "enum": ["project_list", "mouse_list", "scheme"]},
            "project": {"type": "string", "description": "kind=scheme 时必填；其余可选，用于过滤"},
            "keyword": S,
            "target_name": S,
            "owner": S,
            "status": {"type": "string", "description": "ongoing=进行中 / completed=已结题（结题+无效价处死） / 具体状态文字"},
            "mine": {"type": "boolean"},
        },
        ["kind"],
    ),
    "build_report": _fn(
        "build_report",
        "按用户自定义的要求整理数据并生成 Excel（确认卡片，用户点了才下载）：统计、分组计数、筛选、挑列、排序、按某列分工作表。"
        "所有计数和合计由代码精确计算，结果里的 groups / matched 可直接引用。系统固定格式的导出用 propose_export；"
        "用户要“按X统计/汇总”“只要某几列”“按X分sheet”“把这页的表导出/整理”时用它。\n"
        "source=projects：免疫项目列表全量（最多 5000 个；进行中/已结题这类页签用 status 参数，不是列值），列：编号、实验ID、项目名称、靶点、靶点编号、靶点类型、靶点大小、"
        "负责人、PM、状态、制备状态、开始日期、开始月份、课题类型、鼠型、归类鼠型、免疫间隔、检测方法、FACS板数、ELISA板数、"
        "效价负责人、笼位、实验记录本、实验备注、项目目的。没有执行记录、延期、效价数值这类列："
        "用户要按这些维度统计时不要调用本工具凑一个近似结果，直接说明没有这项数据。\n"
        "source=page_table：当前页面上的表格（任意页面），会按页面当前筛选条件自动翻页取全部；取不到全部时 partial=true，要告诉用户。\n"
        "source=数据源 id（如 s2）：用户打开过的其他模块列表，见系统消息「已认识的数据源」，列名用 list_data_sources 查；"
        "默认取该模块全部数据（scope=all），scope=page_filters 表示按用户上次在那个页面设的筛选。\n"
        "join：把另一个数据源按某一列关联进来做联查（例：项目 和 效价工单 按实验ID关联）。"
        "列名不确定时先调用 list_data_sources，或看报错返回的 available_columns。",
        {
            "source": {"type": "string", "description": "projects / page_table / 数据源 id（如 s2）"},
            "scope": {"type": "string", "enum": ["all", "page_filters"], "description": "数据源 id 时：all=全部（默认），page_filters=按那个页面上次的筛选"},
            "join": {
                "type": "object",
                "description": "联查另一个数据源",
                "properties": {
                    "source": {"type": "string", "description": "projects / 数据源 id"},
                    "left_on": {"type": "string", "description": "主数据里的关联列"},
                    "right_on": {"type": "string", "description": "被关联数据里的关联列，不写=同名"},
                    "how": {"type": "string", "enum": ["inner", "left", "anti", "count"],
                            "description": "inner=两边都有；left=保留主数据全部；anti=主数据里对不上的（如“还没有工单的项目”）；count=给主数据每行加上对上的条数"},
                },
            },
            "title": {"type": "string", "description": "文件标题，如「按靶点统计进行中项目」"},
            "keyword": {"type": "string", "description": "projects：编号/项目名/靶点关键词（系统侧筛选）"},
            "target_name": S,
            "owner": S,
            "status": {"type": "string", "description": "projects：ongoing=进行中（待X/已X/加免中）；completed=已结题（结题+无效价处死）；"
                       "或具体状态文字。“排除/去掉已结题”不是 ongoing（还有规划中等），要用 where 状态 != 结题 和 状态 != 无效价处死"},
            "mine": {"type": "boolean", "description": "projects：只看当前用户负责的"},
            "table": {"type": "string", "description": "page_table：页面上有多张表时的表名"},
            "where": {
                "type": "array",
                "description": "代码侧筛选，全部满足。value 可写 today、today-30 这类相对日期",
                "items": {"type": "object", "properties": {
                    "column": S,
                    "op": {"type": "string", "enum": ["=", "!=", "contains", "not_contains", ">", ">=", "<", "<=",
                                                      "empty", "not_empty", "in"]},
                    "value": {"type": "string", "description": "in 用逗号分隔多个值"}}},
            },
            "group_by": {"type": "array", "items": S,
                         "description": "分组列，最多 3 个；会生成「汇总」工作表。日期列后加 :month / :week / :quarter / :year 按月/周/季/年分组，如 开始日期:month"},
            "metrics": {
                "type": "array",
                "description": "分组后的统计；不写默认只计数。pct=占比%：不写 column 是各组行数占全部的比例，写 column 是该列合计的占比",
                "items": {"type": "object", "properties": {
                    "op": {"type": "string", "enum": ["count", "pct", "count_distinct", "sum", "avg", "min", "max"]},
                    "column": S}},
            },
            "columns": {"type": "array", "items": S, "description": "明细工作表要的列和顺序；不写=全部列（有 group_by 时也会附上明细）"},
            "sort": {"type": "array", "description": "排序", "items": {"type": "object", "properties": {
                "column": S, "desc": {"type": "boolean"}}}},
            "split_by": {"type": "string", "description": "按这一列的值把明细拆成多个工作表（最多 20 个）"},
            "limit": {"type": "integer", "description": "前 N 个：有 group_by 时是汇总只列前 N 组（如“前 10 个靶点”），否则是明细前 N 行"},
        },
        ["source"],
    ),
    "list_data_sources": _fn(
        "list_data_sources",
        "列出能取数的数据源及其列名：内置的 projects，和用户打开过的各模块列表（id、名称、所在页面、条数、列名）。"
        "要用某个模块的数据或联查、但不确定列名时先调用它。not_opened_pages 是菜单里有、但用户还没打开过的页面。",
    ),
    "propose_open_page": _fn(
        "propose_open_page",
        "要的模块还没认识（在「还没打开过的页面」里）时用：生成一张“打开页面”卡片，用户点了才跳转；"
        "页面照常加载后会自动认识它的列表，并接着回答用户这次的问题。卡片本身就是征求同意，直接调用，不用先问用户要不要打开。",
        {"page": {"type": "string", "description": "「还没打开过的页面」里的页面名称"}},
        ["page"],
    ),
}

FORM_TOOLS = ("check_current_form", "propose_form_fill")

PHASE_LABELS = {
    "search_projects": "翻项目列表…",
    "get_project_progress": "查进度…",
    "get_project_detail": "看项目信息…",
    "get_titer_summary": "算效价结论…",
    "check_current_form": "检查表单…",
    "propose_form_fill": "整理填写建议…",
    "propose_export": "准备导出…",
    "build_report": "取数整理中…",
    "list_data_sources": "看看认识哪些数据…",
    "propose_open_page": "找找是哪个页面…",
}


def phase_for(name: str, args: dict) -> str:
    if name == "propose_form_fill":
        parts = []
        for f in args.get("fills") or []:
            part = re.sub(r"^\d+\.\s*", "", f.get("table") or "基本信息").split("(")[0].strip()
            if part not in parts:
                parts.append(part)
        if parts:
            return f"整理填写建议：{'、'.join(parts[:2])}…"
    if name in ("get_project_detail", "get_project_progress", "get_titer_summary") and args.get("project"):
        return PHASE_LABELS[name].rstrip("…") + f" {args['project']}…"
    return PHASE_LABELS.get(name, "处理中…")


def tools_for_page(page: dict | None) -> list[dict]:
    page = page or {}
    has_form = bool(page.get("interactive"))
    names = [n for n in TOOLS if has_form or n not in FORM_TOOLS]
    return [TOOLS[n] for n in names]


_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff\ufe00-\ufe0f]|[\U000e0000-\U000e007f]")

_STATUS_ALIASES = {
    "进行中": "ongoing", "在跑": "ongoing", "正在进行": "ongoing", "ongoing": "ongoing", "running": "ongoing",
    "已结题": "completed", "结题": "completed", "已完成": "completed", "完成": "completed", "completed": "completed",
}


def strip_invisible(text: str) -> str:
    return _ZERO_WIDTH.sub("", text or "")


def _as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("true", "1", "yes", "是"):
        return True
    if s in ("false", "0", "no", "否", ""):
        return False
    return None


def _clean(v, n: int) -> str:
    return strip_invisible(str(v)).strip()[:n]


def _str_map(v) -> dict:
    return {_clean(k, 60): _clean(val, 500) for k, val in v.items() if _clean(k, 60) and val is not None} \
        if isinstance(v, dict) else {}


MAX_FILLS = 80


def _expand_fills(args: dict) -> tuple[list[dict], str | None]:
    """Compact model format (fields map / table+rows / batch reason) → the per-cell list the browser applies."""
    reason = _clean(args.get("reason") or "", 40)
    reasons = {k: v[:40] for k, v in _str_map(args.get("reasons")).items()}
    fills = []
    for field, value in _str_map(args.get("fields")).items():
        fills.append({"field": field, "value": value, "reason": reasons.get(field, reason)})
    table = _clean(args.get("table") or "", 80)
    rows = args.get("rows") if isinstance(args.get("rows"), list) else []
    if rows and not table:
        return [], "填表格需要 table"
    try:
        start = max(1, int(float(args.get("start_row") or 1)))
    except (TypeError, ValueError):
        start = 1
    for i, row in enumerate(rows):
        for col, value in _str_map(row).items():
            fills.append({"table": table, "row": start + i, "field": col, "value": value,
                          "reason": reasons.get(col, reason)})
    # Legacy per-cell list, still accepted.
    for f in args.get("fills") or []:
        if not isinstance(f, dict) or not _clean(f.get("field") or "", 60) or f.get("value") is None:
            continue
        item = {"field": _clean(f["field"], 60), "value": strip_invisible(str(f["value"]))[:500],
                "reason": _clean(f.get("reason") or reason, 40)}
        if _clean(f.get("table") or "", 80):
            try:
                row = int(float(f.get("row")))
            except (TypeError, ValueError):
                row = 0
            if row < 1:
                return [], f"表格字段 {item['field']} 缺少 row"
            item.update(table=_clean(f["table"], 80), row=row)
        fills.append(item)
    if not fills:
        return [], "没有收到任何填写内容（fields 或 table+rows）"
    return fills[:MAX_FILLS], None


_OP_ALIASES = {
    "==": "=", "eq": "=", "等于": "=", "是": "=", "<>": "!=", "ne": "!=", "不等于": "!=", "不是": "!=",
    "like": "contains", "包含": "contains", "含": "contains", "不包含": "not_contains",
    "gt": ">", "大于": ">", "晚于": ">", "gte": ">=", "ge": ">=", "lt": "<", "小于": "<", "早于": "<", "lte": "<=", "le": "<=",
    "is_empty": "empty", "为空": "empty", "is_not_empty": "not_empty", "不为空": "not_empty", "非空": "not_empty",
    "属于": "in", "one_of": "in",
}
_METRIC_ALIASES = {"计数": "count", "数量": "count", "去重": "count_distinct", "distinct": "count_distinct",
                   "合计": "sum", "求和": "sum", "total": "sum", "平均": "avg", "mean": "avg", "average": "avg",
                   "最小": "min", "最大": "max", "占比": "pct", "百分比": "pct", "比例": "pct", "percent": "pct",
                   "percentage": "pct", "share": "pct", "ratio": "pct"}
_COND_OPS = {"=", "!=", "contains", "not_contains", ">", ">=", "<", "<=", "empty", "not_empty", "in"}
_METRICS = {"count", "pct", "count_distinct", "sum", "avg", "min", "max"}


def _str_list(v, limit: int) -> list[str]:
    if isinstance(v, str):
        v = [x for x in re.split(r"[,，、]", v)]
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        s = _clean(x if not isinstance(x, dict) else x.get("column") or "", 60)
        if s and s not in out:
            out.append(s)
    return out[:limit]


def _report_args(args: dict, base: dict) -> tuple[dict, str | None]:
    """build_report: the nested spec (where / metrics / sort) is cleaned here; the browser re-validates columns."""
    out = {k: v for k, v in base.items() if k in ("source", "scope", "title", "keyword", "target_name", "owner", "status",
                                                    "mine", "table", "split_by", "limit")}
    if not out.get("source"):
        if not out.get("table"):
            return {}, "缺少 source：projects / page_table / 已认识的数据源 id"
        out["source"] = "page_table"
    out["source"] = out["source"][:60]
    for key in ("where", "metrics", "sort"):
        if args.get(key) is not None and not isinstance(args[key], list):
            return {}, f"{key} 必须是数组"
    # Dropping conditions silently would widen the result while still looking exact.
    for key, n in (("where", 10), ("metrics", 6), ("sort", 3), ("group_by", 3), ("columns", 40)):
        if isinstance(args.get(key), list) and len(args[key]) > n:
            return {}, f"{key} 最多 {n} 项，当前 {len(args[key])} 项"
    j = args.get("join")
    if j not in (None, "", {}) and not (isinstance(j, dict) and _clean(j.get("source") or "", 60)):
        return {}, "join 必须是对象，并写明 source（要关联的数据源 id）"
    if j:
        how = _clean(j.get("how") or "left", 10).lower()
        how = {"inner_join": "inner", "left_join": "left", "not_in": "anti", "missing": "anti", "exclude": "anti",
               "计数": "count", "条数": "count"}.get(how, how)
        if how not in ("inner", "left", "anti", "count"):
            return {}, "join.how 只能是 inner / left / anti / count"
        left_on = _clean(j.get("left_on") or j.get("on") or "", 60)
        if not left_on:
            return {}, "join 需要 left_on（主数据里的关联列）"
        out["join"] = {"source": _clean(j["source"], 60), "left_on": left_on,
                       "right_on": _clean(j.get("right_on") or left_on, 60), "how": how}
    where = []
    for c in args.get("where") or []:
        if not isinstance(c, dict):
            return {}, "where 每一项都要是 {column, op, value} 对象"
        op = _clean(c.get("op") or "=", 20).lower()
        op = _OP_ALIASES.get(op, op)
        if op not in _COND_OPS:
            return {}, f"where 的 op 只能是 {sorted(_COND_OPS)}"
        col = _clean(c.get("column") or "", 60)
        if not col:
            return {}, "where 每一项都要写 column"
        item = {"column": col, "op": op}
        if c.get("value") is not None:
            item["value"] = _clean(c["value"], 200)
        where.append(item)
    metrics = []
    for m in args.get("metrics") or []:
        if isinstance(m, str):
            m = {"op": m}
        if not isinstance(m, dict):
            return {}, "metrics 每一项都要是 {op, column} 对象"
        op = _clean(m.get("op") or "", 20).lower()
        op = _METRIC_ALIASES.get(op, op)
        if op not in _METRICS:
            return {}, f"metrics 的 op 只能是 {sorted(_METRICS)}"
        col = _clean(m.get("column") or "", 60)
        if op not in ("count", "pct") and not col:
            return {}, f"{op} 需要 column"
        metrics.append({"op": op, **({"column": col} if col else {})})
    sort = []
    for s in args.get("sort") or []:
        if isinstance(s, str):
            s = {"column": s}
        if not isinstance(s, dict) or not _clean(s.get("column") or "", 60):
            return {}, "sort 每一项都要是 {column, desc} 对象"
        desc = _as_bool(s.get("desc"))
        if desc is None:
            desc = str(s.get("order") or s.get("direction") or "").lower() in ("desc", "降序", "descending")
        sort.append({"column": _clean(s["column"], 60), "desc": bool(desc)})
    if where:
        out["where"] = where[:10]
    if metrics:
        out["metrics"] = metrics[:6]
    if sort:
        out["sort"] = sort[:3]
    for key, n in (("group_by", 3), ("columns", 40)):
        lst = _str_list(args.get(key), n)
        if lst:
            out[key] = lst
    if "limit" in out:
        out["limit"] = max(1, min(2000, int(out["limit"])))
    return out, None


def normalize_args(name: str, args) -> tuple[dict, str | None]:
    """Coerce model-produced args into the schema; returns (args, error)."""
    spec = TOOLS.get(name)
    if spec is None:
        return {}, f"未知工具 {name}"
    if not isinstance(args, dict):
        return {}, "参数必须是 JSON 对象"
    params = spec["function"]["parameters"]
    props = params.get("properties", {})
    out = {}
    for key, schema in props.items():
        if key not in args or args[key] is None:
            continue
        v = args[key]
        t = schema.get("type")
        if t == "string":
            v = strip_invisible(str(v)).strip()[:120]
            if not v:
                continue
            if "enum" in schema:
                match = next((e for e in schema["enum"] if e.lower() == v.lower()), None)
                if match is None:
                    return {}, f"{key} 只能是 {schema['enum']}"
                v = match
        elif t == "boolean":
            v = _as_bool(v)
            if v is None:
                continue
        elif t == "integer":
            try:
                v = int(float(v))
            except Exception:
                continue
        elif t == "array":
            if name == "build_report":
                continue
            if not isinstance(v, list):
                return {}, f"{key} 必须是数组"
            v = v[:60]
        out[key] = v
    if "status" in out:
        out["status"] = _STATUS_ALIASES.get(out["status"], out["status"])
    if name == "propose_form_fill":
        fills, err = _expand_fills(args)
        return ({}, err) if err else ({"fills": fills}, None)
    if name == "build_report":
        return _report_args(args, out)
    if name == "search_projects":
        out["limit"] = max(1, min(20, int(out.get("limit") or 8)))
    if name == "propose_export" and out.get("kind") == "scheme" and not out.get("project"):
        return {}, "导出免疫方案需要 project"
    for req in params.get("required", []):
        if req not in out:
            return {}, f"缺少参数 {req}"
    return out, None
