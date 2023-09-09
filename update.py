#!/usr/bin/env python3
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
import tarfile
import stat
import copy
import platform

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

   remove_symlinks = set()
   def make_symlink(new, existing, is_dir):
      if new in remove_symlinks:
         remove_symlinks.remove(new)
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

   kh15_folder = settings['installs']['kh1.5+2.5']
   kh28_folder = settings['installs']['kh2.8']
   kh3_folder = settings['installs']['kh3']
   khmom_folder = settings['installs']['khmom']
   kh2launch = settings['installs'].get('kh2.exe')
   openkh_folder = settings['mods'].get('openkh')
   is_linux = platform.system() == 'Linux'
   
   if is_linux:
      wineprefix = settings['wineprefix']
      def convert_path(path):
         return subprocess.run(['winepath', '-w', path], check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=dict(os.environ, WINEPREFIX=wineprefix)).stdout.decode('utf-8').rstrip('\n')
      user_folder = os.path.join(wineprefix, 'drive_c/users', os.getlogin())
      runner = settings['runner']
      runner_wine = os.path.join(runner, 'bin/wine')
      if settings['update_runner'] == True:
         print('Checking for runner updates...')
         new_runner = download_latest(settings, 'runner', 'https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases/latest', lambda x: x['name'].endswith('.tar.xz'), True, settings['runner'], True)
      else:
         new_runner = False
      winetricks = []
      if os.path.exists(os.path.join(wineprefix, 'winetricks.log')):
         with open(os.path.join(wineprefix, 'winetricks.log'), 'r') as winetricks_file:
            winetricks = [line.rstrip('\n') for line in winetricks_file]
      if settings['mods'].get('refined') is not None and 'dotnet48' not in winetricks:
         print('Installing dotnet to wineprefix (this will take some time)')
         subprocess.run(['winetricks', '-q', 'dotnet20', 'dotnet48'], env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
      if openkh_folder is not None and 'dotnet6' not in winetricks:
         print('Installing dotnet6 to wineprefix')
         subprocess.run(['winetricks', '-q', 'dotnet6'], env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
         subprocess.run(['wine', 'reg', 'add', 'HKEY_CURRENT_USER\\Environment', '/f', '/v', 'DOTNET_ROOT', '/t', 'REG_SZ', '/d', 'C:\\Program Files\\dotnet'], env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
      if 'vkd3d' not in winetricks:
         print('Installing VKD3D to wineprefix')
         subprocess.run(['winetricks', '-q', 'dxvk', 'vkd3d'], env=dict(os.environ, WINEPREFIX=wineprefix), check=True)
      if (kh3_folder is not None or kh28_folder is not None) and (new_runner or not os.path.exists(os.path.join(wineprefix, 'drive_c/windows/system32/sqmapi.dll'))):
         print('Running mf-install to fix KH3/KH2.8')
         mfinstall_folder = tempfile.mkdtemp()
         subprocess.run(['git', 'clone', 'https://github.com/84KaliPleXon3/mf-install', mfinstall_folder], check=True)
         sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=mfinstall_folder, check=True, stdout=subprocess.PIPE)
         if sha.stdout != b'19669ca372ddd3993e10dc287132edb172188e3e\n':
            raise ValueError('mf-install possibly tampered with!')
         env = os.environ.copy()
         env['PATH'] = f'{runner}/bin:{env["PATH"]}'
         env['WINEPREFIX'] = wineprefix
         subprocess.run(['wineserver', '-w'], check=True)
         subprocess.run(['wineserver', '-w'], env=env, check=True)
         subprocess.run(['/bin/sh', os.path.join(mfinstall_folder, 'mf-install.sh')], env=env, check=True)
         shutil.rmtree(mfinstall_folder)
   else:
      user_folder = os.path.expanduser('~')
      def convert_path(path):
         return path

   remove_symlinks.add(os.path.join(user_folder, 'Documents'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638'))
   remove_symlinks.add(os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store'))
   if (save := settings['saves']['kh1.5+2.5']) is not None and kh15_folder is not None:
      os.makedirs(save, exist_ok=True)
      make_symlink(os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store/1638'), save, True)
      if settings['mods'].get('refined') is not None:
         make_symlink(os.path.join(user_folder, 'Documents/Kingdom Hearts/Configuration/1638'), save, True)
         make_symlink(os.path.join(user_folder, 'Documents/Kingdom Hearts/Save Data/1638'), save, True)
   if (save := settings['saves']['kh2.8']) is not None and kh28_folder is not None:
      os.makedirs(save, exist_ok=True)
      make_symlink(os.path.join(user_folder, 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store/1638'), save, True)
   if (save := settings['saves']['kh3']) is not None and kh3_folder is not None:
      os.makedirs(save, exist_ok=True)
      make_symlink(os.path.join(user_folder, 'Documents/KINGDOM HEARTS III/Epic Games Store/1638'), save, True)
   if (save := settings['saves']['khmom']) is not None and khmom_folder is not None:
      os.makedirs(save, exist_ok=True)
      make_symlink(os.path.join(user_folder, 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store'), save, True)
   
   backup_vanilla = False
   if kh15_folder is not None:
      epic_folder = os.path.join(kh15_folder, 'EPIC')
      if is_linux and os.path.exists(epic_folder) and len(os.listdir(epic_folder)) > 0:
         print('Renaming KH 1.5+2.5 EPIC folder to EPIC.bak to prevent crashes during FMVs')
         os.rename(epic_folder, os.path.join(kh15_folder, 'EPIC.bak'))
      remove_symlinks.add(os.path.join(kh15_folder, 'x64'))
      remove_symlinks.add(os.path.join(kh15_folder, 'Keystone.Net.dll'))
      if kh2launch is not None:
         remove_symlinks.add(kh2launch)
      remove_symlinks.add(os.path.join(kh15_folder, 'reFined.ini'))
      if is_linux:
         remove_symlinks.add(os.path.join(kh15_folder, 'version.dll'))
         remove_symlinks.add(os.path.join(kh15_folder, 'DINPUT8.dll'))
      else:
         remove_symlinks.add(os.path.join(kh15_folder, 'DBGHELP.dll'))
         remove_symlinks.add(os.path.join(kh15_folder, 'LuaBackend.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'panacea_settings.txt'))
      remove_symlinks.add(os.path.join(kh15_folder, 'lua54.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'LuaBackend.toml'))
   if kh28_folder is not None:
      epic_folder = os.path.join(kh28_folder, 'EPIC')
      if is_linux and os.path.exists(epic_folder) and len(os.listdir(epic_folder)) > 0:
         print('Renaming KH 2.8 EPIC folder to EPIC.bak to prevent crashes during FMVs')
         os.rename(epic_folder, os.path.join(kh28_folder, 'EPIC.bak'))
         remove_symlinks.add(os.path.join(kh28_folder, 'DINPUT8.dll'))
      else:
         remove_symlinks.add(os.path.join(kh28_folder, 'DBGHELP.dll'))
      remove_symlinks.add(os.path.join(kh28_folder, 'lua54.dll'))
      remove_symlinks.add(os.path.join(kh28_folder, 'LuaBackend.toml'))

   if openkh_folder is not None:
      default_mods_folder = os.path.join(openkh_folder, 'mods')
      custom_mods_folder = settings['mods'].get('folder')
      write_mods_folder = custom_mods_folder if custom_mods_folder is not None else default_mods_folder
      mods_manager = os.path.join(openkh_folder, 'mods-manager.yml')
      pana_settings = settings['mods'].get('panacea_settings')
      pana_write = pana_settings
      if pana_settings is None:
         pana_write = os.path.join(kh15_folder, 'panacea_settings.txt')
      print('Checking for OpenKH updates...')
      downloaded = download_latest(settings, 'openkh', 'https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest', lambda x: x['name'] == 'openkh.zip', True, openkh_folder, False)
      if downloaded and not os.path.exists(mods_manager):
         print('Creating default OpenKH mod manager configuration')
         with open(mods_manager, 'w') as mods_file:
            yaml.dump({"gameEdition":2}, mods_file)
         if pana_write is not None and not os.path.exists(pana_write):
            print('Creating default panacea configuration')
            with open(pana_write, 'w') as pana_file:
               pana_file.write('show_console=False')
      if settings['mods'].get('panacea') == True:
         if is_linux:
            make_symlink(os.path.join(kh15_folder, 'version.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
         else:
            make_symlink(os.path.join(kh15_folder, 'DBGHELP.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
         if pana_settings is not None:
            make_symlink(os.path.join(kh15_folder, 'panacea_settings.txt'), pana_settings, False)
      built_mods_folder = os.path.join(openkh_folder, 'mod')
      if os.path.exists(pana_write):
         windows_folder = convert_path(built_mods_folder)
         changes = False
         found = False
         with open(pana_write, 'r') as pana_file:
            lines = [line.rstrip('\n') for line in pana_file]
         for i in range(len(lines)):
            line = lines[i]
            key,value = line.split('=', 1)
            if key == 'mod_path':
               found = True
               if value != windows_folder:
                  value = windows_folder
                  changes = True
                  lines[i] = f'{key}={value}'
         if not found:
            lines.append(f'mod_path={windows_folder}')
            changes = True
         if changes:
            print(f'Updating Panacea mods location')
            with open(pana_write, 'w') as pana_file:
               for line in lines:
                  pana_file.write(line + '\n')

      remove_symlinks.add(default_mods_folder)
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-KH1.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-KH2.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-BBS.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-ReCoM.txt'))
      if custom_mods_folder is not None:
         os.makedirs(custom_mods_folder, exist_ok=True)
         make_symlink(default_mods_folder, custom_mods_folder, True)
         make_symlink(os.path.join(openkh_folder, 'mods-KH1.txt'), os.path.join(custom_mods_folder, 'kh1.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-KH2.txt'), os.path.join(custom_mods_folder, 'kh2.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-BBS.txt'), os.path.join(custom_mods_folder, 'bbs.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-ReCoM.txt'), os.path.join(custom_mods_folder, 'Recom.txt'), False)
      if os.path.exists(mods_manager):
         changes = False
         with open(mods_manager, 'r') as mods_file:
            mods_data = yaml.safe_load(mods_file)
         pc_release = convert_path(kh15_folder)
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

      def download_mod(game, repo):
         if openkh_folder is None:
            return
         patch_folder = os.path.join(write_mods_folder, game, repo)
         if game not in mod_changes:
            mod_changes[game] = {}
         if not os.path.exists(patch_folder):
            print(f'Downloading mod {repo}')
            subprocess.run(['git', 'clone', f'https://github.com/{repo}', '--recurse-submodules', patch_folder], check=True)
            del mod_changes[game][repo]
         else:
            mod_changes[game][repo] = True

      mod_changes = {'kh2':{'KH2FM-Mods-Num/GoA-ROM-Edition': False, 'KH-ReFined/KH2-VanillaOST': False, 'KH-ReFined/KH2-VanillaEnemy': False, 'KH-ReFined/KH2-MultiAudio': False, 'KH-ReFined/KH2-MAIN': False}}
      if (refined_folder := settings['mods'].get('refined')) is not None:
         print('Checking for ReFined updates...')
         download_latest(settings, 'refined', 'https://api.github.com/repos/TopazTK/KH-ReFined/releases', lambda x: x['name'].endswith('.zip'), False, refined_folder, False)
         download_mod('kh2', 'KH-ReFined/KH2-MAIN')
         if settings['mods'].get('refined.vanilla_ost') == True:
            download_mod('kh2', 'KH-ReFined/KH2-VanillaOST')
         if settings['mods'].get('refined.vanilla_enemies') == True:
            download_mod('kh2', 'KH-ReFined/KH2-VanillaEnemy')
         if settings['mods'].get('refined.multi_audio') == True:
            download_mod('kh2', 'KH-ReFined/KH2-MultiAudio')
         if os.path.exists(refined_folder):
            make_symlink(os.path.join(kh15_folder, 'x64'), os.path.join(refined_folder, 'x64'), True)
            make_symlink(os.path.join(kh15_folder, 'Keystone.Net.dll'), os.path.join(refined_folder, 'Keystone.Net.dll'), False)
            if kh2launch is not None:
               make_symlink(kh2launch, os.path.join(refined_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), False)
            if (refined_ini := settings['mods'].get('refined_config')) is not None:
               make_symlink(os.path.join(kh15_folder, 'reFined.ini'), refined_ini, False)
            backup_vanilla = True

      if (randomizer_folder := settings['mods'].get('randomizer')) is not None:
         print('Checking for Randomizer updates...')
         download_latest(settings, 'randomizer', 'https://api.github.com/repos/tommadness/KH2Randomizer/releases/latest', lambda x: x['name'] == 'Kingdom.Hearts.II.Final.Mix.Randomizer.zip', False, randomizer_folder, False)
         download_mod('kh2', 'KH2FM-Mods-Num/GoA-ROM-Edition')

      if os.path.exists(write_mods_folder):
         for dir in [os.path.join(dp, f) for dp, dn, _ in os.walk(write_mods_folder) for f in dn]:
            if os.path.exists(os.path.join(dir, '.git')):
               print(f'Checking for updates for mod {os.path.basename(dir)}')
               subprocess.run(['git', 'pull', '--recurse-submodules'], cwd=dir, check=True)
      if 'last_build' not in settings:
         settings['last_build'] = {}
      for gameid, txtid in [('kh1', 'KH1'), ('kh2', 'KH2'), ('bbs', 'BBS'), ('Recom', 'ReCoM')]:
         enabled_mods_path = os.path.join(openkh_folder, f'mods-{txtid}.txt')
         if os.path.exists(enabled_mods_path):
            with open(enabled_mods_path, 'r') as enabled_file:
               enabled_mods = [line.rstrip('\n') for line in enabled_file]
         else:
            enabled_mods = []
         if gameid in mod_changes:
            for mod,enabled in mod_changes[gameid].items():
               if enabled and mod not in enabled_mods:
                  print(f'Enabling {gameid} mod {mod}')
                  enabled_mods.append(mod)
               elif not enabled and mod in enabled_mods:
                  print(f'Disabling {gameid} mod {mod}')
                  enabled_mods.remove(mod)
         last_build = settings['last_build'].get(gameid, [])
         if enabled_mods != last_build:
            with open(enabled_mods_path, 'w') as enabled_file:
               for line in enabled_mods:
                  enabled_file.write(line + '\n')
            data_folder = os.path.join(openkh_folder, 'data', gameid)
            source_folder = os.path.join(kh15_folder, 'Image/en')
            if not os.path.exists(data_folder):
               print(f'Extracting {gameid} data (this will take some time)')
               for file in os.listdir(source_folder):
                  if file.startswith(f'{gameid}_') and os.path.splitext(file)[1] == '.hed':
                     if is_linux:
                        subprocess.run(['wine', os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'extract', '-n', '-o', convert_path(data_folder), convert_path(os.path.join(source_folder, file))], check=True, env=dict(os.environ, WINEPREFIX=wineprefix))
                     else:
                        subprocess.run([os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'extract', '-n', '-o', data_folder, os.path.join(source_folder, file)], check=True)
               for file in os.listdir(os.path.join(data_folder, 'original')):
                  shutil.move(os.path.join(data_folder, 'original', file), data_folder)
            print(f'Building {gameid} mods')
            if is_linux:
               subprocess.run(['wine', os.path.join(openkh_folder, 'OpenKh.Command.Patcher.exe'), 'build', '-g', gameid, '-o', convert_path(os.path.join(built_mods_folder, gameid)), '-e', convert_path(enabled_mods_path), '-f', convert_path(write_mods_folder), '-d', convert_path(data_folder)], check=True, env=dict(os.environ, WINEPREFIX=wineprefix))
            else:
               subprocess.run([os.path.join(openkh_folder, 'OpenKh.Command.Patcher.exe'), 'build', '-g', gameid, '-o',os.path.join(built_mods_folder, gameid), '-e', enabled_mods_path, '-f', write_mods_folder, '-d', data_folder], check=True)
            if settings['mods'].get('panacea') != True:
               print(f'Patching {gameid} mods')
               patch_folder = os.path.join(openkh_folder, 'patched')
               backup_folder = os.path.join(kh15_folder, 'BackupImage')
               if os.path.exists(backup_folder):
                  for file in os.listdir(backup_folder):
                     shutil.copyfile(os.path.join(backup_folder, file), os.path.join(source_folder, file))
                  shutil.rmtree(backup_folder)
               if is_linux:
                  subprocess.run(['wine', os.path.join(openkh_folder, 'OpenKh.Command.Patcher.exe'), 'patch', '-b', convert_path(os.path.join(built_mods_folder, gameid)), '-o', convert_path(patch_folder), '-f', convert_path(source_folder)], check=True, env=dict(os.environ, WINEPREFIX=wineprefix))
               else:
                  subprocess.run([os.path.join(openkh_folder, 'OpenKh.Command.Patcher.exe'), 'patch', '-b', os.path.join(built_mods_folder, gameid), '-o', patch_folder, '-f', source_folder], check=True)
               os.makedirs(backup_folder, exist_ok=True)
               for file in os.listdir(patch_folder):
                  backup_path = os.path.join(backup_folder, file)
                  write_path = os.path.join(source_folder, file)
                  if not os.path.exists(backup_path):
                     shutil.copyfile(write_path, backup_path)
                  shutil.copyfile(os.path.join(patch_folder, file), write_path)
               shutil.rmtree(patch_folder)
            settings['last_build'][gameid] = enabled_mods

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
      if kh15_folder is not None:
         if is_linux:
            make_symlink(os.path.join(kh15_folder, 'DINPUT8.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         else:
            if openkh_folder is not None:
               make_symlink(os.path.join(kh15_folder, 'LuaBackend.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
            else:
               make_symlink(os.path.join(kh15_folder, 'DBGHELP.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'lua54.dll'), os.path.join(lua_folder, 'lua54.dll'), False)
         if toml_user is not None:
            make_symlink(os.path.join(kh15_folder, 'LuaBackend.toml'), toml_user, False)
      if kh28_folder is not None:
         if is_linux:
            make_symlink(os.path.join(kh28_folder, 'DINPUT8.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         else:
            if openkh_folder is not None:
               make_symlink(os.path.join(kh28_folder, 'LuaBackend.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
            else:
               make_symlink(os.path.join(kh28_folder, 'DBGHELP.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         make_symlink(os.path.join(kh28_folder, 'lua54.dll'), os.path.join(lua_folder, 'lua54.dll'), False)
         if toml_user is not None:
            make_symlink(os.path.join(kh28_folder, 'LuaBackend.toml'), toml_user, False)
      if toml_user is not None and openkh_folder is not None and os.path.exists(toml_user):
         with open(toml_user, 'r') as toml_file:
            toml_data = tomlkit.load(toml_file)
         changes = False
         for game in ['kh1', 'kh2', 'bbs', 'recom', 'kh3d']:
            if game in toml_data and 'scripts' in toml_data[game]:
               path = os.path.join(openkh_folder, 'mod', game, 'scripts') 
               windows_path = convert_path(path)
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
   
   if kh15_folder is not None and kh2launch is not None:
      backup_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX VANILLA.exe')
      if backup_vanilla:
         if not os.path.exists(backup_path):
            print('Moving vanilla KH2 executable')
            os.rename(kh2launch, backup_path)

   for path in remove_symlinks:
      if os.path.islink(path):
         print(f'Removing symlink \'{path}\'')
         os.remove(path)

   if kh15_folder is not None and kh2launch is not None:
      backup_path = os.path.join(kh15_folder, 'KINGDOM HEARTS II FINAL MIX VANILLA.exe')
      if not backup_vanilla:
         if os.path.exists(backup_path) and not os.path.exists(kh2launch):
            print('Restoring vanilla KH2 executable')
            os.rename(backup_path, kh2launch)

   def make_launch(name, folder, has_panacea, has_luabackend):
      path = settings['launch'].get(name)
      if path is None:
         return
      exe = settings['installs'].get(name + '.exe')
      if exe is None:
         return
      os.makedirs(os.path.dirname(path), exist_ok=True)
      vars = [f'WINEPREFIX="{wineprefix}"','WINEFSYNC=1','WINE_FULLSCREEN_FSR=1']
      dlls = []
      if has_panacea and settings['mods'].get('panacea') == True:
         dlls.append('version=n,b')
      if has_luabackend and settings['mods'].get('luabackend') is not None:
         dlls.append('dinput8=n,b')
      if len(dlls) > 0:
         vars.append(f'WINEDLLOVERRIDES="{";".join(dlls)}"')
      with open(path, 'w') as sh_file:
         sh_file.write(f'#!/bin/sh\ncd "{folder}" || exit 1\n{" ".join(vars)} "{runner_wine}" "{exe}"\n')
      st = os.stat(path)
      os.chmod(path, st.st_mode | stat.S_IEXEC)

   if is_linux:
      make_launch('kh1', settings['installs']['kh1.5+2.5'], True, True)
      make_launch('kh2', settings['installs']['kh1.5+2.5'], True, True)
      make_launch('khrecom', settings['installs']['kh1.5+2.5'], True, True)
      make_launch('khbbs', settings['installs']['kh1.5+2.5'], True, True)
      make_launch('khddd', settings['installs']['kh2.8'], False, True)
      make_launch('kh0.2', settings['installs']['kh2.8'], False, False)
      make_launch('kh3', settings['installs']['kh3'], False, False)
      make_launch('khmom', settings['installs']['khmom'], False, False)

   with open(settings_path, 'w') as data_file:
      yaml.dump(settings, data_file, sort_keys=False, width=1000)


def download_latest(settings, date_key, url, filter, has_extra_folder, destination_folder, is_tar):
   date = settings['downloads'].get(date_key)
   rq = requests.get(url)
   if rq.status_code != 200:
      print(f'Error {rq.status_code}!')
      try:
         print(json.loads(rq.text)['message'])
      except:
         print(rq.text)
      if not os.path.exists(destination_folder):
         rq.raise_for_status()
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
            if not os.path.exists(destination_folder):
               rq.raise_for_status()
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
         settings['downloads'][date_key] = asset_date
         return True
   return False

def get_settings(settings_path):
   if os.path.exists(settings_path):
      with open(settings_path, 'r') as data_file:
         settings = yaml.safe_load(data_file)
   else:
      print('First-time run, welcome!')
      print('You\'ll be asked some questions about your setup. Every time you run this script, everything will be updated according to your answers. You can change them at any time by editing or deleting settings.yaml. Anything you disable later will be seamlessly reverted; all changes made by this script are reversible.')
      print()
      settings = {}
   old_settings = copy.deepcopy(settings)

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
   if (install := settings['installs']['kh1.5+2.5']) is not None:
      if 'kh1.exe' not in settings['installs']:
         settings['installs']['kh1.exe'] = os.path.join(install, 'KINGDOM HEARTS FINAL MIX.exe')
      if 'kh2.exe' not in settings['installs']:
         settings['installs']['kh2.exe'] = os.path.join(install, 'KINGDOM HEARTS II FINAL MIX.exe')
      if 'khrecom.exe' not in settings['installs']:
         settings['installs']['khrecom.exe'] = os.path.join(install, 'KINGDOM HEARTS Re_Chain of Memories.exe')
      if 'khbbs.exe' not in settings['installs']:
         settings['installs']['khbbs.exe'] = os.path.join(install, 'KINGDOM HEARTS Birth by Sleep FINAL MIX.exe')
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
   if (install := settings['installs']['kh2.8']) is not None:
      if 'khddd.exe' not in settings['installs']:
         settings['installs']['khddd.exe'] = os.path.join(install, 'KINGDOM HEARTS Dream Drop Distance.exe')
      if 'kh0.2.exe' not in settings['installs']:
         settings['installs']['kh0.2.exe'] = os.path.join(install, 'KINGDOM HEARTS 0.2 Birth by Sleep/Binaries/Win64/KINGDOM HEARTS 0.2 Birth by Sleep.exe')
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
   if (install := settings['installs']['kh3']) is not None:
      if 'kh3.exe' not in settings['installs']:
         settings['installs']['kh3.exe'] = os.path.join(install, 'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe')
   if 'khmom' not in settings['installs']:
      settings['installs']['khmom'] = None
   if (install := settings['installs']['khmom']) is not None:
      if 'khmom.exe' not in settings['installs']:
         settings['installs']['khmom.exe'] = os.path.join(install, 'KINGDOM HEARTS Melody of Memory.exe')

   if 'folder' not in settings:
      print('Now where would you like to store the extra stuff installed by this script?')
      folder = input('> ')
      settings['folder'] = os.path.expanduser(folder)
      print()
   
   base_folder = settings['folder']

   if platform.system() == 'Linux':
      if 'runner' not in settings:
         print('Linux detected: the games will be run with an automatically-configured build of Wine.')
         print()
         settings['runner'] = os.path.join(base_folder, 'runner')
      
      if 'update_runner' not in settings:
         settings['update_runner'] = True

      if 'wineprefix' not in settings:
         settings['wineprefix'] = os.path.join(base_folder, 'wineprefix')

      if 'launch' not in settings:
         launch = os.path.join(base_folder, 'launch')
         settings['launch'] = {'kh1': os.path.join(launch, 'kh1.sh'), 'khrecom': os.path.join(launch, 'khrecom.sh'), 'kh2': os.path.join(launch, 'kh2.sh'), 'khbbs': os.path.join(launch, 'khbbs.sh'), 'khddd': os.path.join(launch, 'khddd.sh'), 'kh0.2': os.path.join(launch, 'kh0.2.sh'), 'kh3': os.path.join(launch, 'kh3.sh'), 'khmom': os.path.join(launch, 'khmom.sh')}

   if 'saves' not in settings:
      saves = os.path.join(base_folder, 'Save Data')
      settings['saves'] = {'kh1.5+2.5': os.path.join(saves, 'Kingdom Hearts 1.5+2.5'), 'kh2.8': os.path.join(saves, 'Kingdom Hearts 2.8'), 'kh3': os.path.join(saves, 'Kingdom Hearts III'), 'khmom': os.path.join(saves, 'Kingdom Hearts Melody of Memory')}

   supports_mods = settings['installs']['kh1.5+2.5'] is not None or settings['installs']['kh2.8'] is not None
   if 'mods' not in settings:
      settings['mods'] = {'folder': os.path.join(base_folder, 'Mods')}
      if supports_mods:
         print('Modding applications to use:')
         print()
   if supports_mods:
      if 'refined' not in settings['mods'] and settings['installs']['kh1.5+2.5'] is not None:
         print('Kingdom Hearts ReFined: (y/n)')
         settings['mods']['refined'] = os.path.join(base_folder, 'ReFined') if yes_no() else None
         print()
      if settings['mods']['refined'] is not None:
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
         settings['mods']['randomizer'] = os.path.join(base_folder, 'Randomizer') if yes_no() else None
         print()
      if settings['mods']['randomizer'] is not None:
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
         settings['mods']['panacea'] = yes_no()
         print()
      if settings['mods'].get('panacea') == True:
         if 'panacea_settings' not in settings['mods']:
            settings['mods']['panacea_settings'] = os.path.join(base_folder, 'panacea_settings.txt')
      if 'luabackend' not in settings['mods']:
         print('LuaBackend script loader: (y/n)')
         settings['mods']['luabackend'] = os.path.join(base_folder, 'LuaBackend') if yes_no() else None
         print()
      if settings['mods']['luabackend'] is not None:
         if 'luabackend_config' not in settings['mods']:
            settings['mods']['luabackend_config'] = os.path.join(base_folder, 'LuaBackend.toml')

   with open(settings_path, 'w') as data_file:
      yaml.dump(settings, data_file, sort_keys=False, width=1000)

   return (settings, settings != old_settings)

def yes_no():
   while True:
      answer = input('> ')
      if answer in ('y','n','Y','N'):
         break
   return answer in ('y','Y')

if __name__ == '__main__':
   main()
