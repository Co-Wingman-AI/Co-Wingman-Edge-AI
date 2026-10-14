# Run the inventory on the Jetson

The inventory script installs nothing, records no audio, changes no power or
clock settings, and does not use `sudo`.

## 1. Move the drive from macOS

Close files and terminals using the project. In Finder, click the eject icon
beside the USB drive and wait for it to disappear before disconnecting it.
Do not unplug it while files are being written.

## 2. Locate it on Jetson Linux

Connect the drive, open a terminal, and inspect mounted filesystems:

```sh
lsblk -f
findmnt
```

Typical removable-media paths are under `/media/<user>/`, but use the path
shown on your Jetson; do not copy that placeholder literally.

## 3. Enter the project and run the script

Quote the path in case the drive label contains spaces:

```sh
cd "/path/to/Co-Wingman-jetson"
python3 scripts/jetson_inventory.py
```

No virtual environment or installed Python packages are required. The command
prints the two exact report paths it created. It is safe for unavailable Jetson
utilities to be reported as `not detected`.

## 4. Review the reports

```sh
ls -lh reports/jetson_inventory_*.md reports/jetson_inventory_*.json
```

Bring back both files with the same timestamp:

- `reports/jetson_inventory_YYYYMMDD_HHMMSS.md`
- `reports/jetson_inventory_YYYYMMDD_HHMMSS.json`

The script redacts common identifiers, but review the Markdown report before
sharing or committing it.

## 5. Safely remove the drive

Leave the project directory, flush pending writes, identify the correct mount
point with `findmnt`, and unmount that exact mount point:

```sh
cd /
sync
udisksctl unmount -b /dev/<usb-partition>
udisksctl power-off -b /dev/<usb-device>
```

Replace both placeholders using `lsblk -f`. Never guess a device name. If
`udisksctl` is unavailable, use the desktop file manager's eject control.
Wait for confirmation before disconnecting the drive, then reconnect it to the
Mac and provide both timestamp-matched reports to Codex.
