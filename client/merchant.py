import argparse
import getpass
import logging
import shlex
import sys
from pathlib import Path

# Add project root to path for running from project root: python client/merchant.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit import print_formatted_text

# local imports
from client.client_helper.user_manager import (
    AuthenticationError,
    user_add,
    user_delete,
    get_users,
    get_user,
)
from client.client_helper.auth_manager import InMemoryAuthManager
from client.client_helper.session_manager import get_sessions, test_session, interact_implant
from client.client_helper.tasking_manager import get_tasking
from agent.build_agent import (
    ARCHS,
    DEFAULT_CERT_PATH,
    build_dir_setup,
    build_galleon,
)

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
        "agent_build",
        "quit",
    ]
)


def command_router(
    cmd: str,
    args: list,
    auth_manager: InMemoryAuthManager,
    server: str,
    certificate: str,
    insecure_build_provisioning: bool,
) -> None:
    """
    Routes commands to their respective handlers based on the command name
    :param cmd: The command to execute
    :param args: The arguments for the command
    :param token: The authentication token
    :param server: The lighthouse server address
    :return: None
    """
    token = auth_manager.get_token()

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
        case "agent_build":
            handle_agent_build(
                args,
                token,
                server,
                certificate,
                insecure_build_provisioning,
            )


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
def handle_interact(args: list, token: str, server: str):
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


def handle_agent_build(
    args: list,
    token: str,
    server: str,
    certificate: str,
    insecure_build_provisioning: bool,
):
    if not args or len(args) > 4 or args[0] not in ARCHS:
        print_formatted_text(
            "[*] Expecting agent_build <architecture> <callback host> <callback minutes> [debug]"
        )
        return

    if len(args) == 3 and not args[2].isdigit():
        print_formatted_text("[*] Third argument must be an integer for callback minutes")
        return

    debug = len(args) == 4 and args[3].lower() == "debug"
    if len(args) == 4 and not debug:
        print_formatted_text("[*] Optional fourth argument must be 'debug'")
        return

    try:
        build_dir_setup()
        build_galleon(
            args[0], # arch
            debug,   # bool 
            args[1], # callback host
            token,
            args[2], # callback minutes
            certificate,
            insecure_build_provisioning,
        )
    except Exception as exc:
        print_formatted_text(f"[-] Agent build failed: {exc}")


def driver(
    username: str,
    password: str,
    server: str,
    certificate: str,
    insecure_build_provisioning: bool,
):
    """
    Main driver to handle the user input and pass to the command router
    :param username: The username to authenticate to lighthouse with
    :param password: The password to authenticate to lighthouse with
    :param server: The lighthouse server address
    :return: None
    """
    auth_manager = InMemoryAuthManager(
        username,
        password,
        server,
        on_refresh_error=lambda exc: print_formatted_text(
            f"[-] Token refresh failed; retrying automatically: {exc}"
        ),
    )
    try:
        auth_manager.start()
    except (AuthenticationError, RuntimeError) as exc:
        auth_manager.stop()
        print_formatted_text(f"[-] {exc}")
        return

    session = PromptSession()
    print_formatted_text("[+] Enter <tab> to see available commands")

    try:
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
            try:
                command_router(
                    cmd,
                    args,
                    auth_manager,
                    server,
                    certificate,
                    insecure_build_provisioning,
                )
            except (AuthenticationError, RuntimeError) as exc:
                print_formatted_text(f"[-] Authentication failed: {exc}")
    except (EOFError, KeyboardInterrupt):
        print_formatted_text("\n[*] Goodbye...")
    finally:
        auth_manager.stop()


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
        default=None,
        required=False,
        help="The password to authenticate with; omitted values are prompted",
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
    options.add_argument(
        "--certificate",
        default=str(DEFAULT_CERT_PATH),
        help="Lighthouse certificate used when provisioning agent builds",
        dest="certificate",
    )
    options.add_argument(
        "--insecure-build-provisioning",
        action="store_true",
        help="disable TLS verification only for build-time provisioning",
        dest="insecure_build_provisioning",
    )
    args = options.parse_args()

    password = args.password or getpass.getpass("Lighthouse password: ")
    driver(
        args.username,
        password,
        args.server,
        args.certificate,
        args.insecure_build_provisioning,
    )
