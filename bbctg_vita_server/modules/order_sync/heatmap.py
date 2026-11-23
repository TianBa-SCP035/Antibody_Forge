"""镁伽热图 CSV（国产「统计项」格式）解析阳性孔，规则与前端 utils/facsExcelPositive.ts 一致。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import io
from pathlib import Path

POSITIVE_RATE_THRESHOLD = 15
_ROW_LABELS = "ABCDEFGH"


@dataclass
class HeatmapResult:
    positive_wells: list[str] = field(default_factory=list)
    error: str = ""


def read_rows(path: Path) -> list[list[str]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    return list(csv.reader(io.StringIO(text)))


def _cell(row: list[str], index: int) -> str:
    return row[index].strip().strip('"') if 0 <= index < len(row) else ""


def _number(text: str) -> float | None:
    raw = text.replace("%", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _scan_from(rows: list[list[str]]) -> int:
    for index, row in enumerate(rows):
        line = ",".join(_cell(row, i) for i in range(len(row)))
        if "统计项" in line and "%Parent" in line:
            return index
    return 0


def _scan_stop(rows: list[list[str]], start: int) -> int:
    for index in range(start, len(rows)):
        first = _cell(rows[index], 0)
        if first in {"样品", "已计算"}:
            return index
        if first == "统计项" and index > start:
            return index
    return len(rows)


def _well_column_start(rows: list[list[str]], start: int, stop: int) -> int:
    for index in range(start, stop):
        row = rows[index]
        for offset in range(4):
            if _cell(row, offset) == "1" and _cell(row, offset + 11) == "12":
                return offset
    return 1


def _extract_matrix(rows: list[list[str]], start: int) -> list[list[float]] | None:
    stop = _scan_stop(rows, start)
    offset = _well_column_start(rows, start, stop)
    matrix = [[0.0] * 12 for _ in range(8)]
    found = False
    for index in range(start, stop):
        row = rows[index]
        label = _cell(row, 0).upper()
        if len(label) != 1 or label not in _ROW_LABELS:
            continue
        values = matrix[_ROW_LABELS.index(label)]
        for column in range(12):
            value = _number(_cell(row, offset + column))
            if value is not None:
                values[column] = value
                found = True
    return matrix if found else None


def parse_heatmap(rows: list[list[str]]) -> HeatmapResult:
    text = "\n".join(",".join(row) for row in rows)
    if "统计项" not in text:
        return HeatmapResult(error="热图不是国产「统计项」格式")
    matrix = _extract_matrix(rows, _scan_from(rows))
    if matrix is None:
        return HeatmapResult(error="热图里没有找到 %Parent 阳性率表")
    values = [value for row in matrix for value in row if value > 0]
    if values and max(values) <= 1:
        matrix = [[value * 100 if value > 0 else value for value in row] for row in matrix]
    wells = [
        f"{_ROW_LABELS[row]}{column + 1}"
        for row in range(8)
        for column in range(12)
        if matrix[row][column] > POSITIVE_RATE_THRESHOLD
    ]
    return HeatmapResult(positive_wells=wells)
