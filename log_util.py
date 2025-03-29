import logging
import os

# ログのフォーマット
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s: %(message)s"

# ログの設定
logging.basicConfig(
    level=logging.DEBUG,  # 開発・デバッグするときはlogging.DEBUGにする
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),  # 標準出力（コンソール）
        logging.FileHandler("app.log", mode="a", encoding="utf-8"),  # ログファイルに保存
    ]
)

# 各スクリプトでこの logger をインポートして使う
logger = logging.getLogger(__name__)
