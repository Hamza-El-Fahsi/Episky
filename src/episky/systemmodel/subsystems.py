"""Subsystem / State-Domain vocabulary.

Owner: RFC-0021 §4, §6, §11.
Responsibility: the subsystem and State-Domain vocabulary that
    Facts and Verification Scopes reference.
Forbidden responsibility: no behavior; vocabulary only.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType

__all__ = [
    "MachineSubsystem",
    "SUBSYSTEM_DEPENDENCIES",
    "SUBSYSTEM_STATE_REPRESENTATION",
    "StateDomain",
    "StateRepresentation",
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


class StateDomain(Enum):
    """A State Domain of the Machine Abstraction (RFC-0021 §6).

    The seven State Domains of §6.2–§6.8, transcribed exactly, in the
    RFC's order. A State Domain is a category of machine state that
    changes together and is reasoned about together (§6.1). State
    Domains are the *mutable* decomposition of machine state; the
    subsystem→domain mapping is the normative §6.10 table, encoded as
    SUBSYSTEM_STATE_REPRESENTATION. The §6.9 independence/influence
    summary is explanatory, not normative (§16 A6), and is not encoded.

    Members:
        PACKAGE: What is installed and at what version, what is
            updateable, what repositories are configured (§6.2).
        SERVICE: Which supervised services are running, enabled at
            boot, or failed (§6.3).
        CONFIGURATION: The machine's configuration: /etc and other
            config locations, plus what init and services read at
            startup (§6.4).
        FILESYSTEM: Mounted filesystems, their usage, and their
            integrity (§6.5).
        NETWORK: Interfaces, addresses, routes, DNS (§6.6).
        USER: Accounts, groups, membership, home directories (§6.7).
        SECURITY: Firewall, mandatory access control, secure boot, and
            security-relevant settings (§6.8).
    """

    PACKAGE = auto()
    SERVICE = auto()
    CONFIGURATION = auto()
    FILESYSTEM = auto()
    NETWORK = auto()
    USER = auto()
    SECURITY = auto()


@dataclass(frozen=True, slots=True)
class StateRepresentation:
    """Where a subsystem's state lives (RFC-0021 §6.10).

    The normative statement of a subsystem's state representation: a
    named State Domain, Facts only (no mutable State Domain), or a
    named domain *plus* Facts (§6.10). Data only — the value never
    assigns behavior to a subsystem or domain.

    Attributes:
        domains: The State Domains owning the subsystem's mutable
            state; empty for a Facts-only subsystem.
        facts_only: True when the subsystem's state is read-only and is
            represented by Facts only (no mutable State Domain).
    """

    domains: frozenset[StateDomain]
    facts_only: bool


SUBSYSTEM_STATE_REPRESENTATION: Mapping[MachineSubsystem, StateRepresentation] = (
    MappingProxyType(
        {
            MachineSubsystem.HARDWARE: StateRepresentation(
                domains=frozenset(), facts_only=True
            ),
            MachineSubsystem.BOOT: StateRepresentation(
                domains=frozenset({StateDomain.CONFIGURATION}), facts_only=False
            ),
            MachineSubsystem.KERNEL: StateRepresentation(
                domains=frozenset({StateDomain.CONFIGURATION}), facts_only=False
            ),
            MachineSubsystem.USERS: StateRepresentation(
                domains=frozenset({StateDomain.USER}), facts_only=False
            ),
            MachineSubsystem.SERVICES: StateRepresentation(
                domains=frozenset({StateDomain.SERVICE}), facts_only=False
            ),
            MachineSubsystem.STORAGE: StateRepresentation(
                domains=frozenset({StateDomain.FILESYSTEM}), facts_only=False
            ),
            MachineSubsystem.FILESYSTEMS: StateRepresentation(
                domains=frozenset({StateDomain.FILESYSTEM}), facts_only=False
            ),
            MachineSubsystem.PACKAGES: StateRepresentation(
                domains=frozenset({StateDomain.PACKAGE}), facts_only=False
            ),
            MachineSubsystem.NETWORKING: StateRepresentation(
                domains=frozenset({StateDomain.NETWORK}), facts_only=False
            ),
            MachineSubsystem.SECURITY: StateRepresentation(
                domains=frozenset({StateDomain.SECURITY}), facts_only=False
            ),
            MachineSubsystem.LOGS: StateRepresentation(
                domains=frozenset(), facts_only=True
            ),
            MachineSubsystem.APPLICATIONS: StateRepresentation(
                domains=frozenset({StateDomain.FILESYSTEM, StateDomain.USER}),
                facts_only=False,
            ),
        }
    )
)
