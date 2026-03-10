"""
benchmark.py — FPS ベンチマークモジュール

mss による画面キャプチャの速度限界を計測する。
異なる領域サイズでの FPS を比較し、ボトルネックを可視化する。
"""

import time
import numpy as np
from src.capture import ScreenCapture


def run_benchmark(
    x: int = 0,
    y: int = 0,
    width: int = 800,
    height: int = 600,
    num_frames: int = 100,
    num_trials: int = 3,
) -> dict:
    """
    指定領域のキャプチャ FPS を計測する。

    Args:
        x, y: キャプチャ開始座標
        width, height: キャプチャ領域サイズ
        num_frames: 1トライアルあたりのフレーム数
        num_trials: トライアル回数

    Returns:
        計測結果の辞書
    """
    fps_list = []

    with ScreenCapture() as cap:
        for trial in range(num_trials):
            start = time.perf_counter()
            for _ in range(num_frames):
                _ = cap.capture_region(x, y, width, height)
            elapsed = time.perf_counter() - start
            fps = num_frames / elapsed
            fps_list.append(fps)

    return {
        "region": f"{width}x{height}",
        "frames_per_trial": num_frames,
        "trials": num_trials,
        "fps_avg": np.mean(fps_list),
        "fps_min": np.min(fps_list),
        "fps_max": np.max(fps_list),
        "ms_per_frame_avg": 1000.0 / np.mean(fps_list),
    }


def run_full_benchmark() -> list[dict]:
    """
    複数の領域サイズでベンチマークを実行。

    Returns:
        各サイズごとの計測結果のリスト
    """
    sizes = [
        (400, 300),
        (800, 600),
        (1280, 720),
        (1920, 1080),
    ]

    results = []
    for width, height in sizes:
        print(f"  計測中: {width}x{height} ... ", end="", flush=True)
        result = run_benchmark(x=0, y=0, width=width, height=height)
        print(f"{result['fps_avg']:.1f} FPS ({result['ms_per_frame_avg']:.2f} ms/frame)")
        results.append(result)

    return results


def print_results(results: list[dict]):
    """ベンチマーク結果をテーブル形式で表示"""
    print("\n" + "=" * 65)
    print(f"{'領域サイズ':>12} | {'平均FPS':>10} | {'最小FPS':>10} | {'ms/frame':>10}")
    print("-" * 65)
    for r in results:
        print(
            f"{r['region']:>12} | "
            f"{r['fps_avg']:>10.1f} | "
            f"{r['fps_min']:>10.1f} | "
            f"{r['ms_per_frame_avg']:>10.2f}"
        )
    print("=" * 65)

    # SLA判定
    target_ms = 16.0  # 60FPS = 16ms/frame
    fastest = results[0]
    print(f"\n[SLA判定] 内部処理目標: {target_ms}ms 以内 (60FPS相当)")
    if fastest["ms_per_frame_avg"] <= target_ms:
        print(f"  ✅ {fastest['region']} でキャプチャのみ {fastest['ms_per_frame_avg']:.2f}ms — SLA達成可能")
    else:
        print(f"  ⚠️  最小領域 {fastest['region']} でも {fastest['ms_per_frame_avg']:.2f}ms — 要最適化")
