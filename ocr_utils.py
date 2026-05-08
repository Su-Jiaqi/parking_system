from __future__ import annotations

import re
from pathlib import Path
from typing import List

CN_PLATE_CHARS = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
CN_PLATE_PATTERN = re.compile(rf"([{CN_PLATE_CHARS}][A-Z][A-Z0-9]{{5,6}})")
GENERIC_PLATE_PATTERN = re.compile(r"\b([A-Z0-9]{5,8})\b")

COMMON_NOISE_WORDS = {
    "NEW",
    "YORK",
    "NEWYORK",
    "EXCELSIOR",
    "USA",
    "TAXI",
}

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
        .replace("路", "")
        .replace(".", "")
        .replace("-", "")
        .replace("_", "")
        .replace(":", "")
        .replace("：", "")
    )


def generate_variants(text: str) -> List[str]:
    variants = set()
    text = normalize_text(text)
    if not text:
        return []

    variants.add(text)

    more = set()
    for value in variants:
        if len(value) < 3:
            continue

        prefix = value[:2]
        suffix = value[2:]
        suffix_variants = {suffix}
        suffix_variants.add(suffix.replace("O", "0"))
        suffix_variants.add(suffix.replace("0", "O"))
        suffix_variants.add(suffix.replace("G", "6"))
        suffix_variants.add(suffix.replace("6", "G"))
        suffix_variants.add(suffix.replace("I", "1"))
        suffix_variants.add(suffix.replace("1", "I"))
        suffix_variants.add(suffix.replace("B", "8"))
        suffix_variants.add(suffix.replace("8", "B"))

        combined = set()
        for item in suffix_variants:
            combined.add(item.replace("O", "0").replace("G", "6").replace("I", "1").replace("B", "8"))
            combined.add(item.replace("0", "O").replace("6", "G").replace("1", "I").replace("8", "B"))
        suffix_variants |= combined

        for item in suffix_variants:
            more.add(prefix + item)

    variants |= more
    return list(variants)


def looks_like_generic_plate(text: str) -> bool:
    if text in COMMON_NOISE_WORDS:
        return False
    if not (5 <= len(text) <= 8):
        return False
    has_letter = any(char.isalpha() for char in text)
    has_digit = any(char.isdigit() for char in text)
    return has_letter and has_digit


def score_plate_candidate(candidate: str) -> tuple[int, int]:
    digits = sum(char.isdigit() for char in candidate)
    letters = sum(char.isalpha() for char in candidate)

    if candidate and candidate[0] in CN_PLATE_CHARS:
        return (3, len(candidate))

    if 6 <= len(candidate) <= 7 and letters >= 2 and digits >= 2:
        return (2, len(candidate))

    return (1, digits + letters)


def extract_plate_candidates(texts: List[str]) -> list[str]:
    candidates: list[str] = []
    normalized_texts = [normalize_text(text) for text in texts if text and text.strip()]

    all_to_try: list[str] = []
    all_to_try.extend(normalized_texts)

    if normalized_texts:
        all_to_try.append("".join(normalized_texts))

    count = len(normalized_texts)
    for index in range(count):
        all_to_try.append("".join(normalized_texts[index:index + 2]))
        all_to_try.append("".join(normalized_texts[index:index + 3]))

    expanded: list[str] = []
    for item in all_to_try:
        expanded.extend(generate_variants(item))

    seen = set()
    unique_candidates: list[str] = []

    for raw in expanded:
        for match in CN_PLATE_PATTERN.findall(raw):
            if match not in seen:
                unique_candidates.append(match)
                seen.add(match)

        for match in GENERIC_PLATE_PATTERN.findall(raw):
            if looks_like_generic_plate(match) and match not in seen:
                unique_candidates.append(match)
                seen.add(match)

    unique_candidates.sort(key=score_plate_candidate, reverse=True)
    return unique_candidates


def recognize_plate(image_path: str | Path) -> str:
    reader = _get_reader()
    results = reader.readtext(str(image_path), detail=1, paragraph=False)
    texts = [str(item[1]) for item in results]
    candidates = extract_plate_candidates(texts)

    if not candidates:
        raise OCRError("OCR识别失败，请上传更清晰、正面的车牌图片")

    return candidates[0]
