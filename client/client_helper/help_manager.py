from prompt_toolkit import print_formatted_text


def print_info_help():
    print_formatted_text("------------------------------------------")
    print_formatted_text("|              INFO HELP                 |")
    print_formatted_text("------------------------------------------")
    print(colored("info", attrs=["bold"]) + " - See basic imlant information")
    print(colored("help info", attrs=["bold"]) + " - See this help menu")
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
    print_formatted_text(
        "reconfig - Change implant callback interval, jitter, max errors"
    )
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
