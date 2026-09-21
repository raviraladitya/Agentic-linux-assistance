"""
MCPilot — Service MCP tools.

Thin wrappers over server/core/systemd.py — no OS logic inline.
"""

from server.schemas import ServiceStatus, ServiceLogs, ListeningPort, ToolError
from server.core import systemd


def get_service_status(service: str) -> ServiceStatus | ToolError:
    """
    Returns the systemd status of a service: active state, sub-state,
    whether enabled, and activation timestamp.

    Use this when investigating whether a specific service is running,
    failed, or misconfigured. Does not modify system state.
    """
    try:
        return systemd.read_service_status(service)
    except ValueError as e:
        return ToolError(error_type="INVALID_SERVICE_NAME", message=str(e))
    except RuntimeError as e:
        return ToolError(error_type="SERVICE_NOT_FOUND", message=str(e))


def get_service_logs(service: str, lines: int = 50) -> ServiceLogs | ToolError:
    """
    Returns the most recent journal log lines for a systemd service.

    Use this when investigating why a service failed, crashed, or is
    misbehaving. Does not modify system state.
    """
    try:
        return systemd.read_service_logs(service, lines=lines)
    except ValueError as e:
        return ToolError(error_type="INVALID_SERVICE_NAME", message=str(e))


def get_listening_ports() -> list[ListeningPort]:
    """
    Returns all currently listening TCP and UDP ports with their associated
    process information (PID, process name, bind address).

    Use this when investigating port conflicts, checking if a service is
    listening, or diagnosing network issues. Does not modify system state.
    """
    return systemd.read_listening_ports()


def restart_service(service: str) -> ServiceStatus | ToolError:
    """
    Restarts a systemd service. This is a STATE-CHANGING operation that
    REQUIRES human approval before execution.

    Use this only when a service needs to be restarted as a remediation step
    and the user has been informed. This is the only mutating tool in MCPilot.
    """
    try:
        return systemd.restart_service(service)
    except ValueError as e:
        return ToolError(error_type="INVALID_SERVICE_NAME", message=str(e))
    except RuntimeError as e:
        return ToolError(error_type="RESTART_FAILED", message=str(e))
