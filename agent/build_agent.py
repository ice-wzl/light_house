#!/usr/bin/python3
import argparse
import getpass
import hashlib
import os
import secrets
import ssl
import subprocess
from pathlib import Path

import httpx


ARCHS = [
    "386",
    "arm",
    "mips",
    "mipsle",
    "arm64",
    "amd64",
    "loong64",
    "mips64",
    "mips64le",
    "ppc64",
    "ppc64le",
    "riscv64",
    "s390x",
]

# Compatibility for callers that imported the original lowercase name.
archs = ARCHS

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
BUILD_DIR = AGENT_DIR / "build"
DEFAULT_CERT_PATH = PROJECT_DIR / "certs" / "server.crt"


def build_dir_setup() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def generate_secret() -> tuple[str, str, str]:
    agent_id = secrets.token_hex(16)
    agent_secret = secrets.token_hex(32)
    secret_hash = hashlib.sha256(agent_secret.encode("ascii")).hexdigest()
    return agent_id, agent_secret, secret_hash


def certificate_fingerprint(certificate_path: Path) -> str:
    pem = certificate_path.read_text(encoding="ascii")
    der = ssl.PEM_cert_to_DER_cert(pem)
    return hashlib.sha256(der).hexdigest()


def provision_agent(
    server_url: str,
    token: str,
    agent_id: str,
    credential_hash: str,
    certificate_path: Path,
    insecure: bool = False,
) -> None:
    response = httpx.post(
        f"{server_url.rstrip('/')}/provision/",
        headers={"Authorization": f"Bearer {token}"},
        json={"id": agent_id, "credential_hash": credential_hash},
        verify=False if insecure else str(certificate_path),
        timeout=10,
    )
    if response.status_code != 201:
        raise RuntimeError(
            f"provisioning failed with HTTP {response.status_code}: {response.text}"
        )


def authenticate_operator(
    server_url: str,
    username: str,
    password: str,
    certificate_path: Path,
    insecure: bool = False,
) -> str:
    response = httpx.post(
        f"{server_url.rstrip('/')}/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "",
            "client_id": "string",
            "client_secret": "string",
        },
        verify=False if insecure else str(certificate_path),
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"authentication failed with HTTP {response.status_code}: {response.text}"
        )
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Lighthouse returned no access token")
    return token


def revoke_agent(
    server_url: str,
    token: str,
    agent_id: str,
    certificate_path: Path,
    insecure: bool = False,
) -> None:
    try:
        httpx.delete(
            f"{server_url.rstrip('/')}/provision/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
            verify=False if insecure else str(certificate_path),
            timeout=10,
        )
    except httpx.HTTPError:
        # Preserve the original build failure. The unused credential can still
        # be revoked later by its printed agent ID.
        pass


def upx_compress(outfile: Path) -> bool:
    try:
        proc = subprocess.run(
            ["upx", "-9", str(outfile)],
            cwd=AGENT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("[-] UPX not found; leaving the uncompressed agent in place")
        return False

    if proc.returncode != 0:
        print(f"[-] UPX failed: {proc.stderr.strip()}")
        return False
    return True


def build_galleon(
    arch: str,
    debug: bool,
    server_url: str,
    token: str,
    certificate_path: str | Path = DEFAULT_CERT_PATH,
    insecure_provisioning: bool = False,
) -> bool:
    if arch not in ARCHS:
        raise ValueError(f"unsupported architecture: {arch}")
    if not server_url or not server_url.startswith("https://"):
        raise ValueError("callback URL must begin with https://")
    if not token:
        raise ValueError("an operator token is required to provision the agent")

    build_dir_setup()

    certificate_path = Path(certificate_path).resolve()
    if not certificate_path.is_file():
        raise FileNotFoundError(f"server certificate not found: {certificate_path}")

    agent_id, agent_secret, credential_hash = generate_secret()
    fingerprint = certificate_fingerprint(certificate_path)
    server_url = server_url.rstrip("/")
    outfile = BUILD_DIR / f"galleon_{arch}_{agent_id[:8]}.elf"

    provision_agent(
        server_url,
        token,
        agent_id,
        credential_hash,
        certificate_path,
        insecure_provisioning,
    )

    env = os.environ.copy()
    env["GOOS"] = "linux"
    env["GOARCH"] = arch
    env["CGO_ENABLED"] = "0"

    ldflags = " ".join(
        [
            "-s",
            "-w",
            f"-X=galleon/agent_config.AgentId={agent_id}",
            f"-X=galleon/agent_config.AgentSecret={agent_secret}",
            f"-X=galleon/agent_config.ServerUrl={server_url}",
            f"-X=galleon/agent_config.ServerCertSHA256={fingerprint}",
        ]
    )

    cmd = ["go", "build"]
    if debug:
        cmd.extend(["-tags", "debug"])
    cmd.extend(
        [
            "-ldflags",
            ldflags,
            "-buildvcs=false",
            "-o",
            str(outfile),
            ".",
        ]
    )

    try:
        proc = subprocess.run(
            cmd,
            cwd=AGENT_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        revoke_agent(
            server_url,
            token,
            agent_id,
            certificate_path,
            insecure_provisioning,
        )
        print("[-] Go compiler not found; provisioned credential was revoked")
        return False

    if proc.returncode != 0:
        revoke_agent(
            server_url,
            token,
            agent_id,
            certificate_path,
            insecure_provisioning,
        )
        print(f"[-] Galleon build failed: {proc.stderr.strip()}")
        print(f"[*] Provisioned credential {agent_id} was revoked")
        return False

    upx_compress(outfile)
    print(f"[+] Galleon build successful: {outfile}")
    print(f"[+] Provisioned agent ID: {agent_id}")
    return True


def load_operator_token(
    server_url: str,
    username: str | None,
    certificate_path: Path,
    insecure: bool,
) -> str:
    environment_token = os.environ.get("LIGHTHOUSE_TOKEN", "").strip()
    if environment_token:
        return environment_token
    if not username:
        raise RuntimeError(
            "set LIGHTHOUSE_TOKEN or supply --username for an interactive login"
        )
    password = getpass.getpass("Lighthouse password: ")
    return authenticate_operator(
        server_url,
        username,
        password,
        certificate_path,
        insecure,
    )


if __name__ == "__main__":
    opts = argparse.ArgumentParser(
        prog="build_agent.py",
        description="Provision and build the Galleon agent",
    )
    opts.add_argument("-a", "--arch", choices=ARCHS, required=True)
    opts.add_argument(
        "-c",
        "--callback",
        required=True,
        help="HTTPS Lighthouse URL, for example https://localhost:8000",
    )
    opts.add_argument("-d", "--debug", action="store_true")
    opts.add_argument(
        "--certificate",
        type=Path,
        default=DEFAULT_CERT_PATH,
        help="Lighthouse certificate to verify and pin",
    )
    opts.add_argument(
        "-u",
        "--username",
        help="operator username; password is prompted and LIGHTHOUSE_TOKEN takes precedence",
    )
    opts.add_argument(
        "--insecure-provisioning",
        action="store_true",
        help="disable TLS verification only for the build-time provisioning request",
    )
    args = opts.parse_args()

    try:
        operator_token = load_operator_token(
            args.callback,
            args.username,
            args.certificate.resolve(),
            args.insecure_provisioning,
        )
        build_dir_setup()
        success = build_galleon(
            args.arch,
            args.debug,
            args.callback,
            operator_token,
            args.certificate,
            args.insecure_provisioning,
        )
    except (OSError, RuntimeError, ValueError, httpx.HTTPError) as exc:
        print(f"[-] {exc}")
        raise SystemExit(1)

    raise SystemExit(0 if success else 1)
