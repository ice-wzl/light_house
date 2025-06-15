package main

import (
	"fmt"
	"os"
	"os/signal"
	"syscall"
)

// Setup the signal channel
func setupSignalHandler() chan os.Signal {
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT)
	return sigChan
}

// Send a "death message" to the server
func sendDeathMessage(serverAddr string, session string) (int, error) {
	url := fmt.Sprintf("%s/health/d/%s", serverAddr, session)

	resp, err := customClient.Get(url)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil
}

// Start signal handling goroutine
func sigHandler(serverAddr string, session string) {
	sigChan := setupSignalHandler()
	go func() {
		_ = <-sigChan
		sendDeathMessage(serverAddr, session)
		os.Exit(5)
	}()
}
