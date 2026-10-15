"""文库结果上传的纯规则。

本模块只负责路径识别、建库编号解析、包指纹和序列核对，不读写数据库或磁盘。
列表批量入口只接受三个已知目录齐全的标准测序包；质检页也可把普通文件夹
作为一个完整文件夹归属当前工单。
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
READ_FOLDER = "测序结果"
ASSEMBLY_FOLDER = "拼接结果"
TRIMMED_FOLDER = "去载体序列"
KNOWN_PACKAGE_FOLDERS = (READ_FOLDER, ASSEMBLY_FOLDER, TRIMMED_FOLDER)

LIBRARY_CODE_RE = re.compile(r"(?:[HKL])?[NLCX]\d+", re.IGNORECASE)
ROLE_GEL = "gel"
ROLE_READ = "read"
ROLE_PACKAGE = "package"
ROLE_OTHER = "other"
ROLE_SKIP = "skip"

SEQUENCE_MATCHED = "matched"
SEQUENCE_NOT_FOUND = "not_found"
SEQUENCE_ARM_ONLY = "arm_only"
SEQUENCE_TRACE_ONLY = "trace_only"
FORWARD_ARM_1 = "ACCGAGATCTACAC"
FORWARD_ARM_2 = "ACACTCTTTCC"
REVERSE_ARM_1 = "AACTCCAGTCAC"
REVERSE_ARM_2 = "ATCTCGTATGCC"
PRIMER_TARGET_LABELS = {
    "i5": "i5",
    "i7": "i7",
    "hF": "H 正向",
    "hR": "H 反向",
    "kF": "K 正向",
    "kR": "K 反向",
    "lF": "L 正向",
    "lR": "L 反向",
}


@dataclass(frozen=True)
class PackagePathGroup:
    root: str
    entries: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class RejectedPackageGroup:
    root: str
    indexes: tuple[int, ...]
    missing_folders: tuple[str, ...]


@dataclass(frozen=True)
class UploadPathPlan:
    paths: tuple[str, ...]
    packages: tuple[PackagePathGroup, ...]
    rejected_packages: tuple[RejectedPackageGroup, ...]
    rootless_indexes: tuple[int, ...]
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


def package_folder_sets(paths: list[str]) -> dict[str, set[str]]:
    """返回每个候选包根目录下实际出现的已知直接子目录。"""
    roots: dict[str, set[str]] = {}
    for raw in paths:
        parts = PurePosixPath(normalize_relative_path(raw, raw)).parts
        for index, part in enumerate(parts[:-1]):
            if part in KNOWN_PACKAGE_FOLDERS and index:
                root = "/".join(parts[:index])
                roots.setdefault(root, set()).add(part)
    return roots


def complete_package_roots(paths: list[str]) -> set[str]:
    required = set(KNOWN_PACKAGE_FOLDERS)
    return {
        root
        for root, folders in package_folder_sets(paths).items()
        if folders == required
    }


def incomplete_package_roots(paths: list[str]) -> dict[str, tuple[str, ...]]:
    required = set(KNOWN_PACKAGE_FOLDERS)
    return {
        root: tuple(folder for folder in KNOWN_PACKAGE_FOLDERS if folder not in folders)
        for root, folders in package_folder_sets(paths).items()
        if folders != required
    }


def detail_folder_roots(paths: list[str]) -> set[str]:
    """质检页把每个有子路径的顶层目录作为普通文件夹。"""
    return {
        PurePosixPath(normalize_relative_path(path, path)).parts[0]
        for path in paths
        if len(PurePosixPath(normalize_relative_path(path, path)).parts) > 1
    }


def locate_in_package(relative_path: str, package_roots: set[str]) -> tuple[str, str] | None:
    path = normalize_relative_path(relative_path, relative_path)
    for root in sorted(package_roots, key=len, reverse=True):
        if path.startswith(f"{root}/"):
            return root, path[len(root) + 1 :]
    return None


def plan_upload_paths(relative_paths: list[str], *, strict_batch: bool) -> UploadPathPlan:
    """仅按路径规划包、零散文件和拒绝项，不读取文件内容。"""
    paths = tuple(normalize_relative_path(path, path) for path in relative_paths)
    complete = complete_package_roots(list(paths))
    incomplete = incomplete_package_roots(list(paths)) if strict_batch else {}
    roots = complete if strict_batch else detail_folder_roots(list(paths))
    grouped: dict[str, list[tuple[int, str]]] = {root: [] for root in roots}
    rejected: dict[str, list[int]] = {}
    rootless: list[int] = []
    loose: list[int] = []

    for index, path in enumerate(paths):
        first_part = path.split("/", 1)[0]
        if strict_batch and first_part in KNOWN_PACKAGE_FOLDERS:
            rootless.append(index)
            continue
        located = locate_in_package(path, roots)
        if located:
            root, inner_path = located
            grouped[root].append((index, inner_path))
            continue
        partial = locate_in_package(path, set(incomplete))
        if strict_batch and partial:
            rejected.setdefault(partial[0], []).append(index)
            continue
        loose.append(index)

    return UploadPathPlan(
        paths=paths,
        packages=tuple(
            PackagePathGroup(root, tuple(entries))
            for root, entries in sorted(grouped.items())
            if entries
        ),
        rejected_packages=tuple(
            RejectedPackageGroup(root, tuple(indexes), incomplete[root])
            for root, indexes in sorted(rejected.items())
        ),
        rootless_indexes=tuple(rootless),
        loose_indexes=tuple(loose),
    )


def package_name(root: str) -> str:
    return PurePosixPath(root).name or "package"


def package_file_role(inner_path: str, *, strict: bool) -> str:
    """分类包内文件。测序编号只认「测序结果」，拼接结果和去载体序列只保存。"""
    inner = normalize_relative_path(inner_path, inner_path)
    parts = PurePosixPath(inner).parts
    if strict and len(parts) > 1 and parts[0] not in KNOWN_PACKAGE_FOLDERS:
        return ROLE_SKIP
    filename = parts[-1]
    suffix = extension_of(filename)
    folder = parts[0] if len(parts) > 1 else ""
    if suffix in READ_EXTENSIONS and folder == READ_FOLDER:
        return ROLE_READ
    if (
        not strict
        and suffix in READ_EXTENSIONS
        and folder not in {ASSEMBLY_FOLDER, TRIMMED_FOLDER}
    ):
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


def parse_library_filename(filename: str) -> tuple[str, str]:
    """返回 (建库编号, F/R/空)。测序结果的编号取文件名开头，HC223 的建库编号是 C223。"""
    token = leading_library_token(filename)
    if not token:
        return "", ""
    code, _chain = library_token_parts(token)
    upper = PurePosixPath(filename or "").name.upper()
    direction = ""
    if "_M13F" in upper or "-M13F" in upper:
        direction = "F"
    elif "_M13R" in upper or "-M13R" in upper:
        direction = "R"
    return code, direction


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
    """正向读数对正向同源臂加引物核对序列，反向读数对反向那一套。中间用核对序列，不是显示序列。"""
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
        return SEQUENCE_TRACE_ONLY, target
    if extension_of(filename) != ".seq":
        return None, None
    observed = _observed_sequence(content)
    if assembled_primer(primers[target], direction) in observed:
        return SEQUENCE_MATCHED, target
    left, right = direction_arms(direction)
    if _wrong_middle(observed, left, right, primer_body(primers[target])):
        return SEQUENCE_ARM_ONLY, target
    return SEQUENCE_NOT_FOUND, target


def sequence_check_text(status: str | None, target: str | None) -> str | None:
    label = PRIMER_TARGET_LABELS.get(target or "", target or "引物")
    if status == SEQUENCE_MATCHED:
        return f"{label} 与核对序列一致"
    if status == SEQUENCE_ARM_ONLY:
        return f"同源臂对上，{label} 不对"
    if status == SEQUENCE_NOT_FOUND:
        return f"序列中未找到 {label} 核对序列"
    return None
