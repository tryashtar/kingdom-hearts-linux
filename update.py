import requests
import json
import zipfile
import shutil
import os

print('OpenKh...')
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
         data = requests.get(asset['browser_download_url'])
         with open('/tmp/openkh.zip', 'wb') as file:
            file.write(data.content)
         with zipfile.ZipFile('/tmp/openkh.zip', 'r') as zip:
            zip.extractall('/tmp/openkh')
         with open('/tmp/openkh/openkh/openkh-release', 'r') as new_file:
            new = new_file.read()
         if os.path.exists('OpenKh/openkh-release'):
            with open('OpenKh/openkh-release', 'r') as existing_file:
               existing = existing_file.read()
         else:
            existing = '(none)'
         if new != existing:
            print(f'{existing} -> {new}')
            shutil.copytree('/tmp/openkh/openkh', 'OpenKh', dirs_exist_ok=True)

print('ReFined-KH2...')
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
         data = requests.get(asset['browser_download_url'])
         with open('/tmp/refined.zip', 'wb') as file:
            file.write(data.content)
         with zipfile.ZipFile('/tmp/refined.zip', 'r') as zip:
            zip.extractall('ReFined-KH2')

print('LuaBackend...')
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
         data = requests.get(asset['browser_download_url'])
         with open('/tmp/luabackend.zip', 'wb') as file:
            file.write(data.content)
         with zipfile.ZipFile('/tmp/luabackend.zip', 'r') as zip:
            zip.extractall('LuaBackend')
         os.remove('LuaBackend/LuaBackend.toml')
