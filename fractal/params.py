"""フラクタルパラメータ生成モジュール

seed (日付 YYYYMMDD) から決定論的に全パラメータを生成する。
同じ seed → 常に同じパラメータ（再現性保証）。

生成されるパラメータ:
  - 漸化式 (式木)
  - モード (julia / mandelbrot)
  - c パラメータ (julia モード時)
  - ビュー (中心座標, ズーム倍率)
  - 反復回数
  - カラーパレット
  - カラーオフセット / 反転
"""

import math
import random

from fractal.formula import GeneratedFormula
from fractal.palette import generate_random_palette

# 反復回数（固定値）
MAX_ITER = 250


class FractalParams:
    """フラクタル生成に必要な全パラメータを保持する

    seed を渡すだけで全パラメータが決定論的に生成される。
    """

    def __init__(self, seed: int, date_str: str = "", attempt: int = 0):
        self.seed = seed
        self.date_str = date_str
        self.attempt = attempt
        self.rng = random.Random(seed)

        # ① 漸化式を生成（文法ベースの式木）
        self.formula = GeneratedFormula(self.rng)

        # ② モード選択: julia=c固定/各ピクセルがz₀, mandelbrot=z₀=0/各ピクセルがc
        self.mode: str = self.rng.choice(["julia", "mandelbrot"])

        # ③ Julia set の c パラメータ
        if self.mode == "julia":
            self.c_param = self._generate_c()
        else:
            self.c_param = complex(0, 0)

        # ④ ビュー（中心座標 + ズーム倍率）
        self.center_re, self.center_im, self.zoom = self._generate_view()

        # ⑤ 最大反復回数（固定）
        self.max_iter: int = MAX_ITER

        # ⑥ カラーパレット（HSV ランダム生成）
        self.palette_colors, self.palette_name = generate_random_palette(self.rng)

        # ⑦ カラーオフセット（パレット内の開始位置をずらす）
        self.color_offset: float = self.rng.uniform(0, 1)

        # ⑧ (削除: invert_colors は廃止)

    # ──────────────────────────────────
    # c パラメータ生成
    # ──────────────────────────────────

    def _generate_c(self) -> complex:
        """Julia set 用の c パラメータを生成する

        3 つの戦略からランダムに選択:
          - classic (45%): 有名な美しい c 値の近傍 + 摂動
          - polar   (35%): 半径 0.4〜1.1 の円上ランダム
          - free    (20%): 有界矩形内の自由ランダム
        """
        rng = self.rng
        strategy = rng.choices(
            ["classic", "polar", "free"], weights=[0.45, 0.35, 0.20],
        )[0]

        if strategy == "classic":
            interesting_c = [
                (-0.7269, 0.1889), (-0.4, 0.6), (0.285, 0.01),
                (-0.8, 0.156), (-0.75, 0.11), (0.355, 0.355),
                (-0.1, 0.651), (-0.624, 0.435), (-0.52, 0.57),
                (0.28, 0.008), (-0.12, 0.74), (-0.76, 0.0),
            ]
            base = rng.choice(interesting_c)
            re = base[0] + rng.gauss(0, 0.04)
            im = base[1] + rng.gauss(0, 0.04)
        elif strategy == "polar":
            r = rng.uniform(0.4, 1.1)
            theta = rng.uniform(0, 2 * math.pi)
            re = r * math.cos(theta)
            im = r * math.sin(theta)
        else:
            re = rng.uniform(-1.5, 0.5)
            im = rng.uniform(-1.0, 1.0)

        return complex(re, im)

    # ──────────────────────────────────
    # ビュー生成
    # ──────────────────────────────────

    def _generate_view(self) -> tuple[float, float, float]:
        """表示領域（中心座標 + ズーム倍率）を生成する"""
        rng = self.rng
        if self.mode == "mandelbrot":
            center_re = rng.uniform(-0.5, 0.0)
            center_im = rng.uniform(-0.2, 0.2)
            zoom = rng.choice([0.7, 0.8, 1.0, 1.2, 1.5])
        else:
            center_re = rng.uniform(-0.1, 0.1)
            center_im = rng.uniform(-0.1, 0.1)
            zoom = rng.choice([0.7, 0.8, 1.0, 1.2])
        return 0, 0, zoom # ひとまず原点中心で固定

    # ──────────────────────────────────
    # 表示
    # ──────────────────────────────────

    def summary(self) -> str:
        """パラメータの要約文字列を返す"""
        lines = [
            f"Date: {self.date_str}  Seed: {self.seed}  (attempt {self.attempt})",
            f"Mode: {self.mode}",
            f"Formula: {self.formula.display_formula()}",
        ]
        if self.mode == "julia":
            lines.append(f"c = {self.c_param.real:.4f}{self.c_param.imag:+.4f}i")
        lines += [
            f"Center: ({self.center_re:.4f}, {self.center_im:.4f})",
            f"Zoom: {self.zoom:.1f}x",
            f"Palette: {self.palette_name}",
        ]
        return "\n".join(lines)
