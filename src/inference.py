"""
inference.py — Gemini Flash 推論モジュール

google-generativeai SDK を使用して、画像に対する
ストリーミング推論を実行する。
"""

import os
import base64
from typing import Callable
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

from src.prompt import get_system_prompt, get_user_prompt

# .env からAPIキーを読み込み
load_dotenv()


def _configure():
    """Gemini API を設定"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY が設定されていません。\n"
            ".env ファイルに有効なAPIキーを設定してください。"
        )
    genai.configure(api_key=api_key)


def _create_model() -> genai.GenerativeModel:
    """推論用モデルを作成"""
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=get_system_prompt(),
        generation_config=genai.GenerationConfig(
            max_output_tokens=100,
            temperature=0.0,
        ),
    )


def get_answer(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    画像に対して推論を実行し、完全な応答を返す（非ストリーミング）。
    テスト・デバッグ用。

    Args:
        image_bytes: JPEG エンコード済み画像バイト列
        mime_type: 画像の MIME タイプ

    Returns:
        AI の応答テキスト
    """
    _configure()
    model = _create_model()

    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            get_user_prompt(),
        ]
    )
    return response.text


def stream_answer(
    image_bytes: bytes,
    callback: Callable[[str], None],
    mime_type: str = "image/jpeg",
) -> str:
    """
    画像に対してストリーミング推論を実行し、
    チャンク毎に callback を呼び出す。

    Args:
        image_bytes: JPEG エンコード済み画像バイト列
        callback: チャンクテキストを受け取るコールバック関数
        mime_type: 画像の MIME タイプ

    Returns:
        完全な応答テキスト
    """
    _configure()
    model = _create_model()

    response = model.generate_content(
        [
            {"mime_type": mime_type, "data": image_bytes},
            get_user_prompt(),
        ],
        stream=True,
    )

    full_text = ""
    for chunk in response:
        if chunk.text:
            callback(chunk.text)
            full_text += chunk.text

    return full_text
