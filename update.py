import requests
import json
import zipfile
import shutil
import os

data_path = os.path.join(os.path.dirname(__file__), 'data.json')
if os.path.exists(data_path):
   with open(data_path, 'r') as data_file:
      data = json.load(data_file)
else:
   print('First-time run, welcome!')
   print('You\'ll be asked some questions about your setup. Every time you run this script, everything will be updated according to your answers. You can change them at any time by editing or deleting data.json.')
   print()
   data = {}

if 'installs' not in data:
   data['installs'] = {}
   print('Input the folders where your Kingdom Hearts games are installed.')
   print('For any you don\'t have, just press enter.')
   print()
   print('Kingdom Hearts HD 1.5+2.5 ReMIX:')
   while True:
      install = input('> ')
      if install == '':
         install = None
      else:
         if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe')):
            print('Couldn\t find \'KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe\' in that folder. Please try again.')
            continue
      break
   data['installs']['kh1.5+2.5'] = install
   print()
   print('Kingdom Hearts HD 2.8 Final Chapter Prologue:')
   while True:
      install = input('> ')
      if install == '':
         install = None
      else:
         if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe')):
            print('Couldn\t find \'KINGDOM HEARTS HD 2.8 Final Chapter Prologue.exe\' in that folder. Please try again.')
            continue
      break
   data['installs']['kh2.8'] = install
   print()
   print('Kingdom Hearts III:')
   while True:
      install = input('> ')
      if install == '':
         install = None
      else:
         if not os.path.exists(os.path.join(install, 'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe')):
            print('Couldn\t find \'KINGDOM HEARTS III/Binaries/Win64/KINGDOM HEARTS III.exe\' in that folder. Please try again.')
            continue
      break
   data['installs']['kh3'] = install
   print()

if 'wineprefix' not in data:
   print('Input the folder for your wineprefix.')
   print('To use the default (~/.wine), just press enter.')
   prefix = input('> ')
   if prefix == '':
      prefix = os.path.expanduser('~/.wine')
   data['wineprefix'] = prefix
   print()

lutris_path = '/bin/lutris'
if 'lutris' not in data and os.path.exists(lutris_path):
   print('Lutris detected. Would you like to add game links to Lutris? (y/n)')
   while True:
      answer = input('> ')
      if answer in ('y','n'):
         break
   data['lutris'] = answer == 'y'
   print()

if 'mods' not in data and data['installs'].get('kh1.5+2.5') is not None:
   data['mods'] = {}
   print('Where would you like to save modding applications?')
   print('If you don\'t want mods, just press enter.')
   folder = input('> ')
   if folder == '':
      folder = None
   data['mods']['folder'] = folder
   print()
   if folder is not None:
      print('Modding applications to use:')
      print()
      print('Kingdom Hearts ReFined: (y/n)')
      while True:
         answer = input('> ')
         if answer in ('y','n'):
            break
      data['mods']['refined'] = answer == 'y'
      print()
      if answer == 'y':
         data['mods']['openkh'] = True
      else:
         print('OpenKh mod manager: (y/n)')
         while True:
            answer = input('> ')
            if answer in ('y','n'):
               break
         data['mods']['openkh'] = answer == 'y'
         print()
      if data['mods']['openkh']:
         print('OpenKh panacea mod loader: (y/n)')
         while True:
            answer = input('> ')
            if answer in ('y','n'):
               break
         data['mods']['panacea'] = answer == 'y'
         print()
      print('LuaBackend script loader: (y/n)')
      while True:
         answer = input('> ')
         if answer in ('y','n'):
            break
      data['mods']['luabackend'] = answer == 'y'
      print()

print('Updating!')

if 'mods' in data:
   if data['mods'].get('refined'):
      print('ReFined...')
      mod_folder = os.path.join(data['mods']['folder'], 'ReFined-KH2')
      rq = requests.get('https://api.github.com/repos/TopazTK/KH-ReFined/releases')
      if rq.status_code != 200:
         print(f'Error {rq.status_code}!')
         try:
            print(json.loads(rq.text)['message'])
         except:
            print(rq.text)
      else:
         release = json.loads(rq.text)[0]
         for asset in release['assets']:
            if asset['name'].endswith('.zip'):
               print(release['tag_name'])
               rq = requests.get(asset['browser_download_url'])
               with open('/tmp/refined.zip', 'wb') as file:
                  file.write(rq.content)
               with zipfile.ZipFile('/tmp/refined.zip', 'r') as zip:
                  zip.extractall(mod_folder)

   if data['mods'].get('openkh'):
      print('OpenKh...')
      mod_folder = os.path.join(data['mods']['folder'], 'OpenKh')
      rq = requests.get('https://api.github.com/repos/OpenKH/OpenKh/releases/tags/latest')
      if rq.status_code != 200:
         print(f'Error {rq.status_code}!')
         try:
            print(json.loads(rq.text)['message'])
         except:
            print(rq.text)
      else:
         for asset in json.loads(rq.text)['assets']:
            if asset['name'] == 'openkh.zip':
               rq = requests.get(asset['browser_download_url'])
               with open('/tmp/openkh.zip', 'wb') as file:
                  file.write(rq.content)
               with zipfile.ZipFile('/tmp/openkh.zip', 'r') as zip:
                  zip.extractall('/tmp/openkh')
               with open('/tmp/openkh/openkh/openkh-release', 'r') as new_file:
                  new = new_file.read()
               if os.path.exists(os.path.join(mod_folder, 'openkh-release')):
                  with open(os.path.join(mod_folder, 'openkh-release'), 'r') as existing_file:
                     existing = existing_file.read()
               else:
                  existing = '(none)'
               if new != existing:
                  print(f'{existing} -> {new}')
                  shutil.copytree('/tmp/openkh/openkh', mod_folder, dirs_exist_ok=True)

   if data['mods'].get('luabackend'):
      print('LuaBackend...')
      mod_folder = os.path.join(data['mods']['folder'], 'LuaBackend')
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
               print(release['tag_name'])
               rq = requests.get(asset['browser_download_url'])
               with open('/tmp/luabackend.zip', 'wb') as file:
                  file.write(rq.content)
               with zipfile.ZipFile('/tmp/luabackend.zip', 'r') as zip:
                  zip.extractall(mod_folder)
               toml_user = os.path.join(data['mods']['folder'], 'LuaBackend.toml')
               toml_default = os.path.join(mod_folder, 'LuaBackend.toml')
               if not os.path.exists(toml_user):
                  shutil.copyfile(toml_default, toml_user)
               os.remove(toml_default)

with open(data_path, 'w') as data_file:
   json.dump(data, data_file, indent=2)
