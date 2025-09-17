import abc
import mashumaro.codecs.yaml
import dataclasses
import typing
import pathlib
import datetime

@dataclasses.dataclass
class LaunchExe:
   launch: typing.Optional[pathlib.Path]
   @classmethod
   @abc.abstractmethod
   def exe(cls) -> pathlib.PurePath: pass

@dataclasses.dataclass
class LaunchKh1(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS FINAL MIX.exe')

@dataclasses.dataclass
class LaunchKh2(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS II FINAL MIX.exe')

@dataclasses.dataclass
class LaunchKhBbs(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS Birth by Sleep FINAL MIX.exe')

@dataclasses.dataclass
class LaunchKhRecom(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS Re_Chain of Memories.exe')

@dataclasses.dataclass
class LaunchKhDdd(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS Dream Drop Distance.exe')

@dataclasses.dataclass
class LaunchKh02(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS 0.2 Birth by Sleep/Binaries/Win64/KINGDOM HEARTS 0.2 Birth by Sleep.exe')

@dataclasses.dataclass
class LaunchKh3(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe')

@dataclasses.dataclass
class LaunchKhMom(LaunchExe):
   @classmethod
   def exe(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS Melody of Memory.exe')

@dataclasses.dataclass
class KhGame:
   wineprefix: typing.Optional[pathlib.Path]
   saves: typing.Optional[pathlib.Path]
   folder: pathlib.Path
   workspace: typing.Optional[pathlib.Path]
   @classmethod
   @abc.abstractmethod
   def saves_folder(cls) -> pathlib.PurePath: pass
   @classmethod
   @abc.abstractmethod
   def umu_id(cls) -> str: pass
   @abc.abstractmethod
   def get_exes(self) -> list[LaunchExe]: pass
   
   def get_workspace(self):
      if self.workspace is not None:
         return self.workspace
      return self.folder

@dataclasses.dataclass
class Kh1525(KhGame):
   kh1: LaunchKh1
   kh2: LaunchKh2
   khrecom: LaunchKhRecom
   khbbs: LaunchKhBbs
   
   @classmethod
   def saves_folder(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS HD 1.5+2.5 ReMIX')

   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552430'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.kh1, self.kh2, self.khrecom, self.khbbs] if game is not None]

@dataclasses.dataclass
class Kh28(KhGame):
   khddd: LaunchKhDdd
   kh02: LaunchKh02
   
   @classmethod
   def saves_folder(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS HD 2.8 Final Chapter Prologue')
   
   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552430'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.khddd, self.kh02] if game is not None]

@dataclasses.dataclass
class Kh3(KhGame):
   kh3: LaunchKh3
   
   @classmethod
   def saves_folder(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS III')
   
   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552450'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.kh3] if game is not None]

@dataclasses.dataclass
class KhMom(KhGame):
   khmom: LaunchKhMom
   
   @classmethod
   def saves_folder(cls) -> pathlib.PurePath:
      return pathlib.PurePath('KINGDOM HEARTS Melody of Memory')
   
   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552430'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.khmom] if game is not None]

@dataclasses.dataclass
class Games:
   kh15_25: typing.Optional[Kh1525]
   kh28: typing.Optional[Kh28]
   kh3: typing.Optional[Kh3]
   khmom: typing.Optional[KhMom]
   
   def get_all(self) -> list[KhGame]:
      return [game for game in [self.kh15_25, self.kh28, self.kh3, self.khmom] if game is not None]

   def get_classic(self) -> list[KhGame]:
      return [game for game in [self.kh15_25, self.kh28] if game is not None]

@dataclasses.dataclass
class Panacea:
   settings: pathlib.Path

@dataclasses.dataclass
class OpenKh:
   folder: pathlib.Path
   mods: typing.Optional[pathlib.Path]
   settings: typing.Optional[pathlib.Path]
   panacea: typing.Optional[Panacea]
   update_mods: bool
   update: bool | datetime.datetime
   last_build: typing.Optional[datetime.datetime]

@dataclasses.dataclass
class Luabackend:
   folder: pathlib.Path
   settings: pathlib.Path
   scripts: typing.Optional[pathlib.Path]
   update: bool | datetime.datetime

@dataclasses.dataclass
class Refined:
   folder: pathlib.Path
   settings: pathlib.Path

@dataclasses.dataclass
class Randomizer:
   folder: pathlib.Path
   update: bool | datetime.datetime

@dataclasses.dataclass
class Kh3Mods:
   folder: pathlib.Path

@dataclasses.dataclass
class Mods:
   openkh: typing.Optional[OpenKh]
   luabackend: typing.Optional[Luabackend]
   refined: typing.Optional[Refined]
   randomizer: typing.Optional[Randomizer]
   kh3: typing.Optional[Kh3Mods]

StoreKind = typing.Literal['epic', 'steam']
WineRuntime = typing.Literal['wine', 'umu']

@dataclasses.dataclass
class Settings:
   epic_id: typing.Optional[int]
   steam_id: typing.Optional[int]
   store: StoreKind
   runtime: typing.Optional[WineRuntime]
   games: Games
   mods: Mods
   
def save_settings(settings: Settings, path: pathlib.Path):
   with open(path, 'w', encoding='utf-8') as data_file:
      data = mashumaro.codecs.yaml.encode(settings, Settings)
      assert isinstance(data, str)
      data_file.write(data)

def get_settings(path: pathlib.Path) -> Settings:
   with open(path, 'r', encoding='utf-8') as data_file:
      data = data_file.read()
      settings = mashumaro.codecs.yaml.decode(data, Settings)
      return settings
