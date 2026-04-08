"""日替わりフラクタル画像生成スクリプト (エントリーポイント)

日付をseedとして再現可能なフラクタル画像を生成する。
漸化式 z_{n+1} = f(z_n) + c に基づき、制約付きランダムパラメータで
視覚的に美しいフラクタルを毎日自動生成する。

使い方:
    python generate.py              # 今日の日付で生成 → docs/daily.png
    python generate.py 20260101     # 指定日付で生成
    python generate.py 20260101 out.png  # 指定日付 + 出力先
"""

import datetime
import os
import sys

from PIL import Image

from fractal.params import FractalParams
from fractal.renderer import compute_fractal, colorize, draw_metadata_footer, FOOTER_HEIGHT
from fractal.quality import quality_check

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
IMAGE_SIZE = 1200
MAX_RETRY = 10

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_PATH = os.path.join(DOCS_DIR, "daily.png")


# ──────────────────────────────────────────────
# リトライ用 seed 生成
# ──────────────────────────────────────────────

def _retry_seed(base_seed: int, attempt: int) -> int:
    """品質チェックリトライ時に、日付情報を保持した seed を生成する

    base_seed (YYYYMMDD) * 1000 + attempt で seed を生成する。
    attempt < 1000 であれば隣の日付とは絶対に衝突しない。
    seed を見るだけで日付と試行番号が読み取れる利点がある。
    """
    return base_seed * 1000 + attempt


# ──────────────────────────────────────────────
# メイン生成関数
# ──────────────────────────────────────────────

def generate_fractal(
    date_str: str | None = None,
    output_path: str | None = None,
) -> str:
    """フラクタル画像を生成して保存する

    Args:
        date_str:    YYYYMMDD形式の日付文字列。None なら今日の日付。
        output_path: 出力パス。None ならデフォルト (docs/daily.png)。

    Returns:
        出力ファイルパス
    """
    if date_str is None:
        date_str = datetime.date.today().strftime("%Y%m%d")
    if output_path is None:
        output_path = OUTPUT_PATH

    base_seed = int(date_str)

    # --- 品質チェック付きリトライ ---
    # attempt=0 はそのままの seed を使い、失敗時は
    # ハッシュベースの別 seed で再試行する（他の日付と衝突しない）
    for attempt in range(MAX_RETRY):
        actual_seed = _retry_seed(base_seed, attempt)
        params = FractalParams(actual_seed, date_str=date_str, attempt=attempt)

        print(f"[attempt {attempt + 1}] seed={actual_seed}")
        print(params.summary())

        iterations = compute_fractal(params, IMAGE_SIZE, IMAGE_SIZE)

        if quality_check(iterations, params):
            break
        print("  -> Quality check failed, retrying...\n")
    else:
        print("Warning: Could not pass quality check after "
              f"{MAX_RETRY} attempts. Using last result.")

    # --- 画像化 ---
    rgb = colorize(iterations, params)
    image = Image.fromarray(rgb)

    # メタ情報フッター追加
    image = draw_metadata_footer(image, params, FOOTER_HEIGHT)

    # PNG 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, "PNG", optimize=True)

    print(f"\nSaved: {output_path}  ({IMAGE_SIZE}x{IMAGE_SIZE + FOOTER_HEIGHT})")
    return output_path


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    output_arg = sys.argv[2] if len(sys.argv) > 2 else None
    generate_fractal(date_arg, output_arg)
