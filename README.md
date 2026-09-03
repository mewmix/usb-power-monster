# USB Power Monster

Cross-platform USB storage power-state torture harness 

## Targets

- USB 3.x U0/U1/U2/U3 behavior
- USB 2.0 L1 and selective suspend
- suspend/resume abuse around real file I/O
- SHA-256 integrity verification before and after every transition
- wake latency and I/O latency measurement
- JSONL per-iteration evidence
- Linux kernel and Windows event/ETW failure capture
- Linux sysfs LPM/runtime-suspend controls
- Windows USBLPM U1/U2 control when available

The default workload operates only inside `.usb-power-monster` beneath a user-selected mounted DUT directory. Raw-device destructive writes are intentionally not part of the initial harness.

## Install

```bash
python -m pip install -e .
```

## Linux

```bash
sudo usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/2-3 \
  --states U1,U2,U3 \
  --cycles 10000 \
  --payload-mib 256 \
  --idle-ms 100
```

For USB2:

```bash
sudo usb-power-monster /mnt/dut \
  --sysfs-device /sys/bus/usb/devices/1-3 \
  --states L1,SUSPEND \
  --cycles 10000
```

## Windows

Run from an elevated PowerShell or Command Prompt.

### Microsoft MUTT / USBLPM prerequisite

Explicit U1/U2 control requires Microsoft's `UsbLPM.exe`. USBLPM is distributed as part of the official **MUTT USB Tool** package; do not download `UsbLPM.exe` from third-party mirrors.

Official Microsoft download:

- https://www.microsoft.com/en-us/download/details.aspx?id=51604
- Current package at the time of writing: **MUTT USB Tool 3.0.0** (`MUTTPackage-3_0_0.msi`)

The standard USBTest install provides architecture-specific copies at:

```text
C:\Program Files (x86)\USBTest\x64\UsbLPM.exe
C:\Program Files (x86)\USBTest\x86\UsbLPM.exe
C:\Program Files (x86)\USBTest\arm\UsbLPM.exe
```

Use the executable matching the host architecture. For normal 64-bit Windows systems, use the `x64` copy.

If necessary, discover the installed copies with:

```powershell
Get-ChildItem "C:\Program Files*" -Recurse -Filter UsbLPM.exe -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName
```

Example for 64-bit Windows:

```powershell
python -m usb_power_monster.cli E:\ `
  --usblpm "C:\Program Files (x86)\USBTest\x64\UsbLPM.exe" `
  --states U1,U2,U3 `
  --cycles 10000 `
  --payload-mib 256
```

Microsoft's current MUTT download page lists Windows 10 and Windows 11 support. The separate legacy USBLPM documentation still describes USBLPM as Windows 8-only, so treat USBLPM availability and behavior on newer Windows builds as something the harness must detect and report rather than assume.

## Evidence discipline

The harness distinguishes:

- `requested` — the host/tool requested or enabled a state;
- `host-reported` — the OS reported a runtime/suspend state;
- `observed` — reserved for trace/analyzer evidence proving physical link state;
- `inferred` — behavior suggests a transition but does not prove it.

It therefore will not claim that enabling U1/U2 or selective suspend proves that the wire actually entered U1/U2/U3.

See [docs/CRUSADE.md](docs/CRUSADE.md) for the full A/B regression methodology and escalation plan.
