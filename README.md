### Kingdom Hearts Linux

This Python script sets up and maintains an environment for playing the PC ports of the Kingdom Hearts games on a Linux machine.

Optional popular community tools and mods can also be downloaded, updated, and integrated.

All changes are isolated from your base game install files and are fully reversible. Your configuration is declarative, and the script will update your environment to match your configuration each time it is run.

Windows is also supported. Although the games run natively on Windows, this script can be helpful for automating installation, updating, and building of mods on all platforms. All the Linux-specific operations will be skipped.

### Instructions

**1. Dependencies**

First, you'll need to make sure you have all of these installed:

* **`uv`**: Required to run the script itself.
* **`wine`**: Required for running Windows programs such as the Kingdom Hearts games on Linux. `winetricks` and `wine-mono` are also required for these games.
* **`git`**: Used to download and update mod patches.

On Arch, this command should install all of them:

```sh
sudo pacman -S uv wine winetricks wine-mono git
```

**2. Clone and First Run**

Clone or download this repo wherever you like:

```sh
git clone https://github.com/tryashtar/kingdom-hearts-linux
```

And run it:

```sh
uv run update.py
```

First, it will ask you to input the folders where your games are installed. If you haven't installed them yet, you can run the installers through Wine. They don't need to go in your wineprefix; you can put them anywhere.

It will then ask a few more questions, and allow you to add optional features like mods.

**3. Subsequent Runs**

The created `settings.yaml` file stores all of your settings, and file paths for where the script should put its isolated files. You can change them at any time.

Running the script at any time in the future will check online to download updates for all downloaded features, and update all integrations to reflect changes to your settings. It will also automatically build your selected mods.

**4. Starting the Game**

Once the script is finished, simple scripts should be created in a `launch` folder that can be used to launch each game. Have fun!

### Features

All features are downloaded into their own folders, and *symlinked* into the game installation folders when necessary. This makes everything self-contained, and easy to update or remove.

**Required to Run on Linux**

Dedicated wineprefixs are created. The necessary dependencies are installed.

**Optional Additions**

[OpenKh Mod Manager](https://openkh.dev/tool/GUI.ModsManager): Will be downloaded and updated. Its `mods` folder will be symlinked out for convenience, and all git-based mods inside will be updated and built. If Panacea is selected, the necessary DLLs will be symlinked into the install folders.

[LuaBackend](https://github.com/Sirius902/LuaBackend): Will be downloaded and updated. The DLLs will be symlinked into the install folders. The configuration will be updated to include loading scripts from OpenKH mod folders.

For convenience and by default, a `Save Data` folder is created to hold your game saves. The paths in the wineprefix's `Documents` folder are symlinked to it. Additionally, small scripts to launch each game are created in a `launch` folder. The locations of these can be customized or disabled altogether.
