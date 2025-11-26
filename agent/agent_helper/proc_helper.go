//go:build linux

package agent_helper

import (
	"fmt"
	"os"
	"os/user"
	"strconv"
	"strings"
	"syscall"
)

func get_proc_listing() []string {
	dir, err := os.Open("/proc")
	if err != nil {
		return nil
	}
	defer dir.Close()

	files, err := dir.Readdir(-1)
	if err != nil {
		return nil
	}
	var usernameFilenames []string
	for _, file := range files {
		if stat, ok := file.Sys().(*syscall.Stat_t); ok {
			uid := stat.Uid
			owner, err := user.LookupId(fmt.Sprintf("%d", uid))
			if err != nil {
				continue
			} else {
				usernameFilenames = append(usernameFilenames, owner.Username+","+file.Name())
			}
		}
	}
	return usernameFilenames
}

func read_proc_file(file_name string) string {
	data, err := os.ReadFile(file_name)
	if err != nil {
		return ""
	}
	content := strings.ReplaceAll(string(data), "\x00", " ") // replace \x00 with space
	return content
}

func get_ps() (string, error) {
	proc_files := get_proc_listing()
	process_list := ""
	process_list += fmt.Sprintf("%-20s %-7s  %-7s  %s\n", "USERNAME", "PID", "PPID", "CMDLINE")

	for _, name := range proc_files {
		if !strings.Contains(name, ",") {
			continue
		}
		procFilesParts := strings.Split(name, ",")
		username := procFilesParts[0]
		pid, err := strconv.Atoi(procFilesParts[1])
		if err != nil {
			continue
		}

		cmdline_path := fmt.Sprintf("/proc/%d/cmdline", pid)
		ppid_path := fmt.Sprintf("/proc/%d/status", pid)

		cmdline_file_contents := getCmdFileContents(cmdline_path, ppid_path)

		ppid_file_contents := read_proc_file(ppid_path)
		ppid_lines := strings.Split(ppid_file_contents, "\n")

		ppid_value := getPpidValue(ppid_lines)

		process_list += fmt.Sprintf("%-20s %-7d  %-7s  %s\n", username, pid, ppid_value, cmdline_file_contents)
	}
	return process_list, nil
}

func getCmdFileContents(cmdline_path string, ppid_path string) string {
	if len(read_proc_file(cmdline_path)) != 0 {
		return read_proc_file(cmdline_path)
	}
	status_contents := read_proc_file(ppid_path)
	cmdline_file_lines := strings.Split(status_contents, "\n")

	for _, line := range cmdline_file_lines {
		if strings.HasPrefix(line, "Name:") {
			parts := strings.Fields(line)
			if len(parts) == 2 {
				return fmt.Sprintf("[%s]", parts[1])
			} else {
				return "?"
			}
		}
	}
	return "?"
}

func getPpidValue(ppid_lines []string) string {
	for _, line := range ppid_lines {
		if strings.HasPrefix(line, "PPid:") {
			parts := strings.Fields(line)
			if len(parts) == 2 {
				return parts[1]
			} else {
				return "?"
			}
		}
	}
	return "?"
}
