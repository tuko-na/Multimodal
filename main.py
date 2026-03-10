"""
main.py — Phase 1 統合実行 CLI

サブコマンドで各モジュールを実行する:
  python main.py benchmark  — FPSベンチマーク
  python main.py calibrate  — キャリブレーション（領域指定）
  python main.py capture    — キャプチャ→前処理→保存
"""

import sys
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

    # キャリブレーション設定を読み込む
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

    # キャプチャ
    with ScreenCapture() as cap:
        raw_image = cap.capture_region(
            region["x"], region["y"],
            region["width"], region["height"],
        )

    print(f"   取得画像サイズ: {raw_image.shape[1]}x{raw_image.shape[0]}")

    # 前処理
    processed = preprocess(raw_image, target_width)
    print(f"   前処理後サイズ: {processed.shape[1]}x{processed.shape[0]}")

    # 出力ディレクトリ
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 元画像保存
    raw_path = output_dir / "raw_capture.png"
    cv2.imwrite(str(raw_path), raw_image)
    print(f"   元画像保存: {raw_path}")

    # 前処理済み画像保存
    processed_path = output_dir / "processed.png"
    cv2.imwrite(str(processed_path), processed)
    print(f"   前処理済み保存: {processed_path}")

    # JPEG エンコードのサイズ確認
    jpeg_bytes = preprocess_and_encode(raw_image, target_width)
    print(f"   JPEG サイズ: {len(jpeg_bytes):,} bytes ({len(jpeg_bytes)/1024:.1f} KB)")

    print("\n✅ キャプチャ完了!")


def main():
    commands = {
        "benchmark": cmd_benchmark,
        "calibrate": cmd_calibrate,
        "capture": cmd_capture,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("使い方: python main.py <command>")
        print()
        print("コマンド:")
        print("  benchmark  — FPSベンチマーク（キャプチャ速度計測）")
        print("  calibrate  — キャリブレーション（問題領域の指定）")
        print("  capture    — キャプチャ → 前処理 → 保存")
        sys.exit(1)

    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
