"""
MCPilot — systemd / journalctl abstraction layer.

Wraps systemctl and journalctl via the safe subprocess runner.
Validates service names to prevent injection attacks.
"""

import re

from server.core.command import run_safe
from server.schemas import ServiceStatus, ServiceLogs, ListeningPort


SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9@_.\-]+$")


def validate_service_name(name: str) -> str:
    """
    Reject anything containing ;, |, &, whitespace, $, backticks, or path
    separators — this defeats inputs like 'postgresql; rm -rf /'.
    """
    if not SERVICE_NAME_RE.fullmatch(name) or len(name) > 128:
        raise ValueError(f"Invalid service name: {name!r}")
    return name


def read_service_status(service: str) -> ServiceStatus:
    """Get the status of a systemd service."""
    name = validate_service_name(service)

    # Get active state
    result = run_safe(["systemctl", "is-active", name])
    active_state = result.stdout.strip() or "unknown"

    # Get sub-state
    result_sub = run_safe(["systemctl", "show", name, "--property=SubState", "--value"])
    sub_state = result_sub.stdout.strip() or "unknown"

    # Get enabled state
    result_enabled = run_safe(["systemctl", "is-enabled", name])
    enabled = result_enabled.stdout.strip() == "enabled"

    # Get since (ActiveEnterTimestamp)
    result_since = run_safe(["systemctl", "show", name, "--property=ActiveEnterTimestamp", "--value"])
    since = result_since.stdout.strip() or None

    return ServiceStatus(
        service=name,
        active_state=active_state,
        sub_state=sub_state,
        enabled=enabled,
        since=since,
    )


def read_service_logs(service: str, lines: int = 50) -> ServiceLogs:
    """Read recent journal logs for a systemd service."""
    name = validate_service_name(service)
    lines = min(lines, 200)  # Clamp to sane max

    result = run_safe(
        ["journalctl", "-u", name, "--no-pager", "-n", str(lines), "--output=short"],
        timeout=10,
    )

    log_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    return ServiceLogs(service=name, lines=log_lines)


def read_listening_ports() -> list[ListeningPort]:
    """Get list of listening ports using ss."""
    result = run_safe(["ss", "-tlnp"], timeout=5)
    ports = []

    for line in result.stdout.strip().split("\n")[1:]:  # skip header
        parts = line.split()
        if len(parts) < 5:
            continue

        try:
            # Parse address:port
            addr_port = parts[3]
            if "]:" in addr_port:  # IPv6
                addr, port_str = addr_port.rsplit(":", 1)
            elif addr_port.startswith("["):  # IPv6 without port split
                continue
            else:
                addr, port_str = addr_port.rsplit(":", 1)

            port = int(port_str)

            # Parse process info
            pid = None
            process_name = None
            if len(parts) >= 6:
                proc_info = parts[5] if len(parts) > 5 else ""
                # Extract pid from users:(("name",pid=1234,fd=5))
                import re
                pid_match = re.search(r"pid=(\d+)", proc_info)
                name_match = re.search(r'\("([^"]+)"', proc_info)
                if pid_match:
                    pid = int(pid_match.group(1))
                if name_match:
                    process_name = name_match.group(1)

            ports.append(ListeningPort(
                port=port,
                protocol="tcp",
                pid=pid,
                process_name=process_name,
                address=addr,
            ))
        except (ValueError, IndexError):
            continue

    # Also check UDP
    result_udp = run_safe(["ss", "-ulnp"], timeout=5)
    for line in result_udp.stdout.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            addr_port = parts[3]
            if "]:" in addr_port:
                addr, port_str = addr_port.rsplit(":", 1)
            else:
                addr, port_str = addr_port.rsplit(":", 1)
            port = int(port_str)

            pid = None
            process_name = None
            if len(parts) >= 6:
                proc_info = parts[5] if len(parts) > 5 else ""
                import re
                pid_match = re.search(r"pid=(\d+)", proc_info)
                name_match = re.search(r'\("([^"]+)"', proc_info)
                if pid_match:
                    pid = int(pid_match.group(1))
                if name_match:
                    process_name = name_match.group(1)

            ports.append(ListeningPort(
                port=port,
                protocol="udp",
                pid=pid,
                process_name=process_name,
                address=addr,
            ))
        except (ValueError, IndexError):
            continue

    return ports


def restart_service(service: str) -> ServiceStatus:
    """
    Restart a systemd service. This is the ONLY mutating tool in the project.
    The caller (execute_tools node) must have already obtained human approval.
    """
    name = validate_service_name(service)
    result = run_safe(["sudo", "systemctl", "restart", name], timeout=30)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to restart {name}: {result.stderr.strip()}")

    return read_service_status(name)
