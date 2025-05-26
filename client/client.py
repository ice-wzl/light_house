import argparse
import logging
import shlex
import sys


from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text

# local imports
from client_helper.user_manager import user_add, user_delete, get_users, get_user, authenticate
from client_helper.session_manager import get_sessions, test_session, delete_implant, interact_implant
from client_helper.tasking_manager import get_tasking


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
        "delete",
        "interact",
        "quit",
    ]
)


def command_router(cmd: str, args: list, token: str, server: str):
    if cmd == "sessions":
        get_sessions(token, server)

    elif cmd == "quit":
        print_formatted_text("[*] Goodbye...")
        sys.exit(2)

    elif cmd == "users":
        get_users(token, server)

    elif cmd == "user_add":
        if len(args) == 2:
            user_add(token, server, args[0], args[1])
        else:
            print_formatted_text("[*] Expecting username and password -> user_add <username> <password>")

    elif cmd == "user_delete":
        if len(args) == 1:
            user_delete(token, server, args[0])
        else:
            print_formatted_text("[*] Expecting user id -> user_delete <user-id>")

    elif cmd == "user":
        if len(args) == 1:
            get_user(token, server, args[0])
        else:
            print_formatted_text("[*] Expecting user id -> user <user-id>")

    elif cmd == "delete":
        if len(args) == 1:
            delete_implant(token, server, args[0])
        else:
            print_formatted_text("[*] Expecting session id -> delete <session-id>")

    elif cmd == "interact":
        if len(args) == 1:
            session_id = args[0]
            if test_session(token, server, session_id) == 200:
                interact_implant(token, server, session_id)
            else:
                print_formatted_text("[*] Invalid session ID")
        else:
            print_formatted_text("[*] Expecting session id -> interact <session-id>")

    elif cmd == "tasking":
        if len(args) == 1:
            get_tasking(token, args[0], server)
        else:
            print_formatted_text("[*] Expecting session id -> tasking <session-id>")


def driver(username: str, password: str, server: str):
    token = authenticate(username, password, server)

    session = PromptSession()
    print_formatted_text("[+] Enter commands to see available commands")
    print_formatted_text('[+] Enter help <cmd> to view help menu')

    while True:
        options = session.prompt(message=message_server, 
                                 style=style_server, completer=completer_server)

        try:
            parsed = shlex.split(options)
        except ValueError as e:
            print_formatted_text(f"[*] Input parsing error: {e}")
            continue

        if not parsed:
            continue

        cmd = parsed[0].lower()
        args = parsed[1:]
        command_router(cmd, args, token, server)

        




if __name__ == '__main__':
    options = argparse.ArgumentParser(description="Client to connect to a server")
    options.add_argument("-u", "--username", default=str, required=True, help="The username to authenticate with", dest="username")
    options.add_argument("-p", "--password", default=str, required=True, help="The password to authenticate with", dest="password")
    options.add_argument("-s", "--server", default=str, required=True, help="The listening post address", dest="server")
    args = options.parse_args()

    driver(args.username, args.password, args.server)

    