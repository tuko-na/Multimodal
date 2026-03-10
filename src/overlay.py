"""
overlay.py — PyQt6 透過オーバーレイUI

背景透過の最前面ウィンドウでAI応答をストリーミング表示する。
qasync で asyncio と Qt イベントループを統合。
"""

import asyncio
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class OverlaySignals(QObject):
    """スレッドセーフなシグナル定義"""
    append_text = pyqtSignal(str)
    set_text = pyqtSignal(str)
    show_status = pyqtSignal(str)


class OverlayWindow(QWidget):
    """背景透過の最前面オーバーレイウィンドウ"""

    def __init__(self, width: int = 420, height: int = 200):
        super().__init__()
        self.signals = OverlaySignals()
        self._setup_window(width, height)
        self._setup_ui()
        self._connect_signals()

    def _setup_window(self, width: int, height: int):
        """ウィンドウの基本設定"""
        self.setWindowTitle("解答オーバーレイ")
        # フレームレス + 常に最前面 + ツールウィンドウ（タスクバーに出ない）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # 背景透過
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(width, height)

        # 画面右下に配置
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - width - 20
            y = geometry.bottom() - height - 20
            self.move(x, y)

    def _setup_ui(self):
        """UI レイアウト構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 半透明背景コンテナ
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 30, 220);
                border-radius: 12px;
                border: 1px solid rgba(100, 100, 255, 80);
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)

        # ステータスラベル
        self.status_label = QLabel("⏳ 待機中...")
        self.status_label.setFont(QFont("Helvetica Neue", 11))
        self.status_label.setStyleSheet("color: rgba(150, 150, 255, 200); border: none; background: transparent;")
        container_layout.addWidget(self.status_label)

        # メイン応答テキスト
        self.text_label = QLabel("")
        self.text_label.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        self.text_label.setStyleSheet("color: white; border: none; background: transparent;")
        self.text_label.setWordWrap(True)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(self.text_label, 1)

        layout.addWidget(self.container)

    def _connect_signals(self):
        """シグナルとスロットを接続"""
        self.signals.append_text.connect(self._on_append_text)
        self.signals.set_text.connect(self._on_set_text)
        self.signals.show_status.connect(self._on_show_status)

    def _on_append_text(self, text: str):
        """テキストを追記"""
        current = self.text_label.text()
        self.text_label.setText(current + text)

    def _on_set_text(self, text: str):
        """テキストを上書き"""
        self.text_label.setText(text)

    def _on_show_status(self, status: str):
        """ステータスを更新"""
        self.status_label.setText(status)

    def clear(self):
        """表示をクリア"""
        self.text_label.setText("")
        self.status_label.setText("⏳ 待機中...")

    def keyPressEvent(self, event):
        """Esc キーで閉じる"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            QApplication.quit()
        super().keyPressEvent(event)


def create_app() -> tuple[QApplication, OverlayWindow]:
    """
    QApplication とオーバーレイウィンドウを作成する。

    Returns:
        (QApplication, OverlayWindow) のタプル
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    overlay = OverlayWindow()
    overlay.show()

    return app, overlay
