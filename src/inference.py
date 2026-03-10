"""
inference.py — Gemini Flash 推論モジュール

google.genai SDK を使用して、画像に対する
ストリーミング推論を実行する。

スロットリング（指数バックオフリトライ）とガードレール（エラーハンドリング）付き。
"""

import os
import time
import re
from typing import Callable

from google import genai
from google.genai import types
from google.genai.errors import ClientError
from dotenv import load_dotenv

from src.prompt import get_system_prompt, get_user_prompt

# .env からAPIキーを読み込み
load_dotenv()

# モデル名
MODEL_NAME = "gemini-2.0-flash"

# スロットリング設定
MAX_RETRIES = 5          # 最大リトライ回数
BASE_WAIT_SEC = 10       # 初回待ち時間（秒）
MAX_WAIT_SEC = 120       # 最大待ち時間（秒）


def _get_client() -> genai.Client:
    """Gemini API クライアントを取得"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。\n"
            ".env ファイルに有効なAPIキーを設定してください。"
        )
    return genai.Client(api_key=api_key)


def _extract_retry_delay(error: ClientError) -> float | None:
    """エラーメッセージから推奨リトライ待ち時間を抽出する"""
    error_str = str(error)
    # "Please retry in 10.911556308s." のパターン
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # "retryDelay": "50s" のパターン
    match = re.search(r'"retryDelay":\s*"(\d+)s"', error_str)
    if match:
        return float(match.group(1))
    return None


def _with_throttle(func, *args, **kwargs):
    """
    スロットリング（指数バックオフ）付きでAPI呼び出しを実行。

    429 (RESOURCE_EXHAUSTED) エラー時にリトライする。
    APIが推奨する待ち時間があればそれを使い、なければ指数バックオフで待つ。
    """
    last_error = None
    wait_sec = BASE_WAIT_SEC

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            if "429" not in str(e) and "RESOURCE_EXHAUSTED" not in str(e):
                raise  # 429以外のエラーはそのまま投げる

            last_error = e

            # APIが推奨する待ち時間を抽出
            suggested_delay = _extract_retry_delay(e)
            actual_wait = suggested_delay if suggested_delay else wait_sec

            # 上限クリップ
            actual_wait = min(actual_wait, MAX_WAIT_SEC)

            if attempt < MAX_RETRIES:
                print(f"\n   ⏳ クォータ制限中 (429)... {actual_wait:.0f}秒後にリトライ "
                      f"({attempt}/{MAX_RETRIES})")
                time.sleep(actual_wait)
                # 指数バックオフ（次回は倍に）
                wait_sec = min(wait_sec * 2, MAX_WAIT_SEC)
            else:
                print(f"\n   ❌ {MAX_RETRIES}回リトライしましたが、クォータが回復しません。")

    raise last_error


def get_answer(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    画像に対して推論を実行し、完全な応答を返す（非ストリーミング）。
    テスト・デバッグ用。429エラー時は自動リトライ。

    Args:
        image_bytes: JPEG エンコード済み画像バイト列
        mime_type: 画像の MIME タイプ

    Returns:
        AI の応答テキスト
    """
    client = _get_client()

    def _call():
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                get_user_prompt(),
            ],
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                max_output_tokens=100,
                temperature=0.0,
            ),
        )
        return response.text

    return _with_throttle(_call)


def stream_answer(
    image_bytes: bytes,
    callback: Callable[[str], None],
    mime_type: str = "image/jpeg",
) -> str:
    """
    画像に対してストリーミング推論を実行し、
    チャンク毎に callback を呼び出す。
    429エラー時は自動リトライ。

    Args:
        image_bytes: JPEG エンコード済み画像バイト列
        callback: チャンクテキストを受け取るコールバック関数
        mime_type: 画像の MIME タイプ

    Returns:
        完全な応答テキスト
    """
    client = _get_client()

    def _call():
        response_stream = client.models.generate_content_stream(
            model=MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                get_user_prompt(),
            ],
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                max_output_tokens=100,
                temperature=0.0,
            ),
        )

        full_text = ""
        for chunk in response_stream:
            if chunk.text:
                callback(chunk.text)
                full_text += chunk.text

        return full_text

    return _with_throttle(_call)
