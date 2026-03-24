# Claude Code ルール

## コード編集後の必須手順

Python ファイルを編集・生成した後は必ず以下を実行してから報告すること。

```bash
python -m ruff format src/ main.py tools/
python -m ruff check src/ main.py tools/
python -m mypy src/ main.py
```

**理由:** VS Code の format-on-save で ruff が走るため、事前に整形しておかないとユーザーが保存するたびにファイルが変わって混乱を招く。

## Git

- コミット・プッシュはユーザーの指示があったときのみ実行する。

## 不確かな場合の対応

- 確証のない推測を重ねて回答しない。
- わからないことはわからないと早めに伝え、必要な情報をユーザーに確認してから回答する。
