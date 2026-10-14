from prompt_toolkit import print_formatted_text

def print_error(message: str):
    print_formatted_text(f"[-] {message}")

def print_success(message: str):
    print_formatted_text(f"[*] {message}")