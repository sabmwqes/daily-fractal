"""カラーパレット生成モジュール

HSV色空間からランダムにパレットを生成する。
色相は最大3色に制限し、暗→彩色→明 のグラデーション構造を持つ。
"""

import colorsys
import random

import numpy as np


def _hsv_to_rgb_tuple(h: float, s: float, v: float) -> tuple[int, int, int]:
    """HSV (各0.0〜1.0) → RGB (各0〜255) タプルに変換する"""
    r, g, b = colorsys.hsv_to_rgb(
        h % 1.0,
        max(0.0, min(1.0, s)),
        max(0.0, min(1.0, v)),
    )
    return (int(r * 255), int(g * 255), int(b * 255))


def generate_random_palette(rng: random.Random) -> tuple[list, str]:
    """ランダムなカラーパレットを生成する

    色相の数を1〜3色に制限し、暗→彩色→明の制御点列を返す。

    Args:
        rng: 乱数生成器

    Returns:
        (制御点リスト [(r,g,b), ...], パレット説明文字列)
    """
    # --- 色相の数を決定 (1〜3) ---
    n_hues = rng.choices([1, 2, 3], weights=[0.25, 0.45, 0.30])[0]

    # --- 色相を選択 ---
    base_hue = rng.random()
    if n_hues == 1:
        hues = [base_hue]
    elif n_hues == 2:
        spread = rng.uniform(0.12, 0.45)
        hues = [base_hue, (base_hue + spread) % 1.0]
    else:
        spread1 = rng.uniform(0.08, 0.30)
        spread2 = rng.uniform(0.08, 0.30)
        hues = [
            base_hue,
            (base_hue + spread1) % 1.0,
            (base_hue + spread1 + spread2) % 1.0,
        ]

    # --- 制御点生成: 暗 → 彩色 → 明 ---
    points: list[tuple[int, int, int]] = []

    # 暗い開始点
    points.append(_hsv_to_rgb_tuple(
        hues[0], rng.uniform(0.3, 0.9), rng.uniform(0.0, 0.12),
    ))

    # 各色相の彩色ポイント（グラデーション中間部）
    for h in hues:
        s = rng.uniform(0.55, 1.0)
        v = rng.uniform(0.45, 0.92)
        points.append(_hsv_to_rgb_tuple(h, s, v))

    # 明るい終了点
    points.append(_hsv_to_rgb_tuple(
        hues[-1], rng.uniform(0.0, 0.25), rng.uniform(0.88, 1.0),
    ))

    # 説明文 (例: "H(120,240°)")
    hue_degs = [str(int(h * 360)) for h in hues]
    desc = f"H({','.join(hue_degs)}°)"

    return points, desc


def build_colormap(palette_colors: list, size: int = 256) -> np.ndarray:
    """パレット制御点から size 色のカラーマップを線形補間で生成する

    Args:
        palette_colors: RGB制御点のリスト [(r,g,b), ...]
        size: 出力カラーマップのエントリ数

    Returns:
        shape=(size, 3) の uint8 配列
    """
    n_ctrl = len(palette_colors)
    cmap = np.zeros((size, 3), dtype=np.uint8)
    for i in range(size):
        t = i / (size - 1) * (n_ctrl - 1)
        idx = int(t)
        frac = t - idx
        if idx >= n_ctrl - 1:
            idx = n_ctrl - 2
            frac = 1.0
        c0 = palette_colors[idx]
        c1 = palette_colors[idx + 1]
        cmap[i] = [int(c0[j] + (c1[j] - c0[j]) * frac) for j in range(3)]
    return cmap
