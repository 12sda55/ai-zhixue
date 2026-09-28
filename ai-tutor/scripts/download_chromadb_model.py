"""预下载 ChromaDB 默认 embedding 模型到 chromadb 期望的缓存路径。

为什么需要这个脚本：
- chromadb 0.4.22 的 ONNXMiniLM_L6_V2 默认从 S3 下载 onnx.tar.gz：
  https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz
- 该 S3 在国内访问极慢（Sealos pod 内实测 40k/s，83MB 下载需要 6+ 小时）
- 国内 HuggingFace 镜像 hf-mirror.com 上 sentence-transformers/all-MiniLM-L6-v2
  仓库内的 onnx/model.onnx 与 chromadb 期望的 model.onnx 字节完全一致
  (sha256 校验过, 都是 90405214 字节)
- chromadb 启动时若发现 /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/
  下的 6 个文件全部存在则跳过下载（见 ONNXMiniLM_L6_V2._download_model_if_not_exists）

所以本脚本在 Docker 构建时把模型文件提前放到 chromadb 期望路径，
让容器启动时直接复用，跳过 S3 慢速下载。
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request

# chromadb 0.4.22 ONNXMiniLM_L6_V2 期望路径:
#   DOWNLOAD_PATH = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"
#   EXTRACTED_FOLDER_NAME = "onnx"
#   实际文件在 DOWNLOAD_PATH/onnx/ 下
HOME = os.path.expanduser("~")
TARGET_DIR = os.path.join(
    HOME, ".cache", "chroma", "onnx_models", "all-MiniLM-L6-v2", "onnx"
)

# hf-mirror.com 国内可达，sentence-transformers/all-MiniLM-L6-v2 仓库内的文件
# 与 chromadb onnx.tar.gz 解压后的内容字节一致
HF_MIRROR = "https://hf-mirror.com/sentence-transformers/all-MiniLM-L6-v2/resolve/main"

# chromadb ONNXMiniLM_L6_V2._download_model_if_not_exists 检查的 6 个文件
FILES = [
    ("config.json", f"{HF_MIRROR}/config.json"),
    ("special_tokens_map.json", f"{HF_MIRROR}/special_tokens_map.json"),
    ("tokenizer_config.json", f"{HF_MIRROR}/tokenizer_config.json"),
    ("tokenizer.json", f"{HF_MIRROR}/tokenizer.json"),
    ("vocab.txt", f"{HF_MIRROR}/vocab.txt"),
    # model.onnx 在 onnx/ 子目录
    ("model.onnx", f"{HF_MIRROR}/onnx/model.onnx"),
]

EXPECTED_SIZES = {
    "config.json": 612,
    "special_tokens_map.json": 112,
    "tokenizer_config.json": 350,
    "tokenizer.json": 466247,
    "vocab.txt": 231508,
    "model.onnx": 90405214,
}

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def download_one(name: str, url: str, out_path: str) -> tuple[bool, str]:
    """下载单个文件，带重试。已存在且大小匹配则跳过。"""
    if os.path.exists(out_path):
        actual_size = os.path.getsize(out_path)
        expected = EXPECTED_SIZES.get(name)
        if expected and actual_size == expected:
            return True, f"skip (exists, {actual_size} bytes)"
        # 大小不匹配 → 重新下载
        os.remove(out_path)

    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Downloading {name} (attempt {attempt}/{MAX_RETRIES})...", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Dockerfile-build/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(out_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            actual_size = os.path.getsize(out_path)
            expected = EXPECTED_SIZES.get(name)
            if expected and actual_size != expected:
                last_err = f"size mismatch: got {actual_size}, expected {expected}"
                os.remove(out_path)
                print(f"  WARN {name}: {last_err}, retrying...", flush=True)
                time.sleep(RETRY_DELAY)
                continue
            return True, f"ok ({actual_size} bytes)"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            print(f"  WARN {name} attempt {attempt} failed: {last_err}", flush=True)
            if os.path.exists(out_path):
                os.remove(out_path)
            time.sleep(RETRY_DELAY)
    return False, last_err


def main() -> int:
    print(f"[chromadb-model] Target dir: {TARGET_DIR}", flush=True)
    os.makedirs(TARGET_DIR, exist_ok=True)

    failures = []
    for name, url in FILES:
        out_path = os.path.join(TARGET_DIR, name)
        ok, msg = download_one(name, url, out_path)
        status = "OK " if ok else "FAIL"
        print(f"[{status}] {name}: {msg}", flush=True)
        if not ok:
            failures.append(name)

    if failures:
        print(f"\n[chromadb-model] FAILED files: {', '.join(failures)}", flush=True)
        print("[chromadb-model] chromadb will fall back to slow S3 download at startup.", flush=True)
        return 1

    print("\n[chromadb-model] All 6 files ready. chromadb will skip download at startup.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
