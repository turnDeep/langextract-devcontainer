# LangExtract Dev Container

[LangExtract](https://github.com/google/langextract) - GoogleのGemini駆動情報抽出ライブラリのためのすぐに使える開発環境です。

## 🚀 クイックスタート

### 前提条件
- [Visual Studio Code](https://code.visualstudio.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Dev Containers拡張機能](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- [Gemini APIキー](https://aistudio.google.com/app/apikey) (クラウドモデル用 - 無料枠あり)

### セットアップ

1. **このリポジトリをクローン**
   ```bash
   git clone https://github.com/yourusername/langextract-devcontainer.git
   cd langextract-devcontainer
   ```

2. **VS Codeで開く**
   ```bash
   code .
   ```

3. **Dev Containerで開く**
   - `F1`を押して「Dev Containers: Reopen in Container」を選択
   - またはVS Codeのポップアップ通知をクリック

4. **APIキーを設定**
   ```bash
   cp .env.example .env
   # .envを編集してLANGEXTRACT_API_KEYを追加
   ```

5. **サンプルを実行**
   ```bash
   python examples/basic_extraction.py
   ```

## 📁 プロジェクト構造

```
├── .devcontainer/      # Dev Container設定
├── examples/           # サンプルスクリプト
├── data/              # サンプルデータファイル
├── output/            # 抽出結果（gitignore対象）
├── src/               # カスタムユーティリティ
└── requirements.txt   # Python依存関係
```

## 📚 サンプル

### 基本的な抽出
```python
# 基本的なサンプルを実行
python examples/basic_extraction.py
```

### 医療テキスト抽出
```python
# 医療情報を抽出
python examples/medical_extraction.py
```

### ドキュメント処理
```python
# ドキュメント全体を処理
python examples/document_extraction.py
```

### インタラクティブな視覚化
```python
# インタラクティブなHTML視覚化を生成
python examples/visualization_example.py
```

### バッチ処理（無料枠で1000ファイル）
```python
# Gemini 2.5 Flash無料枠を使用して5日間で1000ファイルを処理
python examples/batch_extraction.py input_files output_files

# 進捗を監視
python examples/monitor_extraction.py

# 失敗したファイルを再試行
python examples/batch_extraction.py input_files output_files --retry-failed
```

## 🛠️ 開発

### Jupyter Notebooksの使用
```bash
# Jupyterサーバーを起動
jupyter notebook --ip=0.0.0.0 --no-browser
```

### テストの実行
```bash
# すべてのテストを実行
pytest

# カバレッジ付きで実行
pytest --cov=src
```

### コードフォーマット
```bash
# Blackでコードをフォーマット
black .

# pylintでリント
pylint src/
```

## 🔧 設定

### 環境変数
- `LANGEXTRACT_API_KEY`: Gemini APIキー
- `DEFAULT_MODEL_ID`: 使用するデフォルトモデル（デフォルト: gemini-2.5-flash）
- `MAX_CHAR_BUFFER`: チャンキングのための最大文字バッファ
- `MAX_WORKERS`: 並列ワーカー数（無料枠では1を維持）

### Gemini 2.5 Flash無料枠の制限
- `REQUESTS_PER_MINUTE`: 10（無料枠の制限）
- `TOKENS_PER_MINUTE`: 250,000（無料枠の制限）
- `REQUESTS_PER_DAY`: 250（無料枠の制限）
- `SAFETY_FACTOR`: 0.8（安全のため制限の80%を使用）

### ローカルモデルの使用（Ollama）
```python
# Ollamaサービスを開始
ollama serve

# モデルをプル
ollama pull llama2

# LangExtractで使用
result = lx.extract(
    text_or_documents=text,
    prompt_description=prompt,
    examples=examples,
    model_id="ollama:llama2"
)
```

### Gemini 2.5 Flash無料枠でのバッチ処理
このリポジトリには、Gemini 2.5 Flash無料枠の制限に最適化された専用のバッチ処理スクリプトが含まれています：

```bash
# 5日間で1000ファイルを処理（1日200ファイル）
python examples/batch_extraction.py input_files output_files

# 機能：
# - 自動レート制限（8 RPM、200K TPM、200 RPD）
# - 再開機能（停止した場所から継続）
# - 言語認識型トークン推定（英語/日本語）
# - 進捗追跡とETA計算
# - 失敗ファイル再試行メカニズム
```

## 📖 リソース

- [LangExtractドキュメント](https://github.com/google/langextract)
- [Gemini APIドキュメント](https://ai.google.dev/)
- [Google開発者ブログ記事](https://developers.googleblog.com/en/introducing-langextract-a-gemini-powered-information-extraction-library/)

## 🤝 貢献

1. リポジトリをフォーク
2. フィーチャーブランチを作成
3. 変更を加える
4. テストとリンティングを実行
5. プルリクエストを送信

## 📄 ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています - 詳細はLICENSEファイルを参照してください。

## 🐛 トラブルシューティング

### APIキーの問題
- `.env`にAPIキーが正しく設定されていることを確認
- Gemini APIのクォータとレート制限を確認

### Dockerの問題
- Docker Desktopが実行されていることを確認
- コンテナの再構築を試す：「Dev Containers: Rebuild Container」

### ポートの競合
- Dev Containerはポート8501（Streamlit）と8888（Jupyter）を転送します
- これらのポートが使用中の場合は`.devcontainer/devcontainer.json`を変更

## 📞 サポート

- このリポジトリでissueを開く
- [LangExtract GitHub Issues](https://github.com/google/langextract/issues)を確認
- [Gemini APIサポート](https://support.google.com/gemini)を確認