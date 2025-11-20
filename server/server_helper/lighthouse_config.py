

class WebServer:
    def __init__(
        self,
        debug,
        server_crt,
        server_key,
        listen_host,
        listen_port,
    ):
        self.debug = debug
        self.server_crt = server_crt
        self.server_key = server_key
        self.listen_host = listen_host
        self.listen_port = int(listen_port)  # ensure int


def parse_config(config_file_path: str) -> str:
    try:
        with open(config_file_path, "r") as fp:
            return fp.readlines()
    except Exception as e:
        print(f"Error reading config: {e}")


def parse_config_vals(conf: str) -> WebServer:
    for line in conf:
        if line.startswith("#") or len(line) == 0 or ":" not in line:
            continue
        line_clean = line.strip()
        key, val = [part.strip() for part in line_clean.split(":", 1)]
        match key:
            case "debug":
                debug = bool(val)
            case "server_crt":
                server_crt = val
            case "server_key":
                server_key = val
            case "listen_host":
                listen_host = val
            case "listen_port":
                listen_port = val
            case _:
                continue
    return WebServer(debug, server_crt, server_key, listen_host, listen_port)
    