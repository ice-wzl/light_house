#!/usr/bin/python3
import httpx
import base64
from prompt_toolkit import print_formatted_text
from prettytable import PrettyTable
from client_helper.user_manager import fix_date


def format_args(args: str):
    based = base64.b64encode(args.encode('utf-8'))
    return based.hex()


def send_task(token: str, server: str, session: str, tasking: str, args: str):
    argsf = format_args(args)
    url = f"http://{server}/tasking/{session}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    data = {
        'task': f'{tasking}',
        'args': f'{argsf}',
    }
    response = httpx.post(url, headers=headers, json=data)
    if response.status_code == 200:
        data = response.json()
        completed = data.get("complete")
        returned_session = data.get("session")
        if session == returned_session and completed == "False":
            print_formatted_text("[*] Tasking successfully recieved")
            return
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session {session} not found")
        return
    elif response.status_code == 401 and response.json().get("detail") == "Bad Credentials":
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        return
    else:
        print_formatted_text(response.status_code, response.text, response)
        return


def get_tasking(token: str, session: str, server: str):
    url = f"http://{server}/tasking/{session}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        if isinstance(json_data, list):
            table = PrettyTable()
            table.field_names = ["ID", "Session", "Date Sent",
                                 "Task", "Args", "Complete"]
            for tasking in json_data:
                id = tasking.get("id")
                session_id = tasking.get("session")
                date_sent = tasking.get("date")
                if date_sent != "Null":
                    date_sent_formatted = fix_date(date_sent)
                task = tasking.get("task")
                args = tasking.get("args")
                complete = tasking.get("complete")
                table.add_row([id, session_id, date_sent_formatted, task, args, complete])
            print_formatted_text(table)
        else:
            print_formatted_text("[*] Unknown data returned")
            print_formatted_text(json_data)
    elif response.status_code == 404:
        print_formatted_text(f"[*] Session id {session} not found!")
    elif response.status_code == 401 and response.json().get("detail") == "Bad Credentials":
        print_formatted_text("[*] Invalid token...time to reauthenticate")
        return
    else: print_formatted_text(response.status_code, response.text, response)
