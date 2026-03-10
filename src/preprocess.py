"""
preprocess.py — 画像前処理パイプライン

キャプチャ画像に対して、固定座標での切り抜き → グレースケール変換 → リサイズ を
高速に実行する。すべての操作で NumPy/OpenCV のネイティブ処理を使用し、
Python の for ループは一切使わない。
"""

import cv2
import numpy as np


def crop(image: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
    """
    指定座標で画像を切り抜く（NumPy スライス = ゼロコピー参照）。

    Args:
        image: 入力画像（BGR or グレースケール）
        x, y: 左上座標
        width, height: 切り抜きサイズ

    Returns:
        切り抜かれた画像（元画像のメモリを参照）
    """
    return image[y : y + height, x : x + width]


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    BGR画像をグレースケールに変換。

    Args:
        image: BGR画像 (H, W, 3)

    Returns:
        グレースケール画像 (H, W)
    """
    if len(image.shape) == 2:
        return image  # 既にグレースケール
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_width(image: np.ndarray, target_width: int) -> np.ndarray:
    """
    アスペクト比を維持したまま、指定幅にリサイズ。

    Args:
        image: 入力画像
        target_width: 目標の横幅（ピクセル）

    Returns:
        リサイズ後の画像
    """
    h, w = image.shape[:2]
    if w == target_width:
        return image
    scale = target_width / w
    target_height = int(h * scale)
    # INTER_AREA は縮小時に最も高品質
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def encode_jpeg(image: np.ndarray, quality: int = 85) -> bytes:
    """
    画像を JPEG バイト列にエンコード。

    Args:
        image: 入力画像
        quality: JPEG品質 (0-100)

    Returns:
        JPEG エンコードされたバイト列
    """
    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    success, buffer = cv2.imencode(".jpg", image, params)
    if not success:
        raise RuntimeError("JPEG エンコードに失敗しました")
    return buffer.tobytes()


def preprocess(image: np.ndarray, target_width: int = 800) -> np.ndarray:
    """
    前処理パイプライン: グレースケール変換 → リサイズ。

    切り抜きはキャプチャ時に済んでいる想定。
    このパイプラインは「取得済みの画像データ」に対して適用する。

    Args:
        image: 切り抜き済みBGR画像
        target_width: 目標横幅（デフォルト800px）

    Returns:
        前処理済みグレースケール画像
    """
    gray = to_grayscale(image)
    resized = resize_width(gray, target_width)
    return resized


def preprocess_and_encode(
    image: np.ndarray, target_width: int = 800, jpeg_quality: int = 85
) -> bytes:
    """
    前処理 + JPEG エンコードの一括実行（API送信用）。

    Args:
        image: 切り抜き済みBGR画像
        target_width: 目標横幅
        jpeg_quality: JPEG品質

    Returns:
        前処理済み画像の JPEG バイト列
    """
    processed = preprocess(image, target_width)
    return encode_jpeg(processed, jpeg_quality)
