.PHONY: preview serve build

SERVE_DIR := /tmp/pricone-re-synthesis-serve
PORT := 8080

# ビルドしてからプレビューサーバーを起動
preview: build serve

# ビルドのみ
build:
	npm run build

# 既存のビルド成果物をそのままプレビューサーバーで配信
serve:
	mkdir -p $(SERVE_DIR)/lab
	ln -sfn $(CURDIR)/dist $(SERVE_DIR)/lab/pricone-re-synthesis
	npx --yes http-server $(SERVE_DIR) -p $(PORT) --cors
