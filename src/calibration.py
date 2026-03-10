"""
calibration.py — キャリブレーションモジュール

Tkinter を使用して全画面の半透明オーバーレイを表示し、
マウスドラッグで問題領域の矩形を選択する。
選択した座標を config/calibration.json に保存する。

macOS の Retina ディスプレイに対応:
- Tkinter は論理座標で動作
- mss は物理ピクセル座標で動作
- スケールファクターを検出し、物理ピクセル座標に変換して保存
"""

import json
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path

# デフォルトの設定ファイルパス
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "calibration.json"

# デフォルトの目標リサイズ幅
DEFAULT_TARGET_WIDTH = 800


def _detect_scale_factor(root: tk.Tk) -> int:
    """
    Retina スケールファクターを検出する。

    Tkinter の winfo_screenwidth() は論理ピクセルを返し、
    mss は物理ピクセルで動作する。
    この比率からスケールファクターを算出する。
    """
    try:
        import mss
        with mss.mss() as sct:
            physical_width = sct.monitors[1]["width"]
        logical_width = root.winfo_screenwidth()
        factor = round(physical_width / logical_width)
        return max(1, factor)
    except Exception:
        return 2  # macOS Retina のデフォルト


class RegionSelector:
    """マウスドラッグで矩形領域を選択するUI"""

    def __init__(self):
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.rect_id = None
        self.selected = False

    def run(self) -> dict | None:
        """
        全画面オーバーレイを表示し、ユーザーに領域を選択させる。

        Returns:
            選択された領域の情報 (dict) または None (キャンセル時)
        """
        self.root = tk.Tk()
        self.root.title("キャリブレーション — ドラッグで問題領域を選択")

        # スケールファクター検出
        self.scale_factor = _detect_scale_factor(self.root)

        # 全画面の半透明オーバーレイ
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.root.configure(bg="black")

        # Canvas（描画領域）
        self.canvas = tk.Canvas(
            self.root,
            cursor="crosshair",
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 操作説明テキスト
        self.canvas.create_text(
            self.root.winfo_screenwidth() // 2,
            30,
            text="ドラッグで問題領域を選択 | Escでキャンセル",
            fill="white",
            font=("Helvetica", 20),
        )

        # イベントバインド
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", self._on_cancel)

        self.root.mainloop()

        if not self.selected:
            return None

        # 論理座標 → 物理ピクセル座標に変換
        x = min(self.start_x, self.end_x) * self.scale_factor
        y = min(self.start_y, self.end_y) * self.scale_factor
        w = abs(self.end_x - self.start_x) * self.scale_factor
        h = abs(self.end_y - self.start_y) * self.scale_factor

        return {
            "region": {
                "x": x,
                "y": y,
                "width": w,
                "height": h,
            },
            "logical_region": {
                "x": min(self.start_x, self.end_x),
                "y": min(self.start_y, self.end_y),
                "width": abs(self.end_x - self.start_x),
                "height": abs(self.end_y - self.start_y),
            },
            "scale_factor": self.scale_factor,
            "target_width": DEFAULT_TARGET_WIDTH,
            "created_at": datetime.now().isoformat(),
        }

    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _on_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.end_x,
            self.end_y,
            outline="lime",
            width=2,
        )

    def _on_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        # 最低サイズのチェック（小さすぎるドラッグは無視）
        if abs(self.end_x - self.start_x) < 10 or abs(self.end_y - self.start_y) < 10:
            return
        self.selected = True
        self.root.destroy()

    def _on_cancel(self, event):
        self.selected = False
        self.root.destroy()


def run_calibration(config_path: Path = CONFIG_FILE) -> dict | None:
    """
    キャリブレーションを実行し、結果をJSONに保存する。

    Args:
        config_path: 設定ファイルの保存先

    Returns:
        キャリブレーション結果 (dict) または None
    """
    print("🎯 キャリブレーション開始")
    print("   画面にオーバーレイが表示されます。")
    print("   マウスドラッグで問題が表示される領域を選択してください。")
    print("   Esc でキャンセルします。\n")

    selector = RegionSelector()
    result = selector.run()

    if result is None:
        print("❌ キャリブレーションがキャンセルされました。")
        return None

    # 設定ディレクトリがなければ作成
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON に保存
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    region = result["region"]
    print(f"✅ キャリブレーション完了!")
    print(f"   物理座標: x={region['x']}, y={region['y']}, "
          f"w={region['width']}, h={region['height']}")
    print(f"   スケールファクター: {result['scale_factor']}x")
    print(f"   保存先: {config_path}")

    return result


def load_calibration(config_path: Path = CONFIG_FILE) -> dict:
    """
    保存済みのキャリブレーション結果を読み込む。

    Args:
        config_path: 設定ファイルのパス

    Returns:
        キャリブレーション設定 (dict)

    Raises:
        FileNotFoundError: キャリブレーション未実施の場合
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"キャリブレーション設定が見つかりません: {config_path}\n"
            "先に 'python main.py calibrate' を実行してください。"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
