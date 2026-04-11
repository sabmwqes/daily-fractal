# Daily Fractal

日付をseedとしたフラクタルっぽい画像を毎日自動生成するリポジトリ。

## Today's Fractal

[![daily fractal](https://sabmwqes.github.io/daily-fractal/daily.png)](https://sabmwqes.github.io/daily-fractal/)

> 画像は毎日 UTC 20:00（日本時間 05:00）に自動更新されます。同じ日には同じ画像が生成されます。

## 仕組み

- **GitHub Actions** が毎日 cron で `generate.py` を実行
- 日付（YYYYMMDD）+ 試行回数（NNN）を乱数seedとして、制約付きランダムパラメータでフラクタルを生成
- 生成画像を `docs/daily.png` に保存し、自動コミット
- **GitHub Pages**（`docs/` フォルダ）で静的配信

## ローカル実行

```bash
pip install -r requirements.txt

# 今日のフラクタルを生成
python generate.py

# 特定の日付を指定
python generate.py 20260101

# テスト（複数日分を一括生成）
python test_generate.py
```

# markdown で表示

```markdown
![daily fractal](https://sabmwqes.github.io/daily-fractal/daily.png)
```

