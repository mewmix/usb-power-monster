# The Crusade

USB Power Monster exists to answer a narrow engineering question with unreasonable confidence:

> Did a USB power-management configuration actually fix the state machine, or did it merely hide the failing path?

## Evidence rule

The harness never equates configuration with physical link-state proof.

- `requested`: host/tool asked for or enabled a state.
- `host-reported`: operating system reports a suspend/runtime state.
- `observed`: reserved for trace/analyzer integration that proves the link state.
- `inferred`: I/O or another side effect suggests a state change, but does not prove it.

A compliance-style statement such as `U2 PASS` should only be made from observed evidence or an external compliance result. The harness itself reports exactly what it knows.

## Primary campaigns

### USB 3.x

Run each independently, then mixed:

1. U1 only: U1 enabled, U2 disabled.
2. U2 only: U1 disabled, U2 enabled.
3. U1 + U2 mixed idle/wake cycles.
4. U3/selective suspend: runtime/device selective suspend followed by immediate I/O.
5. U0 control: LPM disabled where controllable.

### USB 2.0

1. L1 enabled/disabled A/B on Linux xHCI.
2. Selective/runtime suspend.
3. Immediate read/write/hash verification after wake.

## Per-transition workload

Every transition performs:

1. full-file SHA-256 verification before the transition;
2. configure/request the target power state;
3. idle interval;
4. collect state evidence;
5. wake using real disk I/O;
6. measure wake-to-I/O latency;
7. modify a deterministic 4 KiB region;
8. `fsync` by default;
9. full-file SHA-256 verification;
10. append an fsync'd JSONL record;
11. capture kernel/system USB diagnostics on failure.

A test-file workload is deliberate: it is destructive to its own file but not to the disk, partition table, filesystem metadata outside its directory, or unrelated user data.

## Linux

Install:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Find the DUT:

```bash
lsusb
lsusb -t
```

Then inspect `/sys/bus/usb/devices` and identify the physical USB device path, for example `2-3`.

USB 3 campaign:

```bash
sudo .venv/bin/usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/2-3 \
  --states U1,U2,U3 \
  --cycles 10000 \
  --payload-mib 256 \
  --idle-ms 100
```

USB 2 campaign:

```bash
sudo .venv/bin/usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/1-3 \
  --states L1,SUSPEND \
  --cycles 10000 \
  --payload-mib 256
```

Linux exposes U1/U2/L1 enablement controls where the host/device/kernel support them. Runtime status can provide host-side evidence for selective suspend. U1/U2/L1 physical entry should ultimately be correlated with xHCI tracepoints or a protocol analyzer.

## Windows

Run from an elevated terminal.

### Install Microsoft MUTT / USBLPM

USBLPM is optional for campaigns that do not require explicit U1/U2 control, but it is required by the current Windows backend when `U1` or `U2` must be configured directly.

Microsoft distributes `UsbLPM.exe` inside the official **MUTT USB Tool** package:

- Official download: https://www.microsoft.com/en-us/download/details.aspx?id=51604
- Current package at the time of writing: **MUTT USB Tool 3.0.0**
- Installer: `MUTTPackage-3_0_0.msi`

Use the Microsoft package rather than copying `UsbLPM.exe` from an unknown or third-party source.

After installation, locate the executable if its path is not obvious:

```powershell
Get-ChildItem "C:\Program Files*" -Recurse -Filter UsbLPM.exe -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName
```

Install USB Power Monster and run the campaign with the discovered path:

```powershell
py -m pip install -e .
usb-power-monster.exe E:\ `
  --usblpm "C:\path\to\UsbLPM.exe" `
  --states U1,U2,U3 `
  --cycles 10000 `
  --payload-mib 256 `
  --idle-ms 100
```

Microsoft's current MUTT download page lists Windows 10 and Windows 11 as supported operating systems. Microsoft's separate USBLPM documentation is older and still describes USBLPM as Windows 8-only. The harness must therefore detect whether USBLPM is present and working and must not infer support solely from the host Windows version.

The Windows backend starts an ETW trace containing USBXHCI, UCX, and USBHUB3 providers. Windows selective suspend is enabled for U3-oriented testing, but the harness does not falsely claim that changing the policy itself proves the physical link entered U3.

## A/B configuration campaign

Run exactly the same command twice:

- DUT old configuration
- DUT new configuration

Keep host, port, cable, firmware, filesystem, payload size, idle interval and cycle count fixed.

Compare:

- attempts / failures;
- integrity mismatches;
- enumeration or I/O failures;
- suspend timeouts;
- wake latency distribution;
- state evidence;
- kernel/ETW errors.

The desired result is not merely `new = 0 failures`. It is:

> The same low-power behavior remains enabled and evidenced, the old configuration fails reproducibly, the new configuration survives the same transition workload, and no integrity or adjacent-path regression is observed.

## Planned escalation

- randomized state machine (`U0→U1→U0→U2→U1→U3...`);
- randomized idle dwell distributions;
- concurrent random/sequential I/O workers;
- configurable queue depth and fio integration;
- UASP/BOT transport tagging;
- hot/warm/port-reset injection;
- detach/re-enumeration watchdog;
- Linux xHCI tracepoint parser;
- Windows ETW event parser;
- protocol-analyzer timestamp import;
- latency histograms and percentile summaries;
- environmental metadata: chamber temperature, VBUS, DUT serial/FW/configuration;
- deterministic reproduction files for every failure.
