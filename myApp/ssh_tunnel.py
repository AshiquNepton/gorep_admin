import os
import logging
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder

load_dotenv()

logger = logging.getLogger('ssh_tunnel')

_tunnel = None

def start_tunnel():
    global _tunnel
    if _tunnel and _tunnel.is_active:
        return _tunnel

    ssh_host = os.getenv('SSH_HOST', 'localhost')
    ssh_port = int(os.getenv('SSH_PORT', 22))
    ssh_user = os.getenv('SSH_USER')
    ssh_password = os.getenv('SSH_PASSWORD') or None
    ssh_key_file = os.getenv('SSH_KEY_FILE') or None

    remote_pg_host = '127.0.0.1'  # Postgres as seen FROM the VPS itself
    remote_pg_port = int(os.getenv('PG_REMOTE_PORT', 5432))
    local_bind_port = int(os.getenv('PG_TUNNEL_LOCAL_PORT', 15432))

    ssh_pkey = ssh_key_file if ssh_key_file and os.path.exists(ssh_key_file) else None
    logger.info(f"[SSH Tunnel] user={ssh_user!r} password_set={bool(ssh_password)} key_file={ssh_key_file!r} pkey_used={bool(ssh_pkey)}")

    _tunnel = SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_password=None if ssh_pkey else ssh_password,
        ssh_pkey=ssh_pkey,
        remote_bind_address=(remote_pg_host, remote_pg_port),
        local_bind_address=('127.0.0.1', local_bind_port),
    )
    _tunnel.start()
    logger.info(f"[SSH Tunnel] Up: 127.0.0.1:{_tunnel.local_bind_port} -> {ssh_host} -> {remote_pg_host}:{remote_pg_port}")
    return _tunnel

def stop_tunnel():
    global _tunnel
    if _tunnel:
        _tunnel.stop()
        _tunnel = None