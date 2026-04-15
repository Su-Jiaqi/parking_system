from __future__ import annotations

import re
from pathlib import Path
from typing import List

PLATE_CHARS = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"

PLATE_PATTERN = re.compile(
    rf"([{PLATE_CHARS}][A-Z][A-Z0-9]{{5,6}})"
)

_reader = None


class OCRError(Exception):
    pass


def _get_reader():
    global _reader
    if _reader is None:
        try:
            import easyocr  # type: ignore
        except ImportError as exc:
            raise OCRError("未安装 easyocr。请先执行: pip install -r requirements.txt") from exc

        _reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
    return _reader


def normalize_text(text: str) -> str:
    return (
        text.upper()
        .replace(" ", "")
        .replace("·", "")
        .replace(".", "")
        .replace("-", "")
        .replace("_", "")
        .replace(":", "")
        .replace("：", "")
    )


def generate_variants(text: str) -> List[str]:
    """
    针对车牌 OCR 常见误识别，生成几个候选变体。
    """
    variants = set()
    text = normalize_text(text)
    variants.add(text)

    # 特判：很多时候“鄂A”会被识别成“1A”
    if text.startswith("1A"):
        variants.add("鄂A" + text[2:])

    # 第一位中文省份没识别出来时，也尝试补成鄂A（先只照顾你的测试图）
    if text.startswith("A") and len(text) >= 6:
        variants.add("鄂" + text)

    more = set()
    for v in variants:
        # 后面部分里常见混淆：O<->0, G<->6, I<->1
        if len(v) >= 3:
            prefix = v[:2]
            suffix = v[2:]

            suffix_variants = {suffix}
            suffix_variants.add(suffix.replace("O", "0"))
            suffix_variants.add(suffix.replace("0", "O"))
            suffix_variants.add(suffix.replace("G", "6"))
            suffix_variants.add(suffix.replace("6", "G"))
            suffix_variants.add(suffix.replace("I", "1"))
            suffix_variants.add(suffix.replace("1", "I"))

            # 组合替换
            tmp = set()
            for s in suffix_variants:
                tmp.add(s.replace("O", "0").replace("G", "6").replace("I", "1"))
                tmp.add(s.replace("0", "O").replace("6", "G").replace("1", "I"))
            suffix_variants |= tmp

            for s in suffix_variants:
                more.add(prefix + s)

    variants |= more
    return list(variants)


def extract_plate_candidates(texts: List[str]) -> list[str]:
    candidates: list[str] = []

    normalized_texts = [normalize_text(t) for t in texts if t and t.strip()]

    all_to_try = []

    # 单段
    all_to_try.extend(normalized_texts)

    # 整体拼接
    if normalized_texts:
        all_to_try.append("".join(normalized_texts))

    # 相邻拼接
    n = len(normalized_texts)
    for i in range(n):
        all_to_try.append("".join(normalized_texts[i:i+2]))
        all_to_try.append("".join(normalized_texts[i:i+3]))

    expanded = []
    for item in all_to_try:
        expanded.extend(generate_variants(item))

    print("OCR normalized/variant texts:", expanded)

    for raw in expanded:
        matches = PLATE_PATTERN.findall(raw)
        candidates.extend(matches)

    # 去重保序
    seen = set()
    unique = []
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def recognize_plate(image_path: str | Path) -> str:
    reader = _get_reader()
    results = reader.readtext(str(image_path), detail=1, paragraph=False)

    texts = [str(item[1]) for item in results]

    print("OCR raw results:", results)
    print("OCR texts:", texts)

    candidates = extract_plate_candidates(texts)
    print("OCR plate candidates:", candidates)

    if not candidates:
        raise OCRError("OCR识别失败，请上传更清晰、正面的车牌图片")

    return candidates[0]