"""テストスクリプト - フラクタル画像をN×Nグリッドで一括確認する

使い方:
  python test_generate.py                  # ランダム日付から N×N 日分を生成 (N=5)
  python test_generate.py 20260101         # 指定日付から N×N 日分
  python test_generate.py 20260101 4       # 指定日付から N=4 (4×4=16日分)

出力:
  test_output/grid_with_qc.png    品質チェックあり版のグリッド画像
  test_output/grid_without_qc.png 品質チェックなし版のグリッド画像

再現性テストも自動で実行されます。
"""

import os
import sys
import datetime
import random

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fractal import (
    FractalParams,
    compute_fractal,
    colorize,
    draw_metadata_footer,
    FOOTER_HEIGHT,
    quality_check,
)
from generate import generate_fractal, IMAGE_SIZE, _retry_seed

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
DEFAULT_N = 5 # デフォルトのグリッドサイズ (N×N個の画像)
THUMB_SIZE = 1200  # グリッド内の各セルのサイズ


def render_single(date_str: str, skip_quality_check: bool = False) -> Image.Image:
    """1枚分のフラクタルを生成して PIL Image で返す

    skip_quality_check=True: seed そのままで品質チェックなし。
    skip_quality_check=False: リトライで品質チェック。
    """
    base_seed = int(date_str)

    if skip_quality_check:
        actual_seed = _retry_seed(base_seed, 0)
        params = FractalParams(actual_seed, date_str=date_str, attempt=0)
        iterations = compute_fractal(params, IMAGE_SIZE, IMAGE_SIZE)
    else:
        for attempt in range(10):
            actual_seed = _retry_seed(base_seed, attempt)
            params = FractalParams(actual_seed, date_str=date_str, attempt=attempt)
            iterations = compute_fractal(params, IMAGE_SIZE, IMAGE_SIZE)
            if quality_check(iterations, params):
                break

    rgb = colorize(iterations, params)
    image = Image.fromarray(rgb)
    image = draw_metadata_footer(image, params, FOOTER_HEIGHT)
    return image


def build_grid(images: list[Image.Image], dates: list[str], n: int) -> Image.Image:
    """N×N グリッド画像を生成する"""
    padding = 4
    label_h = 20
    # サムネイルは元画像のアスペクト比を維持（幅=THUMB_SIZE）
    if images:
        src_w, src_h = images[0].size
        thumb_h = int(THUMB_SIZE * src_h / src_w)
    else:
        thumb_h = THUMB_SIZE
    cell_w = THUMB_SIZE + padding
    cell_h = thumb_h + padding
    grid_w = cell_w * n + padding
    grid_h = (cell_h + label_h) * n + padding

    grid = Image.new("RGB", (grid_w, grid_h), (32, 32, 32))
    draw = ImageDraw.Draw(grid)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default()

    for idx, (img, date_str) in enumerate(zip(images, dates)):
        row, col = divmod(idx, n)
        thumb = img.resize((THUMB_SIZE, thumb_h), Image.Resampling.LANCZOS)
        x = padding + col * cell_w
        y = padding + row * (cell_h + label_h)
        grid.paste(thumb, (x, y))
        # 日付ラベル
        draw.text((x + 4, y + thumb_h + 2), date_str, fill=(200, 200, 200), font=font)

    return grid


def run_reproducibility_test(start_date: datetime.date):
    """再現性テスト"""
    print("\n=== Reproducibility test ===")
    test_date = start_date.strftime("%Y%m%d")
    path_a = os.path.join(OUTPUT_DIR, f"repro_a_{test_date}.png")
    path_b = os.path.join(OUTPUT_DIR, f"repro_b_{test_date}.png")
    generate_fractal(test_date, path_a)
    generate_fractal(test_date, path_b)

    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        if fa.read() == fb.read():
            print("PASS: Same date produces identical images")
        else:
            print("FAIL: Images differ for the same date!")
            sys.exit(1)


def main():
    if len(sys.argv) >= 2:
        start_date = datetime.datetime.strptime(sys.argv[1], "%Y%m%d").date()
    else:
        # ランダムな日付を選ぶ（1900-01-01 〜 2900-12-31）
        origin = datetime.date(1900, 1, 1)
        days_range = (datetime.date(2900, 12, 31) - origin).days
        start_date = origin + datetime.timedelta(days=random.randint(0, days_range))
        print(f"(No date specified — randomly chose {start_date})")

    n = int(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_N
    count = n * n

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    dates = [(start_date + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(count)]

    # --- 品質チェックあり ---
    print(f"=== Grid {n}x{n} WITH quality check ===")
    images_qc = []
    for i, d in enumerate(dates):
        print(f"  [{i + 1}/{count}] {d} (with QC)")
        images_qc.append(render_single(d, skip_quality_check=False))

    grid_qc = build_grid(images_qc, dates, n)
    path_qc = os.path.join(OUTPUT_DIR, "grid_with_qc.png")
    grid_qc.save(path_qc, "PNG")
    print(f"Saved: {path_qc}\n")

    # --- 品質チェックなし ---
    print(f"=== Grid {n}x{n} WITHOUT quality check ===")
    images_raw = []
    for i, d in enumerate(dates):
        print(f"  [{i + 1}/{count}] {d} (no QC)")
        images_raw.append(render_single(d, skip_quality_check=True))

    grid_raw = build_grid(images_raw, dates, n)
    path_raw = os.path.join(OUTPUT_DIR, "grid_without_qc.png")
    grid_raw.save(path_raw, "PNG")
    print(f"Saved: {path_raw}\n")

    # --- 再現性テスト ---
    # run_reproducibility_test(start_date)

    print(f"\nAll done! Check grid images in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
