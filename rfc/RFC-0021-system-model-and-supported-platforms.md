# RFC-0021 — System Model & Supported Platforms

**Status:** Draft
**Date:** 2026-08-01
**Scope:** The machine model the project targets: which Linux systems the Assistant understands, how it views them, and what it commits to supporting
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0000 (as amended), RFC-0001 (system boundaries and non-goals), RFC-0002 (the runtime that reasons about this model), RFC-0003 (vocabulary). RFC-0004 is referenced for the authority over the machine, but this RFC does not depend on it.

**Roadmap note:** This RFC is the renumbered subject of the former RFC-0004
reservation ("System Model & Supported Platforms"). The reassignment is recorded
in RFC-0000's amendment log (AM-2026-08-01-1).

**BREAKING:** No. This RFC adds normative content about the external machine
model. It does not weaken any Principle, Boundary, Invariant, or canonical
Definition in an accepted RFC. It answers RFC-0001 open questions Q7
(immutable systems) and Q25 (supported distro families).

---

## 0. Preamble

RFC-0001 fixed the boundaries of the project: the Assistant inspects and — with
authority, per RFC-0004 — changes *one Machine* the Operator owns. RFC-0002
fixed how the Assistant behaves in a Session. This RFC fixes the *external
reality* the Assistant is expected to understand: what a Linux machine is, which
machines the project commits to supporting, and how the Assistant views a
machine conceptually.

Three disciplines govern this document:

1. **It defines the world, not the code.** This RFC specifies the model of a
   machine — its subsystems, its state, its capabilities, its boundaries. It
   does **not** specify implementation, APIs, data structures, or internal
   architecture. Nothing in this RFC is a design for code.
2. **It is conservative.** The project's first stable release deliberately
   supports a small, coherent set of systems. Every support promise is a
   long-term maintenance burden; promises are made only where the project can
   keep them.
3. **It is the source for later RFCs.** The Fact Model (RFC-0005), Verification
   (RFC-0006), and the Skill Contract (RFC-0011) all reason *about* the thing
   this RFC defines. A subsystem listed here is a subject for Facts; a state
   domain listed here is a subject for Verification; a distribution family here
   is a target for Skills.

**Reading notes.**

- This RFC uses the canonical vocabulary of RFC-0003 Part I (Machine, Operator,
  Session, Inspection, Observation, Fact, etc.). New terms are defined at first
  use and flagged in §11 for inclusion in RFC-0003.
- "Supported" is a *promise*: it means the project commits to understanding a
  system correctly and to testing against it. "Planned," "Experimental," and
  "Unsupported" are narrower commitments, defined in §1.
- The four status words (Supported, Planned, Unsupported, Out of Scope) have
  exact meanings. They are defined in §2 and used everywhere after.

---

## 1. Supported Operating Systems for the First Stable Release

### 1.1 The commitment

For the first stable release, the Assistant supports **precisely**:

- **Distribution families:** Debian family, Red Hat family (defined in §2).
- **Init system:** systemd as PID 1 (required; §3).
- **Architectures:** x86-64 and aarch64.
- **Context:** a physical or virtual machine the Operator runs the Assistant on,
  locally (§9). This explicitly excludes WSL, containers, and the other
  environments in §8.

Everything else is Planned, Experimental, Unsupported, or Out of Scope — even
if it is "obviously Linux."

### 1.2 Why this is the MVP

1. **Two families prove the abstraction.** A tool that works on only one
   distribution has no reason to have a machine *model* at all — it could hard-
   code one distro's commands. Supporting two families (apt-based Debian family
   and dnf-based Red Hat family) is the smallest set that demonstrates that the
   Assistant understands *a class of machines*, not one distro. This is the
   difference between a model and a lookup table, and it is the core bet of this
   RFC.
2. **Both families are systemd-based.** By requiring systemd, the two families
   share one init contract, one service model, and one journal. This removes the
   single largest source of Linux fragmentation (init systems) from the MVP
   entirely. It is a requirement, not a preference (§3.1).
3. **Both families are mainstream and long-lived.** Debian-family (Debian,
   Ubuntu, and derivatives) and Red Hat family (Fedora, RHEL, and derivatives)
   cover the large majority of both desktop and server Linux systems that a
   beginner is likely to own. Supporting them makes the product real for most
   users; supporting the long tail does not.
4. **Architecture is bounded.** x86-64 and aarch64 cover commodity desktops,
   laptops, and single-board computers. They are the two architectures where a
   beginner is likely to run Linux, and they share enough conventions that one
   model can represent both.
5. **Conservative is a safety property.** Every "Supported" promise becomes an
   expectation that the Assistant's Facts are correct on that system. A wrong
   support matrix produces wrong Facts, and wrong Facts undermine the safety
   model (RFC-0004). It is safer to support two families correctly than ten
   families approximately. Later releases expand the matrix only as the
   project can test it (§11).

### 1.3 What "supported" means operationally

"Supported" for a family means the project commits to:

- the Family Profile (§2.3) being accurate for the family's current stable
  releases, including its package ecosystem, init contract, and configuration
  conventions;
- Facts produced about that family being correct within the bounds of
  RFC-0005;
- testing against at least one representative release of the family.

A family remains Supported as long as the project's test baseline includes it.
Any change to this section is a BREAKING change (RFC-0003 Part II §5) and must
go through the amendment process.

---

## 2. Distribution Families

### 2.1 The status words (normative)

| Status | Meaning |
|---|---|
| **Supported** | The family is in the MVP (§1). The project promises correct Facts, an accurate Family Profile, and a test baseline. |
| **Planned** | The family is on the roadmap with a named owner and a defined reason, but is not yet promised. Nothing downstream may rely on it. |
| **Unsupported** | The family is deliberately not supported in the current release line. It may become Planned later; until then it is treated as an unknown machine. |
| **Out of Scope** | The environment or family is outside the project's purpose (RFC-0001 non-goals). It will never be supported without a new Goal. |

### 2.2 The family table

| Family | Representative members | Status | Rationale |
|---|---|---|---|
| **Debian family** | Debian, Ubuntu, Linux Mint, Pop!_OS | **Supported** | Largest beginner desktop base; apt ecosystem; systemd standard on current releases. |
| **Red Hat family** | Fedora, RHEL, Rocky Linux, AlmaLinux, CentOS Stream | **Supported** | Second mainstream base; dnf ecosystem; systemd standard; strong server presence. |
| **Arch family** | Arch Linux, Manjaro, EndeavourOS | **Planned** | Rolling-release model and pacman need separate semantics; popular with tinkerers, but a distinct Package State model (§6.2) that the MVP does not need. |
| **openSUSE family** | openSUSE Leap, Tumbleweed | **Planned** | zypper and YaST conventions differ; systemd-standard but a distinct configuration culture. |
| **Immutable / atomic systems** | Fedora Silverblue, openSUSE MicroOS, NixOS | **Experimental** | The *concept* is modeled (§2.4) but no family is promised yet; image-based update and rollback semantics need a dedicated system model (RFC-0001 Q7). |
| **Other distros** | Alpine, Gentoo, Slackware, Void, others | **Unsupported** | No Family Profile, no test baseline, no Facts promised. Alpine's musl libc in particular is a different platform model. |
| **Non-Linux OSes** | BSDs, macOS, Windows, ChromeOS | **Out of Scope** | Not the project's purpose (RFC-0001 non-goal 5). |
| **Android** | Android, Android-based | **Out of Scope** | Not a user-facing Linux system in the project's sense (§8.6). |

### 2.3 The Family Profile (conceptual)

Each Supported or Planned family is described by a **Family Profile** — the
conceptual statement of *what kind of machine this is*. The profile covers:

- **Package ecosystem** (§5): which package manager and which containerized/app
  formats are native, secondary, experimental, or unsupported on the family.
- **Init contract** (§3.1): how services are defined and supervised (systemd
  units for the MVP; the profile states the requirement).
- **Configuration conventions** (§6.4): where configuration lives and how it is
  layered, at a family level (e.g., dpkg-managed files on Debian family).
- **Release model** (§6.2): point releases vs. rolling; how "state" is expected
  to evolve.
- **Verification conventions** (§7): which capabilities the family's tooling
  supports natively (e.g., whether rollback of packages is possible).

The Family Profile is *descriptive, not prescriptive*: it says what the family
is like so the Assistant can form correct expectations. The Fact Model
(RFC-0005) turns those expectations into inspectable Facts. The profile is not
a configuration file and not code.

### 2.4 Immutable / atomic systems

Immutable and atomic systems (image-based, transactional update, A/B roots)
are **Experimental** as a class. The project models them conceptually because
they are growing and because they change the meaning of several state domains:

- **Package State** (§6.2) is replaced or layered by *image state*: the machine
  is one of two (or more) root images, and "installing" is composing an image,
  not mutating files.
- **Configuration State** (§6.4) is often delegated to a separate mechanism
  (overlay, declarative config), so the configuration domain's assumptions
  differ.
- **Rollback** (§7) is often *native* to these systems — the A/B root makes
  reverting an image-level operation.

Because these change core assumptions of other domains, no immutable family is
Supported in the MVP. This RFC commits only to the *modeling* of the concept;
concrete support is deferred and must not be relied upon.

---

## 3. System Assumptions

Every assumption below is normative: the Assistant's model of a Machine is
defined against a machine that satisfies these assumptions. A machine that
violates an assumption is not a machine the MVP understands. Each assumption
states its justification.

### 3.1 systemd is PID 1 (required)

- **Assumption:** The machine boots with **systemd** as the init system and
  service manager. `systemctl` (or equivalent systemd tooling) is the interface
  to service state.
- **Justification:** This is the largest single de-fragmentation decision in the
  project. Service state (running, enabled, failed) is one of the most
  consequential state domains (§6.3), and every init system has a different
  model for it. Requiring systemd means one init contract across the entire
  Supported set. Both Supported families standardize on it in their current
  releases, so the requirement costs nothing within the MVP and removes an
  entire class of fragmentation risk (§12).
- **Boundary:** The *concept* of a service (RFC-0003) is init-agnostic. This
  assumption fixes the init for Supported machines only. A future non-systemd
  family (e.g., Alpine) would relax this assumption in its own Family Profile.

### 3.2 No init alternatives in the MVP

- **Assumption:** The MVP does not support SysV init, OpenRC, runit, s6, or
  busybox-init machines, even if they run an otherwise-Supported family.
- **Justification:** Supporting alternative inits would multiply the service
  domain's semantics with no beginner benefit. It is cheaper to *not support* a
  niche configuration than to maintain a second service model. Such machines
  are treated as unknown (§8).

### 3.3 sudo and a root-capable account exist

- **Assumption:** The machine has a `root` account (the standard Unix account)
  and `sudo` (or an equivalent privilege-escalation mechanism) is installed and
  usable by the Operator.
- **Justification:** Repairing a Linux machine — changing packages, services, or
  system configuration — requires privilege. The project's safety model
  (RFC-0004) keeps authority with the Operator, but that authority is
  meaningless if the machine has no escalation path to exercise it. The
  assumption is about the *machine's* capabilities, not about how the Assistant
  uses them (that is RFC-0008/RFC-0009 territory).
- **Boundary:** The Assistant does not assume a root login session, nor that
  passwordless sudo exists. It assumes only that privilege *can* be obtained by
  the Operator.

### 3.4 Native package manager present

- **Assumption:** The machine's native package manager (§5) for its family is
  installed: `apt`/`dpkg` on Debian family, `dnf`/`rpm` on Red Hat family.
- **Justification:** Package State (§6.2) is the domain the Assistant must most
  often reason about, and its native manager defines what "installed,"
  "updateable," and "removable" mean on that family. The package manager is the
  family's most stable identity marker.

### 3.5 Shell assumptions

- **Assumption:** A POSIX-compatible shell environment exists on the machine,
  and the machine follows the POSIX model of processes, files, and permissions.
  The Assistant does **not** assume a specific interactive shell (bash, zsh,
  fish) for the Operator.
- **Justification:** Every Linux system the project targets satisfies POSIX in
  practice; it is the common substrate that makes a machine *model* possible at
  all. The interactive shell of the Operator is a user preference, not a system
  property, so the model must not depend on it.

### 3.6 POSIX and filesystem layout

- **Assumption:** The machine follows the conventional Linux layout: a `root`
  filesystem, `/etc` for configuration, `/var` for mutable state, `/usr` for
  software, `/home` for users, `/proc` and `/sys` exposing kernel interfaces.
- **Justification:** The subsystem boundaries in §4 are defined against this
  layout. It is the near-universal convention of both Supported families.
  Unusual layouts are out of the MVP's model (a machine with a nonstandard
  layout is treated as an unknown until Facts establish otherwise).

### 3.7 Everything else is discovered, not assumed

- **Assumption:** Beyond the above, the Assistant assumes *nothing* about the
  machine that it can instead observe. It does not assume disk layout, network
  configuration, installed services, kernel version, or hardware from the family
  name — those are Facts to be collected (RFC-0005), not assumptions to be made.
- **Justification:** Assumptions are cheapest where they buy de-fragmentation
  (init, package manager, privilege) and dangerous where they hide reality (disk,
  network, services). This RFC fixes the former and forbids the latter: the
  boundary between assumed and observed is a **governing rule** of this RFC —
  it is a normative constraint on how the Assistant treats a machine, not a
  member of the runtime invariant set (RFC-0002 §9) or the authority invariants
  (RFC-0004 §8). Weakening it requires an amendment to this RFC.

---

## 4. The Machine Abstraction

### 4.1 What the abstraction is

The **Machine Abstraction** is the Assistant's conceptual view of a Linux
machine: a set of **Machine Subsystems**, each with a defined subject, defined
boundaries, and defined relationships to other subsystems. It is a *model*, not
a data structure and not a directory of commands.

The subsystems:

```
Machine
├── Hardware
├── Boot
├── Kernel
├── Users
├── Services
├── Storage
├── Filesystems
├── Packages
├── Networking
├── Security
├── Logs
└── Applications
```

Every subsystem is described below in the same shape: **Subject** (what it
represents), **Boundary** (what is inside/outside), **Owns** (what state and
capabilities belong to it), **Depends on** (which other subsystems it assumes).

Two rules apply to all subsystems:

1. **One subject per subsystem.** A subsystem is a *category of reality*, not a
   process or a file. "Services" is the subject of running programs managed by
   the init system, not a list of `systemctl` calls.
2. **Subsystems overlap only at defined joints.** Where two subsystems touch
   (e.g., Storage and Filesystems), the boundary is stated so that no fact about
   the machine is ambiguous about which subsystem owns it.

### 4.2 Hardware
- **Subject:** The physical or virtual compute resources the machine runs on:
  CPU, memory, and platform firmware (BIOS/UEFI).
- **Boundary:** The machine's own resources. External devices attached but not
  part of the platform (printers, phones) are outside.
- **Owns:** Hardware state (what the platform is), and the interface by which
  the OS starts. State representation: Facts only — no mutable State Domain
  (§6.10).
- **Depends on:** nothing — it is the bottom of the stack.

### 4.3 Boot
- **Subject:** The transition from power-on to a running OS: firmware discovery,
  bootloader, kernel handoff.
- **Boundary:** Ends when the init system (systemd) takes over as PID 1. The
  running kernel is Kernel's subject.
- **Owns:** Boot state — the question "does this machine boot, and to what?".
  State representation: Configuration State (boot configuration) plus Facts
  (boot outcome) (§6.10).
- **Depends on:** Hardware (it boots *something*).

### 4.4 Kernel
- **Subject:** The running Linux kernel: version, parameters, loaded modules.
- **Boundary:** The kernel *as running* is here; the files it boots from are
  Boot's; the drivers' userspace interfaces appear in /sys and /proc, which
  belong here.
- **Owns:** Kernel state — what is running and with what parameters. State
  representation: Configuration State (parameters set at boot) plus Facts
  (running kernel) (§6.10).
- **Depends on:** Hardware, Boot.

### 4.5 Users
- **Subject:** Accounts and groups on the machine: who can act on it.
- **Boundary:** Account *identity* and *membership* here; the security rules
  applied to them belong to Security; their running processes to Services.
- **Owns:** User state (§6.7).
- **Depends on:** Filesystems (home directories), Kernel (users are a kernel
  notion).

### 4.6 Services
- **Subject:** Programs supervised by the init system (systemd): system
  services, user services, and their lifecycle.
- **Boundary:** Init-managed programs here. Standalone programs the user starts
  themselves belong to Applications; a service's configuration belongs to
  Configuration State.
- **Owns:** Service state (§6.3).
- **Depends on:** Boot (the init must have started), Users (services run as
  accounts), Filesystems (binaries), Networking (many services are network
  daemons).

### 4.7 Storage
- **Subject:** Block devices and their partitioning: physical and virtual disks,
  partitions, and their identities.
- **Boundary:** Ends at the *block level*: raw devices and partitions. What a
  filesystem makes of them is Filesystems' subject.
- **Owns:** Storage state (devices, partitioning, free space at the block
  level). State representation: Filesystem State (block usage, free space) plus
  Facts (device and partition identity) (§6.10).
- **Depends on:** Hardware, Kernel (device drivers).

### 4.8 Filesystems
- **Subject:** Filesystems mounted on the storage: mount points, usage, and the
  files they expose.
- **Boundary:** The *filesystem layer* here (mounts, usage, inodes, files).
  Block layout is Storage's; specific file categories live in their owning
  subsystems (configuration files are Configuration State's, package files are
  Packages').
- **Owns:** Filesystem state (§6.5).
- **Depends on:** Storage, Kernel.

### 4.9 Packages
- **Subject:** Installed software managed by the package ecosystem: what is
  installed, its version, its origin (repository).
- **Boundary:** Package *registration* here — what the package manager knows.
  The files a package installed into /etc belong to Configuration State; the
  running programs belong to Services/Applications.
- **Owns:** Package state (§6.2).
- **Depends on:** Filesystems (the files are on disk), Networking (repositories
  are remote), Kernel (kernel packages).

### 4.10 Networking
- **Subject:** The machine's network configuration and connections: interfaces,
  addresses, routes, DNS.
- **Boundary:** The machine's *own* networking here. Remote peers and the wider
  network are outside the Machine (RFC-0001 non-goal 6).
- **Owns:** Network state (§6.6).
- **Depends on:** Hardware (NICs), Kernel (drivers), Services (network manager
  daemons).

### 4.11 Security
- **Subject:** The machine's security posture as state: firewall rules,
  mandatory access control policy (e.g., SELinux/AppArmor), secure boot, and
  security-relevant configuration.
- **Boundary:** Security *state* here; the project's own security principles
  (RFC-0001 §8) are a separate matter and are not part of this subsystem.
  Passwords and secrets are RFC-0009's subject, not this subsystem's.
- **Owns:** Security state (§6.8).
- **Depends on:** Kernel, Packages, Services, Users.

### 4.12 Logs
- **Subject:** The machine's record of its own behavior: system journal
  (journald), service logs, and other machine logs.
- **Boundary:** Machine-generated records here. The project's Audit (§13 of
  RFC-0002) is a *different* record owned by the project; it is not this
  subsystem.
- **Owns:** Log state (what the machine has recorded). State representation:
  Facts only — no mutable State Domain (§6.10).
- **Depends on:** Services (most log lines come from services), Boot, Kernel.

### 4.13 Applications
- **Subject:** Software beyond the package ecosystem: user-installed programs,
  flatpaks/snaps (where applicable), AppImages, and manually installed
  software.
- **Boundary:** What the package manager does *not* own here. A program that is
  an installed package is Packages' subject; the same program's running state is
  Services'.
- **Owns:** Application state (what else is on the machine). State
  representation: Filesystem State (app files), User State (per-user app data),
  plus Facts (presence and version) (§6.10).
- **Depends on:** Filesystems, Users, Packages (some apps wrap packages),
  Networking.

### 4.14 Subsystem dependency graph (summary)

```
Hardware → Boot → Kernel → { Services, Storage, Networking }
                            │         │
                            │         └─→ Filesystems → Packages
                            │              │              │
                            └──────────────┼──────────────┤
                                           ▼              ▼
                                    Users → Applications   Services
                                     │                     │
                                     └─────→ Security ←────┘
                                              │
                                              ▼
                                           Logs
```

This graph is normative: a subsystem may only assume the subsystems it points
to. It is the reason §6 can state which state domains influence which.

---

## 5. Package Ecosystems

### 5.1 The ecosystem statuses (normative)

| Status | Meaning |
|---|---|
| **Native** | The ecosystem is the family's primary, package-manager-native way to install software. The Assistant models its Package State natively. |
| **Secondary** | The ecosystem is present on Supported families and installs software, but is not the family's package manager; it is modeled as a distinct Application-layer concern. |
| **Experimental** | The ecosystem is recognized and modeled conceptually, but is not promised to work correctly in the MVP. |
| **Unsupported** | The ecosystem is not modeled and may be misidentified. |

### 5.2 The ecosystem table

| Ecosystem | Status | Rationale |
|---|---|---|
| **apt / dpkg** | **Native** (Debian family) | The identity of the Debian family. Its semantics define Package State there. |
| **dnf / rpm** | **Native** (Red Hat family) | The identity of the Red Hat family. Its semantics define Package State there. |
| **pacman** | **Experimental** | Arch is Planned; pacman's rolling-release and different transaction model are not needed for the MVP and are not promised. |
| **zypper** | **Experimental** | openSUSE is Planned; same logic as pacman. |
| **nix** | **Experimental** | Nix's content-addressed, declarative model is a different package paradigm; the MVP models the concept, not a family. |
| **flatpak** | **Secondary** | Present on both Supported families as an application layer; sandboxed, user-space, and largely independent of the native package state. Modeled as part of Applications. |
| **snap** | **Secondary** | Same rationale as flatpak; present on both Supported families (especially Ubuntu). |
| **appimage** | **Secondary** | A single-file, no-dependency format; modeled as Applications, not as managed state (nothing to track via a manager). |

### 5.3 Why this classification

1. **Native ecosystems are the family's state.** Package State must be
   *correct* — a wrong model of `apt` state can corrupt the whole diagnosis. The
   two native ecosystems are the two the MVP tests.
2. **Secondary ecosystems are containers, not packages.** Flatpak and snap
   install *applications* into their own sandboxes; they update independently of
   the system's package manager and rarely need system-level repair. Modeling
   them as Applications rather than Packages keeps Package State simple and
   correct, while still letting the Assistant see what the user experiences.
3. **Experimental ecosystems are deferrals, not rejections.** pacman, zypper,
   and nix are all legitimate and important; they are simply not the MVP's
   promise. Marking them Experimental rather than Unsupported signals that the
   project recognizes them and will not misidentify them as unknowns — but it
   makes no commitment.
4. **AppImage is a file, not a state domain.** There is no "appimage manager
   state" to model; an AppImage is a user-run executable. It belongs in
   Applications and needs no ecosystem machinery.

---

## 6. State Domains

### 6.1 The concept of a State Domain

A **State Domain** is a category of machine state that changes together and is
reasoned about together. The domains below are the decomposition of "the
Machine's current state" (RFC-0003 §2.2) that this project uses. Verification
(RFC-0006) compares before/after state *within* these domains; Facts (RFC-0005)
describe state *in* these domains.

Two properties are stated for each domain:

- **Independence:** whether the domain's state can change without the others.
- **Influence:** which other domains this domain's state tends to change.

The domains below are the *mutable* decomposition of machine state. Subsystems
whose state is read-only (Hardware, Logs) or decomposed across existing domains
(Boot, Kernel, Storage, Applications) are mapped to these domains — or to Facts
— in §6.10, which is the normative owner of that mapping.

### 6.2 Package State
- **What:** What is installed and at what version, according to the family's
  native ecosystem; what is updateable; what repositories are configured.
- **Independence:** High — packages can be installed/removed without touching
  service or configuration state.
- **Influences:** Configuration State (package installs drop config files),
  Services (installing a daemon package enables it), Applications (apps depend
  on packages), Filesystem State (packages occupy disk).

### 6.3 Service State
- **What:** Which supervised services are running, enabled at boot, or failed.
- **Independence:** Medium — a service can be toggled alone, but its *ability to
  run* depends on many other domains.
- **Influences:** Networking (network daemons), Logs (services write them),
  Applications (an app may be a service), Security (services are attack surface).

### 6.4 Configuration State
- **What:** The machine's configuration: /etc and other config locations, plus
  what the init system and services read at startup.
- **Independence:** High — configuration files can change alone.
- **Influences:** Services (config changes need reload/restart), Boot (boot
  config lives here), Networking, Security, Applications.

### 6.5 Filesystem State
- **What:** Mounted filesystems, their usage, and their integrity.
- **Independence:** Medium — mounts can change alone, but a full disk blocks
  almost everything.
- **Influences:** Packages, Applications, Services (they read from disk), Logs
  (full disk kills logging).

### 6.6 Network State
- **What:** Interfaces, addresses, routes, DNS.
- **Independence:** Medium — network config can change alone.
- **Influences:** Services (network-bound daemons), Packages (repositories are
  remote), Applications (online apps).

### 6.7 User State
- **What:** Accounts, groups, membership, home directories.
- **Independence:** Medium — users can be added alone, but their home dirs touch
  Filesystem State.
- **Influences:** Security (access rules reference users), Services (services
  run as users), Applications (per-user app data).

### 6.8 Security State
- **What:** Firewall, mandatory access control, secure boot, and
  security-relevant settings.
- **Independence:** Medium — firewall rules can change alone.
- **Influences:** Networking (firewall), Services (a service may be blocked),
  Boot (secure boot), Users (login policy).

### 6.9 Independence and influence (summary)

| Domain | Independent of others? | Influences |
|---|---|---|
| Package | High | Config, Services, Apps, Filesystem |
| Service | Medium | Network, Logs, Apps, Security |
| Configuration | High | Services, Boot, Network, Security, Apps |
| Filesystem | Medium | Packages, Apps, Services, Logs |
| Network | Medium | Services, Packages, Apps |
| User | Medium | Security, Services, Apps |
| Security | Medium | Network, Services, Boot, Users |

Influence targets that are subsystems (Boot, Logs, Apps) are shorthand for the
state representation those subsystems are mapped to in §6.10. The summary is
explanatory; §6.10 is the normative owner of that mapping.

The **order of change** the Assistant assumes when diagnosing: configuration
tends to be the *cause* (config → service → symptom), packages tend to be the
*remedy* (fix by changing package or config state), and filesystem/network are
the common *enabling* failures. This ordering is a model, not a rule: Facts and
Verification (RFC-0005, RFC-0006) are what actually establish cause.

### 6.10 Subsystem ↔ State Domain mapping (normative)

The Machine Subsystems (§4) are *subjects of reality*; the State Domains
(§6.2–§6.8) are *categories of mutable machine state*. They are different cuts
of the same machine and are therefore not one-to-one. This table is the
normative statement of where each subsystem's state lives. Every subsystem maps
to one of: a named State Domain; **Facts only** (no mutable State Domain — its
state is read-only and is represented by Facts, RFC-0005); or a named domain
*plus* Facts, where the domain owns the configurable state and Facts own the
observed state.

| Subsystem | State representation | Notes |
|---|---|---|
| **Hardware** | Facts only | Immutable in the model (§7.1 grants Inspect only, no Modify). State = platform identity. |
| **Boot** | Configuration State (§6.4) + Facts | Boot *configuration* (bootloader, boot entries, kernel command line) is Configuration State; the boot *outcome* ("does it boot, and to what") is a Fact established by Observation/Verification. |
| **Kernel** | Configuration State (§6.4) + Facts | Kernel parameters are set through boot configuration (Configuration State); the *running* kernel (version, modules, runtime parameters) is a Fact. |
| **Users** | User State (§6.7) | |
| **Services** | Service State (§6.3) | |
| **Storage** | Filesystem State (§6.5) + Facts | Device identity and partition layout are Facts; block-level usage and free space are Filesystem State (a full disk is a Filesystem-State failure). |
| **Filesystems** | Filesystem State (§6.5) | |
| **Packages** | Package State (§6.2) | |
| **Networking** | Network State (§6.6) | |
| **Security** | Security State (§6.8) | |
| **Logs** | Facts only | The machine's record is read-only (§7.1: Inspect only, no Modify). It is observed, never mutated. |
| **Applications** | Filesystem State (§6.5) + User State (§6.7) + Facts | Application presence and version are Facts; application files are Filesystem State; per-user application data is User State. |

Two normative rules complete the mapping:

1. **Every Fact about the machine belongs to exactly one subsystem** (§4) and is
   expressed in that subsystem's State representation above — either in its
   State Domain or as one of its own Facts.
2. **No individual fact or state item is owned by more than one
   representation.** Where a subsystem's state spans a domain *and* Facts (Boot,
   Kernel, Storage, Applications), the table fixes which items belong to the
   domain and which are Facts; a Fact that could be read as belonging to two
   rows is invalid until the ambiguity is resolved in the subsystem's favor.

---

## 7. System Capabilities

A **System Capability** is a conceptual statement of what can be done *with a
subsystem or domain*. These are capabilities of the *model*, not promises of
the implementation, and not authorities (RFC-0004 owns who may do what). Every
capability is scoped by the subsystem's boundary (§4) and its facts (RFC-0005).

| Capability | Meaning | Scope and limits |
|---|---|---|
| **Can inspect** | The Assistant can establish Facts about the subsystem: what state it is in, deterministically and read-only. | Inspection is always read-only (RFC-0002 invariant; RFC-0004 A4). |
| **Can modify** | The subsystem's state can be changed by a proposed Action, under the approval flow (RFC-0004). | The model distinguishes "this subsystem *can be* modified" from "the Assistant will modify it"; the latter is authority, not capability. |
| **Can verify** | The subsystem's state can be re-observed after a change to confirm the Post-condition (RFC-0006). | Verification compares Facts; it never assumes success (RFC-0004 A5). Some state (e.g., "user perception of an app") cannot be verified and must be labeled as such. |
| **Can rollback** | A prior state of the subsystem can be restored. | This is a *modeling* claim: e.g., image-based systems roll back natively; apt has no native rollback (only reverse-operations). Whether the project *promises* rollback is RFC-0006's decision. |
| **Can observe** | The subsystem's behavior over time can be watched (logs, journal, metrics). | Logs is the canonical observable; other subsystems are observable only through the Facts they expose. |
| **Can restart** | The subsystem can be stopped and started to apply changes or recover. | Primarily Services and Boot; restarting a service is a modification requiring the same flow as any other. |

### 7.1 Capability matrix (subsystems × capabilities)

| Subsystem | Inspect | Modify | Verify | Rollback | Observe | Restart |
|---|---|---|---|---|---|---|
| Hardware | yes | no¹ | limited | no | no | no |
| Boot | yes | yes | yes | no² | boot log | yes³ |
| Kernel | yes | limited⁴ | limited | no | /proc, /sys | no⁵ |
| Users | yes | yes | yes | limited⁶ | no | n/a |
| Services | yes | yes | yes | limited⁷ | yes (logs) | yes |
| Storage | yes | limited⁸ | yes | no | no | n/a |
| Filesystems | yes | yes | yes | limited⁹ | usage | n/a |
| Packages | yes | yes | yes | limited¹⁰ | no | n/a |
| Networking | yes | yes | yes | limited | yes (status) | yes¹¹ |
| Security | yes | yes | yes | limited | no | n/a |
| Logs | yes | no | n/a | no | yes | n/a |
| Applications | yes | yes | limited | limited | yes (per-app) | yes¹² |

Notes:
1. Hardware is modified physically; the model can only inspect.
2. Rollback of boot state is only via boot-config changes (a modification).
3. A reboot is a Boot-domain action.
4. Kernel parameters can be changed (boot config), but the running kernel is not
   hot-swapped in the model.
5. Restarting a kernel is a reboot.
6. Removing a user can be reversed only by recreating it.
7. Service config can revert; a service itself has no "undo."
8. Storage modification means re-partitioning — possible but high-impact.
9. Filesystem rollback is limited to snapshots where they exist.
10. Package rollback depends on the ecosystem (§5.3); native apt/dnf have no
    true rollback, only reverse transactions.
11. Network restart applies to network interfaces/manager.
12. An application can be stopped/started if it is a service or runnable
    program; standalone apps are not supervised.

This matrix is the *conceptual* statement of what the model believes is
possible. RFC-0005, RFC-0006, and RFC-0011 will refine per-subsystem what the
Assistant can actually do and promise.

---

## 8. Unsupported Environments

Each environment below is classified **Supported / Limited / Unsupported /
Future work**, with rationale. "Limited" means the Assistant may run but its
model is knowingly incomplete; "Unsupported" means the Assistant must not be
relied upon and should identify the environment as unknown rather than reason
with wrong assumptions.

| Environment | Status | Rationale |
|---|---|---|
| **WSL (Windows Subsystem for Linux)** | **Limited** | The Linux is real but its init, filesystem, and service model differ deliberately (WSLg, no systemd by default on WSL1, a different `/etc/wsl.conf` culture). The Assistant's model assumptions (§3) may not hold. Treat as unknown until Facts confirm the model. |
| **Containers (Docker, Podman, etc.)** | **Unsupported** | A container is not a Machine in this project's sense: no boot, no init as PID 1, no journal as a system. It is a process boundary, not a system model. Modeling it would corrupt the Machine abstraction. |
| **Live ISO / rescue media** | **Limited** | A live environment boots to RAM with no persistent state. It has no Package State worth reasoning about and no durable Configuration State. The Assistant's state domains assume persistence. Useful conceptually for "does the machine boot" but not as a target. |
| **Minimal rescue systems** | **Future work** | A rescue system (e.g., a minimal recovery environment) is a legitimate target for repair work, but it is a *different* machine model (no package manager, no service state). This is deferred; see §11. |
| **Embedded Linux** | **Unsupported** | Embedded targets (buildroot, Yocto) have custom init, no package manager, and often no root account. They violate nearly every §3 assumption. |
| **Android** | **Out of Scope** | Android is a Linux kernel with a non-Linux platform above it. It is not a user-facing Linux system in the project's sense (RFC-0001 non-goal 5). |

**Rule for unknown environments:** when the Assistant cannot confirm that the
machine satisfies the §3 assumptions, it must treat the machine as *unknown*
and collect Facts to establish what kind of machine it is — it must never
silently reason as if the machine were Supported (RFC-0001 §10, RFC-0004 §9.5).

---

## 9. Architectural Assumptions

The model assumes the following about *how* the Assistant operates. Each is
justified.

### 9.1 Single machine
- **Assumption:** The Assistant models exactly **one** Machine — the one the
  Operator runs it on.
- **Why:** RFC-0001 non-goal 6 (no fleet). Multi-machine reasoning would
  multiply every state domain and break the machine abstraction's coherence.
  One machine keeps every Fact unambiguous about its subject.

### 9.2 Local execution
- **Assumption:** The Assistant runs **on** the Machine it models, not against
  it from elsewhere.
- **Why:** Local execution makes Observation trustworthy: the Assistant sees the
  same reality the Operator sees, and its Facts come from the actual machine, not
  from a network hop. Remote execution would add a trust and identity problem
  (which machine am I talking to?) that the model deliberately does not have.

### 9.3 One active Operator
- **Assumption:** Exactly one human Operator holds authority over the Machine
  and the Session at any time (RFC-0004).
- **Why:** Two concurrent operators would make Approval ambiguous and Machine
  State race between them. The authority model (RFC-0004) is built on a single
  decision-maker; the system model inherits that.

### 9.4 One active Session
- **Assumption:** At most one active Session per Machine (RFC-0002).
- **Why:** Two sessions would each hold Context and claim state, and their
  observations could disagree about the same machine. The state domains (§6)
  assume a single observer-model maintaining a coherent view.

### 9.5 No remote management
- **Assumption:** The Assistant does not manage other machines, and is not
  managed by another instance.
- **Why:** Remote management would violate 9.1 and 9.2 simultaneously and
  reintroduce the fleet and trust problems the project excludes. Any network
  traffic is the *subject of repair* (Networking state), not a control channel.

---

## 10. Out of Scope

This section is exhaustive of what the machine model does **not** cover, so no
later document can assume otherwise.

1. **Non-Linux operating systems** — BSD, macOS, Windows, ChromeOS. Not the
   project's purpose (RFC-0001 non-goal 5).
2. **Android and Android-based systems** (§8.6).
3. **Fleet / multi-machine / remote management** (§9.1, §9.5).
4. **Containers as machines** — the Assistant models a Machine; a container is
   not one (§8.3).
5. **Non-systemd init systems** in the MVP (§3.1–3.2).
6. **Non-Supported architectures** — anything beyond x86-64 and aarch64 for the
   first release.
7. **Unusual or nonstandard filesystem layouts** as a first-class model
   (§3.6); they are handled by Facts, not by the abstraction.
8. **Package ecosystems beyond the §5 classification** — the table is
   exhaustive for the MVP.
9. **Embedded Linux, live ISO persistence, and rescue-system models** (§8).
10. **The project's own Audit and security state** — these are internal
    (RFC-0002 §13, RFC-0009) and are deliberately *not* subsystems of the
    Machine model (§4.11–4.12).

Anything not listed in §2, §5, or §8 as Supported is, by default, Unsupported
or Out of Scope until a Family Profile exists for it.

---

## 11. Future Expansion

New distributions and environments must be addable **without changing the Core
Architecture**. The mechanism, stated conceptually:

### 11.1 The seam: Family Profiles, not new architecture

The Machine Abstraction (§4), State Domains (§6), and Capabilities (§7) are
**family-agnostic by construction**: they describe *a machine*, not *a distro*.
Adding a new family consists of:

1. **Writing a Family Profile** (§2.3) for it — the conceptual statement of its
   package ecosystem, init contract, configuration conventions, release model,
   and verification conventions.
2. **Adding Facts for it** in RFC-0005's model — its package state, service
   state, etc., expressed in the canonical Fact Model.
3. **Promising it** — moving its status from Planned to Supported, with a test
   baseline, by the normal RFC process.

The Core (RFC-0001, RFC-0002, RFC-0004) does not change: the abstraction,
states, capabilities, and authority model are already expressed against a
generic machine. This is why the MVP supports two families (§1.2): it proves
the seam works without paying for every family.

### 11.2 Planned expansion order (conceptual)

1. **Arch family and openSUSE family** (Planned) — new Family Profiles, native
   ecosystems promoted from Experimental (pacman, zypper).
2. **Immutable families** (Experimental) — once the image-state model for
   Package and Rollback semantics is specified; this will extend §6.2 and §7,
   and is expected to be a normative amendment to this RFC, not a silent
   expansion.
3. **Minimal rescue systems** (Future work) — a deliberately reduced machine
   model (no package manager, no service state) for repair scenarios.
4. **More architectures** — following the same profile-and-promise pattern.

### 11.3 What never changes

- The Machine Abstraction's subsystems and boundaries (§4).
- The State Domains' definitions (§6).
- The Capability model's meaning (§7).
- The architectural assumptions (§9).

Expansion is *additive*: a new family adds a profile and facts; it never
rewrites the model of a machine. If a new environment genuinely requires a new
subsystem or a changed boundary, that is a BREAKING change to this RFC and must
follow RFC-0003 Part II.

---

## 12. Architectural Risks

### 12.1 Linux fragmentation
- **Risk:** The sheer variety of Linux systems defeats any unified model.
- **Mitigation:** The model is deliberately conservative (§1): it supports a
  small set and treats everything else as unknown (RFC-0004 §9.5, §8 rule).
  Fragmentation is acknowledged as the norm and is handled by *not* promising
  the long tail, not by trying to model it.

### 12.2 Init diversity
- **Risk:** Different init systems make Service State (§6.3) ambiguous.
- **Mitigation:** systemd is *required* for Supported families (§3.1). This is
  the single most effective de-fragmentation decision in the document, and it
  costs nothing inside the MVP. Non-systemd machines are Unsupported (§3.2).

### 12.3 Package ecosystem diversity
- **Risk:** apt, dnf, pacman, zypper, nix, and others each define "installed"
  differently.
- **Mitigation:** Only two native ecosystems are promised (§5); everything else
  is Experimental/Unsupported. The Capability matrix (§7.1) marks what can and
  cannot be done per ecosystem, so the model never assumes an ecosystem
  capability it does not have.

### 12.4 Immutable operating systems
- **Risk:** Image-based systems break the assumption that "installing a package"
  changes the running system.
- **Mitigation:** Immutable systems are Experimental as a class (§2.4), with
  their Package/Rollback model explicitly *different*. They are not silently
  forced into the mutable model. Their promotion is a normative amendment
  (§11.2), not an assumption.

### 12.5 Distro-specific behaviors
- **Risk:** Two members of the same family may behave differently (e.g., Ubuntu
  and Debian), producing wrong Facts.
- **Mitigation:** Facts are *observed*, not assumed (§3.7): the family name sets
  expectations; only collected Facts establish reality. RFC-0005's model will
  treat member-specific variation as Facts to verify, and §1.3's test baseline
  covers at least one representative per family.

### 12.6 Unsupported configurations
- **Risk:** A machine that violates the assumptions (custom init, unusual
  layout, container-in-WSL) is reasoned about with wrong assumptions.
- **Mitigation:** The §8 rule is normative: when assumptions cannot be
  confirmed, the machine is *unknown*, and the Assistant establishes what it is
  before reasoning about it. Wrong assumptions are treated as a failure of the
  model, never silently accepted.

### 12.7 Why the architecture is resilient to these risks

Every risk above is addressed by the same structural move: **the model is
separated from the machine.** The Assistant holds an abstraction (§4) and
expectations (Family Profiles, §2.3), but the only reality it trusts is Facts
collected by Inspection (RFC-0001 §3.5, RFC-0005). A surprising machine
surfaces as surprising Facts, which the runtime handles by treating the machine
as unknown — it does not collapse because a configuration was unexpected.
Fragmentation is therefore an *input condition* the model handles, not an
exception it fails on.

---

## 13. New Terms for RFC-0003 (flagged for inclusion in Part I)

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Distribution Family**, **Family Profile**, **Machine
Subsystem**, **State Domain**, **System Capability**, **Package Ecosystem**,
**Machine Abstraction**.

---

## 14. Open Questions

1. **Family internals.** Whether two members of a Supported family (e.g.,
   Debian vs. Ubuntu) each need their own Family Profile, or one profile per
   family, is owned by RFC-0005 (which defines how Facts encode member-specific
   differences).
2. **systemd-minimal variants.** Whether systemd-less variants of otherwise
   Supported families (e.g., a container base image) should be Limited rather
   than Unsupported is deferred to the Fact Model.
3. **Immutable model.** The exact modeling of image state and A/B rollback
   (§2.4) is an open design owned by this RFC's future amendment; it is recorded
   here so it is not lost.
4. **Rescue-system model.** Whether a reduced machine model for rescue
   environments is a new subsystem set or a restricted profile is Future work.
5. **"Applications" boundary.** Whether user-executed standalone programs
   belong in a model at all (vs. only supervised services) is to be settled by
   RFC-0005/Skills; the boundary here is provisional.

---

*End of RFC-0021. Normative: sections 1, 2, 3, 4, 5, 6, 7, 9, 10.
Explanatory and maintained alongside: sections 0, 8, 11, 12, 13, 14. Any
change to a Supported/Planned/Unsupported classification, a subsystem boundary,
an assumption in §3, a state domain, or a capability cell is a BREAKING change
and must be made by amendment (RFC-0003 Part II).*
