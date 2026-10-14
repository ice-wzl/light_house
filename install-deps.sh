#!/bin/bash 
sudo apt update

sudo apt install -y \
    clang \
    llvm \
    libbpf-dev \
    bpftool \
    make
