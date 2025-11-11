import argparse
import logging
import shlex
import sys
import threading

from time import sleep
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text

# local imports
from client_helper.user_manager import (
    user_add,
    user_delete,
    get_users,
    get_user,
    authenticate,
)
from client_helper.session_manager import get_sessions, test_session, interact_implant
from client_helper.tasking_manager import get_tasking

# currently not using this logger, keeping for future use
log_format = "%(asctime)s - %(message)s"
logging.basicConfig(format=log_format, stream=sys.stdout, level=logging.ERROR)
logger = logging.getLogger()

style_server = Style.from_dict(
    {
        # User input (default text).
        "": "#FFFAF0",
        # Prompt.
        "host": "#00EBFC",
        "arrow": "#FFFAF0",
    }
)
message_server = [
    ("class:host", "!server"),
    ("class:arrow", " > "),
]
completer_server = WordCompleter(
    [
        "sessions",
        "users",
        "user",
        "user_add",
        "user_delete",
        "tasking",
        "interact",
        "quit",
    ]
)


def command_router(cmd: str, args: list, server: str) -> None:
    """
    Routes commands to their respective handlers based on the command name
    :param cmd: The command to execute
    :param args: The arguments for the command
    :param token: The authentication token
    :param server: The lighthouse server address
    :return: None
    """
    with open(".auth-token", "r") as fp:
        token = fp.read()

    match cmd:
        case "sessions":
            get_sessions(token, server)
        case "quit":
            print_formatted_text("[*] Goodbye...")
            sys.exit(2)
        case "users":
            get_users(token, server)
        case "user_add":
            handle_user_add(args, token, server)
        case "user_delete":
            handle_user_delete(args, token, server)
        case "user":
            handle_user(args, token, server)
        case "interact":
            handle_interact(args, token, server)                
        case "tasking":
            handle_tasking(args, token, server)


def handle_user_delete(args: list, token: str, server: str):
    if len(args) == 1:
        user_delete(token, server, args[0])
    else:
        print_formatted_text("[*] Expecting user id -> user_delete <user-id>")


def handle_user_add(args: list, token, server):
    if len(args) == 2:
        user_add(token, server, args[0], args[1])
    else:
        print_formatted_text(
            "[*] Expecting username and password -> user_add <username> <password>"
        )


def handle_user(args: list, token: str, server: str):
    if len(args) == 1:
        get_user(token, server, args[0])
    else:
        print_formatted_text("[*] Expecting user id -> user <user-id>")


# switch is likely better suited here
def handle_interact(args: list, token: str, server: str, session_id: str):
    if len(args) == 1:
        session_id = args[0]
        valid_agent = test_session(token, server, session_id)
        if valid_agent == 200:
            interact_implant(token, server, session_id)
        elif valid_agent == 404:
            print_formatted_text("[*] Invalid session ID")
        elif valid_agent == 410:
            print_formatted_text("[*] Implant is dead")
    else:
        print_formatted_text(
            "[*] Expecting session id -> interact <session-id>"
        )



def handle_tasking(args: list, token: str, server: str):
    if len(args) == 1:
        get_tasking(token, args[0], server)
    else:
        print_formatted_text("[*] Expecting session id -> tasking <session-id>")


def auth_timer(seconds: int, username: str, password: str, server: str):
    sleep(seconds - 120)
    token = authenticate(username, password, server)
    with open(".auth-token", "w") as fp:
        fp.write(token)
    return token


def driver(username: str, password: str, server: str):
    """
    Main driver to handle the user input and pass to the command router
    :param username: The username to authenticate to lighthouse with
    :param password: The password to authenticate to lighthouse with
    :param server: The lighthouse server address
    :return: None
    """
    token = authenticate(username, password, server)
    timer_thread = threading.Thread(target=auth_timer, args=(1800,username, password, server,), daemon=True)
    timer_thread.start()

    session = PromptSession()
    print_formatted_text("[+] Enter commands to see available commands")

    while True:
        options = session.prompt(
            message=message_server, style=style_server, completer=completer_server
        )

        try:
            parsed = shlex.split(options)
        except ValueError as e:
            print_formatted_text(f"[*] Input parsing error: {e}")
            continue

        if not parsed:
            continue

        cmd = parsed[0].lower()
        args = parsed[1:]
        command_router(cmd, args, server)


if __name__ == "__main__":
    options = argparse.ArgumentParser(description="Client to connect to a server")
    options.add_argument(
        "-u",
        "--username",
        default=str,
        required=True,
        help="The username to authenticate with",
        dest="username",
    )
    options.add_argument(
        "-p",
        "--password",
        default=str,
        required=True,
        help="The password to authenticate with",
        dest="password",
    )
    options.add_argument(
        "-s",
        "--server",
        default=str,
        required=True,
        help="The listening post address",
        dest="server",
    )
    args = options.parse_args()

    driver(args.username, args.password, args.server)
