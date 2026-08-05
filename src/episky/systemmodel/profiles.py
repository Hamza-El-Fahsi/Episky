"""Family Profile access and distribution-family vocabulary.

Owner: RFC-0021 §2.1, §2.2, §2.3, §5.
Responsibility: Family Profile (supported families, descriptive
    profile) and the distribution-family / status vocabulary.
Forbidden responsibility: unsupported families promise no Facts
    (RFC-0021 §2.1); no behavior, no I/O; profile data only.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto

__all__ = [
    "DistributionFamily",
    "ECOSYSTEM_STATUS",
    "EcosystemStatus",
    "FAMILY_PROFILES",
    "FAMILY_STATUS",
    "FamilyProfile",
    "FamilyStatus",
    "PackageEcosystem",
]


class FamilyStatus(Enum):
    """Status of a distribution family (RFC-0021 §2.1, §2.2; DN-8).

    Ratified DN-8: five status words. RFC-0021 §2.1's table lists four
    (Supported, Planned, Unsupported, Out of Scope); §2.2's Immutable /
    atomic row, §2.4, and §5.1 use Experimental as a status word, and
    that usage is canonical. The five members are structurally distinct:
    Supported and Planned are the only statuses that promise a Family
    Profile (blueprint §7); Unsupported and Out of Scope promise no
    Facts (RFC-0021 §2.1).

    Members:
        SUPPORTED: In the MVP (§1); correct Facts and an accurate
            Family Profile are promised, with a test baseline (§2.1).
        PLANNED: On the roadmap with a named reason; not yet promised;
            nothing downstream may rely on it (§2.1).
        EXPERIMENTAL: Modeled conceptually as a class, with no family
            promised yet (§2.4); never a support promise.
        UNSUPPORTED: Deliberately not supported in the current release
            line; treated as an unknown machine until Facts establish
            otherwise (§2.1, §8).
        OUT_OF_SCOPE: Outside the project's purpose; never supported
            without a new Goal (§2.1).
    """

    SUPPORTED = auto()
    PLANNED = auto()
    EXPERIMENTAL = auto()
    UNSUPPORTED = auto()
    OUT_OF_SCOPE = auto()


class DistributionFamily(Enum):
    """A distribution family of the Machine model (RFC-0021 §2.2).

    The eight family rows of the §2.2 table, transcribed exactly. A
    family is a class of machines — a distro lineage or a class of
    systems — not a single distribution. The two class-like rows,
    Immutable / atomic systems and Other distros, are first-class
    members of the same table (design review §16 A8, reported to
    RFC-0021).

    Members:
        DEBIAN: Debian, Ubuntu, Linux Mint, Pop!_OS — Supported.
        RED_HAT: Fedora, RHEL, Rocky Linux, AlmaLinux, CentOS Stream —
            Supported.
        ARCH: Arch Linux, Manjaro, EndeavourOS — Planned.
        OPENSUSE: openSUSE Leap, Tumbleweed — Planned.
        IMMUTABLE: Fedora Silverblue, openSUSE MicroOS, NixOS —
            Experimental; the concept is modeled (§2.4), no family is
            promised.
        OTHER_DISTROS: Alpine, Gentoo, Slackware, Void, others —
            Unsupported.
        NON_LINUX: BSDs, macOS, Windows, ChromeOS — Out of Scope.
        ANDROID: Android and Android-based — Out of Scope.
    """

    DEBIAN = auto()
    RED_HAT = auto()
    ARCH = auto()
    OPENSUSE = auto()
    IMMUTABLE = auto()
    OTHER_DISTROS = auto()
    NON_LINUX = auto()
    ANDROID = auto()


FAMILY_STATUS: dict[DistributionFamily, FamilyStatus] = {
    DistributionFamily.DEBIAN: FamilyStatus.SUPPORTED,
    DistributionFamily.RED_HAT: FamilyStatus.SUPPORTED,
    DistributionFamily.ARCH: FamilyStatus.PLANNED,
    DistributionFamily.OPENSUSE: FamilyStatus.PLANNED,
    DistributionFamily.IMMUTABLE: FamilyStatus.EXPERIMENTAL,
    DistributionFamily.OTHER_DISTROS: FamilyStatus.UNSUPPORTED,
    DistributionFamily.NON_LINUX: FamilyStatus.OUT_OF_SCOPE,
    DistributionFamily.ANDROID: FamilyStatus.OUT_OF_SCOPE,
}


class EcosystemStatus(Enum):
    """Status of a package ecosystem on a family (RFC-0021 §5.1).

    The four ecosystem statuses of §5.1. Native and Secondary are the
    statuses the MVP models concretely; Experimental ecosystems are
    recognized but not promised; Unsupported ecosystems are not modeled
    and may be misidentified. These are the *base* classifications of
    the §5.2 table; the per-family status map (which ecosystem is
    native/secondary/etc. on a given family) is part of the Family
    Profile (RFC-0021 §2.3, plan Commit 3).

    Members:
        NATIVE: The family's primary, package-manager-native way to
            install software; its Package State is modeled natively.
        SECONDARY: Present on Supported families and installs software,
            but is not the family's package manager; modeled as a
            distinct Application-layer concern.
        EXPERIMENTAL: Recognized and modeled conceptually, but not
            promised to work correctly in the MVP.
        UNSUPPORTED: Not modeled; may be misidentified.
    """

    NATIVE = auto()
    SECONDARY = auto()
    EXPERIMENTAL = auto()
    UNSUPPORTED = auto()


class PackageEcosystem(Enum):
    """A package ecosystem of the Machine model (RFC-0021 §5.2).

    The eight ecosystems of the §5.2 table, transcribed exactly. The
    table is exhaustive for the MVP (RFC-0021 §10 #8).

    Members:
        APT_DPKG: apt / dpkg — the identity of the Debian family.
        DNF_RPM: dnf / rpm — the identity of the Red Hat family.
        PACMAN: pacman — Arch is Planned; experimental.
        ZYPPER: zypper — openSUSE is Planned; experimental.
        NIX: nix — content-addressed, declarative model; experimental.
        FLATPAK: flatpak — an application-layer, sandboxed format.
        SNAP: snap — an application-layer, sandboxed format.
        APPIMAGE: appimage — a single-file, no-dependency format.
    """

    APT_DPKG = auto()
    DNF_RPM = auto()
    PACMAN = auto()
    ZYPPER = auto()
    NIX = auto()
    FLATPAK = auto()
    SNAP = auto()
    APPIMAGE = auto()


ECOSYSTEM_STATUS: dict[PackageEcosystem, EcosystemStatus] = {
    PackageEcosystem.APT_DPKG: EcosystemStatus.NATIVE,
    PackageEcosystem.DNF_RPM: EcosystemStatus.NATIVE,
    PackageEcosystem.PACMAN: EcosystemStatus.EXPERIMENTAL,
    PackageEcosystem.ZYPPER: EcosystemStatus.EXPERIMENTAL,
    PackageEcosystem.NIX: EcosystemStatus.EXPERIMENTAL,
    PackageEcosystem.FLATPAK: EcosystemStatus.SECONDARY,
    PackageEcosystem.SNAP: EcosystemStatus.SECONDARY,
    PackageEcosystem.APPIMAGE: EcosystemStatus.SECONDARY,
}


@dataclass(frozen=True, slots=True)
class FamilyProfile:
    """The descriptive profile of a distribution family (RFC-0021 §2.3).

    The conceptual statement of *what kind of machine this is*: the five
    descriptive dimensions of §2.3, exactly as ratified (DN-12). The
    profile is **descriptive, not prescriptive** — it states what the
    family is like so the Assistant forms correct expectations; it is
    never a configuration file and never code, and it carries no
    behavior, no policy, and no inference. Only Supported and Planned
    families have a profile; Unsupported, Experimental, and Out-of-Scope
    families have none and promise no Facts (blueprint §7; RFC-0021
    §2.1).

    Exact constructor and method signatures are RFC-0020's to define
    (DN-1); this type is the in-memory data shape only.

    Attributes:
        package_ecosystems: Which package manager and which containerized
            or app formats are native, secondary, experimental, or
            unsupported on the family (§2.3; §5). Statuses not stated
            for the family are Unsupported (RFC-0021 §10 default).
        init_contract: How services are defined and supervised; the
            profile states the init requirement (§2.3; §3.1).
        configuration_conventions: Where configuration lives and how it
            is layered, at a family level (§2.3; §6.4).
        release_model: Point releases vs. rolling; how "state" is
            expected to evolve (§2.3; §6.2).
        verification_conventions: Which capabilities the family's tooling
            supports natively, in §7 capability terms (§2.3; §7).
    """

    package_ecosystems: Mapping[PackageEcosystem, EcosystemStatus]
    init_contract: str
    configuration_conventions: str
    release_model: str
    verification_conventions: str


FAMILY_PROFILES: dict[DistributionFamily, FamilyProfile] = {
    DistributionFamily.DEBIAN: FamilyProfile(
        package_ecosystems={
            PackageEcosystem.APT_DPKG: EcosystemStatus.NATIVE,
            PackageEcosystem.FLATPAK: EcosystemStatus.SECONDARY,
            PackageEcosystem.SNAP: EcosystemStatus.SECONDARY,
            PackageEcosystem.APPIMAGE: EcosystemStatus.SECONDARY,
            PackageEcosystem.DNF_RPM: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.PACMAN: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.ZYPPER: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.NIX: EcosystemStatus.UNSUPPORTED,
        },
        init_contract="systemd",
        configuration_conventions="dpkg-managed files on Debian family",
        release_model="point release",
        verification_conventions="no native rollback (reverse transactions only)",
    ),
    DistributionFamily.RED_HAT: FamilyProfile(
        package_ecosystems={
            PackageEcosystem.DNF_RPM: EcosystemStatus.NATIVE,
            PackageEcosystem.FLATPAK: EcosystemStatus.SECONDARY,
            PackageEcosystem.SNAP: EcosystemStatus.SECONDARY,
            PackageEcosystem.APPIMAGE: EcosystemStatus.SECONDARY,
            PackageEcosystem.APT_DPKG: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.PACMAN: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.ZYPPER: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.NIX: EcosystemStatus.UNSUPPORTED,
        },
        init_contract="systemd",
        configuration_conventions="systemd standard; dnf ecosystem",
        release_model="point release",
        verification_conventions="no native rollback (reverse transactions only)",
    ),
    DistributionFamily.ARCH: FamilyProfile(
        package_ecosystems={
            PackageEcosystem.PACMAN: EcosystemStatus.EXPERIMENTAL,
            PackageEcosystem.APT_DPKG: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.DNF_RPM: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.ZYPPER: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.NIX: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.FLATPAK: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.SNAP: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.APPIMAGE: EcosystemStatus.UNSUPPORTED,
        },
        init_contract="systemd",
        configuration_conventions="rolling-release model; distinct Package State model",
        release_model="rolling",
        verification_conventions="not promised (Planned)",
    ),
    DistributionFamily.OPENSUSE: FamilyProfile(
        package_ecosystems={
            PackageEcosystem.ZYPPER: EcosystemStatus.EXPERIMENTAL,
            PackageEcosystem.APT_DPKG: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.DNF_RPM: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.PACMAN: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.NIX: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.FLATPAK: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.SNAP: EcosystemStatus.UNSUPPORTED,
            PackageEcosystem.APPIMAGE: EcosystemStatus.UNSUPPORTED,
        },
        init_contract="systemd",
        configuration_conventions="YaST conventions; distinct configuration culture",
        release_model="Leap: point release; Tumbleweed: rolling",
        verification_conventions="not promised (Planned)",
    ),
}
