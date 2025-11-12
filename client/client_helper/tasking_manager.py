#!/usr/bin/python3
import httpx
import base64
from prompt_toolkit import print_formatted_text
from prettytable import PrettyTable
from client_helper.user_manager import fix_date


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


def format_args(args: str) -> str:
    """
    Base64 encodes the arguments and converts them to a hex string.
    This is to ensure no special characters break the tasking.
    :param args: The arguments to be formatted
    :return: A hex string representation of the base64 encoded arguments
    """
    based = base64.b64encode(args.encode("utf-8"))
    return based.hex()

'''
send_task(
                token, server, session_id, "upload", src_path + "," + dst_path + ":" + binary_to_send
         )
'''
def send_task(token: str, server: str, session: str, tasking: str, args: str) -> None:
    """
    Sends a task to the lighthouse server for a specific session.
    :param token: The authentication token for the lighthouse server
    :param server: The lighthouse server address
    :param session: The session ID to which the task is sent
    :param tasking: The task to be sent
    :param args: The arguments for the task
    :return: None
    """
    # DEBUGGING
    print(f"ARGS: {args}")

    argsf = format_args(args)
    print(f"ARGSF: {argsf}")
    url = f"https://{server}/tasking/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {
        "task": f"{tasking}",
        "args": f"{argsf}",
    }
    response = httpx.post(url, headers=headers, json=data, verify=False)
    if response.status_code == 200:
        data = response.json()
        completed = data.get("complete")
        returned_session = data.get("session")
        if session == returned_session and completed == "False":
            print_formatted_text("[*] Tasking successfully sent")
            return
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session {session} not found")
        return
    elif (
        response.status_code == 401
        and response.json().get("detail") == "Bad Credentials"
    ):
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        return
    else:
        print_formatted_text(response.status_code, response.text, response)
        return


def reformat_upload(input: str) -> str:
    args_split = input.split(":")
    return format_output(args_split[0])


def create_tasking_table(json_data: list):
    table = PrettyTable()
    table.field_names = [
        "ID",
        "Session",
        "Date Sent",
        "Task",
        "Args",
        "Complete",
    ]
    for tasking in json_data:
        id = tasking.get("id")
        session_id = tasking.get("session")
        date_sent = tasking.get("date")
        if date_sent != "Null":
            date_sent_formatted = fix_date(date_sent)
        task = tasking.get("task")
        if task == "upload":
            args = reformat_upload(tasking.get("args"))
        else:
            args = tasking.get("args")
        complete = tasking.get("complete")
        table.add_row(
            [id, session_id, date_sent_formatted, task, args, complete]
        )
    return table


def get_tasking(token: str, session: str, server: str) -> None:
    """
    Retrieves tasking for a specific session from the lighthouse server.
    :param token: The authentication token for the lighthouse server
    :param session: The session ID for which to retrieve tasking
    :param server: The lighthouse server address
    :return: None
    """
    url = f"https://{server}/tasking/{session}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        json_data = response.json()
        if isinstance(json_data, list):
            print_formatted_text(create_tasking_table(json_data))
        else:
            print_formatted_text("[*] Unknown data returned")
            print_formatted_text(json_data)
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    elif (
        response.status_code == 401
        and response.json().get("detail") == "Bad Credentials"
    ):
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        return
    else:
        print_formatted_text(response.status_code, response.text, response)
