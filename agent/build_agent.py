#!/usr/bin/python3
import argparse
import subprocess
import os

archs = [
    "386",
    "arm",
    "mips",
    "mipsle",
    "arm64",
    "amd64",
    "loong64",
    "mips64",
    "mips64le",
    "ppc64",
    "ppc64le",
    "riscv64le",
    "s390x",
]
BUILD_DIR = "build"


def build_dir_setup():
    if not os.path.exists(BUILD_DIR):
        os.mkdir(BUILD_DIR)


def build_galleon(arch: str):
    # need to add ldflags
    env = os.environ.copy()
    env["GOOS"] = "linux"
    env["GOARCH"] = f"{arch}"
    env["CGO_ENABLED"] = "0"

    OUTFILE = f"galleon_{arch}.elf"

    cmd = ["go", "build", "-ldflags=-s -w", "-o", f"{BUILD_DIR}/{OUTFILE}"]

    proc = subprocess.run(cmd, capture_output=True, check=False)
    print("-----GO BUILD STDOUT-----")
    print(proc.stdout)
    print("-----GO BUILD STDERR-----")
    print(proc.stderr)
    if len(proc.stderr) == 0:
        print("[+] Galleon build successful")
        upx_compress(OUTFILE)
    else:
        print("[-] Galleon build failed")


def upx_compress(OUTFILE: str):
    cmd = ["upx", "-9", f"{BUILD_DIR}/{OUTFILE}"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    print("-----UPX STDOUT-----")
    print(proc.stdout)
    print("-----UPX STDERR-----")
    print(proc.stderr)


if __name__ == "__main__":
    opts = argparse.ArgumentParser(
        prog="build_agent.py", description="Builder for the Galleon agent"
    )
    opts.add_argument(
        "-a",
        "--arch",
        choices=archs,
        help="The arch to build Galleon with",
        required=True,
        dest="arch",
        type=str,
    )
    args = opts.parse_args()

    build_dir_setup()
    build_galleon(args.arch)
