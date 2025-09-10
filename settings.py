import abc
import mashumaro.codecs.yaml
import dataclasses
import typing
import pathlib
import datetime

StoreKind = typing.Literal['epic', 'steam']

@dataclasses.dataclass
class LaunchExe:
   exe: pathlib.Path
   launch: typing.Optional[pathlib.Path]

@dataclasses.dataclass
class KhGame:
   saves: typing.Optional[pathlib.Path]
   folder: pathlib.Path
   @abc.abstractmethod
   @classmethod
   def saves_folder(cls) -> str: pass
   @abc.abstractmethod
   @classmethod
   def umu_id(cls) -> str: pass
   @abc.abstractmethod
   def get_exes(self) -> list[LaunchExe]: pass

@dataclasses.dataclass
class Kh1525(KhGame):
   kh1: LaunchExe
   kh2: LaunchExe
   khrecom: LaunchExe
   khbbs: LaunchExe
   
   @classmethod
   def saves_folder(cls) -> str:
      return 'KINGDOM HEARTS HD 1.5+2.5 ReMIX'

   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552430'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.kh1, self.kh2, self.khrecom, self.khbbs] if game is not None]

@dataclasses.dataclass
class Kh28(KhGame):
   khddd: LaunchExe
   kh02: LaunchExe
   
   @classmethod
   def saves_folder(cls) -> str:
      return 'KINGDOM HEARTS HD 2.8 Final Chapter Prologue'
   
   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552430'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.khddd, self.kh02] if game is not None]

@dataclasses.dataclass
class Kh3(KhGame):
   kh3: LaunchExe
   
   @classmethod
   def saves_folder(cls) -> str:
      return 'KINGDOM HEARTS III'
   
   @classmethod
   def umu_id(cls) -> str:
      return 'umu-2552450'
   
   def get_exes(self) -> list[LaunchExe]:
      return [game for game in [self.kh3] if game is not None]

@dataclasses.dataclass
class KhMom(KhGame):
   khmom: LaunchExe
   
   @classmethod
   def saves_folder(cls) -> str:
      return 'KINGDOM HEARTS Melody of Memory'
   
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
   update: bool | datetime.datetime

@dataclasses.dataclass
class Refined:
   settings: pathlib.Path

@dataclasses.dataclass
class Randomizer:
   folder: pathlib.Path
   update: bool | datetime.datetime

@dataclasses.dataclass
class Mods:
   openkh: typing.Optional[OpenKh]
   luabackend: typing.Optional[Luabackend]
   refined: typing.Optional[Refined]
   randomizer: typing.Optional[Randomizer]

@dataclasses.dataclass
class Settings:
   wineprefix: typing.Optional[pathlib.Path]
   epic_id: typing.Optional[int]
   steam_id: typing.Optional[int]
   store: StoreKind
   games: Games
   mods: Mods
   
def save_settings(settings: Settings, path: pathlib.Path):
   with open(path, 'w', encoding='utf-8') as data_file:
      data = mashumaro.codecs.yaml.encode(settings, Settings)
      data_file.write(data)

def get_settings(path: pathlib.Path) -> Settings:
   with open(path, 'r', encoding='utf-8') as data_file:
      data = data_file.read()
      settings = mashumaro.codecs.yaml.decode(data, Settings)
      return settings
