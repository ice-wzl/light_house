#!/user/bin/python3 
import httpx
import datetime
from prompt_toolkit import print_formatted_text
from prettytable import PrettyTable


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

def user_add(token: str, server: str, username: str, password: str):
    url = f"http://{server}/users/create"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    data = {
        'username': username,
        'password': password,
    }
    response = httpx.post(url, headers=headers, json=data)
    if response.status_code == 400:
        print_formatted_text("[*] Username already exists")
    elif response.status_code == 200:
        print_formatted_text("[*] User created successfully")
    else:    
        print_formatted_text(response.json(), response.status_code, response.text, response)


def user_delete(token:str, server: str, user_id: int):
    url = f"http://{server}/users/delete/{user_id}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.delete(url, headers=headers)
    if response.status_code == 404:
        print_formatted_text(f"[*] User id {user_id} not found!")
    elif response.status_code == 200:
            print_formatted_text(f"[*] User id {user_id} deleted") 
    else:
        print_formatted_text(response.status_code, response.text, response)


def get_users(token: str, server: str):
    url = f"http://{server}/users"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)
    if response.status_code != 200:
        print_formatted_text("[*] Error fetching users")
        print_formatted_text(response.status_code, response.text, response)
    else:
        if isinstance(response.json(), list):
            table = PrettyTable()
            table.field_names = ["ID", "Username", "Password", "Created At"]
            for user in response.json():
                id = user.get("id")
                username = user.get("username")
                password = user.get("password")
                created_at = user.get("created_at", "Null")
                if created_at != "Null":
                    created_at_formatted = fix_date(created_at)
                else:
                    created_at_formatted = "Null"
                table.add_row([id, username, password, created_at_formatted])
            print_formatted_text(table)
        else:
            print_formatted_text("[*] Invalid data format")
            print_formatted_text(response.json())
            return
        
def get_user(token: str, server:str, id: int):
    url = f"http://{server}/users/{id}"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        user = response.json()
        table = PrettyTable()
        table.field_names = ["ID", "Username", "Password", "Created At"]
        id = user.get("id")
        username = user.get("username", "Null")
        password = user.get("password", "Null")
        created_at = user.get("created_at", "Null")
        if created_at != "Null":
            created_at_formatted = fix_date(created_at)
        else:
            created_at_formatted = "Null"
        table.add_row([id, username, password, created_at_formatted])
        print_formatted_text(table)
    elif response.status_code == 404:
        print_formatted_text(f"[*] User id {id} not found!")
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
