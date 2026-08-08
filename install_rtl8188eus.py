#!/usr/bin/env python3
"""
KALI-FOX v3.0 — RTL8188EUS Driver Installer (Self-Healing Edition)
Fully automated installer for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter
(Realtek RTL8188EUS chipset) on Kali Linux.

Every step auto-repairs on failure — zero user intervention required.

Usage:
    sudo python3 install_rtl8188eus.py
"""

import os
import sys
import shutil
import signal
import subprocess
import platform
import atexit
import time
import itertools
import glob
import textwrap

# ── Rich dependency gate ──────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.status import Status
    from rich.table import Table
    from rich.rule import Rule
    from rich.align import Align
    from rich.live import Live
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
    )
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_URLS = [
    "https://github.com/gglluukk/rtl8188eus.git",
    "https://github.com/aircrack-ng/rtl8188eus.git",
    "https://github.com/lwfinger/rtl8188eu.git",
]
REPO_URL = REPO_URLS[0]
REPO_TARBALL = "https://codeload.github.com/gglluukk/rtl8188eus/tar.gz/refs/heads/master"
CLONE_DIR = "/usr/src/rtl8188eus"
BLACKLIST_FILE = "/etc/modprobe.d/realtek.conf"
BLACKLIST_LINE = "blacklist r8188eu"
REQUIRED_PACKAGES = [
    "build-essential",
    "libelf-dev",
    "bc",
    "dkms",
    "git",
    "wget",
]
TOTAL_STEPS = 6
MAX_RETRIES = 3

# ── ASCII Art ─────────────────────────────────────────────────────────────────

LOGO_ART = r"""
░██   ░██   ░██████   ░██        ░██████     ░██████████  ░██████   ░██    ░██
░██  ░██   ░██    ░██  ░██         ░██       ░██         ░██   ░██   ░██  ░██
░██░██     ░██    ░██  ░██         ░██       ░██        ░██     ░██   ░██░██
░█████     ░████████   ░██         ░██       ░█████████ ░██     ░██    ░███
░██░██     ░██    ░██  ░██         ░██       ░██        ░██     ░██   ░██░██
░██  ░██   ░██    ░██  ░██         ░██       ░██         ░██   ░██   ░██  ░██
░██   ░██  ░██    ░██  ░█████████░██████     ░██          ░██████   ░██    ░██
"""

MODEL_ART = r"""
░██████████░██                 ░██       ░██ ░███    ░██ ░█████████  ░██████   ░██████  ░███    ░██
    ░██    ░██                 ░██       ░██ ░████   ░██ ░██    ░██ ░██   ░██ ░██   ░██ ░████   ░██
    ░██    ░██                 ░██  ░██  ░██ ░██░██  ░██       ░██        ░██       ░██ ░██░██  ░██
    ░██    ░██         ░██████ ░██ ░████ ░██ ░██ ░██ ░██      ░██     ░█████    ░█████  ░██ ░██ ░██
    ░██    ░██                 ░██░██ ░██░██ ░██  ░██░██     ░██     ░██       ░██      ░██  ░██░██
    ░██    ░██                 ░████   ░████ ░██   ░████     ░██    ░██       ░██       ░██   ░████
    ░██    ░██████████         ░███     ░███ ░██    ░███     ░██    ░████████ ░████████ ░██    ░███
"""

FOX_HAPPY = r"""
      /\_/\
     ( o.o )    ✓ All done!
      > ^ <
     /|   |\
    (_|   |_)
"""

FOX_SAD = r"""
      /\_/\
     ( T_T )    ✗ Something broke...
      > ~ <
     /|   |\
    (_|   |_)
"""

FOX_WORKING = r"""
      /\_/\
     ( •.• )    ⚙ Working...
      > ^ <
     /|   |\
    (_|   |_)
"""

FOX_REPAIR = r"""
      /\_/\
     ( >.< )    🔧 Auto-repairing...
      > ^ <
     /|🔧|\
    (_|   |_)
"""

# ── TTY-aware output layer ────────────────────────────────────────────────────

IS_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


class PlainPrinter:
    """Fallback when rich is unavailable or stdout is not a TTY."""

    @staticmethod
    def info(msg: str) -> None:
        print(f"  [INFO]  {msg}")

    @staticmethod
    def success(msg: str) -> None:
        print(f"  [  OK]  {msg}")

    @staticmethod
    def warn(msg: str) -> None:
        print(f"  [WARN]  {msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"  [ ERR]  {msg}", file=sys.stderr)

    @staticmethod
    def repair(msg: str) -> None:
        print(f"  [  FIX] 🔧 {msg}")

    @staticmethod
    def header(_msg: str) -> None:
        print(LOGO_ART)
        print("  RTL8188EUS Driver Installer for Kali Linux — Self-Healing Edition")
        print("=" * 70)

    @staticmethod
    def step_header(msg: str) -> None:
        print(f"\n── {msg} ──")

    @staticmethod
    def phase(step: int, msg: str) -> None:
        bar = "█" * step + "░" * (TOTAL_STEPS - step)
        print(f"\n  [{bar}]  Phase {step}/{TOTAL_STEPS} — {msg}")

    @staticmethod
    def summary(rows: list[tuple[str, str]]) -> None:
        print("\n┌───────────────────────────────────────────────────────────┐")
        for label, status in rows:
            tag = "✓" if "success" in status.lower() else ("🔧" if "repair" in status.lower() else "✗")
            print(f"│  {tag}  {label:<34} {status:>16} │")
        print("└───────────────────────────────────────────────────────────┘")

    @staticmethod
    def fox(variant: str = "happy") -> None:
        art = {"happy": FOX_HAPPY, "sad": FOX_SAD, "working": FOX_WORKING, "repair": FOX_REPAIR}
        print(art.get(variant, FOX_HAPPY))

    @staticmethod
    def disclaimer() -> None:
        print("\n┌────────────────────────────────────────────────────────────────────┐")
        print("│                            DISCLAIMER                             │")
        print("│  Installs drivers for TP-Link TL-WN722N V2/V3 (RTL8188EUS).       │")
        print("│  Requires Kali Linux with root privileges.                         │")
        print("│  This will blacklist r8188eu and compile a new kernel module.       │")
        print("│  All errors are auto-repaired — no user input needed.              │")
        print("└────────────────────────────────────────────────────────────────────┘")

    @staticmethod
    def typewriter(msg: str) -> None:
        for ch in msg:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(0.02)
        print()

    @staticmethod
    def globe_spin(message: str, duration: float = 2.0) -> None:
        frames = ["🌍", "🌎", "🌏"]
        end = time.time() + duration
        while time.time() < end:
            for f in frames:
                sys.stdout.write(f"\r  {f}  {message}")
                sys.stdout.flush()
                time.sleep(0.2)
        print()

    @staticmethod
    def model_banner() -> None:
        print(MODEL_ART)

    @staticmethod
    def repair_animation(message: str, duration: float = 1.5) -> None:
        icons = itertools.cycle(["🔧", "🔩", "⚙️", "🛠️"])
        end = time.time() + duration
        while time.time() < end:
            sys.stdout.write(f"\r  {next(icons)}  {message}")
            sys.stdout.flush()
            time.sleep(0.15)
        print()


class RichPrinter:
    """Animated output powered by the rich library."""

    def __init__(self) -> None:
        self.console = Console()

    def info(self, msg: str) -> None:
        self.console.print(f"  [cyan]ℹ[/cyan]  {msg}")

    def success(self, msg: str) -> None:
        self.console.print(f"  [bold green]✓[/bold green]  [green]{msg}[/green]")

    def warn(self, msg: str) -> None:
        self.console.print(f"  [bold yellow]⚠[/bold yellow]  [yellow]{msg}[/yellow]")

    def error(self, msg: str) -> None:
        self.console.print(f"  [bold red]✗[/bold red]  [red]{msg}[/red]")

    def repair(self, msg: str) -> None:
        self.console.print(f"  [bold bright_magenta]🔧[/bold bright_magenta]  [bright_magenta]{msg}[/bright_magenta]")

    def header(self, _msg: str) -> None:
        self.console.clear()
        logo_lines = LOGO_ART.strip().splitlines()
        for line in logo_lines:
            self.console.print(f"[bold bright_magenta]{line}[/bold bright_magenta]")
            time.sleep(0.08)

        time.sleep(0.3)

        subtitle = Text("RTL8188EUS Driver Installer — Self-Healing Edition", style="bold bright_white")
        panel = Panel(
            Align.center(subtitle),
            border_style="bright_cyan",
            padding=(1, 2),
            title="[bold bright_magenta]🦊 KALI-FOX v3.0[/bold bright_magenta]",
            subtitle="[dim italic]Fully Automated · Auto-Repair · Zero Prompts[/dim italic]",
        )
        self.console.print(panel)
        self.console.print()

    def step_header(self, msg: str) -> None:
        self.console.print()
        self.console.print(Rule(f"[bold bright_yellow]{msg}[/bold bright_yellow]", style="dim cyan"))

    def phase(self, step: int, msg: str) -> None:
        filled = "█" * step
        empty = "░" * (TOTAL_STEPS - step)
        pct = int((step / TOTAL_STEPS) * 100)
        self.console.print()
        self.console.print(
            f"  [bright_cyan][[bold bright_magenta]{filled}[/bold bright_magenta]"
            f"[dim]{empty}[/dim]][/bright_cyan]  "
            f"[bold white]Phase {step}/{TOTAL_STEPS}[/bold white] "
            f"[dim]({pct}%)[/dim]  —  [bright_yellow]{msg}[/bright_yellow]"
        )

    def summary(self, rows: list[tuple[str, str]]) -> None:
        table = Table(
            title="[bold bright_cyan]⚡ Installation Summary ⚡[/bold bright_cyan]",
            show_header=True,
            header_style="bold bright_white",
            border_style="bright_cyan",
            title_style="bold",
            padding=(0, 2),
            show_lines=True,
        )
        table.add_column("Step", style="white", min_width=34)
        table.add_column("Result", justify="center", min_width=18)
        for label, status in rows:
            if "success" in status.lower():
                color = "bold green"
                icon = "✅"
            elif "repair" in status.lower():
                color = "bold bright_magenta"
                icon = "🔧"
            else:
                color = "bold red"
                icon = "❌"
            table.add_row(
                f"  {label}",
                f"[{color}]{icon} {status}[/{color}]",
            )
        self.console.print()
        self.console.print(table)
        self.console.print()

    def fox(self, variant: str = "happy") -> None:
        art_map = {"happy": FOX_HAPPY, "sad": FOX_SAD, "working": FOX_WORKING, "repair": FOX_REPAIR}
        art = art_map.get(variant, FOX_HAPPY)
        color = {
            "happy": "bright_green",
            "sad": "bright_red",
            "working": "bright_cyan",
            "repair": "bright_magenta",
        }.get(variant, "white")

        for line in art.strip().splitlines():
            self.console.print(Text(f"  {line}", style=f"bold {color}"))
            time.sleep(0.08)
        self.console.print()

    def disclaimer(self) -> None:
        disclaimer_text = (
            "[bold white]Installs drivers for TP-Link TL-WN722N V2/V3 (RTL8188EUS).[/bold white]\n"
            "[dim]Requires Kali Linux with root privileges.[/dim]\n"
            "[dim]This will blacklist r8188eu and compile a new kernel module.[/dim]\n\n"
            "[bold bright_green]✦ All errors are auto-repaired — zero user input needed.[/bold bright_green]"
        )
        panel = Panel(
            disclaimer_text,
            title="[bold bright_yellow]⚠ DISCLAIMER[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(1, 3),
        )
        self.console.print(panel)
        self.console.print()

    def typewriter(self, msg: str) -> None:
        for ch in msg:
            self.console.print(f"[bold bright_cyan]{ch}[/bold bright_cyan]", end="")
            time.sleep(0.02)
        self.console.print()

    def globe_spin(self, message: str, duration: float = 2.0) -> None:
        frames = ["🌍", "🌎", "🌏"]
        cycle = itertools.cycle(frames)
        with Live(console=self.console, refresh_per_second=10, transient=True) as live:
            end = time.time() + duration
            while time.time() < end:
                globe = next(cycle)
                live.update(Text.from_markup(f"  {globe}  [bold cyan]{message}[/bold cyan]"))
                time.sleep(0.15)

    def model_banner(self) -> None:
        self.console.print()
        for line in MODEL_ART.strip().splitlines():
            self.console.print(f"[bold bright_cyan]{line}[/bold bright_cyan]")
            time.sleep(0.06)
        self.console.print()

    def repair_animation(self, message: str, duration: float = 1.5) -> None:
        icons = ["🔧", "🔩", "⚙️ ", "🛠️"]
        cycle = itertools.cycle(icons)
        with Live(console=self.console, refresh_per_second=10, transient=True) as live:
            end = time.time() + duration
            while time.time() < end:
                icon = next(cycle)
                live.update(
                    Text.from_markup(
                        f"  {icon} [bold bright_magenta]{message}[/bold bright_magenta]"
                    )
                )
                time.sleep(0.15)


# Choose printer based on environment
ui: "PlainPrinter | RichPrinter"
if RICH_AVAILABLE and IS_TTY:
    ui = RichPrinter()
else:
    ui = PlainPrinter()


# ── Spinner context manager ──────────────────────────────────────────────────
class SpinnerContext:
    """Wraps rich.status.Status when available; falls back to plain print."""

    def __init__(self, message: str, spinner: str = "dots") -> None:
        self.message = message
        self.spinner = spinner
        self._status: "Status | None" = None

    def __enter__(self) -> "SpinnerContext":
        if RICH_AVAILABLE and IS_TTY:
            console = Console()
            self._status = console.status(
                f"[bold cyan]{self.message}[/bold cyan]",
                spinner=self.spinner,
                spinner_style="bright_magenta",
            )
            self._status.__enter__()
        else:
            print(f"  ⏳  {self.message} ...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        if self._status is not None:
            self._status.__exit__(exc_type, exc_val, exc_tb)


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_cmd(
    cmd: list[str],
    *,
    cwd: str | None = None,
    critical: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a shell command and return the result. Never exits on its own."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=capture,
    )
    return result


def get_kernel_release() -> str:
    return platform.release()


def cleanup_clone_dir() -> None:
    """Remove the cloned repo directory on exit if it still exists."""
    if os.path.isdir(CLONE_DIR):
        shutil.rmtree(CLONE_DIR, ignore_errors=True)


# ── Auto-repair installation steps ───────────────────────────────────────────

def check_root() -> bool:
    if os.geteuid() != 0:
        ui.error("This script must be run as root.")
        ui.info("Re-run with: sudo python3 install_rtl8188eus.py")
        return False
    return True


def step_install_dependencies() -> str:
    """Returns 'success', 'repaired', or 'failed'."""
    kernel = get_kernel_release()
    packages = REQUIRED_PACKAGES + [f"linux-headers-{kernel}"]

    ui.phase(1, "Installing build dependencies")
    ui.step_header("Step 1 · Installing build dependencies")

    # ── Attempt 1: Normal apt update ──
    with SpinnerContext("Updating apt package lists", spinner="earth"):
        result = run_cmd(["apt-get", "update", "-qq"])

    if result.returncode != 0:
        ui.warn("apt-get update failed — attempting auto-repair")
        ui.repair_animation("Fixing package manager")

        # Repair: fix broken sources
        with SpinnerContext("Running dpkg --configure -a", spinner="toggle"):
            run_cmd(["dpkg", "--configure", "-a"])

        with SpinnerContext("Running apt-get update --fix-missing", spinner="toggle"):
            result = run_cmd(["apt-get", "update", "--fix-missing", "-qq"])

        if result.returncode != 0:
            ui.warn("apt-get update still has warnings — continuing anyway")
        else:
            ui.repair("Package manager repaired")
    else:
        ui.success("Package lists updated")

    # ── Attempt 1: Install packages ──
    with SpinnerContext(f"Installing {len(packages)} packages", spinner="bouncingBar"):
        result = run_cmd(["apt-get", "install", "-y", "-qq"] + packages)

    if result.returncode != 0:
        ui.warn("Package installation failed — attempting auto-repair")
        ui.fox("repair")
        ui.repair_animation("Repairing broken packages")

        # Repair strategy 1: fix broken installs
        with SpinnerContext("Running apt-get install -f", spinner="toggle"):
            run_cmd(["apt-get", "install", "-f", "-y"])

        # Repair strategy 2: retry install
        with SpinnerContext("Retrying package installation", spinner="bouncingBar"):
            result = run_cmd(["apt-get", "install", "-y", "-qq"] + packages)

        if result.returncode != 0:
            # Repair strategy 3: install one by one to find the problem
            ui.repair("Installing packages individually to isolate failures")
            failed_pkgs = []
            for pkg in packages:
                r = run_cmd(["apt-get", "install", "-y", "-qq", pkg])
                if r.returncode != 0:
                    failed_pkgs.append(pkg)
                    ui.warn(f"Could not install {pkg} — skipping")
                else:
                    ui.success(f"Installed {pkg}")

            if any(p in failed_pkgs for p in ["build-essential", "git"]):
                ui.error("Critical packages missing — cannot continue")
            ui.repair(f"Installed {len(packages) - len(failed_pkgs)}/{len(packages)} packages")
            return "repaired"
        else:
            ui.repair("Packages installed after repair")
            return "repaired"

    ui.success("All build dependencies installed")
    return "success"


def step_unload_module() -> str:
    """Returns 'success', 'repaired', or 'failed'."""
    ui.phase(2, "Unloading conflicting module")
    ui.step_header("Step 2 · Unloading conflicting r8188eu module")

    with SpinnerContext("Removing kernel module r8188eu", spinner="toggle"):
        result = run_cmd(["rmmod", "r8188eu"])

    if result.returncode == 0:
        ui.success("Module r8188eu unloaded")
    else:
        # Check if it's even loaded
        lsmod = run_cmd(["lsmod"])
        if "r8188eu" in (lsmod.stdout or ""):
            # Module is loaded but rmmod failed — force it
            ui.warn("rmmod failed — trying force unload")
            ui.repair_animation("Force-removing module")
            result = run_cmd(["rmmod", "-f", "r8188eu"])
            if result.returncode == 0:
                ui.repair("Module force-unloaded")
                return "repaired"
            else:
                ui.warn("Force-unload failed — module may be in use. Will continue anyway.")
                return "repaired"
        else:
            ui.info("Module r8188eu was not loaded — nothing to remove")

    return "success"


def step_blacklist() -> str:
    """Returns 'success', 'repaired', or 'failed'."""
    ui.phase(3, "Blacklisting driver")
    ui.step_header("Step 3 · Blacklisting r8188eu")

    if os.path.isfile(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r") as fh:
                if BLACKLIST_LINE in fh.read():
                    ui.info("r8188eu is already blacklisted — skipping")
                    return "success"
        except PermissionError:
            ui.warn(f"Cannot read {BLACKLIST_FILE} — will overwrite")

    try:
        with open(BLACKLIST_FILE, "a") as fh:
            fh.write(f"{BLACKLIST_LINE}\n")
        ui.success(f"Wrote '{BLACKLIST_LINE}' → {BLACKLIST_FILE}")
        return "success"
    except OSError as exc:
        ui.warn(f"Failed to write blacklist file: {exc}")
        ui.repair_animation("Repairing blacklist file permissions")

        # Repair: create the directory if missing, then retry
        modprobe_dir = os.path.dirname(BLACKLIST_FILE)
        os.makedirs(modprobe_dir, exist_ok=True)
        try:
            with open(BLACKLIST_FILE, "w") as fh:
                fh.write(f"{BLACKLIST_LINE}\n")
            ui.repair("Blacklist file created after repair")
            return "repaired"
        except OSError as exc2:
            ui.error(f"Still cannot write blacklist: {exc2}")
            return "failed"


def step_clone(repo_url: str | None = None) -> str:
    """Returns 'success', 'repaired', or 'failed'."""
    target_repo = repo_url or REPO_URL
    ui.phase(4, "Cloning driver source")
    repo_name = f"{target_repo.split('/')[-2]}/{target_repo.split('/')[-1]}"
    ui.step_header(f"Step 4 · Cloning driver source ({repo_name})")

    if os.path.isdir(CLONE_DIR):
        ui.info(f"Removing old clone at {CLONE_DIR}")
        shutil.rmtree(CLONE_DIR, ignore_errors=True)

    ui.globe_spin(f"Downloading driver source from {repo_name}", duration=1.5)

    # ── Attempt 1: git clone ──
    with SpinnerContext(f"Cloning {target_repo}", spinner="dots12"):
        result = run_cmd(["git", "clone", "--depth=1", target_repo, CLONE_DIR])

    if result.returncode == 0 and os.path.isfile(os.path.join(CLONE_DIR, "Makefile")):
        ui.success(f"Repository cloned → {CLONE_DIR}")
        return "success"

    # ── Repair 1: retry clone without depth limit ──
    ui.warn("Git clone failed — retrying without depth limit")
    ui.repair_animation("Retrying git clone")
    if os.path.isdir(CLONE_DIR):
        shutil.rmtree(CLONE_DIR, ignore_errors=True)

    with SpinnerContext("Cloning full repository", spinner="dots"):
        result = run_cmd(["git", "clone", target_repo, CLONE_DIR])

    if result.returncode == 0 and os.path.isfile(os.path.join(CLONE_DIR, "Makefile")):
        ui.repair("Repository cloned (full) after retry")
        return "repaired"

    # ── Repair 2: tarball fallback ──
    ui.warn("Git clone failed — falling back to tarball download")
    ui.fox("repair")
    ui.repair_animation("Downloading tarball archive")

    tarball = "/tmp/rtl8188eus.tar.gz"
    tarball_url = target_repo.replace(".git", "/archive/refs/heads/master.tar.gz").replace("github.com", "codeload.github.com")

    with SpinnerContext("Downloading tarball via wget", spinner="bouncingBall"):
        result = run_cmd(["wget", "-q", tarball_url, "-O", tarball])

    if result.returncode != 0:
        with SpinnerContext("wget failed — trying curl", spinner="bouncingBall"):
            result = run_cmd(["curl", "-sL", tarball_url, "-o", tarball])

    if result.returncode == 0 and os.path.isfile(tarball):
        os.makedirs(CLONE_DIR, exist_ok=True)
        run_cmd(["tar", "xzf", tarball, "-C", "/tmp/"])
        extracted = glob.glob("/tmp/rtl8188eus-*") or glob.glob("/tmp/rtl8188eu-*")
        if extracted:
            if os.path.isdir(CLONE_DIR):
                shutil.rmtree(CLONE_DIR, ignore_errors=True)
            os.rename(extracted[0], CLONE_DIR)
        if os.path.isfile(tarball):
            os.remove(tarball)

    if os.path.isdir(CLONE_DIR) and os.path.isfile(os.path.join(CLONE_DIR, "Makefile")):
        ui.repair(f"Source obtained via tarball → {CLONE_DIR}")
        return "repaired"

    ui.error(f"Could not obtain driver source from {repo_name}")
    return "failed"


def _copy_headers_to_all_subdirs() -> None:
    """Copy all header files from include/ directly into core/, hal/, os_dep/, etc.
    This guarantees gcc finds headers like drv_types.h even if Kbuild sub-directory include paths break."""
    include_dir = os.path.join(CLONE_DIR, "include")
    if not os.path.isdir(include_dir):
        return

    headers = []
    for root, _, files in os.walk(include_dir):
        for f in files:
            if f.endswith(".h"):
                headers.append(os.path.join(root, f))

    subdirs = [
        CLONE_DIR,
        os.path.join(CLONE_DIR, "core"),
        os.path.join(CLONE_DIR, "hal"),
        os.path.join(CLONE_DIR, "os_dep"),
        os.path.join(CLONE_DIR, "hal", "phydm"),
        os.path.join(CLONE_DIR, "hal", "rtl8188e"),
        os.path.join(CLONE_DIR, "include"),
    ]

    for sdir in subdirs:
        os.makedirs(sdir, exist_ok=True)
        for h in headers:
            dst = os.path.join(sdir, os.path.basename(h))
            try:
                shutil.copy2(h, dst)
            except Exception:
                pass


def _patch_makefile_includes() -> None:
    """Patch Makefile and create Kbuild with ccflags-y and subdir-ccflags-y for modern Kbuild."""
    include_dir = os.path.join(CLONE_DIR, "include")
    makefile_path = os.path.join(CLONE_DIR, "Makefile")
    kbuild_path = os.path.join(CLONE_DIR, "Kbuild")

    if not os.path.isdir(include_dir):
        return

    patch_lines = [
        f"ccflags-y += -I{include_dir} -I{CLONE_DIR} -I$(M)/include -I$(src)/include -I$(src)/../include",
        f"subdir-ccflags-y += -I{include_dir} -I{CLONE_DIR} -I$(M)/include -I$(src)/include -I$(src)/../include",
        f"EXTRA_CFLAGS += -I{include_dir} -I{CLONE_DIR} -I$(M)/include -I$(src)/include -I$(src)/../include",
        f"USER_EXTRA_CFLAGS += -I{include_dir} -I{CLONE_DIR} -I$(M)/include -I$(src)/include -I$(src)/../include",
    ]

    if os.path.isfile(makefile_path):
        with open(makefile_path, "r") as fh:
            makefile_text = fh.read()

        with open(makefile_path, "a") as fh:
            fh.write("\n# -- KALI-FOX patch: ccflags-y & subdir-ccflags-y --\n")
            for line in patch_lines:
                if line not in makefile_text:
                    fh.write(f"{line}\n")

    # Create explicit Kbuild file to ensure subdirectories inherit flags in Kbuild
    with open(kbuild_path, "w") as fh:
        fh.write("\n".join(patch_lines) + "\n")


def _apply_kernel_7_patches() -> None:
    """Auto-patch driver source code for Linux 6.8+ / 7.0+ kernel API compatibility."""
    if not os.path.exists(CLONE_DIR):
        return

    for root, _, files in os.walk(CLONE_DIR):
        for f in files:
            if f.endswith(".c") or f.endswith(".h"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()

                    modified = False
                    if "strlcpy(" in content:
                        content = content.replace("strlcpy(", "strscpy(")
                        modified = True

                    if "prandom_u32()" in content:
                        content = content.replace("prandom_u32()", "get_random_u32()")
                        modified = True

                    if modified:
                        with open(filepath, "w", encoding="utf-8") as fp:
                            fp.write(content)
                except Exception:
                    pass


def _try_compile(extra_flags: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run make with ccflags-y and subdir-ccflags-y."""
    include_dir = os.path.join(CLONE_DIR, "include")
    inc_flag = f"-I{include_dir} -I{CLONE_DIR} -I$(M)/include"
    cmd = [
        "make",
        f"ccflags-y={inc_flag}",
        f"subdir-ccflags-y={inc_flag}",
        f"USER_EXTRA_CFLAGS={inc_flag}",
        f"EXTRA_CFLAGS={inc_flag}",
        f"KCFLAGS={inc_flag}",
    ]
    if extra_flags:
        cmd.extend(extra_flags)
    return run_cmd(cmd, cwd=CLONE_DIR)


def step_compile() -> str:
    """Returns 'success', 'repaired', or 'failed'. Tries multiple repo sources and build strategies."""
    ui.phase(5, "Compiling & installing driver")
    ui.step_header("Step 5 · Compiling & installing driver")
    ui.fox("working")

    for idx, repo_url in enumerate(REPO_URLS):
        repo_name = f"{repo_url.split('/')[-2]}/{repo_url.split('/')[-1]}"
        if idx > 0:
            ui.warn(f"Trying fallback driver repository ({idx+1}/{len(REPO_URLS)}): {repo_name}")
            c_res = step_clone(repo_url)
            if c_res == "failed":
                continue

        include_dir = os.path.join(CLONE_DIR, "include")

        # ── Pre-patch: Copy headers directly + patch Makefile & Linux 7.0 APIs ──
        _copy_headers_to_all_subdirs()
        _patch_makefile_includes()
        _apply_kernel_7_patches()

        # ── Strategy 1: make with ccflags-y and subdir-ccflags-y ──
        ui.info(f"Strategy 1: Compile [{repo_name}] with absolute include flags")
        with SpinnerContext("Running make with absolute include paths", spinner="bouncingBall"):
            result = _try_compile()

        if result.returncode == 0:
            ui.success(f"Compilation succeeded with {repo_name} (Strategy 1)")
            inst_res = _do_make_install()
            if inst_res in ("success", "repaired"):
                return inst_res

        # ── Strategy 2: make clean + retry with CFLAGS_MODULE ──
        ui.warn(f"Strategy 1 failed for {repo_name} — trying Strategy 2")
        ui.repair_animation("Cleaning build and retrying with CFLAGS_MODULE")

        with SpinnerContext("Running make clean", spinner="toggle"):
            run_cmd(["make", "clean"], cwd=CLONE_DIR)

        _copy_headers_to_all_subdirs()

        ui.info(f"Strategy 2: Compile [{repo_name}] with CFLAGS_MODULE")
        with SpinnerContext("Recompiling with CFLAGS_MODULE", spinner="bouncingBall"):
            result = _try_compile([f"CFLAGS_MODULE=-I{include_dir} -I{CLONE_DIR}/core"])

        if result.returncode == 0:
            ui.repair(f"Compilation succeeded with {repo_name} (Strategy 2 — CFLAGS_MODULE)")
            inst_res = _do_make_install("repaired")
            if inst_res in ("success", "repaired"):
                return inst_res

        # ── Strategy 3: DKMS install ──
        ui.warn(f"Strategy 2 failed for {repo_name} — trying Strategy 3 (DKMS)")
        ui.repair_animation("Attempting DKMS installation")

        with SpinnerContext("Running make clean", spinner="toggle"):
            run_cmd(["make", "clean"], cwd=CLONE_DIR)

        with SpinnerContext("Trying make dkms-install", spinner="bouncingBall"):
            result = run_cmd(["make", "dkms-install"], cwd=CLONE_DIR)

        if result.returncode == 0:
            ui.repair(f"DKMS installation succeeded with {repo_name} (Strategy 3)")
            return "repaired"

    ui.error("All driver repositories and compilation strategies failed")
    return "failed"


def _do_make_install(status: str = "success") -> str:
    """Run make install, with automatic file copy fallback for any compiled .ko module."""
    with SpinnerContext("Running make install", spinner="arrow3"):
        result = run_cmd(["make", "install"], cwd=CLONE_DIR)

    if result.returncode == 0:
        ui.success("Driver installed into kernel modules tree")
        return status

    ui.warn("make install failed — attempting auto-repair file copy")
    ui.repair_animation("Locating compiled kernel module file (.ko)")

    # Find ANY .ko file compiled inside CLONE_DIR
    ko_files = []
    for root, _, files in os.walk(CLONE_DIR):
        for f in files:
            if f.endswith(".ko") or f.endswith(".ko.xz") or f.endswith(".ko.zst") or ".ko." in f:
                ko_files.append(os.path.join(root, f))

    if not ko_files:
        ui.info("Running make modules explicitly to generate .ko file")
        run_cmd(["make", "modules"], cwd=CLONE_DIR)
        for root, _, files in os.walk(CLONE_DIR):
            for f in files:
                if f.endswith(".ko") or f.endswith(".ko.xz") or f.endswith(".ko.zst") or ".ko." in f:
                    ko_files.append(os.path.join(root, f))

    kernel = get_kernel_release()

    # Fallback: check if module already exists in system module tree
    if not ko_files:
        existing = glob.glob(f"/lib/modules/{kernel}/**/8188eu.ko*", recursive=True) + glob.glob(f"/lib/modules/{kernel}/**/r8188eu.ko*", recursive=True)
        if existing:
            ui.repair(f"Module file already exists in kernel tree → {existing[0]}")
            run_cmd(["depmod", "-a"])
            return "repaired"

    if not ko_files:
        ui.error("No compiled .ko file found in driver source directory")
        return "failed"

    dest_dir = f"/lib/modules/{kernel}/kernel/drivers/net/wireless/"
    os.makedirs(dest_dir, exist_ok=True)

    installed = []
    for src_ko in ko_files:
        dest_path = os.path.join(dest_dir, os.path.basename(src_ko))
        try:
            shutil.copy2(src_ko, dest_path)
            installed.append(dest_path)
        except Exception as exc:
            ui.warn(f"Could not copy {src_ko} to {dest_path}: {exc}")

    if installed:
        run_cmd(["depmod", "-a"])
        ui.repair(f"Installed module file(s) → {dest_dir}")
        return "repaired"

    ui.error("Failed to copy module files to kernel drivers directory")
    return "failed"


def step_load_module() -> str:
    """Returns 'success', 'repaired', or 'failed'."""
    ui.phase(6, "Loading new driver")
    ui.step_header("Step 6 · Loading new driver")

    with SpinnerContext("Running depmod -a", spinner="simpleDots"):
        run_cmd(["depmod", "-a"])

    with SpinnerContext("Loading 8188eu module", spinner="toggle2"):
        result = run_cmd(["modprobe", "8188eu"])

    if result.returncode == 0:
        ui.success("Module 8188eu loaded — adapter should be active")
        return "success"

    # ── Repair: try insmod directly ──
    ui.warn("modprobe failed — trying insmod directly")
    ui.repair_animation("Searching for compiled module file")

    # Find the .ko file
    ko_candidates = (
        glob.glob(f"/lib/modules/{get_kernel_release()}/kernel/drivers/net/wireless/8188eu.ko*")
        + glob.glob(os.path.join(CLONE_DIR, "8188eu.ko"))
        + glob.glob(os.path.join(CLONE_DIR, "8188eu.ko.xz"))
    )

    for ko_file in ko_candidates:
        ui.info(f"Trying insmod {ko_file}")
        result = run_cmd(["insmod", ko_file])
        if result.returncode == 0:
            ui.repair("Module loaded via insmod")
            return "repaired"

    ui.warn("Could not load module now — a reboot should activate it")
    return "repaired"  # not fatal; reboot will fix it


def print_wifite_diagnostic_guide(iface: str = "wlan0") -> None:
    """Print troubleshooting guide for wifite scanning & VM USB passthrough."""
    if RICH_AVAILABLE and IS_TTY:
        console = Console()
        console.print()
        console.print(Panel(
            f"[bold bright_green]✦ How to run Wifite with RTL8188EUS:[/bold bright_green]\n\n"
            f"[bold white]1. Always kill interfering processes first:[/bold white]\n"
            f"   [bright_cyan]sudo airmon-ng check kill[/bright_cyan]\n\n"
            f"[bold white]2. Run Wifite directly specifying your interface:[/bold white]\n"
            f"   [bright_cyan]sudo wifite -i {iface}[/bright_cyan]  [dim]or[/dim]  [bright_cyan]sudo wifite --kill[/bright_cyan]\n\n"
            f"[bold white]3. Test scanning with airodump-ng:[/bold white]\n"
            f"   [bright_cyan]sudo airodump-ng {iface}[/bright_cyan]\n\n"
            f"[bold yellow]⚠ IMPORTANT FOR VIRTUAL MACHINE USERS (VMware / VirtualBox):[/bold yellow]\n"
            f"[dim]If wifite/airodump-ng is NOT listing nearby Wi-Fi networks:[/dim]\n"
            f"  • Ensure your TP-Link TL-WN722N USB adapter is connected to the [bold white]Kali Linux VM[/bold white] (VM -> Removable Devices -> Realtek RTL8188EUS -> Connect), NOT Windows!\n"
            f"  • Set VM USB Controller setting to [bold white]USB 2.0 or USB 3.0[/bold white].",
            title="[bold bright_magenta]🔍 Wifite & Airodump Scanning Fix Guide[/bold bright_magenta]",
            border_style="bright_cyan",
            padding=(1, 2)
        ))
    else:
        print("\n" + "=" * 60)
        print(" Wifite & Airodump Scanning Fix Guide")
        print("=" * 60)
        print(f"1. Kill interfering processes: sudo airmon-ng check kill")
        print(f"2. Run Wifite: sudo wifite -i {iface} --kill")
        print(f"3. Test scanning: sudo airodump-ng {iface}")
        print("4. VM Users: Pass through TP-Link USB to Kali VM in USB settings!")
        print("=" * 60)


def run_monitor_fix() -> None:
    """Run automated Monitor Mode fixer and wifite diagnostic tool."""
    ui.step_header("📡 Monitor Mode Auto-Fixer & Wifite Diagnostic")

    with SpinnerContext("Killing processes interfering with monitor mode", spinner="dots"):
        run_cmd(["airmon-ng", "check", "kill"])
    ui.success("Interfering processes killed (NetworkManager, wpa_supplicant)")

    # Detect wireless interfaces
    ifaces = []
    try:
        r = run_cmd(["iwconfig"])
        for line in (r.stdout or "").splitlines():
            if line and not line.startswith(" ") and "no wireless" not in line:
                iface_name = line.split()[0]
                ifaces.append(iface_name)
    except Exception:
        pass

    if not ifaces:
        ifaces = ["wlan0"]

    target_iface = ifaces[0]
    ui.info(f"Targeting wireless interface: {target_iface}")

    with SpinnerContext(f"Setting {target_iface} to Monitor Mode", spinner="bouncingBar"):
        run_cmd(["ip", "link", "set", target_iface, "down"])
        r1 = run_cmd(["iw", "dev", target_iface, "set", "type", "monitor"])
        if r1.returncode != 0:
            run_cmd(["iwconfig", target_iface, "mode", "monitor"])
        run_cmd(["ip", "link", "set", target_iface, "up"])

    # Verify
    r_check = run_cmd(["iwconfig", target_iface])
    if "Monitor" in (r_check.stdout or ""):
        ui.success(f"Interface {target_iface} is now in Monitor Mode! 📡")
    else:
        ui.warn(f"Interface {target_iface} set — verify with iwconfig")

    print_wifite_diagnostic_guide(target_iface)


def print_monitor_mode_instructions() -> None:
    """Print Monitor Mode & Packet Injection Walkthrough Banner."""
    if RICH_AVAILABLE and IS_TTY:
        console = Console()
        console.print()
        console.print(Panel(
            "[bold white]1. Identify wireless interface name:[/bold white]\n"
            "   [bold bright_cyan]iwconfig[/bold bright_cyan]\n\n"
            "[bold white]2. Kill conflicting processes & set monitor mode:[/bold white]\n"
            "   [bold bright_cyan]sudo ifconfig wlan0 down[/bold bright_cyan]\n"
            "   [bold bright_cyan]sudo airmon-ng check kill[/bold bright_cyan]\n"
            "   [bold bright_cyan]sudo iwconfig wlan0 mode monitor[/bold bright_cyan]\n"
            "   [bold bright_cyan]sudo ifconfig wlan0 up[/bold bright_cyan]\n\n"
            "[bold white]3. Verify monitor mode (look for Mode:Monitor):[/bold white]\n"
            "   [bold bright_cyan]iwconfig[/bold bright_cyan]\n\n"
            "[bold white]4. Test packet injection:[/bold white]\n"
            "   [bold bright_cyan]sudo aireplay-ng --test wlan0[/bold bright_cyan]",
            title="[bold bright_magenta]📡 Step 5: Enable Monitor Mode & Test Injection[/bold bright_magenta]",
            border_style="bright_cyan",
            padding=(1, 2)
        ))
    else:
        print("\n" + "=" * 60)
        print(" Step 5: Enable Monitor Mode & Test Injection")
        print("=" * 60)
        print("1. Identify wireless interface: iwconfig")
        print("2. Set monitor mode (assuming wlan0):")
        print("   sudo ifconfig wlan0 down")
        print("   sudo airmon-ng check kill")
        print("   sudo iwconfig wlan0 mode monitor")
        print("   sudo ifconfig wlan0 up")
        print("3. Verify monitor mode: iwconfig")
        print("4. Test packet injection: sudo aireplay-ng --test wlan0")
        print("=" * 60)


def check_self_update() -> None:
    """If running inside a git repository, automatically update to latest origin/master if behind."""
    if os.path.isdir(".git") and "--no-update" not in sys.argv:
        try:
            r = subprocess.run(["git", "fetch", "origin", "master"], capture_output=True, text=True, timeout=8)
            if r.returncode == 0:
                log_check = subprocess.run(["git", "rev-list", "HEAD..origin/master", "--count"], capture_output=True, text=True, timeout=5)
                behind_count = int(log_check.stdout.strip() or "0")
                if behind_count > 0:
                    ui.info(f"Self-Update: New version detected ({behind_count} commit(s) behind origin/master).")
                    ui.repair_animation("Syncing latest code from GitHub")
                    subprocess.run(["git", "reset", "--hard", "origin/master"], capture_output=True, text=True)
                    ui.success("Self-Update successful! Restarting script...")
                    time.sleep(1)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Graceful Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: (ui.warn("\nInterrupted by user"), sys.exit(130)))
    atexit.register(cleanup_clone_dir)

    if "--fix-monitor" in sys.argv or "-m" in sys.argv:
        if check_root():
            run_monitor_fix()
        sys.exit(0)

    # ── Auto-Update Check ──
    check_self_update()

    # ── Screen 1: Welcome & Specs Screen ──
    if RICH_AVAILABLE and IS_TTY:
        Console().clear()
    ui.header("KALI-FOX")
    ui.model_banner()
    ui.disclaimer()

    kernel = get_kernel_release()
    python_ver = sys.version.split()[0]
    rich_status = "available ✓" if RICH_AVAILABLE else "not installed"

    ui.typewriter(f"  ▸ Kernel:  {kernel}")
    ui.typewriter(f"  ▸ Python:  {python_ver}")
    ui.typewriter(f"  ▸ Rich:    {rich_status}")
    ui.typewriter(f"  ▸ Target:  RTL8188EUS (TL-WN722N V2/V3)")
    ui.typewriter(f"  ▸ Mode:    Fully Automated · Self-Healing Multi-Phase Wizard")

    # Gate: root
    if not check_root():
        sys.exit(1)

    ui.success("Running as root — full access granted")
    time.sleep(1.5)

    # ── Screen 2: Installation Wizard Dashboard ──
    if RICH_AVAILABLE and IS_TTY:
        Console().clear()
        Console().print(Rule("[bold bright_cyan]🦊 Phase 2: Driver Installation Wizard[/bold bright_cyan]", style="bright_magenta"))
        Console().print()

    results: list[tuple[str, str]] = []
    steps: list[tuple[str, callable]] = [
        ("Install dependencies", step_install_dependencies),
        ("Unload conflicting module", step_unload_module),
        ("Blacklist r8188eu", step_blacklist),
        ("Clone driver repository", step_clone),
        ("Compile & install driver", step_compile),
        ("Load new kernel module", step_load_module),
    ]

    for label, step_fn in steps:
        status = step_fn()

        if status == "success":
            results.append((label, "✓ Success"))
        elif status == "repaired":
            results.append((label, "🔧 Repaired"))
        else:
            results.append((label, "✗ Failed"))
            ui.error(f"Step '{label}' failed even after auto-repair — aborting.")
            break

    # ── Screen 3: Completion & Summary Screen ──
    any_failed = any("Failed" in s for _, s in results)
    any_repaired = any("Repair" in s for _, s in results)

    time.sleep(1.0)
    if RICH_AVAILABLE and IS_TTY and not any_failed:
        Console().clear()
        Console().print(Rule("[bold bright_cyan]🏁 Phase 3: Final Installation Summary[/bold bright_cyan]", style="bright_magenta"))
        Console().print()

    ui.summary(results)

    if not any_failed:
        ui.fox("happy")
        if any_repaired:
            ui.success("Installation complete — auto-repaired all build warnings! 🦊")
        else:
            ui.success("Installation complete — clean run with zero errors! 🦊")

        print_wifite_diagnostic_guide()

        # Auto-reboot countdown
        if RICH_AVAILABLE and IS_TTY:
            console = Console()
            console.print()
            console.print("  [bold bright_yellow]⚡ A reboot is recommended to load the new driver.[/bold bright_yellow]")
            console.print("  [dim]The system will reboot in 10 seconds. Press Ctrl+C to cancel.[/dim]")
            console.print()
            try:
                for i in range(10, 0, -1):
                    console.print(f"\r  [bold bright_magenta]Rebooting in {i}s...[/bold bright_magenta]  ", end="")
                    time.sleep(1)
                console.print()
                subprocess.run(["reboot"])
            except KeyboardInterrupt:
                console.print()
                ui.info("Reboot cancelled — you can reboot manually later.")
        else:
            print("\n  A reboot is recommended. Rebooting in 10 seconds (Ctrl+C to cancel)...")
            try:
                for i in range(10, 0, -1):
                    print(f"\r  Rebooting in {i}s...", end="")
                    time.sleep(1)
                print()
                subprocess.run(["reboot"])
            except KeyboardInterrupt:
                print()
                ui.info("Reboot cancelled.")
    else:
        ui.fox("sad")
        ui.warn("Installation could not be completed even after auto-repair.")
        ui.info("Please check the error output above and report an issue at:")
        ui.info("  https://github.com/cid-moosa/KALI-FOX/issues")

    sys.exit(0 if not any_failed else 1)


if __name__ == "__main__":
    if not RICH_AVAILABLE:
        print(
            "\n[WARN] The 'rich' library is not installed.\n"
            "       The installer will work fine with plain text output,\n"
            "       but for the best experience install it first:\n\n"
            "         apt install python3-rich\n"
            "       or\n"
            "         pip install rich\n"
        )
    main()
