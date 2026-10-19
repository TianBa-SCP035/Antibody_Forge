"""文库结果上传的纯规则。

本模块只负责路径识别、建库编号解析、包指纹和序列核对，不读写数据库或磁盘。
列表批量上传和质检页用同一套规则：有标记文件夹时其上一层是一个测序包。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import PurePosixPath
import re

from models.molecular_cell import MolecularLibraryOrder
from modules.molecular_cell.primer_catalog.service import check_sequence as primer_check_sequence

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
TRACE_EXTENSIONS = {".ab1", ".abi"}
READ_EXTENSIONS = TRACE_EXTENSIONS | {".seq"}
PACKAGE_MARKERS = frozenset({"测序结果", "测序合格结果", "完成"})
ARCHIVE_FOLDERS = frozenset({"拼接结果", "去载体序列"})
CODE_BOUNDARIES = set("-_()（）. ")

LIBRARY_CODE_RE = re.compile(r"(?:[HKL])?[NLCX]\d+", re.IGNORECASE)
PRIMER_MARK_RE = re.compile(r"(?<![A-Z0-9])M13([FR])(?![A-Z0-9])")
ROLE_GEL = "gel"
ROLE_READ = "read"
ROLE_PACKAGE = "package"
ROLE_OTHER = "other"
ROLE_SKIP = "skip"

SEQUENCE_MATCHED = "matched"
SEQUENCE_MATCHED_RC = "matched_rc"
SEQUENCE_NOT_FOUND = "not_found"
SEQUENCE_ARM_ONLY = "arm_only"
SEQUENCE_ARM_ONLY_RC = "arm_only_rc"
SEQUENCE_TRACE_ONLY = "trace_only"
MATCHED_STATUSES = frozenset({SEQUENCE_MATCHED, SEQUENCE_MATCHED_RC})
ARM_STATUSES = frozenset({SEQUENCE_ARM_ONLY, SEQUENCE_ARM_ONLY_RC})
FORWARD_ARM_1 = "ACCGAGATCTACAC"
FORWARD_ARM_2 = "ACACTCTTTCC"
REVERSE_ARM_1 = "GGCATACGAGAT"
REVERSE_ARM_2 = "GTGACTGGAGTT"
PRIMER_TARGET_LABELS = {
    "i5": "i5",
    "i7": "i7",
    "hF": "H链正向",
    "hR": "H链反向",
    "kF": "K链正向",
    "kR": "K链反向",
    "lF": "L链正向",
    "lR": "L链反向",
}


@dataclass(frozen=True)
class PackagePathGroup:
    root: str
    entries: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class UploadPathPlan:
    paths: tuple[str, ...]
    packages: tuple[PackagePathGroup, ...]
    loose_indexes: tuple[int, ...]


def extension_of(filename: str) -> str:
    suffix = PurePosixPath(filename or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ""


def normalize_relative_path(value: str | None, filename: str) -> str:
    raw = (value or filename or "").replace("\\", "/").strip("/")
    parts = [part for part in PurePosixPath(raw).parts if part not in {"", ".", ".."}]
    if not parts:
        parts = [PurePosixPath(filename or "file").name or "file"]
    return "/".join(parts)


def _marked_package_roots(paths: list[str]) -> set[str]:
    """标记文件夹的上一层是一包；标记就在最外层时，它自己是一包。"""
    roots: set[str] = set()
    for path in paths:
        parts = PurePosixPath(path).parts
        for index, part in enumerate(parts[:-1]):
            if part not in PACKAGE_MARKERS:
                continue
            roots.add("/".join(parts[:index]) if index else part)
            break
    return {
        root
        for root in roots
        if not any(other != root and root.startswith(f"{other}/") for other in roots)
    }


def _top_folder_roots(paths: list[str]) -> set[str]:
    return {
        PurePosixPath(path).parts[0]
        for path in paths
        if len(PurePosixPath(path).parts) > 1
    }


def locate_in_package(relative_path: str, package_roots: set[str]) -> tuple[str, str] | None:
    path = normalize_relative_path(relative_path, relative_path)
    for root in sorted(package_roots, key=len, reverse=True):
        if path.startswith(f"{root}/"):
            return root, path[len(root) + 1 :]
    return None


def plan_upload_paths(relative_paths: list[str]) -> UploadPathPlan:
    """按标记文件夹拆包。没有标记时，每个顶层文件夹自己是一包。"""
    paths = tuple(normalize_relative_path(path, path) for path in relative_paths)
    roots = _marked_package_roots(list(paths)) or _top_folder_roots(list(paths))
    grouped: dict[str, list[tuple[int, str]]] = {root: [] for root in roots}
    loose: list[int] = []

    for index, path in enumerate(paths):
        located = locate_in_package(path, roots)
        if located:
            root, inner_path = located
            grouped[root].append((index, inner_path))
            continue
        loose.append(index)

    return UploadPathPlan(
        paths=paths,
        packages=tuple(
            PackagePathGroup(root, tuple(entries))
            for root, entries in sorted(grouped.items())
            if entries
        ),
        loose_indexes=tuple(loose),
    )


def package_name(root: str) -> str:
    return PurePosixPath(root).name or "package"


def package_file_role(inner_path: str) -> str:
    """包内的 ab1/abi/seq 参与匹配。拼接结果和去载体序列只保存。"""
    parts = PurePosixPath(normalize_relative_path(inner_path, inner_path)).parts
    if any(part in ARCHIVE_FOLDERS for part in parts[:-1]):
        return ROLE_PACKAGE
    if extension_of(parts[-1]) in READ_EXTENSIONS:
        return ROLE_READ
    return ROLE_PACKAGE


def loose_file_role(relative_path: str, *, current_order: bool) -> str:
    filename = PurePosixPath(normalize_relative_path(relative_path, relative_path)).name
    suffix = extension_of(filename)
    if suffix in IMAGE_EXTENSIONS:
        return ROLE_GEL
    if suffix in READ_EXTENSIONS:
        return ROLE_READ
    return ROLE_OTHER if current_order else ROLE_SKIP


def library_token_parts(token: str) -> tuple[str, str]:
    """HC223 → (建库编号 C223, 链 H)。没有链前缀时链为空。"""
    text = str(token or "").upper()
    chained = re.fullmatch(r"([HKL])([NLCX]\d+)", text)
    if chained:
        return chained.group(2), chained.group(1)
    return text, ""


def library_codes_in_name(filename: str) -> list[str]:
    """文件名里出现的建库编号。HC223 记成 C223，链别另看。编号前不能再紧挨着字母或数字。"""
    name = PurePosixPath(filename or "").name
    found: list[str] = []
    for match in LIBRARY_CODE_RE.finditer(name):
        if match.start() and name[match.start() - 1].isalnum():
            continue
        code, _chain = library_token_parts(match.group(0))
        if code not in found:
            found.append(code)
    return found


def leading_library_token(filename: str) -> str:
    name = PurePosixPath(filename or "").name
    match = LIBRARY_CODE_RE.match(name)
    return match.group(0).upper() if match else ""


def code_match_head(filename: str) -> str:
    """HC223_… 去掉链字母后再和工单编号比较。"""
    name = PurePosixPath(filename or "").name.upper()
    if re.match(r"[HKL](?=[NLCX]\d+)", name):
        return name[1:]
    return name


def library_code_stem(filename: str) -> str:
    """文件名开头的短编号，用来缩小工单查询。C766-L169_… 得到 C766。"""
    matched = re.match(r"[NLCX]\d+", code_match_head(filename))
    return matched.group(0) if matched else ""


def read_direction(filename: str) -> str:
    """文件名里的 M13F、M13R 决定核 i5 端还是 i7 端。两个都有则不猜。"""
    name = PurePosixPath(filename or "").name.upper()
    marks = {item.group(1) for item in PRIMER_MARK_RE.finditer(name)}
    if len(marks) == 1:
        return marks.pop()
    return ""


def longest_library_code(filename: str, codes: list[str | None]) -> str:
    """取工单编号里最长的前缀。编号后面必须是分隔符或结束。"""
    head = code_match_head(filename)
    best = ""
    for raw in codes:
        code = str(raw or "").strip().upper()
        if len(code) <= len(best) or not head.startswith(code):
            continue
        if len(head) == len(code) or head[len(code)] in CODE_BOUNDARIES:
            best = code
    return best


def parse_library_filename(filename: str) -> tuple[str, str]:
    """返回 (短编号, F/R/空)。工单归属用最长前缀，不看这个短编号。"""
    return library_code_stem(filename), read_direction(filename)


def parse_chain(filename: str) -> str:
    """链别只看开头的 H/K/L 前缀。HC223 是 H 链，C223-H-1 这种旧写法不算。"""
    _code, chain = library_token_parts(leading_library_token(filename))
    return chain


def primer_body(primer: str) -> str:
    """显示序列去掉空白后转成核对序列。文件里要找的就是这一串，不再反向。"""
    shown = re.sub(r"\s+", "", str(primer or "").upper())
    return primer_check_sequence(shown)


def direction_arms(direction: str) -> tuple[str, str]:
    if direction == "F":
        return FORWARD_ARM_1, FORWARD_ARM_2
    return REVERSE_ARM_1, REVERSE_ARM_2


def assembled_primer(primer: str, direction: str) -> str:
    """i5 端用 i5 同源臂加核对序列，i7 端用 i7 那一套。中间用核对序列，不是显示序列。"""
    left, right = direction_arms(direction)
    return f"{left}{primer_body(primer)}{right}"


def safe_path_part(value: str, fallback: str) -> str:
    text = re.sub(r'[<>:"|?*\x00-\x1f]', "_", (value or "").strip())
    text = text.strip(". ") or fallback
    if len(text) <= 80:
        return text
    suffix = extension_of(text)
    stem = text[: -len(suffix)] if suffix else text
    room = 80 - len(suffix)
    if suffix and stem and room > 0:
        return f"{stem[:room]}{suffix}"
    return text[:80]


def preview_extension(storage_name: str, original_name: str, recognized: set[str]) -> str:
    """磁盘名被截断时，用原始文件名判断预览格式。"""
    disk = extension_of(storage_name)
    named = extension_of(original_name)
    if disk in recognized:
        return disk
    if named in recognized:
        return named
    return disk or named


def month_directory(kind: str, now: datetime) -> str:
    return f"library_results/{kind}/{now.strftime('%Y')}/{now.strftime('%m')}"


def other_directory(order: MolecularLibraryOrder, now: datetime) -> str:
    order_key = safe_path_part(order.library_order_id, f"order-{order.id}")
    return f"library_results/others/{now.strftime('%Y')}/{order_key}"


def package_signature(
    name: str,
    files: list[tuple[str, str, int]],
) -> str:
    """包名和规范化文件清单共同组成稳定、可重试的包指纹。"""
    digest = hashlib.sha256()
    digest.update((name or "").strip().casefold().encode("utf-8"))
    digest.update(b"\0")
    for relative_path, file_hash, byte_size in sorted(
        files,
        key=lambda item: (item[0].casefold(), item[1]),
    ):
        digest.update(normalize_relative_path(relative_path, relative_path).casefold().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(byte_size).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def primer_slot(filename: str, direction: str, primers: dict[str, str]) -> str:
    """只返回这份工单实际要核对的目标。没加的方向不返回。"""
    if not primers or direction not in {"F", "R"}:
        return ""
    hkl = any(len(key) == 2 and key[0] in "hkl" for key in primers)
    if hkl:
        chain = parse_chain(filename)
        key = f"{chain.lower()}{direction}" if chain else ""
        return key if key in primers else ""
    key = "i5" if direction == "F" else "i7"
    return key if key in primers else ""


def _observed_sequence(content: bytes) -> str:
    text = content.decode("utf-8", "replace")
    return "".join(
        re.sub(r"[\s\d]+", "", line.upper())
        for line in text.splitlines()
        if not line.lstrip().startswith(">")
    )


def _wrong_middle_side(observed: str, left: str, right: str, middle: str) -> str:
    if _wrong_middle(observed, left, right, middle):
        return "direct"
    if _wrong_middle(
        observed,
        primer_check_sequence(right),
        primer_check_sequence(left),
        primer_check_sequence(middle),
    ):
        return "rc"
    return ""


def _wrong_middle(observed: str, left: str, right: str, expected_middle: str) -> bool:
    start = 0
    while True:
        opening = observed.find(left, start)
        if opening < 0:
            return False
        closing = observed.find(right, opening + len(left))
        if closing < 0:
            return False
        middle = observed[opening + len(left):closing]
        if len(middle) == len(expected_middle) and middle != expected_middle:
            return True
        start = opening + 1


def classify_observed(observed: str, primer: str, direction: str) -> str:
    """同一套规则：整段、整段反补、同源臂对上但引物不对、都没有。"""
    expected = assembled_primer(primer, direction)
    if expected in observed:
        return SEQUENCE_MATCHED
    if primer_check_sequence(expected) in observed:
        return SEQUENCE_MATCHED_RC
    left, right = direction_arms(direction)
    side = _wrong_middle_side(observed, left, right, primer_body(primer))
    if side == "direct":
        return SEQUENCE_ARM_ONLY
    if side == "rc":
        return SEQUENCE_ARM_ONLY_RC
    return SEQUENCE_NOT_FOUND


def called_bases_from_abi(content: bytes) -> str:
    """读 ABI/AB1 里已经判出的碱基。读不出来就返回空，核对显示保持不做结论。"""
    try:
        from io import BytesIO

        from Bio import SeqIO

        record = SeqIO.read(BytesIO(content), "abi")
        raw = record.annotations.get("abif_raw", {})
        base_calls = raw.get("PBAS2", bytes(str(record.seq), "ascii"))
        if isinstance(base_calls, bytes):
            base_calls = base_calls.decode("ascii", "ignore")
    except Exception:
        return ""
    return re.sub(r"[^ACGTN]", "", str(base_calls).upper())


def sequence_check(
    filename: str,
    content: bytes,
    primers: dict[str, str],
) -> tuple[str | None, str | None]:
    """只核这份文件自己的方向。引物字典里没有的方向直接跳过。"""
    code, direction = parse_library_filename(filename)
    if not code or direction not in {"F", "R"}:
        return None, None
    target = primer_slot(filename, direction, primers)
    if not target:
        return None, None
    if extension_of(filename) in TRACE_EXTENSIONS:
        observed = called_bases_from_abi(content)
        if not observed:
            return SEQUENCE_TRACE_ONLY, target
        return classify_observed(observed, primers[target], direction), target
    if extension_of(filename) != ".seq":
        return None, None
    return classify_observed(_observed_sequence(content), primers[target], direction), target


def sequence_check_text(status: str | None, target: str | None) -> str | None:
    label = PRIMER_TARGET_LABELS.get(target or "", target or "引物")
    if status == SEQUENCE_MATCHED:
        return f"{label} 匹配"
    if status == SEQUENCE_MATCHED_RC:
        return f"{label} 匹配-反补"
    if status == SEQUENCE_ARM_ONLY:
        return f"{label} 引物错误"
    if status == SEQUENCE_ARM_ONLY_RC:
        return f"{label} 引物错误-反补"
    if status == SEQUENCE_NOT_FOUND:
        return f"{label} 同源臂未匹配"
    return None
