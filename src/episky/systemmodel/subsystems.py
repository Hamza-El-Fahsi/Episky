"""Subsystem / State-Domain vocabulary.

Owner: RFC-0021 §4, §6, §11.
Responsibility: the subsystem and State-Domain vocabulary that
    Facts and Verification Scopes reference.
Forbidden responsibility: no behavior; vocabulary only.
"""

from collections.abc import Mapping
from enum import Enum, auto
from types import MappingProxyType

__all__ = [
    "MachineSubsystem",
    "SUBSYSTEM_DEPENDENCIES",
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


SUBSYSTEM_DEPENDENCIES: Mapping[MachineSubsystem, frozenset[MachineSubsystem]] = (
    MappingProxyType(
        # The per-subsystem "Depends on" clauses of §4.2–§4.13, transcribed
        # exactly. Data only: no traversal, no resolution, no ordering.
        {
            MachineSubsystem.HARDWARE: frozenset(),
            MachineSubsystem.BOOT: frozenset({MachineSubsystem.HARDWARE}),
            MachineSubsystem.KERNEL: frozenset(
                {MachineSubsystem.HARDWARE, MachineSubsystem.BOOT}
            ),
            MachineSubsystem.USERS: frozenset(
                {MachineSubsystem.FILESYSTEMS, MachineSubsystem.KERNEL}
            ),
            MachineSubsystem.SERVICES: frozenset(
                {
                    MachineSubsystem.BOOT,
                    MachineSubsystem.USERS,
                    MachineSubsystem.FILESYSTEMS,
                    MachineSubsystem.NETWORKING,
                }
            ),
            MachineSubsystem.STORAGE: frozenset(
                {MachineSubsystem.HARDWARE, MachineSubsystem.KERNEL}
            ),
            MachineSubsystem.FILESYSTEMS: frozenset(
                {MachineSubsystem.STORAGE, MachineSubsystem.KERNEL}
            ),
            MachineSubsystem.PACKAGES: frozenset(
                {
                    MachineSubsystem.FILESYSTEMS,
                    MachineSubsystem.NETWORKING,
                    MachineSubsystem.KERNEL,
                }
            ),
            MachineSubsystem.NETWORKING: frozenset(
                {
                    MachineSubsystem.HARDWARE,
                    MachineSubsystem.KERNEL,
                    MachineSubsystem.SERVICES,
                }
            ),
            MachineSubsystem.SECURITY: frozenset(
                {
                    MachineSubsystem.KERNEL,
                    MachineSubsystem.PACKAGES,
                    MachineSubsystem.SERVICES,
                    MachineSubsystem.USERS,
                }
            ),
            MachineSubsystem.LOGS: frozenset(
                {
                    MachineSubsystem.SERVICES,
                    MachineSubsystem.BOOT,
                    MachineSubsystem.KERNEL,
                }
            ),
            MachineSubsystem.APPLICATIONS: frozenset(
                {
                    MachineSubsystem.FILESYSTEMS,
                    MachineSubsystem.USERS,
                    MachineSubsystem.PACKAGES,
                    MachineSubsystem.NETWORKING,
                }
            ),
        }
    )
)
