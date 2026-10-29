from modules.discovery.workbench.constants import MOUSE_STRAIN_OPTIONS

STATUS_WAIT_ORDER = "待下单"
STATUS_SYNTHESIZING = "合成中"
STATUS_WAIT_ASSAY = "待检测"
STATUS_ASSAYING = "检测中"
STATUS_COMPLETED = "已完成"
STATUS_CANCELLED = "已取消"
STATUS_OPTIONS = (
    STATUS_WAIT_ORDER,
    STATUS_SYNTHESIZING,
    STATUS_WAIT_ASSAY,
    STATUS_ASSAYING,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)
TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_CANCELLED})
ACTIVE_STATUSES = frozenset(
    {
        STATUS_WAIT_ORDER,
        STATUS_SYNTHESIZING,
        STATUS_WAIT_ASSAY,
        STATUS_ASSAYING,
    }
)

UNCLAIMED_OWNER = "无人问津"

ORDER_KIND_NORMAL = "常规合成"
ORDER_KIND_ENGINEERING = "改造"
ORDER_KIND_OPTIONS = (
    ORDER_KIND_NORMAL,
    ORDER_KIND_ENGINEERING,
)

SUPPLY_MODE_ARRIVAL = "合成到货"
SUPPLY_MODE_INTERNAL = "内部转染"
SUPPLY_MODE_ISOTYPE = "改亚型"
SUPPLY_MODE_OPTIONS = (
    SUPPLY_MODE_ARRIVAL,
    SUPPLY_MODE_INTERNAL,
    SUPPLY_MODE_ISOTYPE,
)

AFFINITY_RESULT_NORMAL = "正常"
AFFINITY_RESULT_FEW = "阳性极少"
AFFINITY_RESULT_ALL_NEG = "全阴"
AFFINITY_RESULT_OPTIONS = (
    AFFINITY_RESULT_NORMAL,
    AFFINITY_RESULT_FEW,
    AFFINITY_RESULT_ALL_NEG,
)

SELECTION_METHOD_OPTIONS = (
    "补挑",
    "EYE",
    "DS",
    "JX_P",
    "JX_C",
    "RH_P",
    "RH_C",
    "D",
    "D模型",
    "D模型-3轮",
    "P",
)

TARGET_TYPE_OPTIONS = (
    "分泌型",
    "I型跨膜",
    "II型跨膜",
    "III型跨膜",
    "IV型跨膜",
    "单次跨膜",
    "多次穿膜",
    "GPI锚定",
    "细胞膜蛋白",
    "外周膜蛋白",
    "脂锚定蛋白",
    "胞内蛋白",
    "其他",
)

TARGET_COLOR_OPTIONS = (
    "yellow",
    "orange",
    "red",
    "green",
    "blue",
    "purple",
)

SOURCE_ONE_TYPES = ("ngs", "beacon")

ENG_TYPE_OPTIONS = (
    "亲和力",
    "人源化",
    "去PTM",
    "Tm",
    "PI",
    "亲水性",
    "稳定性",
    "CIC",
    "HIC",
    "Tagg",
    "糖基化",
    "氧化风险",
    "脱酰胺风险",
    "同家族交叉",
    "VHH序列改造",
    "改亚型",
    "其他",
)

ENG_METHOD_OPTIONS = (
    "AI",
    "NGS姐妹克隆",
    "理性设计",
    "饱和突变",
    "其他",
)

SYNTHETIC_CORP_OPTIONS = (
    "君跻",
    "擎科",
    "金斯瑞",
    "百奥",
    "内部",
)

DRIFT_COMPARE_FIELDS = (
    "order_no",
    "synthetic_corp",
    "synthetic_count",
    "synthetic_date",
    "arrival_count",
    "arrival_date",
)

DRIFT_FIELD_LABELS = {
    "order_no": "订单号",
    "synthetic_corp": "合成公司",
    "synthetic_count": "合成个数",
    "synthetic_date": "合成日期",
    "arrival_count": "到货个数",
    "arrival_date": "到货日期",
}

__all__ = [
    "ACTIVE_STATUSES",
    "AFFINITY_RESULT_ALL_NEG",
    "AFFINITY_RESULT_FEW",
    "AFFINITY_RESULT_NORMAL",
    "AFFINITY_RESULT_OPTIONS",
    "DRIFT_COMPARE_FIELDS",
    "DRIFT_FIELD_LABELS",
    "ENG_METHOD_OPTIONS",
    "ENG_TYPE_OPTIONS",
    "MOUSE_STRAIN_OPTIONS",
    "ORDER_KIND_ENGINEERING",
    "ORDER_KIND_NORMAL",
    "ORDER_KIND_OPTIONS",
    "SELECTION_METHOD_OPTIONS",
    "SOURCE_ONE_TYPES",
    "STATUS_ASSAYING",
    "STATUS_CANCELLED",
    "STATUS_COMPLETED",
    "STATUS_OPTIONS",
    "STATUS_SYNTHESIZING",
    "STATUS_WAIT_ASSAY",
    "STATUS_WAIT_ORDER",
    "SUPPLY_MODE_ARRIVAL",
    "SUPPLY_MODE_INTERNAL",
    "SUPPLY_MODE_ISOTYPE",
    "SUPPLY_MODE_OPTIONS",
    "SYNTHETIC_CORP_OPTIONS",
    "TARGET_COLOR_OPTIONS",
    "TARGET_TYPE_OPTIONS",
    "TERMINAL_STATUSES",
    "UNCLAIMED_OWNER",
]
