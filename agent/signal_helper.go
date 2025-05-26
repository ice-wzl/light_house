package main

import (
    "fmt"
    "net/http"
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

    resp, err := http.Get(url)
    if err != nil {
        return 0, err
    }
    defer resp.Body.Close()
    fmt.Println("Death message response:", resp.StatusCode)
    return resp.StatusCode, nil
}

// Start signal handling goroutine
func sigHandler(serverAddr string, session string) {
    sigChan := setupSignalHandler()
    go func() {
        sig := <-sigChan
        fmt.Printf("Received signal: %s\n", sig)
        sendDeathMessage(serverAddr, session)
        os.Exit(5)
    }()
}
