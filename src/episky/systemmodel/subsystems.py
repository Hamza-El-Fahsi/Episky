"""Subsystem / State-Domain vocabulary.

Owner: RFC-0021 §4, §6, §11.
Responsibility: the subsystem and State-Domain vocabulary that
    Facts and Verification Scopes reference.
Forbidden responsibility: no behavior; vocabulary only.
"""

from enum import Enum, auto

__all__ = [
    "MachineSubsystem",
]


class MachineSubsystem(Enum):
    """A Machine Subsystem of the Machine Abstraction (RFC-0021 §4.1).

    The twelve subsystems of the §4.1 tree, transcribed exactly, in the
    tree's order. A subsystem is a subject for Facts and a category of
    reality, not a process or a file (RFC-0021 §4.1); each has a
    defined subject, boundary, and dependencies (§4.2–§4.13).

    Members:
        HARDWARE: The machine's compute resources: CPU, memory, and
            platform firmware (§4.2).
        BOOT: The transition from power-on to a running OS (§4.3).
        KERNEL: The running Linux kernel: version, parameters, loaded
            modules (§4.4).
        USERS: Accounts and groups on the machine (§4.5).
        SERVICES: Programs supervised by the init system (§4.6).
        STORAGE: Block devices and their partitioning (§4.7).
        FILESYSTEMS: Mounted filesystems: mount points, usage, files
            (§4.8).
        PACKAGES: Installed software managed by the package ecosystem
            (§4.9).
        NETWORKING: The machine's network configuration and connections
            (§4.10).
        SECURITY: The machine's security posture as state (§4.11).
        LOGS: The machine's record of its own behavior (§4.12).
        APPLICATIONS: Software beyond the package ecosystem (§4.13).
    """

    HARDWARE = auto()
    BOOT = auto()
    KERNEL = auto()
    USERS = auto()
    SERVICES = auto()
    STORAGE = auto()
    FILESYSTEMS = auto()
    PACKAGES = auto()
    NETWORKING = auto()
    SECURITY = auto()
    LOGS = auto()
    APPLICATIONS = auto()
