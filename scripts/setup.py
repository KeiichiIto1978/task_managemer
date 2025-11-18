#!/usr/bin/env python3
"""Initial setup helper for the Task Collection System."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List

# Top level directories and their required sub-directories
REQUIRED_DIRECTORIES: Dict[Path, Iterable[Path]] = {
    Path("config"): (),
    Path("docs"): (),
    Path("logs"): (),
    Path("scripts"): (),
    Path("servers"): (),
    Path("tests"): (),
    Path("cache"): (Path("slack"),),
}

def ensure_directories(root: Path) -> List[Path]:
    """Create required directories if they are missing."""
    created: List[Path] = []

    for top_level, sub_paths in REQUIRED_DIRECTORIES.items():
        target = root / top_level
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(target)

        for child in sub_paths:
            subdir = target / child
            if not subdir.exists():
                subdir.mkdir(parents=True, exist_ok=True)
                created.append(subdir)

    return created


def copy_env_template(root: Path, overwrite: bool) -> Path | None:
    """Copy .env template to project root if needed."""
    template = root / "config" / ".env.template"
    destination = root / ".env"

    if not template.exists():
        print("WARNING: config/.env.template が見つかりません。テンプレートを準備してください。")
        return None

    if destination.exists() and not overwrite:
        print("INFO: .env は既に存在するためコピーをスキップします (--force で上書き可)。")
        return destination

    shutil.copyfile(template, destination)
    print(f"SUCCESS: .env を {template} からコピーしました。")
    return destination


def ensure_requirements(root: Path, install: bool) -> None:
    """Install Python dependencies when requested."""
    requirements = root / "requirements.txt"

    if not requirements.exists():
        print("WARNING: requirements.txt が見つかりません。Python 依存関係は別途ご確認ください。")
        return

    if not install:
        print("INFO: 必要な場合は手動で実行してください -> pip install -r requirements.txt")
        return

    print("INFO: pip install -r requirements.txt を実行します...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
    except subprocess.CalledProcessError as exc:  # pragma: no cover - 表示用
        print(f"ERROR: 依存関係のインストールに失敗しました: {exc}")
        print("       コマンドを再実行してみてください。")
    else:
        print("SUCCESS: 依存関係をインストールしました。")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Task Collection System の初期セットアップを実行します。"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="プロジェクトルート (既定: 現在の作業ディレクトリ)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=".env が存在する場合でもテンプレートを上書き",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="requirements.txt を使って依存関係をインストール",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()

    print(f"INFO: プロジェクトルート -> {project_root}")
    created_dirs = ensure_directories(project_root)
    if created_dirs:
        for directory in created_dirs:
            print(f"SUCCESS: ディレクトリを作成しました -> {directory}")
    else:
        print("INFO: 必要なディレクトリは既に存在します。")

    env_path = copy_env_template(project_root, args.force)
    if env_path is None:
        print("ERROR: .env が存在しないため手動で作成してください。")
    else:
        print(f"INFO: .env に API キー等の値を入力してください -> {env_path}")

    ensure_requirements(project_root, args.install_deps)

    print("\n次のステップ:")
    print("  1. .env に API キーやトークン類を入力する")
    print("  2. Claude Desktop 用の config/mcp.json を確認する (README 参照)")
    print("  3. tests/validate_config.py で設定チェックを実行する")


if __name__ == "__main__":
    main()
