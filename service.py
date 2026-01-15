import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import requests
import zipfile
from urllib.parse import parse_qsl

# Inițializare addon și setări
ADDON = xbmcaddon.Addon()
# Preluăm API Key din settings.xml
API_KEY = ADDON.getSetting("api_key")
BASE_URL = "https://subs.ro/api/v1.0"

def log(msg):
    xbmc.log(f"Subs.ro DEBUG: {msg}", xbmc.LOGINFO)

def search(handle, params):
    # Mapăm limbile conform specificației OpenAPI
    languages = params.get('languages', 'ro')
    search_value = params.get('imdbid')
    search_field = "imdbid"

    # Dacă nu avem IMDB ID, căutăm după titlu
    if not search_value:
        search_value = params.get('searchstring') or params.get('title')
        search_field = "title"

    if not search_value:
        return

    log(f"Căutare {search_field}: {search_value}")

    # Endpoint-ul de căutare din specificație
    url = f"{BASE_URL}/search/{search_field}/{search_value}"
    headers = {"X-Subs-Api-Key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('status') == 200:
            for sub in data.get('items', []):
                # SubtitleItem conține title, language, poster
                label = f"{sub['title']} [{sub.get('language', 'ro').upper()}]"
                list_item = xbmcgui.ListItem(label=label)
                list_item.setArt({'poster': sub.get('poster')})
                
                # Construim URL-ul de download pentru pasul următor
                cmd = f"{sys.argv[0]}?action=download&id={sub['id']}"
                xbmcplugin.addDirectoryItem(handle=handle, url=cmd, listitem=list_item, isFolder=False)
    except Exception as e:
        log(f"Eroare API Search: {e}")

def download(params):
    sub_id = params.get('id')
    # Locație pentru stocare temporară
    path = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
    zip_path = os.path.join(path, "temp_sub.zip")
    extract_path = os.path.join(path, "extracted_subs")
    
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)

    # Endpoint-ul de download binar
    url = f"{BASE_URL}/subtitle/{sub_id}/download"
    headers = {"X-Subs-Api-Key": API_KEY}

    try:
        # Descărcare binar (application/octet-stream)
        r = requests.get(url, headers=headers, stream=True)
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Dezarhivare pentru a găsi fișierul .srt
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            for file in zip_ref.namelist():
                if file.endswith(('.srt', '.ass')):
                    return os.path.join(extract_path, file)
    except Exception as e:
        log(f"Eroare Download/Extract: {e}")
    return None

if __name__ == '__main__':
    handle = int(sys.argv[1])
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get('action')

    if action == 'download':
        sub_file = download(params)
        if sub_file:
            # Îi dăm lui Kodi calea finală către fișierul de subtitrare
            list_item = xbmcgui.ListItem(path=sub_file)
            xbmcplugin.setResolvedUrl(handle, True, list_item)
    else:
        search(handle, params)

    xbmcplugin.endOfDirectory(handle)
