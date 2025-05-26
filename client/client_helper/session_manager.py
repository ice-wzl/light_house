#!/usr/bin/python3
import httpx
import shlex

from prettytable import PrettyTable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text

# local imports
from client_helper.user_manager import fix_date
from client_helper.tasking_manager import get_tasking, send_task


# colors for the sessions prompt
style_session = Style.from_dict(
    {
        "": "#FFFAF0",
        "host": "#f20707",
        "arrow": "#FFFAF0",
    }
)

# the prompty layout and design for the session context
message_session = [
    ("class:host", "!session"),
    ("class:arrow", " > ")
]

# valid commands for the session context
cmds_session = WordCompleter(
    [
        "info",
        "ls",
        "exec",
        "back",
        "upload",
        "ps",
        "tasking",
        "view",
        "help",
    ]
)

def format_sessions(sessions: list):
    if isinstance(sessions, list):
        table = PrettyTable()
        table.field_names = ["Session", "Alive", "Last Seen",
                             "First Seen", "CB Freq(m)", "User", "Hostname"]
        for session in sessions:
            session_id = session.get("session", "Null")
            status = session.get("alive", "Null")
            last_seen = session.get("last_checkin", "Null")
            if last_seen != "Null":
                last_seen_formatted = fix_date(last_seen)
            first_seen = session.get("first_checkin", "Null")
            if first_seen != "Null":
                first_seen_formatted = fix_date(first_seen)
            cb_freq = session.get("callback_freq", "Null")
            user = session.get("username", "Null")
            hostname = session.get("hostname", "Null")
            table.add_row([session_id, status, last_seen_formatted,
                           first_seen_formatted, cb_freq, user, hostname])
    print_formatted_text(table)


def get_sessions(token: str, server: str):
    url = f"http://{server}/implants/"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)

    if response.status_code != 200:
        print_formatted_text(response.status_code, response.text, response)

    if isinstance(response.json(), list):
        # proper json array
        format_sessions(response.json())
    else:
        print_formatted_text("[*] Invalid data format")
        return

    
def test_session(token: str, server: str, session: str):
    url = f"http://{server}/implants/{session}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)
    return response.status_code


def get_session(token: str, server: str, session: str):
    url = f"http://{server}/implants/{session}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        session = response.json()
        table = PrettyTable()
        table.field_names = ["Session", "Alive", "Last Seen",
                             "First Seen", "CB Freq(m)", "User", "Hostname"]

        session_id = session.get("session", "Null")
        status = session.get("alive", "Null")
        last_seen = session.get("last_checkin", "Null")
        if last_seen != "Null":
            last_seen_formatted = fix_date(last_seen)
        first_seen = session.get("first_checkin", "Null")
        if first_seen != "Null":
            first_seen_formatted = fix_date(first_seen)
        cb_freq = session.get("callback_freq", "Null")
        user = session.get("username", "Null")
        hostname = session.get("hostname", "Null")
        table.add_row([session_id, status, last_seen_formatted,
                       first_seen_formatted, cb_freq, user, hostname])
        print_formatted_text(table)
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    else: print_formatted_text(response.status_code, response.text, response)
    return response.status_code


def delete_implant(token: str, server: str, session: str):
    url = f"http://{server}/implants/delete/{session}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.delete(url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        session_id = json_data.get("session")
        if session_id == session:
            print_formatted_text(f"[*] Session id {session} deleted")
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    else: print_formatted_text(response.status_code, response.text, response)


def interact_implant(token: str, server: str, session_id: str):
    interact = PromptSession()
    while True:
        options = interact.prompt(message=message_session, 
                                  style=style_session, completer=cmds_session)
        options = options.lower().strip()
        try:
            parsed = shlex.split(options)
        except ValueError as e:
            print_formatted_text(f"[*] Input parsing error: {e}")
            continue

        if not parsed:
            continue

        cmd = parsed[0].lower()
        args = parsed[1:]

        if cmd == "back":
             return

        session_router(cmd, args, token, server, session_id)
        

def session_router(cmd: str, args: list, token: str, server: str, session_id: str):
    if cmd == "info":
            get_session(token, server, session_id)
    elif cmd == "ls":
        if len(args) == 1:
            send_task(token, server, session_id, "ls", args[0])
    elif cmd == "tasking":
        get_tasking(token, session_id, server)
    elif cmd == "ps":
        send_task(token, server, session_id, "ps", "")