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
from settings import KhGame, Luabackend, OpenKh, Randomizer, Settings, get_settings, save_settings

def main():
   settings_path = pathlib.Path(__file__).parent / 'settings.yaml'
   settings = get_settings(settings_path)
   print('Starting!')

   symlinks = Symlinks()
   environment = get_environment(settings)
   
   check_saves(symlinks, environment, settings)
   
   if settings.games.kh15_25 is not None:
      symlinks.remove(settings.games.kh15_25.folder / 'reFined.cfg')
      if settings.mods.refined is not None:
         symlinks.make(settings.games.kh15_25.folder / 'reFined.cfg', settings.mods.refined.settings, is_dir=False)
   
   for game in settings.games.get_classic():
      symlinks.remove(game.folder / 'version.dll')
      symlinks.remove(game.folder / 'DINPUT8.dll')
      symlinks.remove(game.folder / 'DBGHELP.dll')
      symlinks.remove(game.folder / 'LuaBackend.dll')
      symlinks.remove(game.folder / 'LuaBackend.toml')
      symlinks.remove(game.folder / 'panacea_settings.txt')
      if settings.mods.openkh is not None and settings.mods.openkh.panacea is not None:
         restore_folder(game.folder / 'Image', game.folder / 'Image-BACKUP')

   if settings.mods.openkh is not None:
      check_openkh(settings.mods.openkh, symlinks, environment, settings, settings_path)

   if settings.mods.luabackend is not None:
      check_luabackend(settings.mods.luabackend, symlinks, environment, settings, settings_path)
   
   if settings.mods.randomizer is not None:
      check_randomizer(settings.mods.randomizer, settings, settings_path)
   
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
            run_program([os.path.join(openkh_folder, 'OpenKh.Command.IdxImg.exe'), 'hed', 'build', '-g', gameid, '-o', convert_path(os.path.join(built_mods_folder, gameid)), '-e', convert_path(enabled_mods[gameid][0]), '-f', convert_path(os.path.join(mods_folder, gameid)), '-d', convert_path(data_folder)])
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
            symlinks.make(os.path.join(folder, 'DINPUT8.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         else:
            if openkh_folder is not None:
               symlinks.make(os.path.join(folder, 'LuaBackend.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
            else:
               symlinks.make(os.path.join(folder, 'DBGHELP.dll'), os.path.join(lua_folder, 'DBGHELP.dll'), False)
         symlinks.make(os.path.join(folder, 'lua54.dll'), os.path.join(lua_folder, 'lua54.dll'), False)
         if toml_user is not None:
            symlinks.make(os.path.join(folder, 'LuaBackend.toml'), toml_user, False)
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
   
   symlinks.commit()

   make_launch('kh1', kh15_folder, True, True, False)
   make_launch('kh2', kh15_folder, True, True, True)
   make_launch('khrecom', kh15_folder, True, True, False)
   make_launch('khbbs', kh15_folder, True, True, False)
   make_launch('khddd', kh28_folder, False, True, False)
   make_launch('kh0.2', kh28_folder, False, False, False)
   make_launch('kh3', kh3_folder, False, False, False)
   make_launch('khmom', khmom_folder, False, False, False)

def set_data(data: dict[str, typing.Any], key: str, value: typing.Any) -> bool:
   current = data.get(key)
   data[key] = value
   if value != current:
      print(f'Changing {key} from {value} to {current}')
   return value != current

def backup_folder(source: pathlib.Path, backup: pathlib.Path):
   if source.exists():
      backup.mkdir(parents=True, exist_ok=True)
      for file in source.iterdir():
         relative_name = file.relative_to(source)
         shutil.copyfile(file, backup / relative_name)

def restore_folder(source: pathlib.Path, backup: pathlib.Path):
   if backup.exists():
      for file in backup.iterdir():
         relative_name = file.relative_to(backup)
         shutil.copyfile(file, source / relative_name)
      shutil.rmtree(backup)

class Environment:
   user_folder: pathlib.Path
   @abc.abstractmethod
   def convert_path(self, path: pathlib.Path) -> pathlib.Path: pass
   @abc.abstractmethod
   def run_program(self, args: list[str]) -> subprocess.CompletedProcess: pass
   @abc.abstractmethod
   def make_launch(self, name, folder, has_panacea, has_luabackend): pass
   @abc.abstractmethod
   @classmethod
   def is_linux(cls) -> bool: pass

class WindowsEnvironment(Environment):
   def __init__(self):
      self.user_folder = pathlib.Path.home()
   
   def convert_path(self, path: pathlib.Path) -> pathlib.Path:
      return path
   
   def run_program(self, args: list[str]) -> subprocess.CompletedProcess:
      return subprocess.run(args, check=True)
   
   def make_launch(self, name, folder, has_panacea, has_luabackend):
      return
   
   @classmethod
   def is_linux(cls) -> bool:
      return False

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
      
   @classmethod
   def is_linux(cls) -> bool:
      return True

def get_environment(settings: Settings) -> Environment:
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
      if (len(settings.games.get_classic()) > 0) and 'vkd3d' not in winetricks:
         # is this needed?
         print('Installing VKD3D to wineprefix')
         subprocess.run(
            ['winetricks', '-q', 'dxvk', 'vkd3d'],
            check=True,
            env=environment.wine_env
         )
      return environment
   else:
      print('Windows detected')
      return WindowsEnvironment()

class Symlinks:
   def __init__(self):
      self.remove_symlinks: set[pathlib.Path] = set()
   
   def remove(self, path: pathlib.Path):
      self.remove_symlinks.add(path)
      
   def make(self, new: pathlib.Path, existing: pathlib.Path, is_dir: bool):
      if new in self.remove_symlinks:
         self.remove_symlinks.remove(new)
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
      else:
         print(f'Can\'t create symlink in \'{new}\' pointing to \'{existing}\', file already exists!')
   
   def commit(self):
      for path in self.remove_symlinks:
         if path.is_symlink():
            print(f'Removing symlink \'{path}\'')
            path.unlink()

def handle_saves(game: KhGame, symlinks: Symlinks, environment: Environment, settings: Settings):
   path_part = game.saves_folder()
   if game.saves is not None:
      game.saves.mkdir(parents=True, exist_ok=True)
      if settings.epic_id is not None and settings.store == 'epic':
         symlinks.make(environment.user_folder / 'Documents' / path_part / 'Epic Games Store' / str(settings.epic_id), game.saves, True)
      if settings.steam_id is not None and settings.store == 'steam':
         symlinks.make(environment.user_folder / 'Documents/My Games' / path_part / 'Steam' / str(settings.steam_id), game.saves, True)
   else:
      if settings.epic_id is not None:
         symlinks.remove(environment.user_folder / 'Documents' / path_part / 'Epic Games Store' / str(settings.epic_id))
      if settings.steam_id is not None:
         symlinks.remove(environment.user_folder / 'Documents/My Games' / path_part / 'Steam' / str(settings.epic_id))

def check_saves(symlinks: Symlinks, environment: Environment, settings: Settings):
   print('Checking save folders')
   for game in settings.games.get_all():
      handle_saves(game, symlinks, environment, settings)
   if settings.games.kh15_25 is not None:
      if (save := settings.games.kh15_25.saves) and settings.mods.refined is not None:
         symlinks.make(environment.user_folder / 'Documents/Kingdom Hearts/Configuration', save, True)
         symlinks.make(environment.user_folder / 'Documents/Kingdom Hearts/Save Data', save, True)
      else:
         symlinks.remove(environment.user_folder / 'Documents/Kingdom Hearts/Configuration')
         symlinks.remove(environment.user_folder / 'Documents/Kingdom Hearts/Save Data')

def check_openkh(openkh: OpenKh, symlinks: Symlinks, environment: Environment, settings: Settings, settings_path: pathlib.Path):
   print('Checking OpenKh')
   default_manager_settings = openkh.folder / 'mods-manager.yml'
   manager_settings = openkh.settings if openkh.settings is not None else default_manager_settings
   if (openkh.update != False) or not openkh.folder.exists():
      print('Checking for OpenKh updates...')
      downloaded = download_latest(
         last_date = openkh.update if isinstance(openkh.update, datetime.datetime) else None,
         name = 'openkh',
         url = 'https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest',
         predicate = lambda x: x['name'] == 'openkh.zip',
         has_extra_folder = True,
         destination_folder = openkh.folder
      )
      if downloaded is not None:
         if openkh.update != False:
            openkh.update = downloaded
            save_settings(settings, settings_path)

   print('Checking mod manager configuration')
   symlinks.remove(default_manager_settings)
   if openkh.settings is not None:
      symlinks.make(default_manager_settings, openkh.settings, is_dir=True)
   symlinks.remove(openkh.folder / 'mods-KH1.txt')
   symlinks.remove(openkh.folder / 'mods-KH2.txt')
   symlinks.remove(openkh.folder / 'mods-BBS.txt')
   symlinks.remove(openkh.folder / 'mods-ReCoM.txt')
   symlinks.remove(openkh.folder / 'mods-KH3D.txt')
   symlinks.remove(openkh.folder / 'collection-mods-KH1.json')
   symlinks.remove(openkh.folder / 'collection-mods-KH2.json')
   symlinks.remove(openkh.folder / 'collection-mods-BBS.json')
   symlinks.remove(openkh.folder / 'collection-mods-ReCoM.json')
   symlinks.remove(openkh.folder / 'collection-mods-KH3D.json')
   if openkh.mods is not None:
      if settings.games.kh15_25 is not None:
         symlinks.make(openkh.folder / 'mods-KH1.txt', openkh.mods / 'kh1.txt', is_dir=False)
         symlinks.make(openkh.folder / 'mods-KH2.txt', openkh.mods / 'kh2.txt', is_dir=False)
         symlinks.make(openkh.folder / 'mods-BBS.txt', openkh.mods / 'bbs.txt', is_dir=False)
         symlinks.make(openkh.folder / 'mods-ReCoM.txt', openkh.mods / 'Recom.txt', is_dir=False)
         symlinks.make(openkh.folder / 'collection-mods-KH1.json', openkh.mods / 'kh1-collection.json', is_dir=False)
         symlinks.make(openkh.folder / 'collection-mods-KH2.json', openkh.mods / 'kh2-collection.json', is_dir=False)
         symlinks.make(openkh.folder / 'collection-mods-BBS.json', openkh.mods / 'bbs-collection.json', is_dir=False)
         symlinks.make(openkh.folder / 'collection-mods-ReCoM.json', openkh.mods / 'Recom-collection.json', is_dir=False)
      if settings.games.kh28 is not None:
         symlinks.make(openkh.folder / 'mods-KH3D.txt', openkh.mods / 'kh3d.txt', is_dir=False)
         symlinks.make(openkh.folder / 'collection-mods-KH3D.json', openkh.mods / 'kh3d-collection.json', is_dir=False)
   if not manager_settings.exists():
      print('Creating default mod manager configuration')
      with open(manager_settings, 'w', encoding='utf-8') as mods_file:
         mgr_data = {
            'wizardVersionNumber': 1,
            'gameEdition': 2,
         }
         yaml.dump(mgr_data, mods_file)
   with open(manager_settings, 'r', encoding='utf-8') as mods_file:
      mgr_data = yaml.load(mods_file, yaml.CLoader)
   changed = False
   if openkh.mods is not None:
      changed |= set_data(mgr_data, 'modCollectionPath', environment.convert_path(openkh.mods))
      changed |= set_data(mgr_data, 'modCollectionsPath', environment.convert_path(openkh.mods / 'collections'))
      changed |= set_data(mgr_data, 'gameModPath', environment.convert_path(openkh.mods / 'output'))
   changed |= set_data(mgr_data, 'panaceaInstalled', openkh.panacea is not None)
   changed |= set_data(mgr_data, 'pcVersion', {'steam': 'Steam', 'epic': 'EGS'}[settings.store])
   if settings.games.kh15_25 is not None:
      changed |= set_data(mgr_data, 'pcReleaseLocation', environment.convert_path(settings.games.kh15_25.folder))
   if settings.games.kh28 is not None:
      changed |= set_data(mgr_data, 'pcReleaseLocationKH3D', environment.convert_path(settings.games.kh28.folder))
   if changed:
      with open(manager_settings, 'w', encoding='utf-8') as mods_file:
         yaml.dump(mgr_data, mods_file)
   
   if openkh.panacea is not None:
      print('Checking panacea')
      for game in settings.games.get_classic():
         dll = 'version.dll' if environment.is_linux() else 'DBGHELP.dll'
         symlinks.make(game.folder / dll, openkh.folder / 'OpenKH.Panacea.dll', is_dir=False)
         symlinks.make(game.folder / dll, openkh.folder / 'OpenKH.Panacea.dll', is_dir=False)
         symlinks.make(game.folder / 'panacea_settings.txt', openkh.panacea.settings, is_dir=False)
      if not openkh.panacea.settings.exists():
         print('Creating default panacea settings')
         with open(openkh.panacea.settings, 'w', encoding='utf-8') as mods_file:
            mods_file.writelines([
               'show_console=False\n'
            ])
      with open(openkh.panacea.settings, 'r', encoding='utf-8') as mods_file:
         pana_data = dict(line.rstrip('\n').split('=', 1) for line in mods_file.readlines())
      changed = False
      path = mgr_data.get('gameModPath', openkh.folder / 'mod')
      changed |= set_data(pana_data, 'mod_path', environment.convert_path(path))
      if changed:
         with open(openkh.panacea.settings, 'r', encoding='utf-8') as mods_file:
            mods_file.writelines([f'{key}={value}\n' for key, value in pana_data.items()])
            
   if openkh.update_mods:
      print('Updating mods')
      rebuild: set[str] = set()
      mods_folder = openkh.mods if openkh.mods is not None else openkh.folder / 'mods'
      if mods_folder.exists():
         for game in mods_folder.iterdir():
            if game.is_dir():
               for root, folders, _files in game.walk():
                  if '.git' in folders:
                     print(f'Checking for updates for mod {root.name}')
                     old_hash = subprocess.run(
                        ['git', 'rev-parse', 'HEAD'],
                        cwd=root,
                        check=True,
                        stdout=subprocess.PIPE
                     ).stdout
                     subprocess.run(
                        ['git', 'pull', '--recurse-submodules'],
                        cwd=root,
                        check=True
                     )
                     new_hash = subprocess.run(
                        ['git', 'rev-parse', 'HEAD'],
                        cwd=root,
                        check=True,
                        stdout=subprocess.PIPE
                     ).stdout
                     if old_hash != new_hash:
                        rebuild.add(game.name)

def check_luabackend(luabackend: Luabackend, symlinks: Symlinks, environment: Environment, settings: Settings, settings_path: pathlib.Path):
   print('Checking luabackend')
   if (luabackend.update != False) or not luabackend.folder.exists():
      print('Checking for luabackend updates...')
      # exclude luabackend.toml
      # symlink the dll correctly
      downloaded = download_latest(
         last_date = luabackend.update if isinstance(luabackend.update, datetime.datetime) else None,
         name = 'luabackend',
         url = 'https://api.github.com/repos/Sirius902/LuaBackend/releases/latest',
         predicate = lambda x: x['name'] == 'DBGHELP.zip',
         has_extra_folder = False,
         destination_folder = luabackend.folder
      )
      if downloaded is not None:
         if luabackend.update != False:
            luabackend.update = downloaded
            save_settings(settings, settings_path)
   if not luabackend.settings.exists():
      print('Creating default luabackend settings')
      with open(luabackend.settings, 'w', encoding='utf-8') as mods_file:
         mgr_data = {}
         tomlkit.dump(mgr_data, mods_file)

def check_randomizer(randomizer: Randomizer, settings: Settings, settings_path: pathlib.Path):
   print('Checking randomizer')
   if (randomizer.update != False) or not randomizer.folder.exists():
      print('Checking for randomizer updates...')
      downloaded = download_latest(
         last_date = randomizer.update if isinstance(randomizer.update, datetime.datetime) else None,
         name = 'randomizer',
         url = 'https://api.github.com/repos/tommadness/KH2Randomizer/releases/latest',
         predicate = lambda x: x['name'] == 'Kingdom.Hearts.II.Final.Mix.Randomizer.zip',
         has_extra_folder = False,
         destination_folder = randomizer.folder
      )
      if downloaded is not None:
         if randomizer.update != False:
            randomizer.update = downloaded
            save_settings(settings, settings_path)

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
