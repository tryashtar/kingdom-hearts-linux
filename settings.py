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
   store: StoreKind
   folder: pathlib.Path

@dataclasses.dataclass
class Kh1525(KhGame):
   kh1: LaunchExe
   kh2: LaunchExe
   khrecom: LaunchExe
   khbbs: LaunchExe

@dataclasses.dataclass
class Kh28(KhGame):
   khddd: LaunchExe
   kh02: LaunchExe

@dataclasses.dataclass
class Kh3(KhGame):
   kh3: LaunchExe
   
@dataclasses.dataclass
class KhMom(KhGame):
   khmom: LaunchExe

@dataclasses.dataclass
class Games:
   kh15_25: typing.Optional[Kh1525]
   kh28: typing.Optional[Kh28]
   kh3: typing.Optional[Kh3]
   khmom: typing.Optional[KhMom]

@dataclasses.dataclass
class Panacea:
   settings: typing.Optional[pathlib.Path]

@dataclasses.dataclass
class OpenKh:
   folder: pathlib.Path
   mods: typing.Optional[pathlib.Path]
   settings: typing.Optional[pathlib.Path]
   panacea: typing.Optional[Panacea]
   update_mods: bool
   update: bool | datetime.datetime
   last_build: dict[str, list[str]]

@dataclasses.dataclass
class Luabackend:
   folder: pathlib.Path
   settings: typing.Optional[pathlib.Path]
   update: bool | datetime.datetime

@dataclasses.dataclass
class Refined:
   settings: typing.Optional[pathlib.Path]

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
