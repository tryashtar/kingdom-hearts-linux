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
from settings import KhGame, LaunchExe, Luabackend, OpenKh, Randomizer, Settings, get_settings, save_settings

def main():
   settings_path = pathlib.Path(__file__).parent / 'settings.yaml'
   settings = get_settings(settings_path)
   print('Starting!')

   symlinks = Symlinks()
   environment = get_environment(settings)
   
   check_saves(symlinks, environment, settings)
   
   if (game := settings.games.kh15_25) is not None:
      symlinks.remove(game.folder / 'reFined.cfg')
      if (refined := settings.mods.refined) is not None:
         symlinks.make(game.folder / 'reFined.cfg', refined.settings, is_dir=False)
   
   for game in settings.games.get_classic():
      symlinks.remove(game.folder / 'version.dll')
      symlinks.remove(game.folder / 'DINPUT8.dll')
      symlinks.remove(game.folder / 'DBGHELP.dll')
      symlinks.remove(game.folder / 'LuaBackend.dll')
      symlinks.remove(game.folder / 'LuaBackend.toml')
      symlinks.remove(game.folder / 'panacea_settings.txt')
      if settings.mods.openkh is None or settings.mods.openkh.panacea is not None:
         restore_folder(game.folder / 'Image', game.folder / 'Image-BACKUP')

   if (openkh := settings.mods.openkh) is not None:
      openkh_settings = check_openkh(openkh, symlinks, environment, settings, settings_path)
   else:
      openkh_settings = None

   if (luabackend := settings.mods.luabackend) is not None:
      check_luabackend(luabackend, openkh_settings, symlinks, environment, settings, settings_path)
   
   if (randomizer := settings.mods.randomizer) is not None:
      check_randomizer(randomizer, settings, settings_path)
   
   for game in settings.games.get_all():
      for exe in game.get_exes():
         environment.make_launch(game, exe, settings)
   
   symlinks.commit()

def set_data(data, key: str, value: typing.Any) -> bool:
   current = data.get(key)
   data[key] = value
   if value != current:
      print(f'Changing {key} from {current} to {value}')
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
   @abc.abstractmethod
   def user_folder(self, game: KhGame) -> pathlib.Path: pass
   @abc.abstractmethod
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.Path: pass
   @abc.abstractmethod
   def run_program(self, game: KhGame, args: list[str]) -> subprocess.CompletedProcess: pass
   @abc.abstractmethod
   def make_launch(self, game: KhGame, exe: LaunchExe, settings: Settings): pass
   @classmethod
   @abc.abstractmethod
   def is_linux(cls) -> bool: pass

class WindowsEnvironment(Environment):
   def user_folder(self, game: KhGame) -> pathlib.Path:
      return pathlib.Path.home()
   
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.Path:
      return path
   
   def run_program(self, game: KhGame, args: list[str]) -> subprocess.CompletedProcess:
      return subprocess.run(args, check=True)
   
   def make_launch(self, game: KhGame, exe: LaunchExe, settings: Settings):
      if exe.launch is None:
         return
      exe.launch.parent.mkdir(parents=True, exist_ok=True)
      with open(exe.launch, 'w', encoding='utf-8') as sh_file:
         exe_path = exe.exe.relative_to(game.folder)
         sh_file.writelines([
            f'cd /d "{game.folder}" || exit 1\n',
            f'{exe_path}\n'
         ])
      filestat = exe.launch.stat()
      exe.launch.chmod(filestat.st_mode | stat.S_IEXEC)
   
   @classmethod
   def is_linux(cls) -> bool:
      return False

class LinuxEnvironment(Environment):
   def user_folder(self, game: KhGame) -> pathlib.Path:
      assert game.wineprefix is not None
      return game.wineprefix / 'drive_c/users' / os.getlogin()
   
   def wine_env(self, game: KhGame):
      assert game.wineprefix is not None
      return dict(os.environ, WINEPREFIX=str(game.wineprefix))
   
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.Path:
      result = subprocess.run(
         ['winepath', '-w', str(path)],
         check=True,
         stdout=subprocess.PIPE,
         stderr=subprocess.DEVNULL,
         env=self.wine_env(game)
      ).stdout.decode('utf-8').rstrip('\n')
      return pathlib.Path(result)

   def run_program(self, game: KhGame, args: list[str]) -> subprocess.CompletedProcess:
      cmds = ['wine']
      cmds.extend(args)
      return subprocess.run(
         cmds,
         check=True,
         env=self.wine_env(game)
      )
      
   def make_launch(self, game: KhGame, exe: LaunchExe, settings: Settings):
      if exe.launch is None:
         return
      assert game.wineprefix is not None
      exe.launch.parent.mkdir(parents=True, exist_ok=True)
      env_vars: dict[str, str] = {
         'WINEPREFIX': str(game.wineprefix),
         'WINEFSYNC': '1',
         'WINE_FULLSCREEN_FSR': '1',
         'WINEDEBUG': '-all'
      }
      dlls: dict[str, str] = {
         'version': 'n,b',
         'dinput8': 'n,b'
      }
      env_vars['WINEDLLOVERRIDES'] = ';'.join(f'{key}={value}' for key, value in dlls.items())
      env_vars['GAMEID'] = game.umu_id()
      env_vars['STORE'] = {'steam': 'steam', 'epic': 'egs'}[settings.store]
      with open(exe.launch, 'w', encoding='utf-8') as sh_file:
         env = ' '.join(f'{key}="{value}"' for key, value in env_vars.items())
         exe_path = exe.exe.relative_to(game.folder)
         sh_file.writelines([
            '#!/bin/sh\n',
            f'cd "{game.folder}" || exit 1\n',
            f'{env} exec wine "{exe_path}"\n'
         ])
      filestat = exe.launch.stat()
      exe.launch.chmod(filestat.st_mode | stat.S_IEXEC)
      
   @classmethod
   def is_linux(cls) -> bool:
      return True

def get_environment(settings: Settings) -> Environment:
   is_linux = platform.system() == 'Linux'
   if is_linux:
      print('Linux detected')
      environment = LinuxEnvironment()
      for game in settings.games.get_all():
         assert game.wineprefix is not None
         game.wineprefix.mkdir(parents=True, exist_ok=True)
         user_folder = environment.user_folder(game)
         if not user_folder.exists():
            print('Creating wineprefix')
            subprocess.run(
               ['wineboot'],
               check=True,
               env=environment.wine_env(game)
            )
         docs_folder = user_folder / 'Documents'
         if docs_folder.is_symlink():
            print('Unlinking new documents folder')
            docs_folder.unlink()
      for game in settings.games.get_classic():
         assert game.wineprefix is not None
         winetricks = get_winetricks(game.wineprefix)
         if 'vkd3d' not in winetricks:
            print('Installing vkd3d to wineprefix')
            subprocess.run(
               ['winetricks', '-q', 'vkd3d'],
               check=True,
               env=environment.wine_env(game)
            )
         if 'dxvk' not in winetricks:
            print('Installing dxvk to wineprefix')
            subprocess.run(
               ['winetricks', '-q', 'dxvk'],
               check=True,
               env=environment.wine_env(game)
            )
      if (game := settings.games.kh3) is not None:
         assert game.wineprefix is not None
         winetricks = get_winetricks(game.wineprefix)
         if 'wmp11' not in winetricks:
            print('Installing wmp11 to wineprefix')
            subprocess.run(
               ['winetricks', '-q', 'wmp11'],
               check=True,
               env=environment.wine_env(game)
            )
      return environment
   else:
      print('Windows detected')
      return WindowsEnvironment()

def get_winetricks(prefix: pathlib.Path) -> list[str]:
   winetricks: list[str] = []
   winetricks_log = prefix / 'winetricks.log'
   if winetricks_log.exists():
      with open(winetricks_log, 'r', encoding='utf-8') as winetricks_file:
         winetricks = [line.rstrip('\n') for line in winetricks_file]
   return winetricks

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
   user_folder = environment.user_folder(game)
   (epic_id, steam_id, store) = (settings.epic_id, settings.steam_id, settings.store)
   if game.saves is not None:
      game.saves.mkdir(parents=True, exist_ok=True)
      if epic_id is not None and store == 'epic':
         symlinks.make(user_folder / 'Documents' / path_part / 'Epic Games Store' / str(epic_id), game.saves, True)
      if steam_id is not None and store == 'steam':
         symlinks.make(user_folder / 'Documents/My Games' / path_part / 'Steam' / str(steam_id), game.saves, True)
   else:
      if epic_id is not None:
         symlinks.remove(user_folder / 'Documents' / path_part / 'Epic Games Store' / str(epic_id))
      if steam_id is not None:
         symlinks.remove(user_folder / 'Documents/My Games' / path_part / 'Steam' / str(epic_id))

def check_saves(symlinks: Symlinks, environment: Environment, settings: Settings):
   print('Checking save folders')
   for game in settings.games.get_all():
      handle_saves(game, symlinks, environment, settings)
   if (game := settings.games.kh15_25) is not None:
      user_folder = environment.user_folder(game)
      if (save := game.saves) is not None and settings.mods.refined is not None:
         symlinks.make(user_folder / 'Documents/Kingdom Hearts/Configuration', save, True)
         symlinks.make(user_folder / 'Documents/Kingdom Hearts/Save Data', save, True)
      else:
         symlinks.remove(user_folder / 'Documents/Kingdom Hearts/Configuration')
         symlinks.remove(user_folder / 'Documents/Kingdom Hearts/Save Data')

def check_openkh(openkh: OpenKh, symlinks: Symlinks, environment: Environment, settings: Settings, settings_path: pathlib.Path) -> dict[str, typing.Any]:
   print('Checking OpenKh')
   default_manager_settings = openkh.folder / 'mods-manager.yml'
   manager_settings = openkh.settings if openkh.settings is not None else default_manager_settings
   if (openkh.update != False) or not openkh.folder.exists():
      print('Checking for OpenKh updates...')
      downloaded = download_latest(
         last_date = openkh.update if isinstance(openkh.update, datetime.datetime) else None,
         url = 'https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest',
         asset_filter = lambda x: x['name'] == 'openkh.zip',
         has_extra_folder = True,
         extract_filter = None,
         destination_folder = openkh.folder
      )
      if downloaded is not None:
         if openkh.update != False:
            openkh.update = downloaded
            save_settings(settings, settings_path)

   print('Checking mod manager configuration')
   use_game = settings.games.kh15_25
   if use_game is None:
      use_game = settings.games.kh28
   if use_game is None:
      raise ValueError('No game to get wineprefix from')
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
            'gameModPath': str(environment.convert_path(use_game, openkh.folder / 'mod')),
            'gameDataPath': str(environment.convert_path(use_game, openkh.folder / 'data')),
         }
         yaml.dump(mgr_data, mods_file)
   with open(manager_settings, 'r', encoding='utf-8') as mods_file:
      mgr_data = yaml.load(mods_file, yaml.CLoader)
   changed = False
   if openkh.mods is not None:
      # until https://github.com/OpenKH/OpenKh/issues/1202 is fixed, we may need to use symlinks instead
      # still, users that manually customize it will get broken behavior both here and in openkh
      changed |= set_data(mgr_data, 'modCollectionPath', str(environment.convert_path(use_game, openkh.mods)))
      changed |= set_data(mgr_data, 'modCollectionsPath', str(environment.convert_path(use_game, openkh.mods / 'collections')))
      changed |= set_data(mgr_data, 'gameModPath', str(environment.convert_path(use_game, openkh.mods / 'output')))
   changed |= set_data(mgr_data, 'panaceaInstalled', openkh.panacea is not None)
   changed |= set_data(mgr_data, 'pcVersion', {'steam': 'Steam', 'epic': 'EGS'}[settings.store])
   if (game := settings.games.kh15_25) is not None:
      changed |= set_data(mgr_data, 'pcReleaseLocation', str(environment.convert_path(game, game.folder)))
   if (game := settings.games.kh28) is not None:
      changed |= set_data(mgr_data, 'pcReleaseLocationKH3D', str(environment.convert_path(game, game.folder)))
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
               'show_console=False\n',
            ])
      with open(openkh.panacea.settings, 'r', encoding='utf-8') as mods_file:
         pana_data = dict(line.rstrip('\n').split('=', 1) for line in mods_file.readlines())
      changed = False
      path = pathlib.Path(mgr_data['gameModPath'])
      changed |= set_data(pana_data, 'mod_path', str(environment.convert_path(use_game, path)))
      if changed:
         with open(openkh.panacea.settings, 'w', encoding='utf-8') as mods_file:
            mods_file.writelines([f'{key}={value}\n' for key, value in pana_data.items()])
   
   rebuild: set[str] = set()            
   if openkh.update_mods:
      print('Updating mods')
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

   if settings.games.kh15_25 is not None:
      mod_game(settings.games.kh15_25, {'kh1': 'KH1', 'kh2': 'KH2', 'bbs': 'BBS', 'Recom': 'ReCoM'}, rebuild, openkh, settings, settings_path)
   if settings.games.kh28 is not None:
      mod_game(settings.games.kh28, {'kh3d': 'KH3D'}, rebuild, openkh, settings, settings_path)
   
   return mgr_data

def mod_game(game: KhGame, ids: dict[str, str], rebuild: set[str], openkh: OpenKh, settings: Settings, settings_path: pathlib.Path):
   latest_modified: datetime.datetime | None = None
   for gameid, text in ids.items():
      enabled_mods_path = openkh.folder / f'mods-{text}.txt'
      if enabled_mods_path.exists():
         modified = datetime.datetime.fromtimestamp(enabled_mods_path.stat().st_mtime)
         if latest_modified is None or modified > latest_modified:
            latest_modified = modified
            if openkh.last_build is None or modified > openkh.last_build:
               rebuild.add(gameid)
   for gameid in rebuild:
      pass
   if openkh.last_build is None or (latest_modified is not None and latest_modified > openkh.last_build):
      openkh.last_build = latest_modified
      save_settings(settings, settings_path)

def check_luabackend(luabackend: Luabackend, openkh_settings: dict[str, typing.Any] | None, symlinks: Symlinks, environment: Environment, settings: Settings, settings_path: pathlib.Path):
   print('Checking luabackend')
   if (luabackend.update != False) or not luabackend.folder.exists():
      print('Checking for luabackend updates...')
      downloaded = download_latest(
         last_date = luabackend.update if isinstance(luabackend.update, datetime.datetime) else None,
         url = 'https://api.github.com/repos/Sirius902/LuaBackend/releases/latest',
         asset_filter = lambda x: x['name'] == 'DBGHELP.zip',
         has_extra_folder = False,
         extract_filter = lambda x: x.name != 'LuaBackend.toml',
         destination_folder = luabackend.folder
      )
      if downloaded is not None:
         if luabackend.update != False:
            luabackend.update = downloaded
            save_settings(settings, settings_path)
   if not luabackend.settings.exists():
      print('Creating default luabackend settings')
      with open(luabackend.settings, 'w', encoding='utf-8') as mods_file:
         data = {
            'kh1': {'scripts':[{'path':'scripts/kh1/','relative':True}]},
            'kh2': {'scripts':[{'path':'scripts/kh2/','relative':True}]},
            'bbs': {'scripts':[{'path':'scripts/bbs/','relative':True}]},
            'recom': {'scripts':[{'path':'scripts/recom/','relative':True}]},
            'kh3d': {'scripts':[{'path':'scripts/kh3d/','relative':True}]},
         }
         tomlkit.dump(data, mods_file)
   print('Checking luabackend settings')
   with open(luabackend.settings, 'r', encoding='utf-8') as mods_file:
      data = tomlkit.load(mods_file)
   changed = False
   def add_scripts(key: str, game: KhGame, version: str, path: pathlib.Path):
      script_path = environment.convert_path(game, path)
      for entry in data[version]['scripts']:
         if entry.get(key) == True:
            return set_data(entry, 'path', str(script_path))
      data[version]['scripts'].append({'path': str(script_path), 'relative': False, key: True})
      print(f'Added {key} script entry {path}')
      return True
   def add_openkh(game: KhGame, version: str) -> bool:
      if openkh_settings is None:
         return False
      game_folder = pathlib.Path(openkh_settings['gameModPath'])
      script_path = game_folder / version / 'scripts'
      add_scripts('openkh', game, version, script_path)
      return True
   if (game := settings.games.kh15_25) is not None:
      changed |= set_data(data['kh1'], 'exe', str(game.kh1.exe.relative_to(game.folder)))
      changed |= set_data(data['kh2'], 'exe', str(game.kh2.exe.relative_to(game.folder)))
      changed |= set_data(data['bbs'], 'exe', str(game.khbbs.exe.relative_to(game.folder)))
      changed |= set_data(data['recom'], 'exe', str(game.khrecom.exe.relative_to(game.folder)))
      path = pathlib.PurePath(game.saves_folder())
      if settings.store == 'steam':
         path = 'My Games' / path
      for version in ['kh1', 'kh2', 'bbs', 'recom']:
         changed |= set_data(data[version], 'game_docs', str(path))
         changed |= add_openkh(game, version)
         if luabackend.scripts is not None:
            changed |= add_scripts('lua', game, version, luabackend.scripts / version)
   if (game := settings.games.kh28) is not None:
      changed |= set_data(data['kh3d'], 'exe', str(game.khddd.exe.relative_to(game.folder)))
      path = pathlib.PurePath(game.saves_folder())
      if settings.store == 'steam':
         path = 'My Games' / path
      changed |= set_data(data['kh3d'], 'game_docs', str(path))
      changed |= add_openkh(game, 'kh3d')
      if luabackend.scripts is not None:
            changed |= add_scripts('lua', game, 'kh3d', luabackend.scripts / 'kh3d')
   if changed:
      with open(luabackend.settings, 'w', encoding='utf-8') as mods_file:
         tomlkit.dump(data, mods_file)
   for game in settings.games.get_classic():
      symlinks.make(game.folder / 'LuaBackend.toml', luabackend.settings, is_dir=False)
      if environment.is_linux():
         symlinks.make(game.folder / 'DINPUT8.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)
      else:
         if settings.mods.openkh is None:
            symlinks.make(game.folder / 'DBGHELP.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)
         else:
            symlinks.make(game.folder / 'LuaBackend.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)

def check_randomizer(randomizer: Randomizer, settings: Settings, settings_path: pathlib.Path):
   print('Checking randomizer')
   if (randomizer.update != False) or not randomizer.folder.exists():
      print('Checking for randomizer updates...')
      downloaded = download_latest(
         last_date = randomizer.update if isinstance(randomizer.update, datetime.datetime) else None,
         url = 'https://api.github.com/repos/tommadness/KH2Randomizer/releases/latest',
         asset_filter = lambda x: x['name'] == 'Kingdom.Hearts.II.Final.Mix.Randomizer.zip',
         has_extra_folder = False,
         extract_filter = None,
         destination_folder = randomizer.folder
      )
      if downloaded is not None:
         if randomizer.update != False:
            randomizer.update = downloaded
            save_settings(settings, settings_path)

def download_latest(
   last_date: datetime.datetime | None,
   url: str,
   asset_filter: typing.Callable[[dict[str, typing.Any]], bool],
   has_extra_folder: bool,
   extract_filter: typing.Callable[[pathlib.Path], bool] | None,
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
      if not asset_filter(asset):
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
            temp_zip = temp_folder_path / 'archive.zip'
            with open(temp_zip, 'wb') as file:
               file.write(response.content)
            os.makedirs(destination_folder, exist_ok=True)
            if has_extra_folder:
               temp_extract = temp_folder_path / 'extract'
               os.makedirs(temp_extract, exist_ok=True)
               extract_with_filter(temp_zip, temp_extract, extract_filter)
               shutil.copytree(os.path.join(temp_extract, os.listdir(temp_extract)[0]), destination_folder, dirs_exist_ok=True)
            else:
               extract_with_filter(temp_zip, destination_folder, extract_filter)
         return asset_date
   return None

def extract_with_filter(zip_path: pathlib.Path, destination_folder: pathlib.Path, extract_filter: typing.Callable[[pathlib.Path], bool] | None):
   archive = pyunpack.Archive(str(zip_path))
   archive.extractall(str(destination_folder))
   if extract_filter is None:
      return
   for root, _folders, files in destination_folder.walk():
      for file in files:
         full_file = root / file
         if not extract_filter(full_file):
            full_file.unlink()

if __name__ == '__main__':
   main()
