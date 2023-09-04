import requests
import json
import zipfile
import shutil
import os
import subprocess
import datetime
import tomlkit

def main():
   settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
   settings = get_settings(settings_path)
   if 'downloads' not in settings:
      settings['downloads'] = {}
   print('Starting!')
   symlinks = {}

   if (wineprefix := settings.get('wineprefix')) is not None:
      if not os.path.exists(wineprefix):
         print('Initializing wineprefix')
         subprocess.run('wineboot', env=dict(os.environ, WINEPREFIX=wineprefix))
      user_folder = os.path.join(wineprefix, 'drive_c/users', os.getlogin())
      symlinks[os.path.join(user_folder, 'Documents')] = None
      symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638')] = None
      symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638')] = None
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638')] = None
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638')] = None
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638')] = None
      symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store')] = None
      if (saves := settings.get('saves')) is not None:
         if settings['installs'].get('kh1.5+2.5') and (save := saves.get('kh1.5+2.5')) is not None:
            os.makedirs(save, exist_ok=True)
            symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638')] = (save, True)
            if settings['mods'].get('refined'):
               symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638')] = (save, True)
               symlinks[os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638')] = (save, True)
         if settings['installs'].get('kh2.8') and (save := saves.get('kh1.5+2.5')) is not None:
            os.makedirs(save, exist_ok=True)
            symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638')] = (save, True)
         if settings['installs'].get('kh3') and (save := saves.get('kh1.5+2.5')) is not None:
            os.makedirs(save, exist_ok=True)
            symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638')] = (save, True)
         if settings['installs'].get('mom') and (save := saves.get('kh1.5+2.5')) is not None:
            os.makedirs(save, exist_ok=True)
            symlinks[os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store')] = (save, True)
   
   backup_vanilla = False
   kh15_folder = settings['installs'].get('kh1.5+2.5')
   kh28_folder = settings['installs'].get('kh2.8')
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
      symlinks[os.path.join(kh28_folder, 'version.dll')] = None
      symlinks[os.path.join(kh28_folder, 'panacea_settings.txt')] = None
      symlinks[os.path.join(kh28_folder, 'DINPUT8.dll')] = None
      symlinks[os.path.join(kh28_folder, 'lua54.dll')] = None
      symlinks[os.path.join(kh28_folder, 'LuaBackend.toml')] = None
   
   if (mods_folder := settings['mods'].get('folder')) is not None:
      if (mod_folder := settings['mods'].get('refined')) is not None:
         print('Checking for ReFined updates...')
         date = settings['downloads'].get('refined')
         if date is not None:
            date = datetime.datetime.fromisoformat(date)
         rq = requests.get('https://api.github.com/repos/TopazTK/KH-ReFined/releases')
         if rq.status_code != 200:
            print(f'Error {rq.status_code}!')
            try:
               print(json.loads(rq.text)['message'])
            except:
               print(rq.text)
         else:
            newest = None
            for release in json.loads(rq.text):
               for asset in release['assets']:
                  if asset['name'].endswith('.zip'):
                     asset_date = datetime.datetime.fromisoformat(asset['updated_at'])
                     if newest is None or asset_date > newest[0]:
                        newest = (asset_date, release, asset)
            if newest is not None and (date is None or newest[0] > date):
               print(f'Downloading update: {newest[1]["tag_name"]}')
               rq = requests.get(newest[2]['browser_download_url'])
               if rq.status_code != 200:
                  print(f'Error {rq.status_code}!')
                  print(rq.text)
               else:
                  with open('/tmp/refined.zip', 'wb') as file:
                     file.write(rq.content)
                  with zipfile.ZipFile('/tmp/refined.zip', 'r') as zip:
                     zip.extractall(mod_folder)
                  settings['downloads']['refined'] = newest[0].isoformat()
         if os.path.exists(mod_folder) and kh15_folder is not None:
            symlinks[os.path.join(kh15_folder, 'x64')] = (os.path.join(mod_folder, 'x64'), True)
            symlinks[os.path.join(kh15_folder, 'Keystone.Net.dll')] = (os.path.join(mod_folder, 'Keystone.Net.dll'), False)
            symlinks[os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')] = (os.path.join(mod_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), False)
            symlinks[os.path.join(kh15_folder, 'reFined.ini')] = (os.path.join(mods_folder, 'reFined.ini'), False)
            backup_vanilla = True

      if (mod_folder := settings['mods'].get('openkh')) is not None:
         print('Checking for OpenKH updates...')
         date = settings['downloads'].get('openkh')
         if date is not None:
            date = datetime.datetime.fromisoformat(date)
         rq = requests.get('https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest')
         if rq.status_code != 200:
            print(f'Error {rq.status_code}!')
            try:
               print(json.loads(rq.text)['message'])
            except:
               print(rq.text)
         else:
            release = json.loads(rq.text)
            for asset in release['assets']:
               if asset['name'] == 'openkh.zip':
                  asset_date = datetime.datetime.fromisoformat(asset['updated_at'])
                  if date is None or asset_date > date:
                     print(f'Downloading update: {release["tag_name"]}')
                     rq = requests.get(asset['browser_download_url'])
                     if rq.status_code != 200:
                        print(f'Error {rq.status_code}!')
                        print(rq.text)
                     else:
                        with open('/tmp/openkh.zip', 'wb') as file:
                           file.write(rq.content)
                        with zipfile.ZipFile('/tmp/openkh.zip', 'r') as zip:
                           zip.extractall('/tmp/openkh')
                        shutil.copytree('/tmp/openkh/openkh', mod_folder, dirs_exist_ok=True)
                        settings['downloads']['openkh'] = asset_date.isoformat()
                     break
         if os.path.exists(mod_folder):
            if settings['mods'].get('panacea'):
               if kh15_folder is not None:
                  symlinks[os.path.join(kh15_folder, 'version.dll')] = (os.path.join(mod_folder, 'OpenKH.Panacea.dll'), False)
                  symlinks[os.path.join(kh15_folder, 'panacea_settings.txt')] = (os.path.join(mods_folder, 'panacea_settings.txt'), False)
               if kh28_folder is not None:
                  symlinks[os.path.join(kh28_folder, 'version.dll')] = (os.path.join(mod_folder, 'OpenKH.Panacea.dll'), False)
                  symlinks[os.path.join(kh28_folder, 'panacea_settings.txt')] = (os.path.join(mods_folder, 'panacea_settings.txt'), False)
            mod_dir = os.path.join(mods_folder, 'Mods')
            os.makedirs(mod_dir, exist_ok=True)
            symlinks[os.path.join(mod_folder, 'mods')] = (mod_dir, True)

      if (mod_folder := settings['mods'].get('luabackend')) is not None:
         print('Checking for LuaBackend updates...')
         date = settings['downloads'].get('luabackend')
         if date is not None:
            date = datetime.datetime.fromisoformat(date)
         toml_user = os.path.join(mods_folder, 'LuaBackend.toml')
         rq = requests.get('https://api.github.com/repos/Sirius902/LuaBackend/releases/latest')
         if rq.status_code != 200:
            print(f'Error {rq.status_code}!')
            try:
               print(json.loads(rq.text)['message'])
            except:
               print(rq.text)
         else:
            release = json.loads(rq.text)
            for asset in release['assets']:
               if asset['name'] == 'DBGHELP.zip':
                  asset_date = datetime.datetime.fromisoformat(asset['updated_at'])
                  if date is None or asset_date > date:
                     print(f'Downloading update: {release["tag_name"]}')
                     rq = requests.get(asset['browser_download_url'])
                     if rq.status_code != 200:
                        print(f'Error {rq.status_code}!')
                        print(rq.text)
                     else:
                        with open('/tmp/luabackend.zip', 'wb') as file:
                           file.write(rq.content)
                        with zipfile.ZipFile('/tmp/luabackend.zip', 'r') as zip:
                           zip.extractall(mod_folder)
                        toml_default = os.path.join(mod_folder, 'LuaBackend.toml')
                        if not os.path.exists(toml_user):
                           print('Creating default LuaBackend.toml configuration')
                           shutil.copyfile(toml_default, toml_user)
                        os.remove(toml_default)
                        settings['downloads']['luabackend'] = asset_date.isoformat()
                     break
         if os.path.exists(mod_folder):
            if kh15_folder is not None:
               symlinks[os.path.join(kh15_folder, 'DINPUT8.dll')] = (os.path.join(mod_folder, 'DBGHELP.dll'), False)
               symlinks[os.path.join(kh15_folder, 'lua54.dll')] = (os.path.join(mod_folder, 'lua54.dll'), False)
               symlinks[os.path.join(kh15_folder, 'LuaBackend.toml')] = (toml_user, False)
            if kh28_folder is not None:
               symlinks[os.path.join(kh28_folder, 'DINPUT8.dll')] = (os.path.join(mod_folder, 'DBGHELP.dll'), False)
               symlinks[os.path.join(kh28_folder, 'lua54.dll')] = (os.path.join(mod_folder, 'lua54.dll'), False)
               symlinks[os.path.join(kh28_folder, 'LuaBackend.toml')] = (toml_user, False)
         if os.path.exists(toml_user) and (openkh := settings['mods'].get('openkh')) is not None:
            with open(toml_user, 'r') as toml_file:
               toml_data = tomlkit.load(toml_file)
            changes = False
            for game in ['kh1', 'kh2', 'bbs', 'recom', 'kh3d']:
               if game in toml_data and 'scripts' in toml_data[game]:
                  path = os.path.join(openkh, 'mod', game, 'scripts') 
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

   for (new, old) in symlinks.items():
      if old is None:
         remove_symlink(new)
      else:
         path, dir = old
         symlink(path, new, is_dir=dir)

   if kh15_folder is not None:
      backup_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX VANILLA.exe')
      launch_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX.exe')
      if backup_vanilla:
         if not os.path.exists(backup_path):
            print('Moving vanilla KH2 executable')
            os.rename(launch_path, backup_path)
      else:
         if os.path.exists(backup_path) and not os.path.exists(launch_path):
            print('Restoring vanilla KH2 executable')
            os.rename(backup_path, launch_path)

   with open(settings_path, 'w') as data_file:
      json.dump(settings, data_file, indent=2)


def get_settings(settings_path):
   if os.path.exists(settings_path):
      with open(settings_path, 'r') as data_file:
         settings = json.load(data_file)
   else:
      print('First-time run, welcome!')
      print('You\'ll be asked some questions about your setup. Every time you run this script, everything will be updated according to your answers. You can change them at any time by editing or deleting settings.json. Anything you disable later will be seamlessly reverted; all changes made by this script are reversible.')
      print()
      settings = {}

   if 'installs' not in settings:
      settings['installs'] = {}
      print('Input the folders where your Kingdom Hearts games are installed.')
      print('For any you don\'t have, just press enter.')
      print()
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

   if 'wineprefix' not in settings:
      print('Input the folder for your wineprefix.')
      print('To use the default (~/.wine), just press enter.')
      prefix = input('> ')
      if prefix == '':
         prefix = '~/.wine'
      prefix = os.path.expanduser(prefix)
      settings['wineprefix'] = prefix
      print()

   if 'saves' not in settings:
      print('Where would you like game save files to be stored?')
      print('To leave them in the default location (wineprefix documents folder), just press enter.')
      saves = input('> ')
      if saves == '':
         settings['saves'] = None
      else:
         saves = os.path.expanduser(saves)
         settings['saves'] = {'kh1.5+2.5': os.path.join(saves, 'Kingdom Hearts 1.5+2.5'), 'kh2.8': os.path.join(saves, 'Kingdom Hearts 2.8'), 'kh3': os.path.join(saves, 'Kingdom Hearts III'), 'mom': os.path.join(saves, 'Kingdom Hearts Melody of Memory')}
      print()

   lutris_path = '/bin/lutris'
   if 'lutris' not in settings and os.path.exists(lutris_path):
      print('Lutris detected. Would you like to add game links to Lutris? (y/n)')
      settings['lutris'] = yes_no()
      print()

   if 'mods' not in settings and (settings['installs'].get('kh1.5+2.5') is not None or settings['installs'].get('kh2.8') is not None):
      settings['mods'] = {}
      print('Where would you like to save modding applications?')
      print('If you don\'t want mods, just press enter.')
      folder = input('> ')
      if folder == '':
         folder = None
      else:
         folder = os.path.expanduser(folder)
      settings['mods']['folder'] = folder
      print()
      if folder is not None:
         print('Modding applications to use:')
         print()
         if settings['installs'].get('kh1.5+2.5') is not None:
            print('Kingdom Hearts ReFined: (y/n)')
            answer = yes_no()
            settings['mods']['refined'] = os.path.join(folder, 'ReFined-KH2') if answer else None
            print()
            if answer:
               settings['mods']['openkh'] = os.path.join(folder, 'OpenKH')
         if 'openkh' not in settings['mods']:
            print('OpenKh mod manager: (y/n)')
            settings['mods']['openkh'] = os.path.join(folder, 'OpenKH') if yes_no() else None
            print()
         if settings['mods']['openkh']:
            print('Panacea mod loader: (y/n)')
            settings['mods']['panacea'] = yes_no()
            print()
         print('LuaBackend script loader: (y/n)')
         settings['mods']['luabackend'] = os.path.join(folder, 'LuaBackend') if yes_no() else None
         print()

   with open(settings_path, 'w') as data_file:
      json.dump(settings, data_file, indent=2)

   return settings

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
