import abc
import typing
import requests
import json
import shutil
import os
import subprocess
import datetime
import tomlkit
import yaml
import tempfile
import stat
import platform
import pyunpack
import pathlib
from settings import KhGame, Settings, get_settings, save_settings

def main():
   settings_path = pathlib.Path(__file__).parent / 'settings.yaml'
   settings = get_settings(settings_path)
   print('Starting!')

   remove_symlinks: set[pathlib.Path] = set()
   def make_symlink(new: pathlib.Path, existing: pathlib.Path, is_dir: bool):
      if new in remove_symlinks:
         remove_symlinks.remove(new)
      if new.is_symlink():
         target = new.readlink()
         if target == existing:
            return
         print(f'Removing previous symlink in \'{new}\' pointing to \'{target}\'')
         new.unlink()
      if not new.exists():
         print(f'Creating symlink in \'{new}\' pointing to \'{existing}\'')
         new.parent.mkdir(parents=True, exist_ok=True)
         new.symlink_to(existing, target_is_directory=is_dir)

   is_linux = platform.system() == 'Linux'
   
   if is_linux:
      print('Linux detected')
      assert settings.wineprefix is not None
      environment = LinuxEnvironment(settings)
      # should we do steamuser?
      if not environment.user_folder.exists():
         print('Creating wineprefix')
         subprocess.run(
            ['wineboot'],
            check=True,
            env=environment.wine_env
         )
         docs_folder = environment.user_folder / 'Documents'
         if docs_folder.is_symlink():
            print('Unlinking new documents folder')
            docs_folder.unlink()
      winetricks: list[str] = []
      winetricks_log = settings.wineprefix / 'winetricks.log'
      if winetricks_log.exists():
         with open(winetricks_log, 'r', encoding='utf-8') as winetricks_file:
            winetricks = [line.rstrip('\n') for line in winetricks_file]
      if settings.mods.openkh is not None and 'dotnet6' not in winetricks:
         # is this needed?
         print('Installing dotnet6 to wineprefix')
         subprocess.run(
            ['winetricks', '-q', 'dotnet6'],
            check=True,
            env=environment.wine_env
         )
         subprocess.run(
            ['wine', 'reg', 'add', 'HKEY_CURRENT_USER\\Environment', '/f', '/v', 'DOTNET_ROOT', '/t', 'REG_SZ', '/d', 'C:\\Program Files\\dotnet'],
            check=True,
            env=environment.wine_env
         )
      if settings.mods.openkh is not None and 'dotnetdesktop6' not in winetricks:
         # is this needed?
         print('Installing dotnetdesktop6 to wineprefix')
         subprocess.run(
            ['winetricks', '-q', 'dotnetdesktop6'],
            check=True,
            env=environment.wine_env
         )
      if (settings.games.kh15_25 is not None or settings.games.kh28 is not None) and 'vkd3d' not in winetricks:
         # is this needed?
         print('Installing VKD3D to wineprefix')
         subprocess.run(
            ['winetricks', '-q', 'dxvk', 'vkd3d'],
            check=True,
            env=environment.wine_env
         )
   else:
      print('Windows detected')
      environment = WindowsEnvironment()

   print('Checking save folders')
   if settings.games.kh15_25 is not None and settings.games.kh15_25.saves is not None:
      save = settings.games.kh15_25.saves
      save.mkdir(parents=True, exist_ok=True)
      if settings.epic_id is not None and settings.games.kh15_25.store == 'epic':
         make_symlink(environment.user_folder / 'Documents/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Epic Games Store' / str(settings.epic_id), save, True)
      if settings.steam_id is not None and settings.games.kh15_25.store == 'steam':
         make_symlink(environment.user_folder / 'Documents/My Games/KINGDOM HEARTS HD 1.5+2.5 ReMIX/Steam' / str(settings.steam_id), save, True)
      if settings.mods.refined is not None:
         make_symlink(environment.user_folder / 'Documents/Kingdom Hearts/Configuration', save, True)
         make_symlink(environment.user_folder / 'Documents/Kingdom Hearts/Save Data', save, True)
   if settings.games.kh28 is not None and settings.games.kh28.saves is not None:
      save = settings.games.kh28.saves
      save.mkdir(parents=True, exist_ok=True)
      if settings.epic_id is not None and settings.games.kh28.store == 'epic':
         make_symlink(environment.user_folder / 'Documents/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Epic Games Store' / str(settings.epic_id), save, True)
      if settings.steam_id is not None and settings.games.kh28.store == 'steam':
         make_symlink(environment.user_folder / 'Documents/My Games/KINGDOM HEARTS HD 2.8 Final Chapter Prologue/Steam' / str(settings.steam_id), save, True)
   if settings.games.kh3 is not None and settings.games.kh3.saves is not None:
      save = settings.games.kh3.saves
      save.mkdir(parents=True, exist_ok=True)
      if settings.epic_id is not None and settings.games.kh3.store == 'epic':
         make_symlink(environment.user_folder / 'Documents/KINGDOM HEARTS III/Epic Games Store' / str(settings.epic_id), save, True)
      if settings.steam_id is not None and settings.games.kh3.store == 'steam':
         make_symlink(environment.user_folder / 'Documents/My Games/KINGDOM HEARTS III/Steam' / str(settings.steam_id), save, True)
   if settings.games.khmom is not None and settings.games.khmom.saves is not None:
      save = settings.games.khmom.saves
      save.mkdir(parents=True, exist_ok=True)
      if settings.epic_id is not None and settings.games.khmom.store == 'epic':
         make_symlink(environment.user_folder / 'Documents/KINGDOM HEARTS Melody of Memory/Epic Games Store' / str(settings.epic_id), save, True)
      if settings.steam_id is not None and settings.games.khmom.store == 'steam':
         make_symlink(environment.user_folder / 'Documents/My Games/KINGDOM HEARTS Melody of Memory/Steam' / str(settings.steam_id), save, True)
   
      remove_symlinks.add(os.path.join(kh15_folder, 'reFined.ini'))
      remove_symlinks.add(os.path.join(kh15_folder, 'reFined.cfg'))
      remove_symlinks.add(os.path.join(kh15_folder, 'version.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'DINPUT8.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'DBGHELP.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'LuaBackend.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'panacea_settings.txt'))
      remove_symlinks.add(os.path.join(kh15_folder, 'lua54.dll'))
      remove_symlinks.add(os.path.join(kh15_folder, 'LuaBackend.toml'))

   
   if kh28_folder is not None:
      epic_folder = os.path.join(kh28_folder, 'EPIC')
      remove_symlinks.add(os.path.join(kh28_folder, 'DINPUT8.dll'))
      remove_symlinks.add(os.path.join(kh28_folder, 'DBGHELP.dll'))
      remove_symlinks.add(os.path.join(kh28_folder, 'lua54.dll'))
      remove_symlinks.add(os.path.join(kh28_folder, 'LuaBackend.toml'))
      remove_symlinks.add(os.path.join(kh28_folder, 'panacea_settings.txt'))

   def restore_folder(kh_folder):
      backup_folder = os.path.join(kh_folder, 'BackupImage')
      source_folder = os.path.join(kh_folder, 'Image/en')
      if os.path.exists(backup_folder):
         for file in os.listdir(backup_folder):
            shutil.copyfile(os.path.join(backup_folder, file), os.path.join(source_folder, file))
         shutil.rmtree(backup_folder)

   if openkh_folder is not None:
      default_mods_folder = os.path.join(openkh_folder, 'mods')
      custom_mods_folder = settings['mods'].get('folder')
      write_mods_folder = custom_mods_folder if custom_mods_folder is not None else default_mods_folder
      mods_manager = os.path.join(openkh_folder, 'mods-manager.yml')
      pana_settings = settings['mods'].get('panacea_settings')
      if settings['mods']['update_openkh'] == True or not os.path.exists(openkh_folder):
         print('Checking for OpenKH updates...')
         downloaded = download_latest(settings, settings_path, 'openkh', 'https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest', lambda x: x['name'] == 'openkh.zip', True, openkh_folder)
      else:
         downloaded = False
      if downloaded and not os.path.exists(mods_manager):
         print('Creating default OpenKH mod manager configuration')
         with open(mods_manager, 'w', encoding='utf-8') as mods_file:
            yaml.dump({"gameEdition":2}, mods_file)
         if pana_settings is not None and not os.path.exists(pana_settings):
            print('Creating default panacea configuration')
            with open(pana_settings, 'w', encoding='utf-8') as pana_file:
               pana_file.write('show_console=False')
      if kh15_folder is not None:
         if settings['mods'].get('panacea') == True:
            if is_linux:
               make_symlink(os.path.join(kh15_folder, 'version.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
            else:
               make_symlink(os.path.join(kh15_folder, 'DBGHELP.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/avcodec-vgmstream-59.dll'), os.path.join(openkh_folder, 'avcodec-vgmstream-59.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/avformat-vgmstream-59.dll'), os.path.join(openkh_folder, 'avformat-vgmstream-59.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/avutil-vgmstream-57.dll'), os.path.join(openkh_folder, 'avutil-vgmstream-57.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/bass.dll'), os.path.join(openkh_folder, 'bass.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/bass_vgmstream.dll'), os.path.join(openkh_folder, 'bass_vgmstream.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libatrac9.dll'), os.path.join(openkh_folder, 'libatrac9.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libcelt-0061.dll'), os.path.join(openkh_folder, 'libcelt-0061.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libcelt-0110.dll'), os.path.join(openkh_folder, 'libcelt-0110.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libg719_decode.dll'), os.path.join(openkh_folder, 'libg719_decode.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libmpg123-0.dll'), os.path.join(openkh_folder, 'libmpg123-0.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libspeex-1.dll'), os.path.join(openkh_folder, 'libspeex-1.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/libvorbis.dll'), os.path.join(openkh_folder, 'libvorbis.dll'), False)
         make_symlink(os.path.join(kh15_folder, 'dependencies/swresample-vgmstream-4.dll'), os.path.join(openkh_folder, 'swresample-vgmstream-4.dll'), False)
         if pana_settings is not None:
            make_symlink(os.path.join(kh15_folder, 'panacea_settings.txt'), pana_settings, False)
      if kh28_folder is not None:
         if settings['mods'].get('panacea') == True:
            if is_linux:
               make_symlink(os.path.join(kh28_folder, 'version.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
            else:
               make_symlink(os.path.join(kh28_folder, 'DBGHELP.dll'), os.path.join(openkh_folder, 'OpenKH.Panacea.dll'), False)
         if pana_settings is not None:
            make_symlink(os.path.join(kh28_folder, 'panacea_settings.txt'), pana_settings, False)
      built_mods_folder = os.path.join(openkh_folder, 'mod')
      if os.path.exists(pana_settings):
         windows_folder = convert_path(built_mods_folder)
         changes = False
         found = False
         with open(pana_settings, 'r', encoding='utf-8') as pana_file:
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
            print('Updating Panacea mods location')
            with open(pana_settings, 'w', encoding='utf-8') as pana_file:
               for line in lines:
                  pana_file.write(line + '\n')

      remove_symlinks.add(default_mods_folder)
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-KH1.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-KH2.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-BBS.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-ReCoM.txt'))
      remove_symlinks.add(os.path.join(openkh_folder, 'mods-KH3D.txt'))
      if custom_mods_folder is not None:
         os.makedirs(custom_mods_folder, exist_ok=True)
         make_symlink(default_mods_folder, custom_mods_folder, True)
         make_symlink(os.path.join(openkh_folder, 'mods-KH1.txt'), os.path.join(custom_mods_folder, 'kh1.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-KH2.txt'), os.path.join(custom_mods_folder, 'kh2.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-BBS.txt'), os.path.join(custom_mods_folder, 'bbs.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-ReCoM.txt'), os.path.join(custom_mods_folder, 'Recom.txt'), False)
         make_symlink(os.path.join(openkh_folder, 'mods-KH3D.txt'), os.path.join(custom_mods_folder, 'kh3d.txt'), False)
      if os.path.exists(mods_manager):
         changes = False
         with open(mods_manager, 'r', encoding='utf-8') as mods_file:
            mods_data = yaml.safe_load(mods_file)
         if kh15_folder is not None:
            pc_release = convert_path(kh15_folder)
            if mods_data.get('pcReleaseLocation') != pc_release:
               print('Updating KH 1.5 install location in OpenKH mod manager')
               mods_data['pcReleaseLocation'] = pc_release
               changes = True
         if kh28_folder is not None:
            pc_release = convert_path(kh28_folder)
            if mods_data.get('pcReleaseLocationKH3D') != pc_release:
               print('Updating KH 2.8 install location in OpenKH mod manager')
               mods_data['pcReleaseLocationKH3D'] = pc_release
               changes = True
         panacea = settings['mods'].get('panacea') == True
         if mods_data.get('panaceaInstalled') != panacea:
            print('Updating panacea install status in OpenKH mod manager')
            mods_data['panaceaInstalled'] = panacea
            changes = True
         if changes:
            with open(mods_manager, 'w', encoding='utf-8') as mods_file:
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
            mod_changes[game][repo] = True
         else:
            del mod_changes[game][repo]

      mod_changes = {'kh2':{'KH2FM-Mods-Num/GoA-ROM-Edition': False, 'KH-ReFined/KH2-VanillaOST': False, 'KH-ReFined/KH2-VanillaEnemy': False, 'KH-ReFined/KH2-MultiAudio': False, 'KH-ReFined/KH2-MAIN': False}}
            if (refined_folder := settings['mods'].get('refined')) is not None:
         if settings['mods']['update_refined'] == True or not os.path.exists(refined_folder):
            print('Checking for ReFined updates...')
            download_latest(settings, settings_path, 'refined', 'https://api.github.com/repos/KH-ReFined/KH-ReFined/releases', lambda x: x['name'].endswith('.zip') or x['name'].endswith('.rar'), False, refined_folder)
            download_mod('kh2', 'KH-ReFined/KH2-MAIN')
            if settings['mods'].get('refined.vanilla_ost') == True:
               download_mod('kh2', 'KH-ReFined/KH2-VanillaOST')
            if settings['mods'].get('refined.vanilla_enemies') == True:
               download_mod('kh2', 'KH-ReFined/KH2-VanillaEnemy')
            if settings['mods'].get('refined.multi_audio') == True:
               download_mod('kh2', 'KH-ReFined/KH2-MultiAudio')
         else:
            del mod_changes['kh2']['KH-ReFined/KH2-VanillaOST']
            del mod_changes['kh2']['KH-ReFined/KH2-VanillaEnemy']
            del mod_changes['kh2']['KH-ReFined/KH2-MultiAudio']
            del mod_changes['kh2']['KH-ReFined/KH2-MAIN']
         if kh15_folder is not None:
            if os.path.exists(os.path.join(refined_folder, 'x64')):
               make_symlink(os.path.join(kh15_folder, 'x64'), os.path.join(refined_folder, 'x64'), True)
            if os.path.exists(os.path.join(refined_folder, 'Keystone.Net.dll')):
               make_symlink(os.path.join(kh15_folder, 'Keystone.Net.dll'), os.path.join(refined_folder, 'Keystone.Net.dll'), False)
            if os.path.exists(os.path.join(refined_folder, 'keystone.dll')):
               make_symlink(os.path.join(kh15_folder, 'keystone.dll'), os.path.join(refined_folder, 'keystone.dll'), False)
            if os.path.exists(os.path.join(refined_folder, 'Newtonsoft.Json.dll')):
               make_symlink(os.path.join(kh15_folder, 'Newtonsoft.Json.dll'), os.path.join(refined_folder, 'Keystone.Net.dll'), False)
            if os.path.exists(os.path.join(refined_folder, 'ViGEmClient.dll')):
               make_symlink(os.path.join(kh15_folder, 'ViGEmClient.dll'), os.path.join(refined_folder, 'ViGEmClient.dll'), False)
            if os.path.exists(os.path.join(refined_folder, 'System.Runtime.CompilerServices.Unsafe.dll')):
               make_symlink(os.path.join(kh15_folder, 'System.Runtime.CompilerServices.Unsafe.dll'), os.path.join(refined_folder, 'System.Runtime.CompilerServices.Unsafe.dll'), False)
            if kh2launch is not None:
               make_symlink(kh2launch, os.path.join(refined_folder, 'KINGDOM HEARTS II FINAL MIX.exe'), False)
            if (refined_ini := settings['mods'].get('refined_config')) is not None:
               make_symlink(os.path.join(kh15_folder, 'reFined.cfg'), refined_ini, False)
            backup_vanilla = True


      if (randomizer_folder := settings['mods'].get('randomizer')) is not None:
         if settings['mods']['update_randomizer'] == True or not os.path.exists(randomizer_folder):
            print('Checking for Randomizer updates...')
            download_latest(settings, settings_path, 'randomizer', 'https://api.github.com/repos/tommadness/KH2Randomizer/releases/latest', lambda x: x['name'] == 'Kingdom.Hearts.II.Final.Mix.Randomizer.zip', False, randomizer_folder)
            download_mod('kh2', 'KH2FM-Mods-Num/GoA-ROM-Edition')
         else:
            del mod_changes['kh2']['KH2FM-Mods-Num/GoA-ROM-Edition']

      rebuild = set()
      if settings['mods']['update_openkh_mods'] == True:
         if os.path.exists(write_mods_folder):
            for game in next(os.walk(write_mods_folder))[1]:
               for mod_dir in [os.path.join(dp, f) for dp, dn, _ in os.walk(os.path.join(write_mods_folder, game)) for f in dn]:
                  if os.path.exists(os.path.join(mod_dir, '.git')):
                     print(f'Checking for updates for mod {os.path.basename(mod_dir)}')
                     old_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=mod_dir, check=True, stdout=subprocess.PIPE).stdout
                     subprocess.run(['git', 'pull', '--recurse-submodules'], cwd=mod_dir, check=True)
                     new_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=mod_dir, check=True, stdout=subprocess.PIPE).stdout
                     if old_hash != new_hash:
                        rebuild.add(game)
      if 'last_build' not in settings:
         settings['last_build'] = {}
      enabled_mods = {}

      def handle_games(kh_folder, ids):
         for gameid, txtid in ids:
            enabled_mods_path = os.path.join(openkh_folder, f'mods-{txtid}.txt')
            if os.path.exists(enabled_mods_path):
               with open(enabled_mods_path, 'r', encoding='utf-8') as enabled_file:
                  enabled_mods[gameid] = (enabled_mods_path, [line.rstrip('\n') for line in enabled_file])
            else:
               enabled_mods[gameid] = (enabled_mods_path, [])
            if gameid in mod_changes:
               for mod,enabled in mod_changes[gameid].items():
                  if enabled and mod not in enabled_mods:
                     print(f'Enabling {gameid} mod {mod}')
                     enabled_mods[gameid][1].append(mod)
                  elif not enabled and mod in enabled_mods:
                     print(f'Disabling {gameid} mod {mod}')
                     enabled_mods[gameid][1].remove(mod)
            last_build = settings['last_build'].get(gameid, [])
            if enabled_mods[gameid][1] != last_build:
               rebuild.add(gameid)
               with open(enabled_mods_path, 'w', encoding='utf-8') as enabled_file:
                  for line in enabled_mods[gameid][1]:
                     enabled_file.write(line + '\n')
         for gameid in rebuild:      
            data_folder = os.path.join(openkh_folder, 'data', gameid)
            source_folder = os.path.join(kh_folder, 'Image/en')
            restore_folder(kh_folder)
            if not os.path.exists(data_folder):
               print(f'Extracting {gameid} data (this will take some time)')
               for file in os.listdir(source_folder):
                  if file.startswith(f'{gameid}_') and os.path.splitext(file)[1] == '.hed':
                     run_program([os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'extract', '-n', '-o', convert_path(data_folder), convert_path(os.path.join(source_folder, file))])
               for file in os.listdir(os.path.join(data_folder, 'original')):
                  shutil.move(os.path.join(data_folder, 'original', file), data_folder)
            print(f'Building {gameid} mods')
            run_program([os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'build', '-g', gameid, '-o', convert_path(os.path.join(built_mods_folder, gameid)), '-e', convert_path(enabled_mods[gameid][0]), '-f', convert_path(os.path.join(write_mods_folder, gameid)), '-d', convert_path(data_folder)])
            patch_folder = os.path.join(openkh_folder, 'patched')
            if settings['mods'].get('panacea') != True:
               backup_folder = os.path.join(kh_folder, 'BackupImage')
               source_folder = os.path.join(kh_folder, 'Image/en')
               print(f'Patching {gameid} mods')
               run_program([os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'full-patch', '-b', convert_path(os.path.join(built_mods_folder, gameid)), '-o', convert_path(patch_folder), '-f', convert_path(source_folder)])
               os.makedirs(backup_folder, exist_ok=True)
               for file in os.listdir(patch_folder):
                  backup_path = os.path.join(backup_folder, file)
                  write_path = os.path.join(source_folder, file)
                  if not os.path.exists(backup_path):
                     shutil.copyfile(write_path, backup_path)
                  shutil.copyfile(os.path.join(patch_folder, file), write_path)
               shutil.rmtree(patch_folder)
            settings['last_build'][gameid] = enabled_mods[gameid][1]
      
      if kh15_folder is not None:
         handle_games(kh15_folder, [('kh1', 'KH1'), ('kh2', 'KH2'), ('bbs', 'BBS'), ('Recom', 'ReCoM')])
      if kh28_folder is not None:
         handle_games(kh28_folder, [('kh3d', 'KH3D')])

   else:
      if kh15_folder is not None:
         restore_folder(kh15_folder)
      if kh28_folder is not None:
         restore_folder(kh28_folder)
   
   if (lua_folder := settings['mods'].get('luabackend')) is not None:
      if settings['mods']['update_luabackend'] == True or not os.path.exists(lua_folder):
         print('Checking for LuaBackend updates...')
         download_latest(settings, settings_path, 'luabackend', 'https://api.github.com/repos/Sirius902/LuaBackend/releases/latest', lambda x: x['name'] == 'DBGHELP.zip', False, lua_folder)
      toml_user = settings['mods'].get('luabackend_config')
      toml_default = os.path.join(lua_folder, 'LuaBackend.toml')
      if os.path.exists(toml_default):
         if toml_user is not None:
            if not os.path.exists(toml_user):
               print('Creating default LuaBackend.toml configuration')
               shutil.copyfile(toml_default, toml_user)
         else:
            for folder in [kh15_folder, kh28_folder]:
               if folder is not None:
                  shutil.copyfile(toml_default, os.path.join(kh15_folder, kh28_folder))
         os.remove(toml_default)
      for folder in [kh15_folder, kh28_folder]:
         if folder is None:
            continue
         if is_linux:
            make_symlink(os.path.join(folder, 'DINPUT8.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         else:
            if openkh_folder is not None:
               make_symlink(os.path.join(folder, 'LuaBackend.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
            else:
               make_symlink(os.path.join(folder, 'DBGHELP.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         make_symlink(os.path.join(folder, 'lua54.dll'), os.path.join(lua_folder, 'lua54.dll'), False)
         if toml_user is not None:
            make_symlink(os.path.join(folder, 'LuaBackend.toml'), toml_user, False)
      if openkh_folder is not None:
         for folder in [kh15_folder, kh28_folder]:
            if folder is None:
               continue
            toml_path = os.path.join(folder, 'LuaBackend.toml')
            with open(toml_path, 'r', encoding='utf-8') as toml_file:
               toml_data = tomlkit.load(toml_file)
            changes = False
            for game in ['kh1', 'kh2', 'bbs', 'recom', 'kh3d']:
               gamedata = toml_data.get(game)
               if gamedata is not None:
                  scripts = gamedata.get('scripts')
                  if scripts is not None:
                     path = os.path.join(openkh_folder, 'mod', game, 'scripts') 
                     windows_path = convert_path(path)
                     found = False
                     for script in scripts:
                        if 'openkh' in script and script['openkh'] == True:
                           found = True
                           if script['path'] != windows_path:
                              script['path'] = windows_path
                              print(f'Adding OpenKH scripts folder \'{path}\' to LuaBackend configuration')
                              changes = True
                           break
                     if not found:
                        changes = True
                        print(f'Adding OpenKH scripts folder \'{path}\' to LuaBackend configuration')
                        scripts.append({'path':windows_path,'relative':False,'openkh':True})
            if changes:
               with open(toml_user, 'w', encoding='utf-8') as toml_file:
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

   make_launch('kh1', kh15_folder, True, True, False)
   make_launch('kh2', kh15_folder, True, True, True)
   make_launch('khrecom', kh15_folder, True, True, False)
   make_launch('khbbs', kh15_folder, True, True, False)
   make_launch('khddd', kh28_folder, False, True, False)
   make_launch('kh0.2', kh28_folder, False, False, False)
   make_launch('kh3', kh3_folder, False, False, False)
   make_launch('khmom', khmom_folder, False, False, False)

class Environment(abc.ABC):
   @abc.abstractmethod
   def convert_path(self, path: pathlib.Path) -> pathlib.Path: pass
   @abc.abstractmethod
   def run_program(self, args: list[str]) -> subprocess.CompletedProcess: pass
   @abc.abstractmethod
   def make_launch(self, name, folder, has_panacea, has_luabackend): pass

class WindowsEnvironment(Environment):
   def __init__(self):
      self.user_folder = pathlib.Path.home()
   
   def convert_path(self, path: pathlib.Path) -> pathlib.Path:
      return path
   
   def run_program(self, args: list[str]) -> subprocess.CompletedProcess:
      return subprocess.run(args, check=True)
   
   def make_launch(self, name, folder, has_panacea, has_luabackend):
      return

class LinuxEnvironment(Environment):
   def __init__(self, settings: Settings):
      assert settings.wineprefix is not None
      self.wine_env = dict(os.environ, WINEPREFIX=str(settings.wineprefix))
      self.user_folder = settings.wineprefix / 'drive_c/users' / os.getlogin()
      
   def convert_path(self, path: pathlib.Path) -> pathlib.Path:
      result = subprocess.run(
         ['winepath', '-w', str(path)],
         check=True,
         stdout=subprocess.PIPE,
         stderr=subprocess.DEVNULL,
         env=self.wine_env
      ).stdout.decode('utf-8').rstrip('\n')
      return pathlib.Path(result)

   def run_program(self, args: list[str]) -> subprocess.CompletedProcess:
      cmds = ['wine']
      cmds.extend(args)
      return subprocess.run(
         cmds,
         check=True,
         env=self.wine_env
      )
      
   def make_launch(self, name, folder, has_panacea, has_luabackend):
      if folder is None:
         return
      path = settings['launch'].get(name)
      if path is None:
         return 
      exe = settings['installs'].get(name + '.exe')
      if exe is None:
         return
      os.makedirs(os.path.dirname(path), exist_ok=True)
      env_vars = [f'WINEPREFIX="{wineprefix}"','WINEFSYNC=1','WINE_FULLSCREEN_FSR=1','WINEDEBUG=-all']
      dlls = []
      if has_panacea and settings['mods'].get('panacea') == True:
         dlls.append('version=n,b')
      if has_luabackend and settings['mods'].get('luabackend') is not None:
         dlls.append('dinput8=n,b')
      if len(dlls) > 0:
         env_vars.append(f'WINEDLLOVERRIDES="{";".join(dlls)}"')
      gameid = {'kh1':'umu-2552430','kh2':'umu-2552430','khrecom':'umu-2552430','khbbs':'umu-2552430','khddd':'umu-2552430','kh0.2':'umu-2552450','kh3':'umu-2552450','khmom':'umu-2552430'}
      env_vars.append(f'GAMEID="{gameid[name]}"')
      env_vars.append('STORE="egs"')
      with open(path, 'w', encoding='utf-8') as sh_file:
         sh_file.write(f'#!/bin/sh\ncd "{folder}" || exit 1\n{" ".join(env_vars)} exec umu-run "{exe}"\n')
      st = os.stat(path)
      os.chmod(path, st.st_mode | stat.S_IEXEC)

def download_latest(
   last_date: datetime.datetime | None,
   name: str,
   url: str,
   predicate: typing.Callable[[dict[str, typing.Any]], bool],
   has_extra_folder: bool,
   destination_folder: pathlib.Path
) -> datetime.datetime | None:
   response = requests.get(url, timeout=10)
   if response.status_code != 200:
      print(f'Error {response.status_code}!')
      try:
         print(json.loads(response.text)['message'])
      except json.JSONDecodeError:
         print(response.text)
      if not os.path.exists(destination_folder):
         response.raise_for_status()
      return None
   if url.endswith('/releases'):
      newest: datetime.datetime | None = None
      release: dict[str, typing.Any] | None = None
      releases: list[dict[str, typing.Any]] = json.loads(response.text)
      for next_release in releases:
         release_time = datetime.datetime.fromisoformat(next_release['published_at'].replace('Z', '+00:00'))
         if newest is None or release_time > newest:
            newest = release_time
            release = next_release
      if release is None:
         return None
   else:
      release = json.loads(response.text)
      assert release is not None
   for asset in release['assets']:
      if not predicate(asset):
         continue
      asset_date = datetime.datetime.fromisoformat(asset['updated_at'].replace('Z', '+00:00'))
      if last_date is None or asset_date > last_date or not os.path.exists(destination_folder):
         print(f'Downloading update: {release["tag_name"]}')
         response = requests.get(asset['browser_download_url'], timeout=10)
         if response.status_code != 200:
            print(f'Error {response.status_code}!')
            print(response.text)
            if not os.path.exists(destination_folder):
               response.raise_for_status()
            return None
         with tempfile.TemporaryDirectory() as temp_folder:
            temp_folder_path = pathlib.Path(temp_folder)
            temp_zip = temp_folder_path / f'{name}.zip'
            with open(temp_zip, 'wb') as file:
               file.write(response.content)
            os.makedirs(destination_folder, exist_ok=True)
            if has_extra_folder:
               temp_extract = temp_folder_path / name
               os.makedirs(temp_extract, exist_ok=True)
               pyunpack.Archive(str(temp_zip)).extractall(str(temp_extract))
               shutil.copytree(os.path.join(temp_extract, os.listdir(temp_extract)[0]), destination_folder, dirs_exist_ok=True)
            else:
               pyunpack.Archive(str(temp_zip)).extractall(str(destination_folder))
         return asset_date
   return None

if __name__ == '__main__':
   main()
