package agent_config
// Where the agent will call back 
const ServerUrl = "https://192.168.15.45:8000"
// Value in minutes between callback 
var CallbackVal = 1
// Percent of the callback value to vary callback time
var JitterVal = 15
// Amount of missed checkins before self termination
var SelfTerminateVal = 20
// Amount of seconds to sleep before first callback
var StartDelayVal = 5

var ReqHeaders = map[string]string{
	"Content-Type": "application/json",
	"Accept-Encoding": "gzip, deflate, br, zstd",
	"Accept-Language": "en-US,en;q=0.9",
	"SEC-CH-UA-PLATFORM": "Windows",
	"SEC-CH-UA-PLATFORM-VERSION": "3.0.0",
	"SEC-FETCH-SITE": "cross-site",
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}
