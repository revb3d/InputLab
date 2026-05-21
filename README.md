# InputLab

A small Windows desktop app that lets you bind a global hotkey to toggle another key into a held-down state.

It also includes a separate controller-macro tab that loops virtual Xbox button presses while your keyboard hold feature keeps running.

Example:

- Press `F2` once to hold `M`
- Press `F2` again to release `M`

## Run it

1. Do not double-click `app.py`
2. Double-click [OPEN_ME_FIRST.bat](D:\Downloads\autokeyhold\OPEN_ME_FIRST.bat) or [run.bat](D:\Downloads\autokeyhold\run.bat)
3. Wait for the dependencies to install the first time
4. Change the toggle hotkey and target key in the app if you want

## Controller macro tab

1. Open the `Controller Macro` tab
2. Set a macro toggle hotkey such as `F3`
3. Add one or more Xbox button steps like `A`, `RB`, or `DPAD_DOWN`
4. Set how long each button is held and the delay after each step
5. Click `Apply Macro`
6. Press your macro hotkey to start the loop, then press it again to stop

## Build an EXE

1. Double-click [build_exe.bat](D:\Downloads\autokeyhold\build_exe.bat)
2. When it finishes, open `dist\InputLab\`
3. Run `InputLab.exe`

## Build an installer

1. Double-click [build_installer.bat](D:\Downloads\autokeyhold\build_installer.bat)
2. When it finishes, open `installer-dist\`
3. Send `InputLabSetup.exe` to your friend
4. They run the installer, then launch the app from the Start menu or desktop shortcut

## In-app update checker

1. Host [update.json](D:\Downloads\autokeyhold\update.json) in your GitHub repo
2. Put your latest installer URL in its `download_url`
3. Installed copies automatically check the manifest on launch
4. Click `Update now` when a newer version is found

Example manifest fields:

- `version`: latest app version string like `1.0.1`
- `download_url`: direct link to the newest installer
- `notes`: optional short message shown in the app

GitHub manifest URL for this app:

- `https://raw.githubusercontent.com/revb3d/InputLab/main/update.json`

## Installer note

- The packaged app includes the `vgamepad` controller files during the installer build, so always rebuild the installer after controller-macro changes before sharing it.

## Notes

- The app uses the Python `keyboard` package for global hotkeys and key press simulation
- The controller macro uses `vgamepad`, which creates a virtual Xbox 360 controller
- When `vgamepad` installs on Windows, it prompts for the ViGEmBus driver required for virtual controller input
- On some systems, global keyboard hooks may work best when the app is launched with administrator permissions
- Your current mapping is saved in `config.json` after you click `Apply Mapping`
- If `app.py` does not open when double-clicked, that usually means Python file associations are missing on Windows. Use `OPEN_ME_FIRST.bat` instead.
