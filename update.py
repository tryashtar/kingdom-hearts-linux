import requests
import json
import zipfile
import shutil
import os
import subprocess
import datetime
import tomlkit
import yaml
import tempfile
import sqlite3
import time
import tarfile

def main():
   settings_path = os.path.join(os.path.dirname(__file__), 'settings.yaml')
   settings, changed = get_settings(settings_path)
   if changed:
      print('Settings changed!')
      print('Feel free to change your settings in \'settings.yaml\' now or any time.')
      print('Then run the script again to update your setup.')
      input()
      return
   if 'downloads' not in settings:
      settings['downloads'] = {}
   print('Starting!')
   symlinks = {}

   kh15_folder = settings['installs']['kh1.5+2.5']
   kh28_folder = settings['installs']['kh2.8']
   kh3_folder = settings['installs']['kh3']
   khmom_folder = settings['installs']['khmom']
   wineprefix = settings['wineprefix']
   runner = settings['runner']

   print('Checking for runner updates...')
   new_runner = download_latest(settings, 'runner', 'https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases/latest', lambda x: x['name'].endswith('.tar.xz'), True, settings['runner'], True)

   if settings.get('lutris') == True:
      lutris_config = os.path.expanduser('~/.config/lutris')
      lutris_local = os.path.expanduser('~/.local/share/lutris')
      symlinks[os.path.join(lutris_local, 'runners/wine/kingdom-hearts-x86_64')] = (runner, True)
      db_path = os.path.join(lutris_local, 'pga.db')
      if os.path.exists(db_path):
         database = sqlite3.connect(db_path)
         if kh15_folder is not None:
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-final-mix', 'Kingdom Hearts Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS FINAL MIX.exe'), True, True)
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-ii-final-mix', 'Kingdom Hearts II Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), True, True)
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-re-chain-of-memories', 'Kingdom Hearts Re:Chain of Memories', os.path.join(kh15_folder, 'KINGDOM HEARTS Re_Chain of Memories.exe'), True, True)
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-birth-by-sleep-final-mix', 'Kingdom Hearts Birth by Sleep Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS Birth by Sleep FINAL MIX.exe'), True, True)
         if kh28_folder is not None:
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-3d-dream-drop-distance', 'Kingdom Hearts 3D: Dream Drop Distance', os.path.join(kh28_folder, 'KINGDOM HEARTS Dream Drop Distance.exe'), False, True)
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-02-birth-by-sleep-a-fragmentary-passage', 'Kingdom Hearts 0.2 Birth by Sleep -A fragmentary passage-', os.path.join(kh28_folder, 'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe'), False, False)
         if kh3_folder is not None:
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-iii', 'Kingdom Hearts III', os.path.join(kh3_folder, 'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe'), False, False)
         if khmom_folder is not None:
            install_game_lutris(settings, lutris_config, database, wineprefix, 'kingdom-hearts-melody-of-memory', 'Kingdom Hearts Melody of Memory', os.path.join(khmom_folder, 'KINGDOM HEARTS Melody of Memory.exe'), False, False)

   symlinks[os.path.join(wineprefix, 'pfx')] = None
   if settings.get('heroic') == True:
      symlinks[os.path.join(wineprefix, 'pfx')] = (wineprefix, True)
      heroic_config = os.path.expanduser('~/.config/heroic')
      library_path = os.path.join(heroic_config, 'sideload_apps/library.json')
      if not os.path.exists(library_path):
         with open(library_path, 'w') as library_file:
            json.dump({"games":[]}, library_file)
      changes = False
      with open(library_path, 'r') as library_file:
         library = json.load(library_file)
         if kh15_folder is not None:
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-final-mix', 'Kingdom Hearts Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS FINAL MIX.exe'), True, True)
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-ii-final-mix', 'Kingdom Hearts II Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), True, True)
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-re-chain-of-memories', 'Kingdom Hearts Re:Chain of Memories', os.path.join(kh15_folder, 'KINGDOM HEARTS Re_Chain of Memories.exe'), True, True)
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-birth-by-sleep-final-mix', 'Kingdom Hearts Birth by Sleep Final Mix', os.path.join(kh15_folder, 'KINGDOM HEARTS Birth by Sleep FINAL MIX.exe'), True, True)
         if kh28_folder is not None:
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-3d-dream-drop-distance', 'Kingdom Hearts 3D: Dream Drop Distance', os.path.join(kh28_folder, 'KINGDOM HEARTS Dream Drop Distance.exe'), False, True)
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-02-birth-by-sleep-a-fragmentary-passage', 'Kingdom Hearts 0.2 Birth by Sleep -A fragmentary passage-', os.path.join(kh28_folder, 'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe'), False, False)
         if kh3_folder is not None:
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-iii', 'Kingdom Hearts III', os.path.join(kh3_folder, 'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe'), False, False)
         if khmom_folder is not None:
            changes |= install_game_heroic(settings, heroic_config, library, wineprefix, runner, 'kingdom-hearts-melody-of-memory', 'Kingdom Hearts Melody of Memory', os.path.join(khmom_folder, 'KINGDOM HEARTS Melody of Memory.exe'), False, False)
      if changes:
         with open(library_path, 'w') as library_file:
            json.dump(library, library_file)
   
   user_folder = os.path.join(wineprefix, 'drive_c/users', os.getlogin())
   if not os.path.exists(user_folder):
      print('Initializing wineprefix')
      os.makedirs(wineprefix, exist_ok=True)
      subprocess.run('wineboot', env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
   if settings['mods'].get('refined') is not None and not os.path.exists(os.path.join(wineprefix, 'drive_c/windows/dotnet48.installed.workaround')):
      print('Installing dotnet to wineprefix')
      subprocess.run(['winetricks', '-q', 'dotnet20', 'dotnet48'], env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
   if (kh3_folder is not None or kh28_folder is not None) and (new_runner or not os.path.exists(os.path.join(wineprefix, 'drive_c/windows/system32/sqmapi.dll'))):
      print('Running mf-install to fix KH3/KH2.8')
      mfinstall_folder = tempfile.mkdtemp()
      subprocess.run(['git', 'clone', 'https://github.com/z0z0z/mf-install', mfinstall_folder], check=True)
      env = os.environ.copy()
      env['PATH'] = f'{runner}/bin:{env["PATH"]}'
      env['WINEPREFIX'] = wineprefix
      subprocess.run(['wineserver', '-w'], check=True)
      subprocess.run(['wineserver', '-w'], env=env, check=True)
      subprocess.run(['/bin/sh', os.path.join(mfinstall_folder, 'mf-install.sh')], env=env, check=True)
      shutil.rmtree(mfinstall_folder)
   symlinks[os.path.join(user_folder, 'Documents')] = None
   symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638')] = None
   symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638')] = None
   symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638')] = None
   symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638')] = None
   symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638')] = None
   symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store')] = None
   if (save := settings['saves']['kh1.5+2.5']) is not None and kh15_folder is not None:
      os.makedirs(save, exist_ok=True)
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638')] = (save, True)
      if settings['mods'].get('refined') is not None:
         symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638')] = (save, True)
         symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638')] = (save, True)
   if (save := settings['saves']['kh2.8']) is not None and kh28_folder is not None:
      os.makedirs(save, exist_ok=True)
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638')] = (save, True)
   if (save := settings['saves']['kh3']) is not None and kh3_folder is not None:
      os.makedirs(save, exist_ok=True)
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638')] = (save, True)
   if (save := settings['saves']['khmom']) is not None and khmom_folder is not None:
      os.makedirs(save, exist_ok=True)
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store')] = (save, True)
   
   backup_vanilla = False
   if kh15_folder is not None:
      epic_folder = os.path.join(kh15_folder, 'EPIC')
      if os.path.exists(epic_folder) and len(os.listdir(epic_folder)) > 0:
         print('Renaming KH 1.5+2.5 EPIC folder to EPIC.bak to prevent crashes during FMVs')
         os.rename(epic_folder, os.path.join(kh15_folder, 'EPIC.bak'))
      symlinks[os.path.join(kh15_folder, 'x64')] = None
      symlinks[os.path.join(kh15_folder, 'Keystone.Net.dll')] = None
      symlinks[os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')] = None
      symlinks[os.path.join(kh15_folder, 'reFined.ini')] = None
      symlinks[os.path.join(kh15_folder, 'version.dll')] = None
      symlinks[os.path.join(kh15_folder, 'panacea_settings.txt')] = None
      symlinks[os.path.join(kh15_folder, 'DINPUT8.dll')] = None
      symlinks[os.path.join(kh15_folder, 'lua54.dll')] = None
      symlinks[os.path.join(kh15_folder, 'LuaBackend.toml')] = None
   if kh28_folder is not None:
      epic_folder = os.path.join(kh28_folder, 'EPIC')
      if os.path.exists(epic_folder) and len(os.listdir(epic_folder)) > 0:
         print('Renaming KH 2.8 EPIC folder to EPIC.bak to prevent crashes during FMVs')
         os.rename(epic_folder, os.path.join(kh28_folder, 'EPIC.bak'))
      symlinks[os.path.join(kh28_folder, 'DINPUT8.dll')] = None
      symlinks[os.path.join(kh28_folder, 'lua54.dll')] = None
      symlinks[os.path.join(kh28_folder, 'LuaBackend.toml')] = None

   openkh_folder = settings['mods'].get('openkh')
   mods_folder = settings['mods'].get('folder')
   if openkh_folder is not None:
      mods_manager = os.path.join(openkh_folder, 'mods-manager.yml')
      pana_settings = settings['mods'].get('panacea_settings')
      print('Checking for OpenKH updates...')
      downloaded = download_latest(settings, 'openkh', 'https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest', lambda x: x['name'] == 'openkh.zip', True, openkh_folder, False)
      if downloaded and not os.path.exists(mods_manager):
         print('Creating default OpenKH mod manager configuration')
         with open(mods_manager, 'w') as mods_file:
            yaml.dump({"gameEdition":2}, mods_file)
         if pana_settings is not None:
            if not os.path.exists(pana_settings):
               print('Creating default panacea configuration')
               with open(pana_settings, 'w') as pana_file:
                  mod_path = os.path.join(openkh_folder, 'mod')
                  pana_file.write('mod_path=Z:' + mod_path.replace('/', '\\') + '\nshow_console=False')
      if os.path.exists(openkh_folder):
         if settings['mods'].get('panacea') == True and kh15_folder is not None:
            symlinks[os.path.join(kh15_folder, 'version.dll')] = (os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
            if pana_settings is not None:
               symlinks[os.path.join(kh15_folder, 'panacea_settings.txt')] = (pana_settings, False)
         symlinks[os.path.join(openkh_folder, 'mods')] = None
         if mods_folder is not None:
            os.makedirs(mods_folder, exist_ok=True)
            symlinks[os.path.join(openkh_folder, 'mods')] = (mods_folder, True)
         if os.path.exists(mods_manager):
            changes = False
            with open(mods_manager, 'r') as mods_file:
               mods_data = yaml.safe_load(mods_file)
            pc_release = 'Z:' + kh15_folder.replace('/','\\')
            if mods_data.get('pcReleaseLocation') != pc_release:
               print('Updating KH 1.5 install location in OpenKH mod manager')
               mods_data['pcReleaseLocation'] = pc_release
               changes = True
            panacea = settings['mods'].get('panacea') == True
            if mods_data.get('panaceaInstalled') != panacea:
               print('Updating panacea install status in OpenKH mod manager')
               mods_data['panaceaInstalled'] = panacea
               changes = True
            if changes:
               with open(mods_manager, 'w') as mods_file:
                  yaml.dump(mods_data, mods_file, sort_keys=False)

      def download_mod(repo):
         if openkh_folder is None:
            return
         if mods_folder is not None:
            patch_folder = os.path.join(mods_folder, f'kh2/{repo}')
         else:
            patch_folder = os.path.join(openkh_folder, f'mods/kh2/{repo}')
         if not os.path.exists(patch_folder):
            print(f'Downloading mod {repo}')
            subprocess.run(['git', 'clone', f'https://github.com/{repo}', '--recurse-submodules', patch_folder], check=True)
         mod_changes[repo] = True

      mod_changes = {'KH2FM-Mods-Num/GoA-ROM-Edition': False, 'KH-ReFined/KH2-VanillaOST': False, 'KH-ReFined/KH2-VanillaEnemy': False, 'KH-ReFined/KH2-MultiAudio': False, 'KH-ReFined/KH2-MAIN': False}
      if (refined_folder := settings['mods'].get('refined')) is not None:
         print('Checking for ReFined updates...')
         download_latest(settings, 'refined', 'https://api.github.com/repos/TopazTK/KH-ReFined/releases', lambda x: x['name'].endswith('.zip'), False, refined_folder, False)
         download_mod('KH-ReFined/KH2-MAIN')
         if settings['mods'].get('refined.vanilla_ost') == True:
            download_mod('KH-ReFined/KH2-VanillaOST')
         if settings['mods'].get('refined.vanilla_enemies') == True:
            download_mod('KH-ReFined/KH2-VanillaEnemy')
         if settings['mods'].get('refined.multi_audio') == True:
            download_mod('KH-ReFined/KH2-MultiAudio')
         if os.path.exists(refined_folder) and kh15_folder is not None:
            symlinks[os.path.join(kh15_folder, 'x64')] = (os.path.join(refined_folder, 'x64'), True)
            symlinks[os.path.join(kh15_folder, 'Keystone.Net.dll')] = (os.path.join(refined_folder, 'Keystone.Net.dll'), False)
            symlinks[os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')] = (os.path.join(refined_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), False)
            if (refined_ini := settings['mods'].get('refined_config')) is not None:
               symlinks[os.path.join(kh15_folder, 'reFined.ini')] = (refined_ini, False)
            backup_vanilla = True

      if (randomizer_folder := settings['mods'].get('randomizer')) is not None:
         print('Checking for Randomizer updates...')
         download_latest(settings, 'randomizer', 'https://api.github.com/repos/tommadness/KH2Randomizer/releases/latest', lambda x: x['name'] == 'Kingdom.Hearts.II.Final.Mix.Randomizer.zip', False, randomizer_folder, False)
         download_mod('KH2FM-Mods-Num/GoA-ROM-Edition')

      if os.path.exists(openkh_folder):
         mod_dir = os.path.join(openkh_folder, 'mods')
         if os.path.exists(mod_dir):
            for game in os.listdir(mod_dir):
               for parent in os.listdir(os.path.join(mod_dir, game)):
                  for repo in os.listdir(os.path.join(mod_dir, game, parent)):
                     if os.path.exists(os.path.join(mod_dir, game, parent, repo, '.git')):
                        print(f'Checking for updates for mod {parent}/{repo}')
                        subprocess.run(['git', 'pull', '--recurse-submodules'], cwd=os.path.join(mod_dir, game, parent, repo), check=True)
         enabled_mods = []
         enabled_mods_path = os.path.join(openkh_folder, 'mods-KH2.txt')
         if os.path.exists(enabled_mods_path):
            with open(enabled_mods_path, 'r') as enabled_file:
               enabled_mods = [line.rstrip('\n') for line in enabled_file]
         changes = False
         for mod,enabled in mod_changes.items():
            if enabled and mod not in enabled_mods:
               print(f'Enabling mod {mod}')
               enabled_mods.append(mod)
               changes = True
            elif not enabled and mod in enabled_mods:
               print(f'Disabling mod {mod}')
               enabled_mods.remove(mod)
               changes = True
         if changes:
            print('You still need to manually build/patch these changes in the OpenKH Mod Manager!')
            with open(enabled_mods_path, 'w') as enabled_file:
               for line in enabled_mods:
                  enabled_file.write(line + '\n')

   if (lua_folder := settings['mods'].get('luabackend')) is not None:
      print('Checking for LuaBackend updates...')
      toml_user = settings['mods'].get('luabackend_config')
      downloaded = download_latest(settings, 'luabackend', 'https://api.github.com/repos/Sirius902/LuaBackend/releases/latest', lambda x: x['name'] == 'DBGHELP.zip', False, lua_folder, False)
      if downloaded:
         toml_default = os.path.join(lua_folder, 'LuaBackend.toml')
         if toml_user is not None and not os.path.exists(toml_user):
            print('Creating default LuaBackend.toml configuration')
            shutil.copyfile(toml_default, toml_user)
         os.remove(toml_default)
      if os.path.exists(lua_folder):
         if kh15_folder is not None:
            symlinks[os.path.join(kh15_folder, 'DINPUT8.dll')] = (os.path.join(lua_folder, 'DBGHELP.dll'), False)
            symlinks[os.path.join(kh15_folder, 'lua54.dll')] = (os.path.join(lua_folder, 'lua54.dll'), False)
            if toml_user is not None:
               symlinks[os.path.join(kh15_folder, 'LuaBackend.toml')] = (toml_user, False)
         if kh28_folder is not None:
            symlinks[os.path.join(kh28_folder, 'DINPUT8.dll')] = (os.path.join(lua_folder, 'DBGHELP.dll'), False)
            symlinks[os.path.join(kh28_folder, 'lua54.dll')] = (os.path.join(lua_folder, 'lua54.dll'), False)
            if toml_user is not None:
               symlinks[os.path.join(kh28_folder, 'LuaBackend.toml')] = (toml_user, False)
      if toml_user is not None and openkh_folder is not None and os.path.exists(toml_user):
         with open(toml_user, 'r') as toml_file:
            toml_data = tomlkit.load(toml_file)
         changes = False
         for game in ['kh1', 'kh2', 'bbs', 'recom', 'kh3d']:
            if game in toml_data and 'scripts' in toml_data[game]:
               path = os.path.join(openkh_folder, 'mod', game, 'scripts') 
               windows_path = 'Z:' + path.replace('/', '\\')
               found = False
               for script in toml_data[game]['scripts']:
                  if script['path'] == windows_path:
                     found = True
                     break
               if not found:
                  changes = True
                  print(f'Adding OpenKH scripts folder \'{path}\' to LuaBackend configuration')
                  toml_data[game]['scripts'].append({'path':windows_path,'relative':False})
         if changes:
            with open(toml_user, 'w') as toml_file:
               tomlkit.dump(toml_data, toml_file)
   
   if kh15_folder is not None:
      backup_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX VANILLA.exe')
      launch_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')
      if backup_vanilla:
         if not os.path.exists(backup_path):
            print('Moving vanilla KH2 executable')
            os.rename(launch_path, backup_path)

   for (new, old) in symlinks.items():
      if old is None:
         remove_symlink(new)
      else:
         path, dir = old
         symlink(path, new, is_dir=dir)

   if kh15_folder is not None:
      backup_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX VANILLA.exe')
      launch_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')
      if not backup_vanilla:
         if os.path.exists(backup_path) and not os.path.exists(launch_path):
            print('Restoring vanilla KH2 executable')
            os.rename(backup_path, launch_path)

   with open(settings_path, 'w') as data_file:
      yaml.dump(settings, data_file, sort_keys=False)


def download_latest(settings, date_key, url, filter, has_extra_folder, destination_folder, is_tar):
   date = settings['downloads'].get(date_key)
   if date is not None:
      date = datetime.datetime.fromisoformat(date)
   rq = requests.get(url)
   if rq.status_code != 200:
      print(f'Error {rq.status_code}!')
      try:
         print(json.loads(rq.text)['message'])
      except:
         print(rq.text)
      return False
   if url.endswith('/releases'):
      newest = None
      release = None
      releases = json.loads(rq.text)
      for next in releases:
         release_time = datetime.datetime.fromisoformat(next['published_at'])
         if newest is None or release_time > newest:
            newest = release_time
            release = next
      if release is None:
         return False
   else:
      release = json.loads(rq.text)
   for asset in release['assets']:
      if not filter(asset):
         continue
      asset_date = datetime.datetime.fromisoformat(asset['updated_at'])
      if date is None or asset_date > date or not os.path.exists(destination_folder):
         print(f'Downloading update: {release["tag_name"]}')
         rq = requests.get(asset['browser_download_url'])
         if rq.status_code != 200:
            print(f'Error {rq.status_code}!')
            print(rq.text)
            return False
         temp_folder = tempfile.mkdtemp()
         temp_zip = os.path.join(temp_folder, f'{date_key}.zip')
         with open(temp_zip, 'wb') as file:
            file.write(rq.content)
         with (tarfile.open(temp_zip) if is_tar else zipfile.ZipFile(temp_zip, 'r')) as zip:
            if has_extra_folder:
               temp_extract = os.path.join(temp_folder, date_key)
               zip.extractall(temp_extract)
               shutil.copytree(os.path.join(temp_extract, os.listdir(temp_extract)[0]), destination_folder, dirs_exist_ok=True)
            else:
               zip.extractall(destination_folder)
         shutil.rmtree(temp_folder)
         settings['downloads'][date_key] = asset_date.isoformat()
         return True
   return False

def install_game_heroic(settings, config_folder, library, wineprefix, runner, id, name, path, has_panacea, has_luabackend):
   game_path = os.path.join(config_folder, 'GamesConfig', f'{id}.json')
   if not os.path.exists(game_path):
      print(f'Adding \'{name}\' to Heroic')
      with open(game_path, 'w') as game_file:
         json.dump({id:{"wineVersion":{"name":"Kingdom Hearts Runner","type":"wine"}},"explicit":True}, game_file)
   changes = False
   with open(game_path, 'r') as game_file:
      data = json.load(game_file)
   if 'bin' not in data[id]['wineVersion'] or data[id]['wineVersion']['bin'] != os.path.join(runner, 'bin/wine'):
      print(f'Updating \'{name}\' runner in Heroic to \'{runner}\'')
      data[id]['wineVersion']['bin'] = os.path.join(runner, 'bin/wine')
      data[id]['wineVersion']['wineserver'] = os.path.join(runner, 'bin/wineserver')
      data[id]['wineVersion']['wineboot'] = os.path.join(runner, 'bin/wineboot')
      changes = True
   if 'winePrefix' not in data[id] or data[id]['winePrefix'] != wineprefix:
      print(f'Updating \'{name}\' wineprefix in Heroic to \'{wineprefix}\'')
      data[id]['winePrefix'] = wineprefix
      changes = True
   overrides = []
   if 'environmentOptions' in data[id]:
      for opt in data[id]['environmentOptions']:
         if opt['key'] == 'WINEDLLOVERRIDES':
            overrides = opt['value'].split(';')
            data[id]['environmentOptions'].remove(opt)
            break
   if has_panacea:
      pana = settings['mods'].get('panacea') == True
      if pana and 'version=n,b' not in overrides:
         print(f'Adding Panacea DLL override in Heroic for \'{name}\'')
         overrides.append('version=n,b;')
         changes = True
      if not pana and 'version=n,b' in overrides:
         print(f'Removing Panacea DLL override from Heroic for \'{name}\'')
         overrides.remove('version=n,b;')
         changes = True
   if has_luabackend:
      lua = settings['mods'].get('luabackend') is not None
      if lua and 'dinput8=n,b' not in overrides:
         print(f'Adding LuaBackend DLL override in Heroic for \'{name}\'')
         overrides.append('dinput8=n,b;')
         changes = True
      if not lua and 'dinput8=n,b' in overrides:
         print(f'Removing LuaBackend DLL override from Heroic for \'{name}\'')
         overrides.remove('dinput8=n,b;')
         changes = True
   if len(overrides) > 0:
      if 'environmentOptions' not in data[id]:
         data[id]['environmentOptions'] = []
      data[id]['environmentOptions'].append({"key":"WINEDLLOVERRIDES","value":';'.join(overrides)})
   if changes:
      with open(game_path, 'w') as game_file:
         json.dump(data, game_file)
   game = None
   library_changes = False
   for entry in library['games']:
      if entry['app_name'] == id:
         game = entry
         break
   if game is None:
      game = {"runner":"sideload","app_name":id,"title":name,"install":{"platform":"Windows","is_dlc":False},"folder_name":os.path.dirname(path),"is_installed":True,"canRunOffline":True}
      library['games'].append(game)
      library_changes = True
   if 'executable' not in game['install'] or game['install']['executable'] != path:
      print(f'Updating \'{name}\' executable in Heroic to \'{path}\'')
      game['install']['executable'] = path
   return library_changes

def install_game_lutris(settings, config_folder, database, wineprefix, id, name, path, has_panacea, has_luabackend):
   config_path = os.path.join(config_folder, 'games', id + '.yml')
   if not os.path.exists(config_path):
      print(f'Adding \'{name}\' to Lutris')
      with open(config_path, 'w') as config_file:
         yaml.dump({"game":{},"system":{},"wine":{"version":"kingdom-hearts-x86_64"}}, config_file)
      data = {"name":name,"slug":id,"platform":"Windows","runner":"wine","directory":"","installed":1,"installed_at":int(time.time()),"configpath":id,"hidden":0}
      cursor = database.cursor()
      columns = ', '.join(list(data.keys()))
      placeholders = ("?, " * len(data))[:-2]
      values = tuple(data.values())
      cursor.execute(f'INSERT INTO games({columns}) VALUES ({placeholders})', values)
      database.commit()
      cursor.close()
   changes = False
   with open(config_path, 'r') as config_file:
      data = yaml.safe_load(config_file)
   if 'exe' not in data['game'] or data['game']['exe'] != path:
      print(f'Updating \'{name}\' executable in Lutris to \'{path}\'')
      data['game']['exe'] = path
      changes = True
   if 'prefix' not in data['game'] or data['game']['prefix'] != wineprefix:
      print(f'Updating \'{name}\' wineprefix in Lutris to \'{wineprefix}\'')
      data['game']['prefix'] = wineprefix
      changes = True
   if has_panacea:
      pana = settings['mods'].get('panacea') == True
      if pana and ('overrides' not in data['wine'] or 'version' not in data['wine']['overrides']):
         print(f'Adding Panacea DLL override in Lutris for \'{name}\'')
         if 'overrides' not in data['wine']:
            data['wine']['overrides'] = {}
         data['wine']['overrides']['version'] = 'native,builtin'
         changes = True
      if not pana and 'overrides' in data['wine'] and 'version' in data['wine']['overrides']:
         print(f'Removing Panacea DLL override from Lutris for \'{name}\'')
         del data['wine']['overrides']['version']
         changes = True
   if has_luabackend:
      lua = settings['mods'].get('luabackend') is not None
      if lua and ('overrides' not in data['wine'] or 'dinput8' not in data['wine']['overrides']):
         if 'overrides' not in data['wine']:
            data['wine']['overrides'] = {}
         print(f'Adding LuaBackend DLL override in Lutris for \'{name}\'')
         data['wine']['overrides']['dinput8'] = 'native,builtin'
         changes = True
      if not lua and 'overrides' in data['wine'] and 'dinput8' in data['wine']['overrides']:
         print(f'Removing LuaBackend DLL override from Lutris for \'{name}\'')
         del data['wine']['overrides']['dinput8']
         changes = True
   if changes:
      with open(config_path, 'w') as config_file:
         yaml.dump(data, config_file, sort_keys=False)

def get_settings(settings_path):
   if os.path.exists(settings_path):
      with open(settings_path, 'r') as data_file:
         settings = yaml.safe_load(data_file)
   else:
      print('First-time run, welcome!')
      print('You\'ll be asked some questions about your setup. Every time you run this script, everything will be updated according to your answers. You can change them at any time by editing or deleting settings.yaml. Anything you disable later will be seamlessly reverted; all changes made by this script are reversible.')
      print()
      settings = {}
   old_settings = settings.copy()

   if 'installs' not in settings:
      settings['installs'] = {}
      print('Input the folders where your Kingdom Hearts games are installed.')
      print('For any you don\'t have, just press enter.')
      print()
   if 'kh1.5+2.5' not in settings['installs']:
      print('Kingdom Hearts HD 1.5+2.5 ReMIX:')
      while True:
         install = input('> ')
         if install == '':
            install = None
         else:
            install = os.path.expanduser(install)
            if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe')):
               print('Couldn\t find \'KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe\' in that folder. Please try again.')
               continue
         break
      settings['installs']['kh1.5+2.5'] = install
      print()
   if 'kh2.8' not in settings['installs']:
      print('Kingdom Hearts HD 2.8 Final Chapter Prologue:')
      while True:
         install = input('> ')
         if install == '':
            install = None
         else:
            install = os.path.expanduser(install)
            if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe')):
               print('Couldn\t find \'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe\' in that folder. Please try again.')
               continue
         break
      settings['installs']['kh2.8'] = install
      print()
   if 'kh3' not in settings['installs']:
      print('Kingdom Hearts III:')
      while True:
         install = input('> ')
         if install == '':
            install = None
         else:
            install = os.path.expanduser(install)
            if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe')):
               print('Couldn\t find \'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe\' in that folder. Please try again.')
               continue
         break
      settings['installs']['kh3'] = install
      print()
   if 'khmom' not in settings['installs']:
      settings['installs']['khmom'] = None

   if 'folder' not in settings:
      print('Now where would you like to store the extra stuff installed by this script?')
      folder = input('> ')
      settings['folder'] = os.path.expanduser(folder)
      print()
   
   base_folder = settings['folder']

   if 'runner' not in settings:
      settings['runner'] = os.path.join(base_folder, 'runner')

   if 'wineprefix' not in settings:
      settings['wineprefix'] = os.path.join(base_folder, 'wineprefix')

   if 'saves' not in settings:
      saves = os.path.join(base_folder, 'Save Data')
      settings['saves'] = {'kh1.5+2.5': os.path.join(saves, 'Kingdom Hearts 1.5+2.5'), 'kh2.8': os.path.join(saves, 'Kingdom Hearts 2.8'), 'kh3': os.path.join(saves, 'Kingdom Hearts III'), 'khmom': os.path.join(saves, 'Kingdom Hearts Melody of Memory')}

   if 'lutris' not in settings and os.path.exists('/bin/lutris'):
      print('Lutris detected. Would you like to add the games to Lutris? (y/n)')
      settings['lutris'] = yes_no()
      print()

   if 'heroic' not in settings and os.path.exists('/bin/heroic'):
      print('Heroic Games Launcher detected. Would you like to add the games to Heroic? (y/n)')
      settings['heroic'] = yes_no()
      print()

   supports_mods = settings['installs']['kh1.5+2.5'] is not None or settings['installs']['kh2.8'] is not None
   if 'mods' not in settings:
      settings['mods'] = {'folder': os.path.join(base_folder, 'Mods')}
      if supports_mods:
         print('Modding applications to use:')
         print()
   if supports_mods:
      if 'refined' not in settings['mods'] and settings['installs']['kh1.5+2.5'] is not None:
         print('Kingdom Hearts ReFined: (y/n)')
         answer = yes_no()
         settings['mods']['refined'] = os.path.join(base_folder, 'ReFined') if answer else None
         print()
         if answer:
            if 'refined_config' not in settings['mods']:
               settings['mods']['refined_config'] = os.path.join(base_folder, 'reFined.ini')
            if 'openkh' not in settings['mods']:
               settings['mods']['openkh'] = os.path.join(base_folder, 'OpenKH')
      if settings['mods']['refined'] is not None:
         if 'refined.vanilla_ost' not in settings['mods']:
            print('ReFined addon: Vanilla OST toggle (y/n)')
            settings['mods']['refined.vanilla_ost'] = yes_no()
            print()
         if 'refined.vanilla_enemies' not in settings['mods']:
            print('ReFined addon: Vanilla enemies toggle (y/n)')
            settings['mods']['refined.vanilla_enemies'] = yes_no()
            print()
         if 'refined.multi_audio' not in settings['mods']:
            print('ReFined addon: Multi-language voices (y/n)')
            settings['mods']['refined.multi_audio'] = yes_no()
            print()
      if 'randomizer' not in settings['mods']:
         print('Kingdom Hearts II Randomizer: (y/n)')
         answer = yes_no()
         settings['mods']['randomizer'] = os.path.join(base_folder, 'Randomizer') if answer else None
         print()
         if answer:
            if 'openkh' not in settings['mods']:
               settings['mods']['openkh'] = os.path.join(base_folder, 'OpenKH')
            if 'luabackend' not in settings['mods']:
               settings['mods']['luabackend'] = os.path.join(base_folder, 'LuaBackend')
            if 'luabackend_config' not in settings['mods']:
               settings['mods']['luabackend_config'] = os.path.join(base_folder, 'LuaBackend.toml')
      if 'openkh' not in settings['mods']:
         print('OpenKh mod manager: (y/n)')
         settings['mods']['openkh'] = os.path.join(base_folder, 'OpenKH') if yes_no() else None
         print()
      if settings['mods']['openkh'] is not None and 'panacea' not in settings['mods']:
         print('Panacea mod loader: (y/n)')
         answer = yes_no()
         settings['mods']['panacea'] = answer
         if answer:
            settings['mods']['panacea_settings'] = os.path.join(base_folder, 'panacea_settings.txt')
         print()
      if 'luabackend' not in settings['mods']:
         print('LuaBackend script loader: (y/n)')
         answer = yes_no()
         settings['mods']['luabackend'] = os.path.join(base_folder, 'LuaBackend') if answer else None
         if answer:
            settings['mods']['luabackend_config'] = os.path.join(base_folder, 'LuaBackend.toml')
         print()

   with open(settings_path, 'w') as data_file:
      yaml.dump(settings, data_file, sort_keys=False)

   return (settings, settings != old_settings)

def symlink(existing, new, is_dir=False):
   if os.path.islink(new):
      target = os.readlink(new)
      if target == existing:
         return
      print(f'Removing previous symlink in \'{new}\' pointing to \'{target}\'')
      os.remove(new)
   if not os.path.exists(new):
      print(f'Creating symlink in \'{new}\' pointing to \'{existing}\'')
      os.makedirs(os.path.dirname(new), exist_ok=True)
      os.symlink(existing, new, target_is_directory=is_dir)

def remove_symlink(path):
   if os.path.islink(path):
      print(f'Removing symlink \'{path}\'')
      os.remove(path)

def yes_no():
   while True:
      answer = input('> ')
      if answer in ('y','n','Y','N'):
         break
   return answer in ('y','Y')

if __name__ == '__main__':
   main()
