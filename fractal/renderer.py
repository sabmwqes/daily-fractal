"""フラクタル描画エンジン

compute_fractal(): 反復計算 → 発散回数マップ
colorize():        発散回数マップ → RGB 画像配列
draw_metadata_footer(): フラクタル画像の下にメタ情報フッターを追加
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fractal.params import FractalParams
from fractal.palette import build_colormap

FOOTER_HEIGHT = 48


def compute_fractal(params: FractalParams, width: int, height: int) -> np.ndarray:
    """フラクタルの発散回数マップを計算する（スムーズカラーリング付き）

    複素平面をグリッドに分割し、各ピクセルで漸化式を反復する。
    |z| > 2 で発散と判定し、スムーズな反復回数を記録する。

    Args:
        params: フラクタルパラメータ
        width:  画像幅 (px)
        height: 画像高 (px)

    Returns:
        float64 の (height, width) 配列。
        発散ピクセル: スムーズ化された反復回数 (≥ 0)
        集合内部ピクセル: -1
    """
    # --- 複素平面の範囲を計算 ---
    extent = 2.0 / params.zoom
    re_min = params.center_re - extent
    re_max = params.center_re + extent
    im_min = params.center_im - extent
    im_max = params.center_im + extent

    # --- グリッド生成 ---
    re = np.linspace(re_min, re_max, width)
    im = np.linspace(im_max, im_min, height)  # 上が正（画像座標系）
    Re, Im = np.meshgrid(re, im)
    grid = Re + 1j * Im

    # --- z, c の初期値設定 ---
    if params.mode == "julia":
        # Julia set: 各ピクセルが z₀, c は固定
        z = grid.copy()
        c = np.full_like(grid, params.c_param)
    else:
        # Mandelbrot: z₀ = 0, 各ピクセルが c
        z = np.zeros_like(grid)
        c = grid.copy()

    # --- 反復計算 ---
    iterations = np.full((height, width), -1.0, dtype=np.float64)
    mask = np.ones((height, width), dtype=bool)  # True = まだ発散していない

    for i in range(params.max_iter):
        # 未発散ピクセルだけ反復
        with np.errstate(over="ignore", invalid="ignore"):
            z[mask] = params.formula.iterate(z[mask], c[mask])

        abs_z = np.abs(z)

        # 発散判定: |z| > 2 かつ有限
        diverged = mask & (abs_z > 2.0) & np.isfinite(abs_z)
        if np.any(diverged):
            # スムーズカラーリング: i + 1 - log₂(log(|z|))
            log_zn = np.log(abs_z[diverged])
            smooth_val = i + 1 - np.log2(np.maximum(log_zn, 1e-10))
            iterations[diverged] = smooth_val
            mask[diverged] = False

        # NaN/Inf → 発散扱い
        bad = mask & (~np.isfinite(abs_z))
        if np.any(bad):
            iterations[bad] = i
            mask[bad] = False

        # 全ピクセル発散 → 早期終了
        if not np.any(mask):
            break

    return iterations


def colorize(iterations: np.ndarray, params: FractalParams) -> np.ndarray:
    """発散回数マップから RGB 画像配列を生成する

    対数スケール正規化 + カラーマップ線形補間でグラデーションを表現。

    Args:
        iterations: compute_fractal() の出力
        params: カラーパレット等のパラメータ

    Returns:
        shape=(height, width, 3) の uint8 配列 (RGB)
    """
    height, width = iterations.shape
    cmap = build_colormap(params.palette_colors, 512)

    diverged = iterations >= 0
    img = np.full((height, width, 3), 255, dtype=np.uint8)

    if np.any(diverged):
        vals = iterations[diverged]
        # 対数スケールで正規化 → グラデーションが豊かになる
        log_vals = np.log1p(vals)
        log_max = np.log1p(params.max_iter)
        norm = (log_vals / log_max + params.color_offset) % 1.0
        indices = (norm * (len(cmap) - 1)).astype(int)
        indices = np.clip(indices, 0, len(cmap) - 1)
        img[diverged] = cmap[indices]

    return img


def _get_font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """利用可能なフォントを取得する（OS 非依存）"""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except (OSError, IOError):
        pass
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size,
        )
    except (OSError, IOError):
        pass
    return ImageFont.load_default()


def draw_metadata_footer(
    fractal_image: Image.Image, params: FractalParams, footer_height: int = 48,
) -> Image.Image:
    """フラクタル画像の下にメタ情報フッターバーを追加して新しい画像を返す

    元画像の下部に暗い帯を追加し、そこにテキストを描画する。
    画像本体にオーバーレイしないため、フラクタルが隠れない。

    返り値: RGB の PIL Image (width x (height + footer_height))
    """
    w, h = fractal_image.size
    canvas = Image.new("RGB", (w, h + footer_height), (24, 24, 24))
    canvas.paste(fractal_image, (0, 0))

    draw = ImageDraw.Draw(canvas)
    font = _get_font(14)

    # --- 表示テキスト ---
    line1_parts = []
    if params.date_str:
        line1_parts.append(f"Date: {params.date_str}")
    line1_parts.append(f"Seed: {params.seed}")
    line1_parts.append(f"{params.mode.title()}: {params.formula.display_formula()}")
    line1 = "  |  ".join(line1_parts)

    line2_parts = []
    if params.mode == "julia":
        line2_parts.append(f"c = {params.c_param.real:.4f}{params.c_param.imag:+.4f}i")
    line2_parts.append(f"Zoom: {params.zoom:.1f}x")
    line2_parts.append(f"Palette: {params.palette_name}")
    line2 = "  |  ".join(line2_parts)

    x = 8
    draw.text((x, h + 4), line1, fill=(200, 200, 200), font=font)
    draw.text((x, h + 24), line2, fill=(160, 160, 160), font=font)

    return canvas
