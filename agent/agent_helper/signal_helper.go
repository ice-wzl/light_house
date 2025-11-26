//go:build linux

package agent_helper

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
)

// Setup the signal channel
func SetupSignalHandler() chan os.Signal {
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT)
	return sigChan
}

// Send a "death message" to the server
func SendDeathMessage(serverAddr string, session string) (int, error) {
	url := fmt.Sprintf("%s/health/d/%s", serverAddr, session)

	resp, err := CustomClient.Get(url)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil
}

// Start signal handling goroutine
func SigHandler(serverAddr string, session string) {
	sigChan := SetupSignalHandler()
	go func() {
		_ = <-sigChan
		SendDeathMessage(serverAddr, session)
		os.Exit(5)
	}()
}
