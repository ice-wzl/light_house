package agent_helper

import (
	"fmt"
	"os"
	"strconv"
	"strings"
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
	var filenames []string
	for _, file := range files {
		filenames = append(filenames, file.Name())
	}
	return filenames

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
	process_list += fmt.Sprintf("%-7s  %-7s  %s\n", "PID", "PPID", "CMDLINE")

	for _, name := range proc_files {
		pid, err := strconv.Atoi(name)
		if err != nil {
			continue
		}

		cmdline_path := fmt.Sprintf("/proc/%d/cmdline", pid)
		ppid_path := fmt.Sprintf("/proc/%d/status", pid)

		var cmdline_file_contents string
		if len(read_proc_file(cmdline_path)) != 0 {
			cmdline_file_contents = read_proc_file(cmdline_path)
		} else {
			// Fallback to reading name from /proc/[pid]/status
			status_contents := read_proc_file(ppid_path)
			cmdline_file_lines := strings.Split(status_contents, "\n")

			for _, line := range cmdline_file_lines {
				if strings.HasPrefix(line, "Name:") {
					parts := strings.Fields(line)
					if len(parts) == 2 {
						cmdline_file_contents = fmt.Sprintf("[%s]", parts[1])
					} else {
						cmdline_file_contents = "?"
					}
					break
				}
			}
		}

		ppid_file_contents := read_proc_file(ppid_path)
		ppid_lines := strings.Split(ppid_file_contents, "\n")

		var ppid_value string
		for _, line := range ppid_lines {
			if strings.HasPrefix(line, "PPid:") {
				parts := strings.Fields(line)
				if len(parts) == 2 {
					ppid_value = parts[1]
				} else {
					ppid_value = "?"
				}
				break
			}
		}

		process_list += fmt.Sprintf("%-7d  %-7s  %s\n", pid, ppid_value, cmdline_file_contents)
	}
	return process_list, nil
}
