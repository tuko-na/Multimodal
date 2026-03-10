"""
capture.py — 画面キャプチャモジュール

mss による高速スクリーンキャプチャのラッパー。
Retina ディスプレイのスケーリングを考慮し、物理ピクセル座標で動作する。
"""

import numpy as np
import mss
import mss.tools


class ScreenCapture:
    """mss ベースの高速スクリーンキャプチャ"""

    def __init__(self):
        self._sct = mss.mss()

    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """
        指定領域をキャプチャし、NumPy 配列 (BGR) で返す。

        座標は物理ピクセル（Retina 2x 環境では論理座標の2倍）で指定。
        mss は物理ピクセルで動作するため、キャリブレーション時に
        スケールファクターを適用済みの座標を渡すこと。

        Args:
            x: 左上X座標（物理ピクセル）
            y: 左上Y座標（物理ピクセル）
            width: 幅（物理ピクセル）
            height: 高さ（物理ピクセル）

        Returns:
            np.ndarray: BGR画像（shape: height x width x 3）
        """
        monitor = {"left": x, "top": y, "width": width, "height": height}
        # mss は BGRA で取得 → BGR に変換（アルファチャネル除去）
        raw = self._sct.grab(monitor)
        # NumPy 配列に変換（ゼロコピーに近い）
        img = np.array(raw, dtype=np.uint8)
        # BGRA -> BGR（アルファチャネルを除去）
        return img[:, :, :3]

    def capture_full_screen(self, monitor_index: int = 1) -> np.ndarray:
        """
        指定モニター全体をキャプチャ。

        Args:
            monitor_index: モニター番号（1=プライマリ）

        Returns:
            np.ndarray: BGR画像
        """
        monitor = self._sct.monitors[monitor_index]
        raw = self._sct.grab(monitor)
        img = np.array(raw, dtype=np.uint8)
        return img[:, :, :3]

    def get_screen_size(self, monitor_index: int = 1) -> tuple[int, int]:
        """プライマリモニターの物理ピクセルサイズを返す"""
        monitor = self._sct.monitors[monitor_index]
        return monitor["width"], monitor["height"]

    def close(self):
        """リソースを解放"""
        self._sct.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
