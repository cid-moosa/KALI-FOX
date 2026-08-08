#!/usr/bin/env python3
"""
KALI-FOX — RTL8188EUS Driver Installer
Automated installer for the TP-Link TL-WN722N V2/V3 Wi-Fi adapter
(Realtek RTL8188EUS chipset) on Kali Linux.

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

# ── Rich dependency gate ──────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.status import Status
    from rich.table import Table
    from rich.rule import Rule
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_URL = "https://github.com/aircrack-ng/rtl8188eus.git"
CLONE_DIR = "/tmp/rtl8188eus"
BLACKLIST_FILE = "/etc/modprobe.d/realtek.conf"
BLACKLIST_LINE = "blacklist r8188eu"
REQUIRED_PACKAGES = [
    "build-essential",
    "libelf-dev",
    "bc",
    "dkms",
    "git",
]

# ── TTY-aware output layer ────────────────────────────────────────────────────
# Respects NO_COLOR, non-TTY pipes, and missing rich gracefully.

IS_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


class PlainPrinter:
    """Fallback when rich is unavailable or stdout is not a TTY."""

    @staticmethod
    def info(msg: str) -> None:
        print(f"[INFO]  {msg}")

    @staticmethod
    def success(msg: str) -> None:
        print(f"[  OK]  {msg}")

    @staticmethod
    def warn(msg: str) -> None:
        print(f"[WARN]  {msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"[ ERR]  {msg}", file=sys.stderr)

    @staticmethod
    def header(msg: str) -> None:
        width = 60
        border = "═" * width
        print(f"\n{border}")
        print(f"  {msg}")
        print(f"{border}\n")

    @staticmethod
    def step_header(msg: str) -> None:
        print(f"\n── {msg} ──")

    @staticmethod
    def summary(rows: list[tuple[str, str]]) -> None:
        print("\n┌─────────────────────────────────────────────┐")
        for label, status in rows:
            tag = "✓" if "success" in status.lower() or "ok" in status.lower() else "✗"
            print(f"│  {tag}  {label:<28} {status:>10} │")
        print("└─────────────────────────────────────────────┘")


class RichPrinter:
    """Pretty output powered by the rich library."""

    def __init__(self) -> None:
        self.console = Console()

    def info(self, msg: str) -> None:
        self.console.print(f"  [cyan]ℹ[/cyan]  {msg}")

    def success(self, msg: str) -> None:
        self.console.print(f"  [bold green]✓[/bold green]  {msg}")

    def warn(self, msg: str) -> None:
        self.console.print(f"  [bold yellow]⚠[/bold yellow]  {msg}")

    def error(self, msg: str) -> None:
        self.console.print(f"  [bold red]✗[/bold red]  {msg}")

    def header(self, msg: str) -> None:
        title = Text(msg, style="bold bright_white")
        panel = Panel(
            title,
            border_style="bright_cyan",
            padding=(1, 4),
            title="[bold bright_magenta]🦊 KALI-FOX[/bold bright_magenta]",
            subtitle="[dim]RTL8188EUS Driver Installer[/dim]",
        )
        self.console.print()
        self.console.print(panel)
        self.console.print()

    def step_header(self, msg: str) -> None:
        self.console.print()
        self.console.print(Rule(f"[bold bright_yellow]{msg}[/bold bright_yellow]", style="dim"))

    def summary(self, rows: list[tuple[str, str]]) -> None:
        table = Table(
            title="[bold bright_cyan]Installation Summary[/bold bright_cyan]",
            show_header=True,
            header_style="bold bright_white",
            border_style="bright_cyan",
            title_style="bold",
            padding=(0, 2),
        )
        table.add_column("Step", style="white", min_width=30)
        table.add_column("Result", justify="center", min_width=12)
        for label, status in rows:
            color = "bold green" if "success" in status.lower() or "ok" in status.lower() else "bold red"
            table.add_row(label, f"[{color}]{status}[/{color}]")
        self.console.print()
        self.console.print(table)
        self.console.print()


# Choose printer based on environment
ui: PlainPrinter | RichPrinter
if RICH_AVAILABLE and IS_TTY:
    ui = RichPrinter()
else:
    ui = PlainPrinter()


# ── Spinner context manager (degrades to plain text) ──────────────────────────
class SpinnerContext:
    """Wraps rich.status.Status when available; falls back to plain print."""

    def __init__(self, message: str) -> None:
        self.message = message
        self._status: Status | None = None

    def __enter__(self) -> "SpinnerContext":
        if RICH_AVAILABLE and IS_TTY:
            console = Console()
            self._status = console.status(
                f"[bold cyan]{self.message}[/bold cyan]",
                spinner="dots",
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
    critical: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a shell command, returning the CompletedProcess.

    If *critical* is True and the command fails, print stderr and exit.
    """
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=capture,
    )
    if critical and result.returncode != 0:
        ui.error(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            ui.error(result.stderr.strip())
        if result.stdout:
            ui.info(result.stdout.strip())
        sys.exit(1)
    return result


def get_kernel_release() -> str:
    return platform.release()


def cleanup_clone_dir() -> None:
    """Remove the cloned repo directory on exit if it still exists."""
    if os.path.isdir(CLONE_DIR):
        shutil.rmtree(CLONE_DIR, ignore_errors=True)


# ── Installation steps ────────────────────────────────────────────────────────

def check_root() -> bool:
    if os.geteuid() != 0:
        ui.error("This script must be run as [bold]root[/bold]." if RICH_AVAILABLE else "This script must be run as root.")
        ui.info("Re-run with: sudo python3 install_rtl8188eus.py")
        return False
    return True


def install_dependencies() -> bool:
    kernel = get_kernel_release()
    packages = REQUIRED_PACKAGES + [f"linux-headers-{kernel}"]

    ui.step_header("Step 1 · Installing build dependencies")

    with SpinnerContext("Updating apt package lists"):
        result = run_cmd(["apt-get", "update", "-qq"], critical=False)
    if result.returncode != 0:
        ui.warn("apt-get update had warnings — continuing anyway")
    else:
        ui.success("Package lists updated")

    with SpinnerContext(f"Installing {len(packages)} packages"):
        result = run_cmd(
            ["apt-get", "install", "-y", "-qq"] + packages,
            critical=True,
        )
    ui.success("All build dependencies installed")
    return True


def unload_conflicting_module() -> bool:
    ui.step_header("Step 2 · Unloading conflicting r8188eu module")

    with SpinnerContext("Removing kernel module r8188eu"):
        result = run_cmd(["rmmod", "r8188eu"], critical=False)

    if result.returncode == 0:
        ui.success("Module r8188eu unloaded")
    else:
        ui.info("Module r8188eu was not loaded — nothing to remove")
    return True


def blacklist_module() -> bool:
    ui.step_header("Step 3 · Blacklisting r8188eu")

    # Check if already blacklisted
    if os.path.isfile(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r") as fh:
            if BLACKLIST_LINE in fh.read():
                ui.info("r8188eu is already blacklisted — skipping")
                return True

    try:
        with open(BLACKLIST_FILE, "a") as fh:
            fh.write(f"{BLACKLIST_LINE}\n")
        ui.success(f"Wrote '{BLACKLIST_LINE}' → {BLACKLIST_FILE}")
    except OSError as exc:
        ui.error(f"Failed to write blacklist file: {exc}")
        return False
    return True


def clone_repository() -> bool:
    ui.step_header("Step 4 · Cloning driver source")

    if os.path.isdir(CLONE_DIR):
        ui.info(f"Removing old clone at {CLONE_DIR}")
        shutil.rmtree(CLONE_DIR)

    with SpinnerContext(f"Cloning {REPO_URL}"):
        run_cmd(["git", "clone", "--depth=1", REPO_URL, CLONE_DIR], critical=True)

    ui.success(f"Repository cloned → {CLONE_DIR}")
    return True


def compile_and_install() -> bool:
    ui.step_header("Step 5 · Compiling & installing driver")

    with SpinnerContext("Running make (this may take a few minutes)"):
        result = run_cmd(["make"], cwd=CLONE_DIR, critical=False)

    if result.returncode != 0:
        ui.error("Compilation failed — full output below:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return False

    ui.success("Compilation succeeded")

    with SpinnerContext("Running make install"):
        result = run_cmd(["make", "install"], cwd=CLONE_DIR, critical=False)

    if result.returncode != 0:
        ui.error("make install failed — full output below:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return False

    ui.success("Driver installed into kernel modules tree")
    return True


def load_new_module() -> bool:
    ui.step_header("Step 6 · Loading new driver")

    with SpinnerContext("Running depmod -a"):
        run_cmd(["depmod", "-a"], critical=True)

    with SpinnerContext("Loading 8188eu module"):
        result = run_cmd(["modprobe", "8188eu"], critical=False)

    if result.returncode == 0:
        ui.success("Module 8188eu loaded — adapter should be active")
    else:
        ui.warn("modprobe 8188eu failed — a reboot may be needed")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Graceful Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: (ui.warn("\nInterrupted by user"), sys.exit(130)))
    atexit.register(cleanup_clone_dir)

    ui.header("TP-Link TL-WN722N V2/V3  ·  RTL8188EUS Driver Installer")

    # Gate: root
    if not check_root():
        sys.exit(1)

    ui.info(f"Kernel: {get_kernel_release()}")
    ui.info(f"Python: {sys.version.split()[0]}")
    ui.info(f"Rich:   {'available' if RICH_AVAILABLE else 'not installed'}")

    # Run pipeline
    results: list[tuple[str, str]] = []
    steps: list[tuple[str, callable]] = [
        ("Install dependencies", install_dependencies),
        ("Unload conflicting module", unload_conflicting_module),
        ("Blacklist r8188eu", blacklist_module),
        ("Clone driver repository", clone_repository),
        ("Compile & install driver", compile_and_install),
        ("Load new kernel module", load_new_module),
    ]

    for label, step_fn in steps:
        ok = step_fn()
        results.append((label, "✓ Success" if ok else "✗ Failed"))
        if not ok:
            ui.error(f"Step '{label}' failed — aborting.")
            break

    # Summary
    ui.step_header("Done")
    ui.summary(results)

    all_ok = all("Success" in s for _, s in results)
    if all_ok:
        ui.success("Installation complete! Plug in your adapter or reboot to activate.")
    else:
        ui.warn("Installation finished with errors — review the output above.")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    # Handle missing rich at the very top for users who run the script directly
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
