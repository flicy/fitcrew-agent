"""Compile mini-program templates/styles with locally installed official tools."""

import argparse
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compiler-dir",
        type=Path,
        default=Path(
            "/Applications/wechatwebdevtools.app/Contents/Resources/"
            "app.asar.unpacked/node_modules/wcc-exec"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "apps/wechat-mini"
    with tempfile.TemporaryDirectory(prefix="fitcrew-wechat-compile-") as temporary:
        for compiler, extensions in [("wcc", (".wxml", ".wxs")), ("wcsc", (".wxss",))]:
            executable = args.compiler_dir / compiler
            if not executable.is_file():
                parser.error(f"Official compiler unavailable: {executable}")
            sources = sorted(
                str(path.relative_to(root))
                for path in root.rglob("*")
                if path.is_file() and path.suffix in extensions
            )
            if not sources:
                parser.error(f"No source files for {compiler}")
            output = Path(temporary) / f"{compiler}.js"
            subprocess.run(
                [str(executable), "-o", str(output), *sources], cwd=root, check=True
            )
            if not output.is_file() or output.stat().st_size == 0:
                parser.error(f"Compiler did not produce output: {compiler}")
            print(f"{compiler}: compiled {len(sources)} files")
    print("Offline compilation passed; login, device behavior and submission remain unverified.")


if __name__ == "__main__":
    main()
