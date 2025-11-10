package agent_helper

import (
	"bytes"
	"compress/gzip"
	"encoding/base64"
	"encoding/hex"
	"io"
)

func EncodeToBaseHexString(input string) string {
	encodedBase64 := base64.StdEncoding.EncodeToString([]byte(input))
	encodedHex := hex.EncodeToString([]byte(encodedBase64))
	return encodedHex
}

func DecodeFromHexBaseString(input string) (string, error) {
	decodedHex, err := hex.DecodeString(input)
	if err != nil {
		return "", err
	}
	decodedBase, err := base64.StdEncoding.DecodeString(string(decodedHex))
	if err != nil {
		return "", err
	}
	return string(decodedBase), nil
}

func EncodeBytesToBaseHexString(input []byte) string {
	encodedBase64 := base64.StdEncoding.EncodeToString(input)
	encodedHex := hex.EncodeToString([]byte(encodedBase64))
	return encodedHex
}

func decodeUpload(input string) ([]byte, error) {
	decHex, err := hex.DecodeString(input)
	if err != nil {
		return nil, err
	}
	decBase, err := base64.StdEncoding.DecodeString(string(decHex))
	if err != nil {
		return nil, err
	}
	gzipData, err := gzip.NewReader(bytes.NewReader(decBase))
	if err != nil {
		return nil, err
	}
	defer gzipData.Close()
	var out bytes.Buffer
	if _, err := io.Copy(&out, gzipData); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}
