"""品質チェックモジュール

生成結果が視覚的に破綻していないか簡易判定する。
真っ白（全面集合内部）や単調（発散回数の分散が小さい）を排除する。
"""

import numpy as np

from fractal.params import FractalParams

# 発散回数の標準偏差がこの値未満なら「単調すぎる」と判定
MIN_ITER_STD = 1.0


def quality_check(iterations: np.ndarray, params: FractalParams) -> bool:
    """生成結果が視覚的に破綻していないか簡易チェック

    判定基準:
      1. 発散ピクセルが少なすぎる（ほぼ全面が集合内部 → 真っ白）
      2. 発散ピクセルの反復回数の標準偏差が小さすぎる（単調な色）

    Args:
        iterations: compute_fractal() の出力 (発散=-1以外, 集合内部=-1)
        params: (将来の拡張用)

    Returns:
        True なら合格（表示に適する）
    """
    total = iterations.size
    diverged_mask = iterations >= 0
    diverged_count = np.sum(diverged_mask)
    ratio = diverged_count / total

    # ほぼ全面が集合内部 → 真っ白
    if ratio < 0.15:
        return False

    # 発散ピクセルの反復回数の標準偏差チェック
    # 全て同じ回数で発散 → グラデーションが生まれず単調な1色
    std = float(np.std(iterations[diverged_mask]))
    if std < MIN_ITER_STD:
        return False

    return True
