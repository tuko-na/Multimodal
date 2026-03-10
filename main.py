"""
main.py — 最速解答システム CLI

サブコマンドで各モジュールを実行する:
  python3 main.py benchmark     — FPSベンチマーク
  python3 main.py calibrate     — キャリブレーション（領域指定）
  python3 main.py capture       — キャプチャ→前処理→保存
  python3 main.py solve         — フルパイプライン（キャプチャ→AI推論→オーバーレイ表示）
  python3 main.py solve --no-overlay  — オーバーレイなしでターミナル出力のみ
"""

import sys
import time
from pathlib import Path


def cmd_benchmark():
    """FPS ベンチマークを実行"""
    from src.benchmark import run_full_benchmark, print_results

    print("🚀 FPS ベンチマーク開始\n")
    results = run_full_benchmark()
    print_results(results)


def cmd_calibrate():
    """キャリブレーション（領域選択）を実行"""
    from src.calibration import run_calibration

    run_calibration()


def cmd_capture():
    """キャリブレーション済み座標で1枚キャプチャ→前処理→保存"""
    import cv2
    from src.calibration import load_calibration
    from src.capture import ScreenCapture
    from src.preprocess import preprocess, preprocess_and_encode

    try:
        config = load_calibration()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    region = config["region"]
    target_width = config.get("target_width", 800)

    print(f"📸 キャプチャ実行")
    print(f"   領域: x={region['x']}, y={region['y']}, "
          f"w={region['width']}, h={region['height']}")
    print(f"   目標幅: {target_width}px\n")

    with ScreenCapture() as cap:
        raw_image = cap.capture_region(
            region["x"], region["y"],
            region["width"], region["height"],
        )

    print(f"   取得画像サイズ: {raw_image.shape[1]}x{raw_image.shape[0]}")

    processed = preprocess(raw_image, target_width)
    print(f"   前処理後サイズ: {processed.shape[1]}x{processed.shape[0]}")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    raw_path = output_dir / "raw_capture.png"
    cv2.imwrite(str(raw_path), raw_image)
    print(f"   元画像保存: {raw_path}")

    processed_path = output_dir / "processed.png"
    cv2.imwrite(str(processed_path), processed)
    print(f"   前処理済み保存: {processed_path}")

    jpeg_bytes = preprocess_and_encode(raw_image, target_width)
    print(f"   JPEG サイズ: {len(jpeg_bytes):,} bytes ({len(jpeg_bytes)/1024:.1f} KB)")

    print("\n✅ キャプチャ完了!")


def cmd_solve():
    """フルパイプライン: キャプチャ → 前処理 → AI推論 → オーバーレイ表示"""
    from src.calibration import load_calibration
    from src.capture import ScreenCapture
    from src.preprocess import preprocess_and_encode
    from src.inference import stream_answer, get_answer

    use_overlay = "--no-overlay" not in sys.argv

    # キャリブレーション読み込み
    try:
        config = load_calibration()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    region = config["region"]
    target_width = config.get("target_width", 800)

    print("🧠 最速解答システム起動")
    print(f"   領域: x={region['x']}, y={region['y']}, "
          f"w={region['width']}, h={region['height']}")
    print(f"   目標幅: {target_width}px")
    print(f"   オーバーレイ: {'ON' if use_overlay else 'OFF'}\n")

    # ── Step 1: キャプチャ ──
    t_start = time.perf_counter()
    with ScreenCapture() as cap:
        raw_image = cap.capture_region(
            region["x"], region["y"],
            region["width"], region["height"],
        )
    t_capture = time.perf_counter()

    # ── Step 2: 前処理 ──
    jpeg_bytes = preprocess_and_encode(raw_image, target_width)
    t_preprocess = time.perf_counter()

    print(f"   ⚡ キャプチャ: {(t_capture - t_start)*1000:.1f}ms")
    print(f"   ⚡ 前処理:     {(t_preprocess - t_capture)*1000:.1f}ms")
    print(f"   ⚡ JPEG:       {len(jpeg_bytes)/1024:.1f} KB")
    print()

    if use_overlay:
        # ── オーバーレイ付きストリーミング ──
        _solve_with_overlay(jpeg_bytes, t_start)
    else:
        # ── ターミナルのみ ──
        _solve_terminal(jpeg_bytes, t_start)


def _solve_terminal(jpeg_bytes: bytes, t_start: float):
    """オーバーレイなし — ターミナルにストリーミング出力"""
    from src.inference import stream_answer

    print("   📡 Gemini Flash へ送信中...\n")

    t_first_token = None

    def on_chunk(text: str):
        nonlocal t_first_token
        if t_first_token is None:
            t_first_token = time.perf_counter()
        print(text, end="", flush=True)

    t_send = time.perf_counter()
    full_text = stream_answer(jpeg_bytes, callback=on_chunk)
    t_done = time.perf_counter()

    print("\n")
    print("─" * 40)
    print(f"   ⏱️  E2E 合計:        {(t_done - t_start)*1000:.0f}ms")
    print(f"   ⏱️  API応答 (TTFT):   {(t_first_token - t_send)*1000:.0f}ms" if t_first_token else "")
    print(f"   ⏱️  API応答 (全体):   {(t_done - t_send)*1000:.0f}ms")
    print("─" * 40)


def _solve_with_overlay(jpeg_bytes: bytes, t_start: float):
    """オーバーレイ付きストリーミング — PyQt6 + スレッドで推論"""
    import threading
    from src.overlay import create_app, OverlayWindow
    from src.inference import stream_answer

    app, overlay = create_app()
    overlay.signals.show_status.emit("📡 Gemini Flash へ送信中...")

    t_first_token = None

    def run_inference():
        nonlocal t_first_token

        def on_chunk(text: str):
            nonlocal t_first_token
            if t_first_token is None:
                t_first_token = time.perf_counter()
                overlay.signals.show_status.emit("✅ 応答受信中...")
            overlay.signals.append_text.emit(text)

        try:
            t_send = time.perf_counter()
            full_text = stream_answer(jpeg_bytes, callback=on_chunk)
            t_done = time.perf_counter()

            ttft = f"{(t_first_token - t_send)*1000:.0f}ms" if t_first_token else "N/A"
            total = f"{(t_done - t_start)*1000:.0f}ms"
            overlay.signals.show_status.emit(
                f"✅ 完了 | E2E: {total} | TTFT: {ttft}"
            )

            # ターミナルにもタイミングを出力
            print(f"\n   ⏱️  E2E 合計:        {total}")
            print(f"   ⏱️  API応答 (TTFT):   {ttft}")
            print(f"   ⏱️  API応答 (全体):   {(t_done - t_send)*1000:.0f}ms")

        except Exception as e:
            overlay.signals.show_status.emit(f"❌ エラー: {e}")
            print(f"\n❌ 推論エラー: {e}")

    # 推論をバックグラウンドスレッドで実行
    thread = threading.Thread(target=run_inference, daemon=True)
    thread.start()

    # Qt イベントループ開始（Escで終了）
    print("   🖥️  オーバーレイ表示中 (Esc で終了)")
    app.exec()
    print("\n✅ 完了!")


def main():
    commands = {
        "benchmark": cmd_benchmark,
        "calibrate": cmd_calibrate,
        "capture": cmd_capture,
        "solve": cmd_solve,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("使い方: python3 main.py <command>")
        print()
        print("コマンド:")
        print("  benchmark     — FPSベンチマーク（キャプチャ速度計測）")
        print("  calibrate     — キャリブレーション（問題領域の指定）")
        print("  capture       — キャプチャ → 前処理 → 保存")
        print("  solve         — 解答（キャプチャ → AI推論 → オーバーレイ表示）")
        print()
        print("オプション:")
        print("  --no-overlay  — オーバーレイなし（ターミナル出力のみ）")
        sys.exit(1)

    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()

