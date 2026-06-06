"""
WD14 Extended Models Downloader
自动下载 WD14 扩展模型
"""
import os
import sys
from pathlib import Path

def download_model_from_hf(repo_id: str, files_to_download: list, local_dir: Path, rename_map: dict = None):
    """从 HuggingFace 下载模型文件"""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("错误: 需要安装 huggingface_hub")
        print("请运行: pip install huggingface_hub")
        return False

    local_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n正在从 {repo_id} 下载文件...")

    for file_name in files_to_download:
        try:
            print(f"  下载: {file_name} ...")
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=file_name,
                local_dir=local_dir,
                local_dir_use_symlinks=False
            )

            if rename_map and file_name in rename_map:
                new_name = rename_map[file_name]
                new_path = local_dir / new_name
                os.rename(downloaded_path, new_path)
                print(f"  ✓ 已下载并重命名为: {new_name}")
            else:
                print(f"  ✓ 已下载: {file_name}")

        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            return False

    return True


def main():
    print("=" * 60)
    print("  WD14 扩展模型下载工具")
    print("=" * 60)
    print()

    root_dir = Path(__file__).resolve().parents[0]
    models_dir = root_dir / "models" / "wd14"
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"模型保存目录: {models_dir}")
    print()

    models_config = {
        "1": {
            "name": "CL Tagger v1.02",
            "repo": "Nonene/cl_tagger",
            "files": ["model.onnx", "selected_tags.csv"],
            "rename": {
                "model.onnx": "cl_tagger_model.onnx",
                "selected_tags.csv": "cl_tagger_tags.csv"
            }
        },
        "2": {
            "name": "PixAI Tagger v0.9",
            "repo": "pixai-labs/pixai-tagger-v0.9",
            "files": ["model.onnx", "selected_tags.csv"],
            "rename": {
                "model.onnx": "pixai_tagger_model.onnx",
                "selected_tags.csv": "pixai_tagger_tags.csv"
            }
        },
        "3": {
            "name": "WD EVA02 Large v3",
            "repo": "SmilingWolf/wd-eva02-large-tagger-v3",
            "files": ["model.onnx", "selected_tags.csv"],
            "rename": {
                "model.onnx": "wd_eva02_large_model.onnx",
                "selected_tags.csv": "wd_eva02_large_tags.csv"
            }
        }
    }

    print("可下载的模型:")
    print()
    for key, config in models_config.items():
        print(f"  [{key}] {config['name']}")
        print(f"      仓库: {config['repo']}")
        print()

    print("[0] 下载全部模型")
    print()

    choice = input("请选择要下载的模型 [0-3]: ").strip()

    if choice == "0":
        print("\n开始下载所有模型...")
        for key, config in models_config.items():
            success = download_model_from_hf(
                repo_id=config["repo"],
                files_to_download=config["files"],
                local_dir=models_dir,
                rename_map=config["rename"]
            )
            if not success:
                print(f"\n模型 {config['name']} 下载失败")
            else:
                print(f"\n✓ 模型 {config['name']} 下载成功")

    elif choice in models_config:
        config = models_config[choice]
        print(f"\n开始下载 {config['name']}...")
        success = download_model_from_hf(
            repo_id=config["repo"],
            files_to_download=config["files"],
            local_dir=models_dir,
            rename_map=config["rename"]
        )
        if success:
            print(f"\n✓ 模型下载成功！")
        else:
            print(f"\n✗ 模型下载失败")
    else:
        print("无效的选择")
        return

    print()
    print("=" * 60)
    print("  下载完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
