import argparse
import datetime
import httpx
import logging
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text
from prettytable import PrettyTable


log_format = "%(asctime)s - %(message)s"
logging.basicConfig(format=log_format, stream=sys.stdout, level=logging.ERROR)
logger = logging.getLogger()

style_server = Style.from_dict(
    {
        # User input (default text).
        "": "#FFFAF0",
        # Prompt.
        "host": "#7CFC00",
        "arrow": "#FFFAF0",
    }
)
message_server = [
    ("class:host", "server"),
    ("class:arrow", "--> "),
]
completer_server = WordCompleter(
    [
        "sessions",
        "delete",
        "interact",
        "quit",
    ]
)

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
session_cmds = WordCompleter(
    [
        "ls",
        "exec",
        "back",
        "upload",
        "ps",
        "help",
    ]
)

def fix_date(raw_date: str):
    if isinstance(raw_date, str):
        try:
            # Convert the string to a datetime object
            format = datetime.datetime.fromisoformat(raw_date)
            # Format it as 'YYYY-MM-DD HH:MM:SS'
            fd = format.strftime("%Y-%m-%d %H:%M:%S")
            return fd
        except ValueError:
            fd = "Invalid Date"
            return fd

def format_sessions(sessions: list):
    if isinstance(sessions, list):
        table = PrettyTable()
        table.field_names = ["Session", "Alive", "Last Seen", "First Seen", "CB Freq(m)", "User", "Hostname"]
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
            table.add_row([session_id, status, last_seen_formatted,  first_seen_formatted, cb_freq, user, hostname])
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


def authenticate(username: str, password: str, server: str):
    url = f"http://{server}/token/"
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'password',
        'username': f'{username}',
        'password': f'{password}',
        'scope': '',
        'client_id': 'string',
        'client_secret': 'string'
    }
    
    response = httpx.post(url, headers=headers, data=data)

    if response.status_code == 200:
        response_data = response.json()
        token = response_data['access_token']
        return token
    elif response.status_code == 400:
        print_formatted_text("[*] Invalid credentials")
        sys.exit(1)
    else: print_formatted_text(response.status_code, response.text, response)


def driver(username: str, password: str, server: str):

    token = authenticate(username, password, server)

    session = PromptSession()
    print_formatted_text("[+] Enter commands to see available commands")
    print_formatted_text('[+] Enter help <cmd> to view help menu')

    while True:
        options = session.prompt(message=message_server, style=style_server, completer=completer_server)
        options = options.lower().strip()

        # get all active sessions
        if options == "sessions":
            get_sessions(token, server)
        elif options == "quit":
            print_formatted_text("[*] Goodbye...")
            sys.exit(2)
        elif options.startswith("delete"):
            # going to delete a session 
            # if alive is false just kill it immediately
            # if alive is true prompt user to be sure before removing from db...will really mess things up if we remove
            # alive implant that is phoning home 
            if " " in options:
                session_id = options.split(" ")[-1]
                delete_implant(token, server, session_id)
            else:
                print_formatted_text("[*] Expecting session id -> delete <session-id>")



if __name__ == '__main__':
    options = argparse.ArgumentParser(description="Client to connect to a server")
    options.add_argument("-u", "--username", default=str, required=True, help="The username to authenticate with", dest="username")
    options.add_argument("-p", "--password", default=str, required=True, help="The password to authenticate with", dest="password")
    options.add_argument("-s", "--server", default=str, required=True, help="The listening post address", dest="server")
    args = options.parse_args()

    driver(args.username, args.password, args.server)

    