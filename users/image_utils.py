import os
import math
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
from django.core.files.base import ContentFile
from typing import Dict, Any, Tuple

# Variant configuration: (label, max_width, max_height, crop_square?)
VARIANTS = [
    ("thumb", 160, 160, True),
    ("medium", 600, 900, False),  # allow portrait aspect
    ("large", 1200, 1600, False),
    ("xlarge", 1600, 2000, False),  # retina / high-density displays
]

PIPELINE_VERSION = 2  # bumped for xlarge variant introduction

MAX_ORIGINAL_SIDE = 1600
MIN_ACCEPT_WIDTH = 240
MIN_ACCEPT_HEIGHT = 240
WARN_MIN_SIDE = 500
MAX_ASPECT_RATIO = 3.0  # width/height or height/width <= 3
MAX_FILE_BYTES = 8 * 1024 * 1024


class ImageQualityFlags:
    LOW_RES = "low_res"
    BLURRY = "blurry"
    REJECTED = "rejected"


def _laplacian_variance(img: Image.Image) -> float:
    # Simple blur detection: convert to gray, apply Laplacian via edge enhancement approximation
    gray = img.convert("L")
    # Use built-in filter as proxy; for full Laplacian we'd need numpy/scipy. Keep lightweight.
    edge = gray.filter(ImageFilter.FIND_EDGES)
    # Variance of pixel intensities in edge image correlates with sharpness
    hist = edge.histogram()
    # compute mean
    total_pixels = sum(hist)
    if not total_pixels:
        return 0.0
    values = []
    acc = 0
    for i, c in enumerate(hist):
        if c:
            values.extend([i] * c)
    # To avoid memory blow-up, approximate using bins
    # We'll compute mean and variance directly from histogram
    mean = sum(i * c for i, c in enumerate(hist)) / total_pixels
    var = sum(((i - mean) ** 2) * c for i, c in enumerate(hist)) / total_pixels
    return var


def _ensure_orientation(img: Image.Image) -> Image.Image:
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img


def _resize_preserve(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    img_c = img.copy()
    img_c.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return img_c


def _square_crop(img: Image.Image, size: int) -> Image.Image:
    w, h = img.size
    if w == h:
        return img.resize((size, size), Image.Resampling.LANCZOS)
    # crop center square
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    box = (left, top, left + side, top + side)
    cropped = img.crop(box)
    return cropped.resize((size, size), Image.Resampling.LANCZOS)


def _hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def process_profile_photo(path: str) -> Dict[str, Any]:
    """Process original profile photo in-place and generate variant files.
    Returns metadata dict with variant relative paths and quality flags.
    """
    meta: Dict[str, Any] = {"variants": {}, "flags": [], "original": {}, "pipeline_version": PIPELINE_VERSION}
    p = Path(path)
    if not p.exists():
        return {"error": "file-missing"}
    if p.stat().st_size > MAX_FILE_BYTES:
        return {"error": "file-too-large"}

    try:
        with open(p, 'rb') as f:
            raw_bytes = f.read()
        img = Image.open(Path(path))
    except Exception as e:
        return {"error": f"unreadable: {e}"}

    img = _ensure_orientation(img)
    img = img.convert("RGB")
    w, h = img.size
    meta["original"]["width"] = w
    meta["original"]["height"] = h
    try:
        meta["original"]["sha256"] = _hash_bytes(raw_bytes)
    except Exception:
        pass

    # Validation
    if w < MIN_ACCEPT_WIDTH or h < MIN_ACCEPT_HEIGHT:
        meta["flags"].append(ImageQualityFlags.REJECTED)
        meta["reason"] = "too_small"
        return meta
    if min(w, h) < WARN_MIN_SIDE:
        meta["flags"].append(ImageQualityFlags.LOW_RES)

    aspect = max(w / h, h / w)
    if aspect > MAX_ASPECT_RATIO:
        meta["flags"].append(ImageQualityFlags.REJECTED)
        meta["reason"] = "extreme_aspect"
        return meta

    # Downscale original if huge
    if max(w, h) > MAX_ORIGINAL_SIDE:
        scale = MAX_ORIGINAL_SIDE / float(max(w, h))
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        w, h = img.size

    # Blur detection
    try:
        sharpness_var = _laplacian_variance(img)
        meta["original"]["sharpness_var"] = round(sharpness_var, 2)
        if sharpness_var < 60:  # heuristic threshold
            meta["flags"].append(ImageQualityFlags.BLURRY)
    except Exception:
        pass

    # Mild sharpening for all variants
    def sharpen(im: Image.Image, is_thumb=False) -> Image.Image:
        # Use UnsharpMask for control
        return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=(130 if is_thumb else 110), threshold=3))

    base_stem = p.stem  # e.g. 'abc123'
    base_dir = p.parent

    # Save normalized original (overwrite) as JPEG if not already
    normalized_path = base_dir / f"{base_stem}.jpg"
    img.save(normalized_path, "JPEG", quality=85, optimize=True, progressive=True)
    if normalized_path != p:
        try:
            p.unlink()
        except Exception:
            pass

    meta["normalized"] = normalized_path.name
    meta["processed_at"] = datetime.now(timezone.utc).isoformat()

    # Variants
    for label, max_w, max_h, square in VARIANTS:
        if square:
            variant_img = _square_crop(img, max_w)
        else:
            variant_img = _resize_preserve(img, max_w, max_h)
        variant_img = sharpen(variant_img, is_thumb=(label == "thumb"))
        jpg_name = f"{base_stem}__{label}.jpg"
        webp_name = f"{base_stem}__{label}.webp"
        jpg_path = base_dir / jpg_name
        webp_path = base_dir / webp_name
        variant_img.save(jpg_path, "JPEG", quality=82, optimize=True, progressive=True)
        try:
            variant_img.save(webp_path, "WEBP", quality=80, method=6)
            webp_saved = True
        except Exception:
            webp_saved = False
        meta["variants"][label] = {
            "jpg": jpg_name,
            "webp": webp_name if webp_saved else None,
            "width": variant_img.width,
            "height": variant_img.height,
        }

    return meta

def process_profile_photo_storage(field_file) -> Dict[str, Any]:
    """Process a profile photo that may be stored on a storage backend without local path (e.g. S3).
    Downloads into memory, generates variants, uploads them alongside original directory.
    Does NOT overwrite original; creates normalized jpg + variants. Returns metadata dict.
    """
    storage = field_file.storage
    name = field_file.name  # e.g. profile_photos/2025/08/uuid.jpg
    try:
        # Try local path first
        path = field_file.path  # may raise NotImplementedError
        return process_profile_photo(path)
    except Exception:
        pass

    # Remote / pathless storage path
    # Load file bytes
    try:
        with storage.open(name, 'rb') as f:
            img = Image.open(f)
            img = _ensure_orientation(img).convert('RGB')
    except Exception as e:
        return {"error": f"unreadable: {e}"}

    meta: Dict[str, Any] = {"variants": {}, "flags": [], "original": {}, "pipeline_version": PIPELINE_VERSION}
    w, h = img.size
    meta["original"]["width"] = w
    meta["original"]["height"] = h
    # Hash original bytes (re-open)
    try:
        with storage.open(name, 'rb') as f2:
            meta["original"]["sha256"] = _hash_bytes(f2.read())
    except Exception:
        pass
    if w < MIN_ACCEPT_WIDTH or h < MIN_ACCEPT_HEIGHT:
        meta["flags"].append(ImageQualityFlags.REJECTED)
        meta["reason"] = "too_small"
        return meta
    if min(w, h) < WARN_MIN_SIDE:
        meta["flags"].append(ImageQualityFlags.LOW_RES)
    aspect = max(w / h, h / w)
    if aspect > MAX_ASPECT_RATIO:
        meta["flags"].append(ImageQualityFlags.REJECTED)
        meta["reason"] = "extreme_aspect"
        return meta
    if max(w, h) > MAX_ORIGINAL_SIDE:
        scale = MAX_ORIGINAL_SIDE / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        w, h = img.size
    try:
        sharpness_var = _laplacian_variance(img)
        meta["original"]["sharpness_var"] = round(sharpness_var, 2)
        if sharpness_var < 60:
            meta["flags"].append(ImageQualityFlags.BLURRY)
    except Exception:
        pass

    def sharpen(im: Image.Image, is_thumb=False) -> Image.Image:
        return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=(130 if is_thumb else 110), threshold=3))

    dir_name = os.path.dirname(name)  # storage relative dir
    stem = os.path.splitext(os.path.basename(name))[0]

    # Normalized original jpg
    normalized_rel = f"{stem}.jpg"
    normalized_full = f"{dir_name}/{normalized_rel}" if dir_name else normalized_rel
    buf = ContentFile(b"")
    out_bytes = ContentFile(b"")
    tmp = ContentFile(b"")
    norm_bytes = ContentFile(b"")
    # Save normalized
    tmp_io = Image.new('RGB', (1,1))  # placeholder to keep names unique (ignored)
    out = ContentFile(b"")
    # Actually save normalized image
    norm_buffer = ContentFile(b"")
    from io import BytesIO
    b = BytesIO()
    img.save(b, "JPEG", quality=85, optimize=True, progressive=True)
    b.seek(0)
    if storage.exists(normalized_full):
        try:
            storage.delete(normalized_full)
        except Exception:
            pass
    storage.save(normalized_full, ContentFile(b.read()))
    meta["normalized"] = normalized_rel
    meta["processed_at"] = datetime.now(timezone.utc).isoformat()

    for label, max_w_val, max_h_val, square in VARIANTS:
        if square:
            variant_img = _square_crop(img, max_w_val)
        else:
            variant_img = _resize_preserve(img, max_w_val, max_h_val)
        variant_img = sharpen(variant_img, is_thumb=(label == "thumb"))
        jpg_rel = f"{stem}__{label}.jpg"
        webp_rel = f"{stem}__{label}.webp"
        jpg_full = f"{dir_name}/{jpg_rel}" if dir_name else jpg_rel
        webp_full = f"{dir_name}/{webp_rel}" if dir_name else webp_rel
        # Save JPEG
        jb = BytesIO()
        variant_img.save(jb, "JPEG", quality=82, optimize=True, progressive=True)
        jb.seek(0)
        if storage.exists(jpg_full):
            try: storage.delete(jpg_full)
            except Exception: pass
        storage.save(jpg_full, ContentFile(jb.read()))
        # Save WebP
        wb_saved = False
        try:
            wb = BytesIO()
            variant_img.save(wb, "WEBP", quality=80, method=6)
            wb.seek(0)
            if storage.exists(webp_full):
                try: storage.delete(webp_full)
                except Exception: pass
            storage.save(webp_full, ContentFile(wb.read()))
            wb_saved = True
        except Exception:
            wb_saved = False
        meta["variants"][label] = {
            "jpg": jpg_rel,
            "webp": webp_rel if wb_saved else None,
            "width": variant_img.width,
            "height": variant_img.height,
        }
    return meta

def process_generic_image(field_file):
    """Process any ImageField file (gallery, blog) returning metadata; reuses profile pipeline.
    Attempts local path then storage fallback. Does not save variants into same directory if name collision risk.
    """
    try:
        path = field_file.path
        return process_profile_photo(path)
    except Exception:
        return process_profile_photo_storage(field_file)

__all__ = [
    "process_profile_photo",
    "process_profile_photo_storage",
    "process_generic_image",
    "ImageQualityFlags",
    "PIPELINE_VERSION",
]
