package agent_helper

//go:generate go tool bpf2go -cc clang bpf ./bpf/pidhide.bpf.c -- -O2 -g -Wall -I./bpf
