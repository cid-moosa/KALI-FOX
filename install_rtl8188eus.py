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
import time
import itertools

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
    from rich.columns import Columns
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

TOTAL_STEPS = 6

# ── ASCII Art ─────────────────────────────────────────────────────────────────

LOGO_ART = r"""
 ██╗  ██╗ █████╗ ██╗     ██╗      ███████╗ ██████╗ ██╗  ██╗
 ██║ ██╔╝██╔══██╗██║     ██║      ██╔════╝██╔═══██╗╚██╗██╔╝
 █████╔╝ ███████║██║     ██║█████╗█████╗  ██║   ██║ ╚███╔╝
 ██╔═██╗ ██╔══██║██║     ██║╚════╝██╔══╝  ██║   ██║ ██╔██╗
 ██║  ██╗██║  ██║███████╗██║      ██║     ╚██████╔╝██╔╝ ██╗
 ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝      ╚═╝      ╚═════╝ ╚═╝  ╚═╝
"""

MODEL_ART = r"""
 ████████╗██╗           ██╗    ██╗███╗   ██╗ ███████╗██████╗ ██████╗ ███╗   ██╗
 ╚══██╔══╝██║           ██║    ██║████╗  ██║ ╚════██║╚════██╗╚════██╗████╗  ██║
    ██║   ██║      ████╗██║ █╗ ██║██╔██╗ ██║     ██╔╝ █████╔╝ █████╔╝██╔██╗ ██║
    ██║   ██║      ╚═══╝██║███╗██║██║╚██╗██║    ██╔╝ ██╔═══╝ ██╔═══╝ ██║╚██╗██║
    ██║   ███████╗      ╚███╔███╔╝██║ ╚████║    ██║  ███████╗███████╗██║ ╚████║
    ╚═╝   ╚══════╝       ╚══╝╚══╝ ╚═╝  ╚═══╝    ╚═╝  ╚══════╝╚══════╝╚═╝  ╚═══╝
"""

FOX_HAPPY = r"""
    /\   /\
   ( o . o )
   (  =^=  )   ✓ All done!
    (     )
     || ||
"""

FOX_SAD = r"""
    /\   /\
   ( x _ x )
   (  =^=  )   ✗ Something broke...
    (     )
     || ||
"""

FOX_WORKING = r"""
    /\   /\
   ( • . • )
   (  =^=  )   ⚙ Working...
    (     )
     || ||
"""

# ── TTY-aware output layer ────────────────────────────────────────────────────

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
    def header(_msg: str) -> None:
        print(LOGO_ART)
        print("  RTL8188EUS Driver Installer for Kali Linux")
        print("=" * 60)

    @staticmethod
    def step_header(msg: str) -> None:
        print(f"\n── {msg} ──")

    @staticmethod
    def phase(step: int, msg: str) -> None:
        bar = "█" * step + "░" * (TOTAL_STEPS - step)
        print(f"\n  [{bar}]  Phase {step}/{TOTAL_STEPS} — {msg}")

    @staticmethod
    def summary(rows: list[tuple[str, str]]) -> None:
        print("\n┌─────────────────────────────────────────────┐")
        for label, status in rows:
            tag = "✓" if "success" in status.lower() or "ok" in status.lower() else "✗"
            print(f"│  {tag}  {label:<28} {status:>10} │")
        print("└─────────────────────────────────────────────┘")

    @staticmethod
    def fox(variant: str = "happy") -> None:
        art = {"happy": FOX_HAPPY, "sad": FOX_SAD, "working": FOX_WORKING}
        print(art.get(variant, FOX_HAPPY))

    @staticmethod
    def disclaimer() -> None:
        print("\n┌────────────────────────────────────────────────────────────────┐")
        print("│                          DISCLAIMER                           │")
        print("│  Installs drivers for TP-Link TL-WN722N V2/V3 (RTL8188EUS).  │")
        print("│  Requires Kali Linux with root privileges.                    │")
        print("│  This will blacklist r8188eu and compile a new kernel module.  │")
        print("└────────────────────────────────────────────────────────────────┘")

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

    def header(self, _msg: str) -> None:
        # Animated logo reveal — line by line
        self.console.clear()
        logo_lines = LOGO_ART.strip().splitlines()
        for line in logo_lines:
            self.console.print(f"[bold bright_magenta]{line}[/bold bright_magenta]")
            time.sleep(0.08)

        time.sleep(0.3)

        subtitle = Text("RTL8188EUS Driver Installer for Kali Linux", style="bold bright_white")
        panel = Panel(
            Align.center(subtitle),
            border_style="bright_cyan",
            padding=(1, 2),
            title="[bold bright_magenta]🦊 KALI-FOX[/bold bright_magenta]",
            subtitle="[dim italic]v2.0 — Fully Automated[/dim italic]",
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
        table.add_column("Step", style="white", min_width=32)
        table.add_column("Result", justify="center", min_width=14)
        for label, status in rows:
            if "success" in status.lower() or "ok" in status.lower():
                color = "bold green"
                icon = "✅"
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
        art_map = {"happy": FOX_HAPPY, "sad": FOX_SAD, "working": FOX_WORKING}
        art = art_map.get(variant, FOX_HAPPY)
        color = {"happy": "bright_green", "sad": "bright_red", "working": "bright_cyan"}.get(variant, "white")

        fox_lines = art.strip().splitlines()
        for line in fox_lines:
            self.console.print(f"  [bold {color}]{line}[/bold {color}]")
            time.sleep(0.12)
        self.console.print()

    def disclaimer(self) -> None:
        disclaimer_text = (
            "[bold white]Installs drivers for TP-Link TL-WN722N V2/V3 (RTL8188EUS).[/bold white]\n"
            "[dim]Requires Kali Linux with root privileges.[/dim]\n"
            "[dim]This will blacklist r8188eu and compile a new kernel module.[/dim]"
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
                live.update(
                    Text.from_markup(f"  {globe}  [bold cyan]{message}[/bold cyan]")
                )
                time.sleep(0.15)

    def model_banner(self) -> None:
        """Show the adapter model ASCII art with animation."""
        self.console.print()
        for line in MODEL_ART.strip().splitlines():
            self.console.print(f"[bold bright_cyan]{line}[/bold bright_cyan]")
            time.sleep(0.06)
        self.console.print()


# Choose printer based on environment
ui: "PlainPrinter | RichPrinter"
if RICH_AVAILABLE and IS_TTY:
    ui = RichPrinter()
else:
    ui = PlainPrinter()


# ── Spinner context manager (degrades to plain text) ──────────────────────────
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
        ui.error("This script must be run as root.")
        ui.info("Re-run with: sudo python3 install_rtl8188eus.py")
        return False
    return True


def install_dependencies() -> bool:
    kernel = get_kernel_release()
    packages = REQUIRED_PACKAGES + [f"linux-headers-{kernel}"]

    ui.phase(1, "Installing build dependencies")
    ui.step_header("Step 1 · Installing build dependencies")

    with SpinnerContext("Updating apt package lists", spinner="earth"):
        result = run_cmd(["apt-get", "update", "-qq"], critical=False)
    if result.returncode != 0:
        ui.warn("apt-get update had warnings — continuing anyway")
    else:
        ui.success("Package lists updated")

    with SpinnerContext(f"Installing {len(packages)} packages", spinner="bouncingBar"):
        result = run_cmd(
            ["apt-get", "install", "-y", "-qq"] + packages,
            critical=True,
        )
    ui.success("All build dependencies installed")
    return True


def unload_conflicting_module() -> bool:
    ui.phase(2, "Unloading conflicting module")
    ui.step_header("Step 2 · Unloading conflicting r8188eu module")

    with SpinnerContext("Removing kernel module r8188eu", spinner="toggle"):
        result = run_cmd(["rmmod", "r8188eu"], critical=False)

    if result.returncode == 0:
        ui.success("Module r8188eu unloaded")
    else:
        ui.info("Module r8188eu was not loaded — nothing to remove")
    return True


def blacklist_module() -> bool:
    ui.phase(3, "Blacklisting driver")
    ui.step_header("Step 3 · Blacklisting r8188eu")

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
    ui.phase(4, "Cloning driver source")
    ui.step_header("Step 4 · Cloning driver source")

    if os.path.isdir(CLONE_DIR):
        ui.info(f"Removing old clone at {CLONE_DIR}")
        shutil.rmtree(CLONE_DIR)

    # Globe spin animation while cloning
    if hasattr(ui, "globe_spin"):
        ui.globe_spin("Downloading driver source from GitHub", duration=1.5)

    with SpinnerContext(f"Cloning {REPO_URL}", spinner="dots12"):
        run_cmd(["git", "clone", "--depth=1", REPO_URL, CLONE_DIR], critical=True)

    ui.success(f"Repository cloned → {CLONE_DIR}")
    return True


def compile_and_install() -> bool:
    ui.phase(5, "Compiling & installing driver")
    ui.step_header("Step 5 · Compiling & installing driver")

    # Show the working fox
    if hasattr(ui, "fox"):
        ui.fox("working")

    # ── Kernel 7.x fix: ensure the repo's include/ dir is on the compiler path ──
    include_dir = os.path.join(CLONE_DIR, "include")
    makefile_path = os.path.join(CLONE_DIR, "Makefile")

    if os.path.isdir(include_dir) and os.path.isfile(makefile_path):
        with open(makefile_path, "r") as fh:
            makefile_text = fh.read()
        patch_line = "EXTRA_CFLAGS += -I$(src)/include"
        if patch_line not in makefile_text:
            ui.info("Patching Makefile with include path for kernel compat")
            with open(makefile_path, "a") as fh:
                fh.write(f"\n# -- KALI-FOX patch: explicit include path for kernel 7.x --\n")
                fh.write(f"{patch_line}\n")

    extra_cflags = f"EXTRA_CFLAGS=-I{include_dir}"

    with SpinnerContext("Running make — compiling kernel module", spinner="bouncingBall"):
        result = run_cmd(["make", extra_cflags], cwd=CLONE_DIR, critical=False)

    if result.returncode != 0:
        ui.error("Compilation failed — full output below:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return False

    ui.success("Compilation succeeded")

    with SpinnerContext("Running make install", spinner="arrow3"):
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
    ui.phase(6, "Loading new driver")
    ui.step_header("Step 6 · Loading new driver")

    with SpinnerContext("Running depmod -a", spinner="simpleDots"):
        run_cmd(["depmod", "-a"], critical=True)

    with SpinnerContext("Loading 8188eu module", spinner="toggle2"):
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

    # ── Animated intro sequence ──
    ui.header("KALI-FOX")

    # Show adapter model banner
    if hasattr(ui, "model_banner"):
        ui.model_banner()

    # Disclaimer
    ui.disclaimer()

    # Typewriter system info
    kernel = get_kernel_release()
    python_ver = sys.version.split()[0]
    rich_status = "available ✓" if RICH_AVAILABLE else "not installed"

    ui.typewriter(f"  ▸ Kernel:  {kernel}")
    ui.typewriter(f"  ▸ Python:  {python_ver}")
    ui.typewriter(f"  ▸ Rich:    {rich_status}")
    ui.typewriter(f"  ▸ Target:  RTL8188EUS (TL-WN722N V2/V3)")

    time.sleep(0.5)

    # Gate: root
    if not check_root():
        sys.exit(1)

    ui.success("Running as root — full access granted")
    time.sleep(0.3)

    # Run pipeline — fully automated, no prompts
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

    # ── Finale ──
    if RICH_AVAILABLE and IS_TTY:
        console = Console()
        console.print()
        console.print(Rule("[bold bright_cyan]Installation Complete[/bold bright_cyan]", style="bright_magenta"))

    ui.summary(results)

    all_ok = all("Success" in s for _, s in results)

    if all_ok:
        ui.fox("happy")
        ui.success("Installation complete! Plug in your adapter or reboot to activate.")

        # Auto-reboot prompt
        if RICH_AVAILABLE and IS_TTY:
            console = Console()
            console.print()
            console.print(
                "  [bold bright_yellow]⚡ A reboot is recommended to load the new driver.[/bold bright_yellow]"
            )
            console.print(
                "  [dim]The system will reboot in 10 seconds. Press Ctrl+C to cancel.[/dim]"
            )
            console.print()
            try:
                for i in range(10, 0, -1):
                    console.print(f"\r  [bold bright_magenta]Rebooting in {i}...[/bold bright_magenta]", end="")
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
                    print(f"\r  Rebooting in {i}...", end="")
                    time.sleep(1)
                print()
                subprocess.run(["reboot"])
            except KeyboardInterrupt:
                print()
                ui.info("Reboot cancelled — you can reboot manually later.")
    else:
        ui.fox("sad")
        ui.warn("Installation finished with errors — review the output above.")

    sys.exit(0 if all_ok else 1)


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
