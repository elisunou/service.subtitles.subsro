import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import requests
import zipfile
from urllib.parse import parse_qsl

# Inițializare addon și setări
ADDON = xbmcaddon.Addon()
API_KEY = ADDON.getSetting("api_key")
BASE_URL = "https://subs.ro/api/v1.0"

def log(msg):
    xbmc.log(f"Subs.ro: {msg}", xbmc.LOGINFO)

def search(params):
    # Extragem datele trimise de Kodi
    languages = params.get('languages', 'ro')
    # Mapăm limbile Kodi pe codurile Subs.ro (simplificat)
    lang_map = {"Romanian": "ro", "English": "en"}
    api_lang = lang_map.get(languages, "ro")

    search_value = params.get('imdbid')
    search_field = "imdbid"

    if not search_value:
        search_value = params.get('searchstring') or params.get('title')
        search_field = "title"

    log(f"Căutare {search_field}: {search_value} în limba {api_lang}")

    url = f"{BASE_URL}/search/{search_field}/{search_value}"
    headers = {"X-Subs-Api-Key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, params={"language": api_lang}, timeout=10)
        data = response.json()
        
        if data.get('status') == 200:
            for sub in data.get('items', []):
                list_item = xbmcgui.ListItem(label=sub['title'])
                # Metadate pentru interfața Kodi
                list_item.setArt({'poster': sub.get('poster')})
                list_item.setProperty("language", sub.get('language', 'ro'))
                
                # Payload-ul pentru descărcare
                cmd = f"plugin://{ADDON.getAddonInfo('id')}/?action=download&id={sub['id']}&title={sub['title']}"
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=cmd, listitem=list_item, isFolder=False)
    except Exception as e:
        log(f"Eroare API: {e}")

def download(sub_id, sub_title):
    # Calea unde salvăm arhiva temporar
    temp_dir = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
    zip_path = os.path.join(temp_dir, "subtitle.zip")
    extract_path = os.path.join(temp_dir, "extracted_subs")
    
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)

    url = f"{BASE_URL}/subtitle/{sub_id}/download"
    headers = {"X-Subs-Api-Key": API_KEY}

    try:
        # 1. Descarcă arhiva
        r = requests.get(url, headers=headers, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 2. Dezarhivează și caută fișierul .srt
        subtitle_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            for file in zip_ref.namelist():
                if file.endswith(('.srt', '.ass', '.ssa')):
                    subtitle_files.append(os.path.join(extract_path, file))
        
        # 3. Returnează fișierul către Kodi
        if subtitle_files:
            # Dacă sunt mai multe fișiere în arhivă, îl luăm pe primul
            return subtitle_files[0]
            
    except Exception as e:
        log(f"Eroare la procesarea arhivei: {e}")
    return None

# --- Router-ul de execuție ---
if __name__ == '__main__':
    # Parsăm argumentele primite de la Kodi
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if action == 'search' or not action:
        # Kodi trimite uneori parametrii direct în sys.argv
        search(params)
    elif action == 'download':
        sub_file = download(params.get('id'), params.get('title'))
        if sub_file:
            # Îi spunem lui Kodi unde este fișierul final
            list_item = xbmcgui.ListItem(label=params.get('title'))
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub_file, listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))
