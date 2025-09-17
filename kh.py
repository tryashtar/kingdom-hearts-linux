import abc
import argparse
import datetime
import json
import os
import pathlib
import platform
import shlex
import shutil
import stat
import subprocess
import tempfile
import tomlkit
import mslex
import pyunpack
import requests
import tomlkit.items
import typing
import yaml
from settings import Games, Kh1525, Kh28, Kh3, Kh3Mods, KhGame, KhMom, LaunchExe, LaunchKh02, LaunchKh1, LaunchKh2, LaunchKh3, LaunchKhBbs, LaunchKhDdd, LaunchKhMom, LaunchKhRecom, Luabackend, Mods, OpenKh, Panacea, Randomizer, Refined, Settings, WineRuntime, get_settings, save_settings

def main():
   games: list[str] = ['kh1', 'kh2', 'khrecom', 'khbbs', 'khddd']
   parser = argparse.ArgumentParser()
   parser.add_argument('--settings', type=pathlib.Path, default=pathlib.Path(__file__).parent / 'settings.yaml')
   commands = parser.add_subparsers(dest='command', required=True)
   commands.add_parser('update')
   mods = commands.add_parser('mods')
   mods.add_argument('game', type=str, choices=games)
   mods_action = mods.add_subparsers(dest='action', required=True)
   mods_add = mods_action.add_parser('add')
   mods_add.add_argument('mod', type=pathlib.PurePath)
   mods_enable = mods_action.add_parser('enable')
   mods_enable.add_argument('mod', type=pathlib.PurePath)
   enable_order = mods_enable.add_subparsers(dest='order', required=True)
   enable_order.add_parser('top')
   enable_order.add_parser('bottom')
   enable_above = enable_order.add_parser('above')
   enable_above.add_argument('existing', type=pathlib.PurePath)
   enable_below = enable_order.add_parser('below')
   enable_below.add_argument('existing', type=pathlib.PurePath)
   mods_disable = mods_action.add_parser('disable')
   mods_disable.add_argument('mod', type=pathlib.PurePath)
   args = parser.parse_args()
   settings_path: pathlib.Path = args.settings
   if not settings_path.exists():
      initial_run(settings_path)
      return
   settings = get_settings(settings_path)
   match args.command:
      case 'mods':
         if (openkh := settings.mods.openkh) is None:
            print('OpenKh not configured in settings')
            return
         handle_mods(args, openkh, settings, settings_path)
      case 'update':
         update(settings, args.settings)

def handle_mods(args: argparse.Namespace, openkh: OpenKh, settings: Settings, settings_path: pathlib.Path):
   symlinks = Symlinks()
   environment = get_environment(settings)
   openkh_settings = check_openkh(openkh, symlinks, environment, settings, settings_path)
   match args.action:
      case 'add':
         download_mod(args.game, args.mod, environment, settings, openkh, openkh_settings)
      case 'enable':
         order: ModOrder = args.order if args.order in ['top', 'bottom'] else (args.order, args.existing)
         enable_mod(args.game, args.mod, order, environment, settings, openkh, openkh_settings)
      case 'disable':
         disable_mod(args.game, args.mod, environment, settings, openkh, openkh_settings)
   symlinks.commit()

def update(settings: Settings, settings_path: pathlib.Path):
   print('Updating installations')

   symlinks = Symlinks()
   environment = get_environment(settings)
   
   check_saves(symlinks, environment, settings)
   
   if (game := settings.games.kh15_25) is not None:
      folder = game.get_workspace()
      symlinks.remove(folder / 'reFined.cfg')
      if (refined := settings.mods.refined) is not None:
         symlinks.make(folder / 'reFined.cfg', refined.settings, is_dir=False)

   for game in settings.games.get_classic():
      folder = game.get_workspace()
      symlinks.remove(game.folder / 'version.dll')
      symlinks.remove(game.folder / 'DINPUT8.dll')
      symlinks.remove(game.folder / 'DBGHELP.dll')
      symlinks.remove(folder / 'LuaBackend.dll')
      symlinks.remove(folder / 'LuaBackend.toml')
      symlinks.remove(folder / 'panacea_settings.txt')
      symlinks.remove(folder / 'dependencies/avcodec-vgmstream-59.dll')
      symlinks.remove(folder / 'dependencies/avformat-vgmstream-59.dll')
      symlinks.remove(folder / 'dependencies/avutil-vgmstream-57.dll')
      symlinks.remove(folder / 'dependencies/bass.dll')
      symlinks.remove(folder / 'dependencies/bass_vgmstream.dll')
      symlinks.remove(folder / 'dependencies/libatrac9.dll')
      symlinks.remove(folder / 'dependencies/libcelt-0061.dll')
      symlinks.remove(folder / 'dependencies/libcelt-0110.dll')
      symlinks.remove(folder / 'dependencies/libg719_decode.dll')
      symlinks.remove(folder / 'dependencies/libmpg123-0.dll')
      symlinks.remove(folder / 'dependencies/libspeex-1.dll')
      symlinks.remove(folder / 'dependencies/libvorbis.dll')
      symlinks.remove(folder / 'dependencies/swresample-vgmstream-4.dll')
      if settings.mods.openkh is None or settings.mods.openkh.panacea is not None:
         restore_folder(game.folder / 'Image', game.folder / 'Image-BACKUP')

   if (game := settings.games.kh3) is not None:
      mods = game.folder / 'KINGDOM HEARTS III/Content/Paks/~mods'
      symlinks.remove(mods)
      if (kh3 := settings.mods.kh3) is not None:
         symlinks.make(mods, kh3.folder, is_dir=True)
   
   if (openkh := settings.mods.openkh) is not None:
      openkh_settings = check_openkh(openkh, symlinks, environment, settings, settings_path)
   else:
      openkh_settings = None
   
   if (luabackend := settings.mods.luabackend) is not None:
      check_luabackend(luabackend, openkh_settings, symlinks, environment, settings, settings_path)
   
   if (randomizer := settings.mods.randomizer) is not None:
      check_randomizer(randomizer, settings, settings_path)
   
   if (openkh := settings.mods.openkh) is not None and openkh_settings is not None:
      mod_games(openkh, openkh_settings, environment, settings, settings_path)
   
   if (game := settings.games.kh15_25) is not None:
      make_launch(game, game.kh1, environment, settings, lua=True, openkh=True, refined=False, kh3=False)
      make_launch(game, game.kh2, environment, settings, lua=True, openkh=True, refined=True, kh3=False)
      make_launch(game, game.khbbs, environment, settings, lua=True, openkh=True, refined=False, kh3=False)
      make_launch(game, game.khrecom, environment, settings, lua=True, openkh=True, refined=False, kh3=False)
   if (game := settings.games.kh28) is not None:
      make_launch(game, game.khddd, environment, settings, lua=True, openkh=True, refined=False, kh3=False)
      make_launch(game, game.kh02, environment, settings, lua=False, openkh=False, refined=False, kh3=False)
   if (game := settings.games.kh3) is not None:
      make_launch(game, game.kh3, environment, settings, lua=False, openkh=False, refined=False, kh3=True)
   if (game := settings.games.khmom) is not None:
      make_launch(game, game.khmom, environment, settings, lua=False, openkh=False, refined=False, kh3=False)
      
   symlinks.commit()

def initial_run(settings_path: pathlib.Path) -> Settings:
   print('First-time run, welcome!')
   print('You\'ll be asked some questions about your setup. Every time you run this script, everything will be updated according to your answers. You can change them at any time by editing or deleting settings.yaml. Anything you disable later will be seamlessly reverted; all changes made by this script are reversible.')
   print()
   print('Input the folders where your Kingdom Hearts games are installed.')
   print('For any you don\'t have, just press enter.')
   print()
   kh1525_install = input_game_path('Kingdom Hearts HD 1.5+2.5 ReMIX', pathlib.PurePath('KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe'))
   kh28_install = input_game_path('Kingdom Hearts HD 2.8 Final Chapter Prologue', pathlib.PurePath('KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe'))
   kh3_install = input_game_path('Kingdom Hearts III', LaunchKh3.exe())
   khmom_install = input_game_path('Kingdom Hearts Melody of Memory', LaunchKhMom.exe())
   print('Now where would you like to store the extra stuff installed by this script?')
   folder = input('> ')
   extra_folder = pathlib.Path(os.path.expanduser(folder))
   print()
   print('Modding applications to use:')
   print('Kingdom Hearts ReFined: (y/n)')
   refined = False
   randomizer = False
   openkh = False
   luabackend = False
   if yes_no():
      refined = True
      openkh = True
   print('Kingdom Hearts II Randomizer: (y/n)')
   if yes_no():
      randomizer = True
      openkh =  True
   if not openkh:
      print('OpenKh mod manager: (y/n)')
      if yes_no():
         openkh = True
   print('Luabackend script loader: (y/n)')
   if yes_no():
      luabackend = True
   is_linux = platform.system() == 'Linux'
   wineprefix = extra_folder / 'wineprefix' if is_linux else None
   def launch(name: str) -> pathlib.Path | None:
      return extra_folder / 'launch' / name if is_linux else None
   saves = extra_folder / 'saves'
   settings = Settings(
      epic_id = None,
      steam_id = None,
      runtime = None,
      store = 'epic',
      games = Games(
         kh15_25 = None if kh1525_install is None else Kh1525(
            wineprefix = wineprefix,
            saves = saves,
            folder = kh1525_install,
            workspace = None,
            kh1 = LaunchKh1(launch = launch('kh1')),
            kh2 = LaunchKh2(launch = launch('kh2')),
            khrecom = LaunchKhRecom(launch = launch('khrecom')),
            khbbs = LaunchKhBbs(launch = launch('khbbs')),
         ),
         kh28 = None if kh28_install is None else Kh28(
            wineprefix = wineprefix,
            saves = saves,
            folder = kh28_install,
            workspace = None,
            khddd = LaunchKhDdd(launch = launch('khddd')),
            kh02 = LaunchKh02(launch = launch('kh02')),
         ),
         kh3 = None if kh3_install is None else Kh3(
            wineprefix = wineprefix,
            saves = saves,
            folder = kh3_install,
            workspace = None,
            kh3 = LaunchKh3(launch = launch('kh3')),
         ),
         khmom = None if khmom_install is None else KhMom(
            wineprefix = wineprefix,
            saves = saves,
            folder = khmom_install,
            workspace = None,
            khmom = LaunchKhMom(launch = launch('khmom')),
         ),
      ),
      mods = Mods(
         openkh = None if not openkh else OpenKh(
            folder = extra_folder / 'openkh',
            mods = extra_folder / 'mods',
            settings = None,
            panacea = Panacea(
               settings = extra_folder / 'panacea/panacea_settings.txt'
            ),
            update_mods = True,
            update = True,
            last_build = None,
         ),
         luabackend = None if not luabackend else Luabackend(
            folder = extra_folder / 'luabackend',
            settings = extra_folder / 'luabackend/LuaBackend.toml',
            scripts = extra_folder / 'scripts',
            update = True,
         ),
         refined = None if not refined else Refined(
            folder = extra_folder / 'refined',
            settings = extra_folder / 'refined/reFined.cfg',
         ),
         randomizer = None if not randomizer else Randomizer(
            folder = extra_folder / 'randomizer',
            update = True
         ),
         kh3 = None if kh3_install is None else Kh3Mods(
            folder = extra_folder / 'mods/kh3'
         ),
      ),
   )
   save_settings(settings, settings_path)
   return settings

def yes_no():
   while True:
      answer = input('> ')
      if answer in ('y','Y'):
         return True
      if answer in ('n','N'):
         return False
      print('Type Y for yes, or N for no')

def input_game_path(name: str, exe: pathlib.PurePath) -> pathlib.Path | None:
   print(name + ':')
   while True:
      install = input('> ')
      if install == '':
         return None
      install_path = pathlib.Path(os.path.expanduser(install))
      if (install_path / exe).exists():
         return install_path
      print(f'Couldn\t find \'{exe}\' in that folder. Please try again.')

def get_access_folders(game: KhGame, settings: Settings, lua: bool, openkh: bool, refined: bool, kh3: bool) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
   readable: list[pathlib.Path] = [game.folder]
   if game.workspace is not None:
      readable.append(game.workspace)
   if lua and (luabackend := settings.mods.luabackend) is not None:
      readable.append(luabackend.folder)
      readable.append(luabackend.settings.parent)
      if luabackend.scripts is not None:
         readable.append(luabackend.scripts)
   if openkh and (okh := settings.mods.openkh) is not None:
      readable.append(okh.folder)
      if okh.panacea is not None:
         readable.append(okh.panacea.settings.parent)
      if okh.mods is not None:
         readable.append(okh.mods)
   if refined and settings.mods.refined is not None:
      readable.append(settings.mods.refined.settings.parent)
   if kh3 and settings.mods.kh3 is not None:
      readable.append(settings.mods.kh3.folder)
   readable = list(dict.fromkeys(readable))
   writable: list[pathlib.Path] = []
   if game.saves is not None:
      writable.append(game.saves)
   return (readable, writable)

def set_data(data: dict[str, str] | tomlkit.items.AbstractTable, key: str, value: typing.Any) -> bool:
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
      shutil.rmtree(source)
      source.mkdir(parents=True, exist_ok=True)
      for file in backup.iterdir():
         relative_name = file.relative_to(backup)
         shutil.copyfile(file, source / relative_name)
      shutil.rmtree(backup)

class Environment:
   @abc.abstractmethod
   def user_folder(self, game: KhGame) -> pathlib.Path: pass
   @abc.abstractmethod
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.PureWindowsPath: pass
   @abc.abstractmethod
   def convert_path_back(self, game: KhGame, path: pathlib.PureWindowsPath) -> pathlib.Path: pass
   @abc.abstractmethod
   def run_program(self, game: KhGame, args: list[str]) -> subprocess.CompletedProcess: pass
   @abc.abstractmethod
   def make_launch(self, file: typing.TextIO, directory: pathlib.PureWindowsPath, exe: pathlib.PureWindowsPath, env: dict[str, str]): pass
   @classmethod
   @abc.abstractmethod
   def is_linux(cls) -> bool: pass

class WindowsEnvironment(Environment):
   def user_folder(self, game: KhGame) -> pathlib.Path:
      return pathlib.Path.home()
   
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.PureWindowsPath:
      return pathlib.PureWindowsPath(path)
   
   def convert_path_back(self, game: KhGame, path: pathlib.PureWindowsPath) -> pathlib.Path:
      return pathlib.Path(path)
   
   def run_program(self, game: KhGame, args: list[str]) -> subprocess.CompletedProcess:
      return subprocess.run(args, check=True)
   
   def make_launch(self, file: typing.TextIO, directory: pathlib.PureWindowsPath, exe: pathlib.PureWindowsPath, env: dict[str, str]):
      file.writelines([
         '@echo off',
         f'cd /d {mslex.quote(str(directory))} || exit 1\n',
         *[f'set {key}={mslex.quote(value)}' for key, value in env.items()],
         f'{mslex.quote(str(exe))}\n',
      ])
   
   @classmethod
   def is_linux(cls) -> bool:
      return False

class LinuxEnvironment(Environment):
   def __init__(self, runtime: WineRuntime):
      self.runtime = runtime
   
   def user_folder(self, game: KhGame) -> pathlib.Path:
      assert game.wineprefix is not None
      return game.wineprefix / 'drive_c/users' / os.getlogin()
   
   def wine_env(self, game: KhGame) -> dict[str, str]:
      assert game.wineprefix is not None
      env: dict[str, str] = dict(os.environ)
      env['WINEPREFIX'] = str(game.wineprefix)
      if self.runtime == 'umu':
         env['PROTONPATH'] = 'GE-Proton'
      return env
   
   def convert_path(self, game: KhGame, path: pathlib.Path) -> pathlib.PureWindowsPath:
      result = subprocess.run(
         ['winepath', '--windows', str(path)],
         check=True,
         stdout=subprocess.PIPE,
         stderr=subprocess.DEVNULL,
         env=self.wine_env(game)
      ).stdout.decode('utf-8').rstrip('\n')
      return pathlib.PureWindowsPath(result)
   
   def convert_path_back(self, game: KhGame, path: pathlib.PureWindowsPath) -> pathlib.Path:
      result = subprocess.run(
         ['winepath', '--unix', str(path)],
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
   
   def make_launch(self, file: typing.TextIO, directory: pathlib.PureWindowsPath, exe: pathlib.PureWindowsPath, env: dict[str, str]):
      env_str = ' '.join(f'{key}={shlex.quote(value)}' for key, value in env.items())
      entry = {'wine': 'wine', 'umu': 'umu-run'}[self.runtime]
      file.writelines([
         '#!/bin/sh\n',
         f'{env_str} exec {entry} start /wait /b /d {shlex.quote(str(directory))} {shlex.quote(str(exe))}\n',
      ])
   
   @classmethod
   def is_linux(cls) -> bool:
      return True

def get_enabled_mods(game: str, openkh: OpenKh) -> list[pathlib.PurePath]:
   game_txt = {'kh1': 'KH1', 'kh2': 'KH2', 'khbbs': 'BBS', 'khrecom': 'ReCoM', 'khddd': 'KH3D'}[game]
   enabled_path = openkh.folder / f'mods-{game_txt}.txt'
   if enabled_path.exists():
      with open(enabled_path, 'r', encoding='utf-8') as file:
         return [pathlib.PurePath(line.rstrip('\n')) for line in file.readlines()]
   return []

def set_enabled_mods(game: str, mods: list[pathlib.PurePath], openkh: OpenKh):
   game_txt = {'kh1': 'KH1', 'kh2': 'KH2', 'khbbs': 'BBS', 'khrecom': 'ReCoM', 'khddd': 'KH3D'}[game]
   enabled_path = openkh.folder / f'mods-{game_txt}.txt'
   with open(enabled_path, 'w', encoding='utf-8') as file:
      file.writelines(str(line) + '\n' for line in mods)

def download_mod(game: str, mod: pathlib.PurePath, environment: Environment, settings: Settings, openkh: OpenKh, openkh_settings: dict[str, typing.Any]):
   url = f'https://github.com/{mod}'
   folder = mod_folder(game, mod, environment, settings, openkh_settings)
   if folder is None:
      print(f'Game {game} not found')
      return
   folder.mkdir(parents=True, exist_ok=True)
   if (folder / '.git').exists():
      subprocess.run(
         ['git', 'pull', '--recurse-submodules'],
         cwd=folder,
         check=True
      )
   else:
      subprocess.run(
         ['git', 'clone', '--recurse-submodules', url, str(folder)],
         check=True
      )
   mods = get_enabled_mods(game, openkh)
   mods.insert(0, mod)
   set_enabled_mods(game, mods, openkh)

def mod_folder(game: str, mod: pathlib.PurePath, environment: Environment, settings: Settings, openkh_settings: dict[str, typing.Any]) -> pathlib.Path | None:
   mod_in = pathlib.PureWindowsPath(openkh_settings['modCollectionPath'])
   game_obj: KhGame | None = {
      'kh1': settings.games.kh15_25,
      'kh2': settings.games.kh15_25,
      'khbbs': settings.games.kh15_25,
      'khrecom': settings.games.kh15_25,
      'khddd': settings.games.kh28
   }[game]
   if game_obj is None:
      return None
   local_in = environment.convert_path_back(game_obj, mod_in)
   return local_in / game / mod

def disable_mod(game: str, mod: pathlib.PurePath, environment: Environment, settings: Settings, openkh: OpenKh, openkh_settings: dict[str, typing.Any]):
   if (folder := mod_folder(game, mod, environment, settings, openkh_settings)) is None or not folder.exists():
      print(f'Mod {mod} in {game} not found')
      return
   enabled_mods = get_enabled_mods(game, openkh)
   if mod not in enabled_mods:
      print(f'Mod {mod} in {game} is already disabled')
      return
   print(f'Disabled mod {mod} in {game}')
   enabled_mods.remove(mod)
   set_enabled_mods(game, enabled_mods, openkh)

ModOrder = typing.Literal['top', 'bottom'] | tuple[typing.Literal['above', 'below'], pathlib.PurePath]

def enable_mod(game: str, mod: pathlib.PurePath, order: ModOrder, environment: Environment, settings: Settings, openkh: OpenKh, openkh_settings: dict[str, typing.Any]):
   if (folder := mod_folder(game, mod, environment, settings, openkh_settings)) is None or not folder.exists():
      print(f'Mod {mod} in {game} not found')
      return
   enabled_mods = get_enabled_mods(game, openkh)
   if mod in enabled_mods:
      enabled_mods.remove(mod)
   match order:
      case 'top':
         index = 0
      case 'bottom':
         index = len(enabled_mods)
      case (rel, existing):
         if (folder := mod_folder(game, existing, environment, settings, openkh_settings)) is None or not folder.exists():
            print(f'Mod {existing} in {game} not found')
            return
         if existing not in enabled_mods:
            print(f'Mod {existing} in {game} not enabled')
            return
         match rel:
            case 'above':
               index = enabled_mods.index(existing)
            case 'below':
               index = enabled_mods.index(existing) + 1
   print(f'Enabled mod {mod} in {game}')
   enabled_mods.insert(index, mod)
   set_enabled_mods(game, enabled_mods, openkh)

def make_env(game: KhGame, environment: Environment, settings: Settings, lua: bool, openkh: bool, refined: bool, kh3: bool) -> dict[str, str]:
   if not environment.is_linux():
      return {}
   dlls: dict[str, str] = {}
   if openkh and settings.mods.openkh is not None and settings.mods.openkh.panacea is not None:
      dlls['version'] = 'n,b'
   if lua and settings.mods.luabackend is not None:
      dlls['dinput8'] = 'n,b'
   assert game.wineprefix is not None
   env: dict[str, str] = {
      'WINEPREFIX': str(game.wineprefix),
      'WINEDLLOVERRIDES': ';'.join(f'{key}={value}' for key, value in dlls.items()),
      'WINEFSYNC': '1',
      'WINE_FULLSCREEN_FSR': '1',
      'WINEDEBUG': '-all'
   }
   if isinstance(environment, LinuxEnvironment) and environment.runtime == 'umu':
      read, write = get_access_folders(game, settings, lua=lua, openkh=openkh, refined=refined, kh3=kh3)
      env |= {
         'PROTONPATH': 'GE-Proton',
         'GAMEID': game.umu_id(),
         'STORE': {'steam': 'steam', 'epic': 'egs'}[settings.store],
         'PRESSURE_VESSEL_FILESYSTEMS_RO': ':'.join((str(x) for x in read)),
         'PRESSURE_VESSEL_FILESYSTEMS_RW': ':'.join((str(x) for x in write)),
      }
   return env

def make_launch(game: KhGame, launch: LaunchExe, environment: Environment, settings: Settings, lua: bool, openkh: bool, refined: bool, kh3: bool):
   if launch.launch is None:
      return
   env = make_env(game, environment, settings, lua=lua, openkh=openkh, refined=refined, kh3=kh3)
   launch.launch.parent.mkdir(parents=True, exist_ok=True)
   with open(launch.launch, 'w', encoding='utf-8') as sh_file:
      environment.make_launch(sh_file, environment.convert_path(game, game.get_workspace()), environment.convert_path(game, game.folder / launch.exe()), env)
   filestat = launch.launch.stat()
   launch.launch.chmod(filestat.st_mode | stat.S_IEXEC)

def get_environment(settings: Settings) -> Environment:
   is_linux = platform.system() == 'Linux'
   if is_linux:
      print('Linux detected')
      assert settings.runtime is not None
      environment = LinuxEnvironment(settings.runtime)
      for game in settings.games.get_all():
         assert game.wineprefix is not None
         game.wineprefix.mkdir(parents=True, exist_ok=True)
         user_folder = environment.user_folder(game)
         if not user_folder.exists():
            print('Creating wineprefix')
            entry = {'wine': 'wine', 'umu': 'umu-run'}[environment.runtime]
            subprocess.run(
               [entry, 'wineboot'],
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
         if 'dotnet8' not in winetricks:
            print('Installing dotnet8 to wineprefix')
            subprocess.run(
               ['winetricks', '--unattended', 'dotnet8'],
               check=True,
               env=environment.wine_env(game)
            )
         if environment.runtime == 'wine':
            if 'vkd3d' not in winetricks:
               print('Installing vkd3d to wineprefix')
               subprocess.run(
                  ['winetricks', '--unattended', 'vkd3d'],
                  check=True,
                  env=environment.wine_env(game)
               )
            if 'dxvk' not in winetricks:
               print('Installing dxvk to wineprefix')
               subprocess.run(
                  ['winetricks', '--unattended', 'dxvk'],
                  check=True,
                  env=environment.wine_env(game)
               )
         if (game := settings.games.kh3) is not None:
            assert game.wineprefix is not None
            winetricks = get_winetricks(game.wineprefix)
            if environment.runtime == 'wine':
               if 'wmp11' not in winetricks:
                  print('Installing wmp11 to wineprefix')
                  subprocess.run(
                     ['winetricks', '--unattended', 'wmp11'],
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
            'modCollectionPath': str(environment.convert_path(use_game, openkh.folder / 'mods')),
            'modCollectionsPath': str(environment.convert_path(use_game, openkh.folder / 'mods/collections')),
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
         folder = game.get_workspace()
         dll = 'version.dll' if environment.is_linux() else 'DBGHELP.dll'
         symlinks.make(game.folder / dll, openkh.folder / 'OpenKH.Panacea.dll', is_dir=False)
         symlinks.make(folder / 'panacea_settings.txt', openkh.panacea.settings, is_dir=False)
         symlinks.make(folder / 'dependencies/avcodec-vgmstream-59.dll', openkh.folder / 'dependencies/avcodec-vgmstream-59.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/avformat-vgmstream-59.dll', openkh.folder / 'dependencies/avformat-vgmstream-59.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/avutil-vgmstream-57.dll', openkh.folder / 'dependencies/avutil-vgmstream-57.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/bass.dll', openkh.folder / 'dependencies/bass.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/bass_vgmstream.dll', openkh.folder / 'dependencies/bass_vgmstream.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libatrac9.dll', openkh.folder / 'dependencies/libatrac9.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libcelt-0061.dll', openkh.folder / 'dependencies/libcelt-0061.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libcelt-0110.dll', openkh.folder / 'dependencies/libcelt-0110.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libg719_decode.dll', openkh.folder / 'dependencies/libg719_decode.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libmpg123-0.dll', openkh.folder / 'dependencies/libmpg123-0.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libspeex-1.dll', openkh.folder / 'dependencies/libspeex-1.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/libvorbis.dll', openkh.folder / 'dependencies/libvorbis.dll', is_dir=False)
         symlinks.make(folder / 'dependencies/swresample-vgmstream-4.dll', openkh.folder / 'dependencies/swresample-vgmstream-4.dll', is_dir=False)
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
   
   return mgr_data

def mod_games(openkh: OpenKh, openkh_settings: dict[str, typing.Any], environment: Environment, settings: Settings, settings_path: pathlib.Path):
   rebuild: set[str] = set()
   if openkh.update_mods:
      print('Updating mods')
      mods_folder = openkh.mods if openkh.mods is not None else openkh.folder / 'mods'
      if mods_folder.exists():
         for game in mods_folder.iterdir():
            if not game.is_dir():
               continue
            for root, folders, _files in game.walk():
               if not '.git' in folders:
                  continue
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
      mod_game(settings.games.kh15_25, {'kh1': 'KH1', 'kh2': 'KH2', 'bbs': 'BBS', 'Recom': 'ReCoM'}, rebuild, openkh, openkh_settings, environment, settings, settings_path)
   if settings.games.kh28 is not None:
      mod_game(settings.games.kh28, {'kh3d': 'KH3D'}, rebuild, openkh, openkh_settings, environment, settings, settings_path)

def mod_game(game: KhGame, ids: dict[str, str], rebuild: set[str], openkh: OpenKh, openkh_settings: dict[str, typing.Any], environment: Environment, settings: Settings, settings_path: pathlib.Path):
   latest_modified: datetime.datetime | None = None
   for gameid, text in ids.items():
      enabled_mods_path = openkh.folder / f'mods-{text}.txt'
      if enabled_mods_path.exists():
         modified = datetime.datetime.fromtimestamp(enabled_mods_path.stat().st_mtime)
         if latest_modified is None or modified > latest_modified:
            latest_modified = modified
         if openkh.last_build is None or modified > openkh.last_build:
            rebuild.add(gameid)
   data_folder = pathlib.PureWindowsPath(openkh_settings['gameDataPath'])
   data_folder_local = environment.convert_path_back(game, data_folder)
   mod_in = pathlib.PureWindowsPath(openkh_settings['modCollectionPath'])
   mod_out = pathlib.PureWindowsPath(openkh_settings['gameModPath'])
   image_source = game.folder / 'Image'
   image_backup = game.folder / 'Image-BACKUP'
   restore_folder(image_source, image_backup)
   for gameid, text in ids.items():
      if gameid not in rebuild:
         continue
      game_data_local = data_folder_local / gameid
      if not game_data_local.exists():
         print(f'Extracting {gameid} data (this will take some time)')
         for root, _folders, files in image_source.walk():
            for file in files:
               if file.startswith(f'{gameid}_') and file.endswith('.hed'):
                  environment.run_program(game, [
                     str(openkh.folder / 'OpenKh.Command.IdxImg.exe'),
                     'hed', 'extract', '--do-not-extract-again',
                     '--output', str(data_folder / gameid),
                     str(environment.convert_path(game, root / file)),
                  ])
         for entry in (game_data_local / 'original').iterdir():
            shutil.move(entry, game_data_local)
      print(f'Building {gameid} mods')
      enabled_mods_path = openkh.folder / f'mods-{text}.txt'
      environment.run_program(game, [
         str(openkh.folder / 'OpenKh.Command.IdxImg.exe'),
         'hed', 'build',
         '--game_id', gameid,
         '--output_folder', str(mod_out / gameid),
         '--enabled_mods', str(environment.convert_path(game, enabled_mods_path)),
         '--mods_folder', str(mod_in / gameid),
         '--game_data', str(data_folder / gameid),
      ])
      if openkh.panacea is None:
         print(f'Patching {gameid} mods')
         backup_folder(image_source, image_backup)
         environment.run_program(game, [
            str(openkh.folder / 'OpenKh.Command.IdxImg.exe'),
            'hed', 'full-patch',
            '--build_folder', str(mod_out / gameid),
            '--output_folder', str(environment.convert_path(game, image_source)),
            '--source_folder', str(environment.convert_path(game, image_backup)),
         ])

   if latest_modified is not None and (openkh.last_build is None or latest_modified > openkh.last_build):
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
   def add_scripts(key: str, version: str, path: pathlib.PureWindowsPath):
      block = data[version]
      assert isinstance(block, tomlkit.items.AbstractTable)
      script_section = block['scripts']
      assert isinstance(script_section, tomlkit.items.AoT)
      for entry in script_section:
         if entry.get('key') == key:
            return set_data(entry, 'path', str(path))
      script_section.append({'path': str(path), 'relative': False, 'key': key})
      print(f'Added {key} script entry {path}')
      return True
   def add_openkh(version: str) -> bool:
      if openkh_settings is None:
         return False
      game_folder = pathlib.PureWindowsPath(openkh_settings['gameModPath'])
      script_path = game_folder / version / 'scripts'
      add_scripts('openkh', version, script_path)
      return True
   if (game := settings.games.kh15_25) is not None:
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['kh1']), 'exe', str(game.kh1.exe()))
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['kh2']), 'exe', str(game.kh2.exe()))
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['bbs']), 'exe', str(game.khbbs.exe()))
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['recom']), 'exe', str(game.khrecom.exe()))
      path = game.saves_folder()
      if settings.store == 'steam':
         path = 'My Games' / path
      for version in ['kh1', 'kh2', 'bbs', 'recom']:
         changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data[version]), 'game_docs', str(path))
         changed |= add_openkh(version)
         if luabackend.scripts is not None:
            changed |= add_scripts('lua', version, environment.convert_path(game, luabackend.scripts / version))
   if (game := settings.games.kh28) is not None:
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['kh3d']), 'exe', str(game.khddd.exe()))
      path = game.saves_folder()
      if settings.store == 'steam':
         path = 'My Games' / path
      changed |= set_data(typing.cast(tomlkit.items.AbstractTable, data['kh3d']), 'game_docs', str(path))
      changed |= add_openkh('kh3d')
      if luabackend.scripts is not None:
         changed |= add_scripts('lua', 'kh3d', environment.convert_path(game, luabackend.scripts / 'kh3d'))
   if changed:
      with open(luabackend.settings, 'w', encoding='utf-8') as mods_file:
         tomlkit.dump(data, mods_file)
   for game in settings.games.get_classic():
      folder = game.get_workspace()
      symlinks.make(folder / 'LuaBackend.toml', luabackend.settings, is_dir=False)
      if environment.is_linux():
         symlinks.make(game.folder / 'DINPUT8.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)
      else:
         if settings.mods.openkh is None:
            symlinks.make(game.folder / 'DBGHELP.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)
         else:
            symlinks.make(folder / 'LuaBackend.dll', luabackend.folder / 'DBGHELP.dll', is_dir=False)

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
      if not destination_folder.exists():
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
      if last_date is None or asset_date > last_date or not destination_folder.exists():
         print(f'Downloading update: {release["tag_name"]}')
         response = requests.get(asset['browser_download_url'], timeout=10)
         if response.status_code != 200:
            print(f'Error {response.status_code}!')
            print(response.text)
            if not destination_folder.exists():
               response.raise_for_status()
            return None
         with tempfile.TemporaryDirectory() as temp_folder:
            temp_folder_path = pathlib.Path(temp_folder)
            temp_zip = temp_folder_path / 'archive.zip'
            with open(temp_zip, 'wb') as file:
               file.write(response.content)
            destination_folder.mkdir(parents=True, exist_ok=True)
            if has_extra_folder:
               temp_extract = temp_folder_path / 'extract'
               temp_extract.mkdir(parents=True, exist_ok=True)
               extract_with_filter(temp_zip, temp_extract, extract_filter)
               shutil.copytree(temp_extract / next(temp_extract.iterdir()), destination_folder, dirs_exist_ok=True)
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
