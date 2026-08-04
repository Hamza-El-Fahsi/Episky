"""Family Profile access and distribution-family vocabulary.

Owner: RFC-0021 §2.1, §2.2, §2.3, §5.
Responsibility: Family Profile (supported families, descriptive
    profile) and the distribution-family / status vocabulary.
Forbidden responsibility: unsupported families promise no Facts
    (RFC-0021 §2.1); no behavior, no I/O; profile data only.
"""

from enum import Enum, auto

__all__ = [
    "DistributionFamily",
    "FAMILY_STATUS",
    "FamilyStatus",
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
