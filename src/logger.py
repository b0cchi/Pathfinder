import logging
from logging.handlers import RotatingFileHandler

# ターミナル: INFO 以上のみ表示
# ログファイル: DEBUG 以上をすべて記録（5MB でローテート、最大10世代保持）
logger = logging.getLogger("pathfinder")
logger.setLevel(logging.DEBUG)

_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(logging.INFO)
_stream_handler.setFormatter(logging.Formatter("%(message)s"))

_file_handler = RotatingFileHandler(
    "pathfinder.log",
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=10,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logger.addHandler(_stream_handler)
logger.addHandler(_file_handler)
