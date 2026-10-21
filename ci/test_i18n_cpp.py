#!/usr/bin/env python3
import argparse
from pathlib import Path
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Compile and run the actual localization core with Qt6Core.")
    parser.add_argument("--tdesktop", type=Path, default=Path("../tdesktop"))
    parser.add_argument("--compiler", default="g++")
    args = parser.parse_args()
    tree = args.tdesktop.resolve()
    source = tree / "Telegram/SourceFiles"
    flags = shlex.split(subprocess.check_output(
        ["pkg-config", "--cflags", "--libs", "Qt6Core"], text=True))
    with tempfile.TemporaryDirectory(prefix="tele-i18n-test-") as directory:
        work = Path(directory)
        prelude = work / "prelude.h"
        prelude.write_text(
            '#include "base/basic_types.h"\n'
            'namespace rpl { template <typename Value = void, typename Error = void, '
            'typename Generator = void> class producer; }\n', encoding="utf-8")
        binary = work / "i18n-tests"
        subprocess.run([
            args.compiler, "-std=c++20", "-fPIC", "-include", str(prelude),
            "-I" + str(source), "-I" + str(tree / "Telegram/lib_base"),
            "-I" + str(tree / "Telegram/ThirdParty/GSL/include"),
            str(source / "tele/tele_i18n.cpp"),
            str(source / "tele/tele_lowercase.cpp"),
            str(source / "tele/tele_i18n_tests.cpp"),
            "-o", str(binary), *flags,
        ], check=True)
        subprocess.run([str(binary)], check=True)
    print("Production Qt localization checks passed: RU/EN, context, plurals, placeholders, raw data and lowercase.")


if __name__ == "__main__":
    main()
