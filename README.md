# MW Session Blocker

A lightweight utility to quickly block MotiveWave's license heartbeat, allowing you to use your license on another machine without having to close the app on your current one.

## How it works
MotiveWave pings its licensing server every 60 seconds. This tool simply adds a local block in your Windows `hosts` file to drop that connection. The server assumes your PC went offline and releases the license to your home PC. MotiveWave keeps running perfectly fine offline in the background on your laptop.

## Usage
1. Go to the `release` folder and download `MW Session Blocker.exe`.
2. Right-click the `.exe` and select **Run as Administrator** (it requires admin privileges to edit the Windows network hosts file).
3. Click **Drop Connection** when you leave the office.
4. Click **Restore Connection** when you return.

## Build from Source
If you prefer to compile the python script yourself:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --uac-admin --name "MW Session Blocker" src/mw_killswitch.py
```
