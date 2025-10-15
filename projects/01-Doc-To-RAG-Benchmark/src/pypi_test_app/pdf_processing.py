from __future__ import annotations

import io
from typing import Iterable, Tuple

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter


LayoutMetrics = dict[str, float | int]


def _measure_page_layout(page: fitz.Page) -> LayoutMetrics:
    rect = page.rect
    width = float(rect.width)
    height = float(rect.height)
    page_area = width * height if width > 0 and height > 0 else 0.0
    mid_x = rect.x0 + width / 2 if width > 0 else 0.0
    center_band_width = width * 0.12
    left_boundary = mid_x - center_band_width / 2
    right_boundary = mid_x + center_band_width / 2

    metrics: LayoutMetrics = {
        "page_area": page_area,
        "left_area": 0.0,
        "right_area": 0.0,
        "center_area": 0.0,
        "left_blocks": 0,
        "right_blocks": 0,
        "bridge_blocks": 0,
        "bridge_area": 0.0,
        "max_block_width_ratio": 0.0,
    }

    if page_area == 0.0:
        return metrics

    for block in page.get_text("blocks"):
        if len(block) < 4:
            continue
        x0, y0, x1, y1 = block[:4]
        block_width = max(0.0, float(x1) - float(x0))
        block_height = max(0.0, float(y1) - float(y0))
        if block_width <= 0 or block_height <= 0:
            continue

        area = block_width * block_height
        if area == 0:
            continue

        left_width = max(0.0, min(x1, mid_x) - x0)
        right_width = max(0.0, x1 - max(x0, mid_x))
        left_ratio = left_width / block_width if block_width else 0.0
        right_ratio = right_width / block_width if block_width else 0.0

        if left_ratio > 0:
            metrics["left_area"] += area * left_ratio
        if right_ratio > 0:
            metrics["right_area"] += area * right_ratio

        band_left = max(x0, left_boundary)
        band_right = min(x1, right_boundary)
        band_width = max(0.0, band_right - band_left)
        if band_width > 0 and block_width > 0:
            metrics["center_area"] += area * (band_width / block_width)

        metrics["max_block_width_ratio"] = max(
            metrics["max_block_width_ratio"], block_width / max(width, 1.0)
        )

        if x1 <= mid_x:
            metrics["left_blocks"] += 1
        elif x0 >= mid_x:
            metrics["right_blocks"] += 1
        else:
            metrics["bridge_blocks"] += 1
            overlap_ratio = min(left_ratio, right_ratio)
            if overlap_ratio > 0:
                metrics["bridge_area"] += area * overlap_ratio

    return metrics


def _is_double_page(pil_img: Image.Image, layout: LayoutMetrics | None = None) -> bool:
    """Heuristically detect double-page spreads based on layout signals."""

    grayscale = np.array(pil_img.convert("L"))
    height, width = grayscale.shape
    if height == 0 or width == 0:
        return False

    aspect_ratio = width / max(height, 1)

    # Highlight foreground (text, drawings) to compare the halves and central gap.
    _, binary = cv2.threshold(grayscale, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    foreground = binary > 0

    if aspect_ratio < 1.1:
        return False

    mid_x = width // 2
    gap_half_width = max(2, int(width * 0.03))  # Central 6% band for gap detection
    left_end = max(0, mid_x - gap_half_width)
    right_start = min(width, mid_x + gap_half_width)

    def _region_density(region: np.ndarray | None) -> float:
        if region is None or region.size == 0:
            return 0.0
        return float(np.mean(region))

    left_region = foreground[:, :left_end] if left_end > 0 else None
    right_region = foreground[:, right_start:] if right_start < width else None
    centre_region = foreground[:, left_end:right_start] if right_start > left_end else None

    left_density = _region_density(left_region)
    right_density = _region_density(right_region)
    centre_density = _region_density(centre_region)

    column_density = foreground.mean(axis=0)
    left_profile = float(column_density[:left_end].mean()) if left_end > 0 else 0.0
    right_profile = float(column_density[right_start:].mean()) if right_start < width else 0.0
    centre_profile = float(column_density[left_end:right_start].mean()) if right_start > left_end else 1.0

    side_profile = min(value for value in (left_profile, right_profile) if value > 0) if any(
        value > 0 for value in (left_profile, right_profile)
    ) else 0.0

    aspect_condition = aspect_ratio >= 1.2
    density_condition = (
        left_density > 0.02
        and right_density > 0.02
        and centre_density < min(left_density, right_density) * 0.6
    )
    profile_condition = side_profile > 0 and centre_profile < side_profile * 0.5

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_contours = 0
    right_contours = 0
    for contour in contours:
        x, _, w_box, _ = cv2.boundingRect(contour)
        centre_x = x + w_box // 2
        if centre_x < mid_x:
            left_contours += 1
        else:
            right_contours += 1
    contour_condition = left_contours > 3 and right_contours > 3

    column_density = foreground.mean(axis=0)
    window = max(3, int(width * 0.01))
    if window % 2 == 0:
        window += 1
    if window > 1:
        kernel = np.ones(window, dtype=np.float64) / window
        smoothed = np.convolve(column_density, kernel, mode="same")
    else:
        smoothed = column_density

    centre_window = max(3, int(width * 0.16))
    centre_start = max(0, mid_x - centre_window // 2)
    centre_end = min(width, mid_x + centre_window // 2)
    centre_band = smoothed[centre_start:centre_end]

    band_min = float(np.min(centre_band)) if centre_band.size else 1.0
    left_mean = float(np.mean(smoothed[:mid_x])) if mid_x > 0 else 0.0
    right_mean = float(np.mean(smoothed[mid_x:])) if mid_x < width else 0.0
    side_mean = min(value for value in (left_mean, right_mean) if value > 0) if any(
        value > 0 for value in (left_mean, right_mean)
    ) else 0.0

    seam_condition = side_mean > 0 and band_min < side_mean * 0.4

    return aspect_condition and (
        density_condition or profile_condition or contour_condition or seam_condition
    )


def _split_page(pil_img: Image.Image, layout: LayoutMetrics | None = None) -> Iterable[Image.Image]:
    if _is_double_page(pil_img, layout):
        width, height = pil_img.size
        left = pil_img.crop((0, 0, width // 2, height))
        right = pil_img.crop((width // 2, 0, width, height))
        return (left, right)
    return (pil_img,)


def _render_pages(source: bytes, dpi: int) -> list[Tuple[Image.Image, LayoutMetrics]]:
    try:
        with fitz.open(stream=source, filetype="pdf") as pdf:
            zoom = max(dpi, 72) / 72
            matrix = fitz.Matrix(zoom, zoom)
            pages: list[Tuple[Image.Image, LayoutMetrics]] = []
            for page in pdf:
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                layout = _measure_page_layout(page)
                pages.append((image.copy(), layout))
            return pages
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"PDF 렌더링에 실패했습니다: {exc}") from exc


def process_pdf_bytes(source: bytes, dpi: int = 200) -> bytes:
    """Process the PDF bytes and return a new PDF with double pages split."""
    pil_pages = _render_pages(source, dpi)
    if not pil_pages:
        return source

    writer = PdfWriter()
    buffers: list[io.BytesIO] = []

    for pil_page, layout in pil_pages:
        for segment in _split_page(pil_page, layout):
            segment_rgb = segment.convert("RGB")
            pdf_buffer = io.BytesIO()
            segment_rgb.save(pdf_buffer, format="PDF")
            pdf_buffer.seek(0)
            buffers.append(pdf_buffer)

            reader = PdfReader(pdf_buffer)
            writer.add_page(reader.pages[0])

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    for buffer in buffers:
        buffer.close()

    return output.read()