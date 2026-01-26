# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import requests, os, sys, urllib.parse, zipfile, difflib

ADDON = xbmcaddon.Addon()
API_BASE = "https://subs.ro/api/v1.0"

def get_api_key():
    """Obține cheia API din setări sau cere utilizatorului să o introducă"""
    api_key = ADDON.getSetting('api_key')
    
    if not api_key or api_key.strip() == "":
        dialog = xbmcgui.Dialog()
        api_key = dialog.input(
            "Introdu cheia ta API de la Subs.ro",
            type=xbmcgui.INPUT_ALPHANUM
        )
        
        if api_key and api_key.strip():
            ADDON.setSetting('api_key', api_key.strip())
        else:
            xbmcgui.Dialog().notification(
                "Subs.ro", 
                "Cheie API necesară! Configurează în setări.", 
                xbmcgui.NOTIFICATION_WARNING, 
                5000
            )
            return None
    
    return api_key.strip()

def handle_api_error(status_code):
    errors = {
        401: "Cheie API invalidă! Verifică setările addon-ului.",
        403: "Acces interzis sau limită de download atinsă.",
        404: "Subtitrarea nu a fost găsită.",
        429: "Prea multe cereri! Încearcă mai târziu.",
        500: "Eroare de server Subs.ro. Revenim imediat."
    }
    msg = errors.get(status_code, f"Eroare API necunoscută (Cod: {status_code})")
    xbmcgui.Dialog().notification("Eroare Subs.ro", msg, xbmcgui.NOTIFICATION_ERROR, 5000)
    
    if status_code == 401:
        ADDON.setSetting('api_key', '')

def get_params():
    param_string = sys.argv[2] if len(sys.argv) > 2 else ""
    return dict(urllib.parse.parse_qsl(param_string.lstrip('?')))

def search_subtitles():
    API_KEY = get_api_key()
    if not API_KEY:
        return
    
    handle = int(sys.argv[1])
    player = xbmc.Player()
    if not player.isPlayingVideo(): return

    info = player.getVideoInfoTag()
    imdb_id = info.getIMDBNumber()
    tvshow = info.getTVShowTitle()
    season = info.getSeason()
    episode = info.getEpisode()
    title = info.getTitle() or xbmc.getInfoLabel('VideoPlayer.Title')

    if imdb_id and imdb_id.startswith('tt'):
        field, value = "imdbid", imdb_id
    else:
        field = "title"
        value = f"{tvshow} S{str(season).zfill(2)}E{str(episode).zfill(2)}" if tvshow and season != -1 else title

    url = f"{API_BASE}/search/{field}/{urllib.parse.quote(value)}"
    headers = {'X-Subs-Api-Key': API_KEY, 'Accept': 'application/json'}

    try:
        r = requests.get(url, params={'language': 'ro'}, headers=headers, timeout=10)
        
        if r.status_code != 200:
            handle_api_error(r.status_code)
            return

        data = r.json() 
        if data.get('status') == 200:
            for item in data.get('items', []):
                # Numele complet pe care vrem să-l vedem
                full_name = item.get('title', 'Unknown Release')
                
                # REPARAȚIE AFIȘARE: Forțăm label și label2 pentru a ocupa tot spațiul
                list_item = xbmcgui.ListItem(label=full_name, label2=full_name)
                list_item.setArt({'thumb': item.get('poster'), 'icon': 'logo.png'})
                
                # Setăm InfoTag-ul de video cu titlul complet
                list_item.setInfo('video', {
                    'title': full_name,
                    'plot': full_name, # Plot-ul apare de obicei sub listă, complet
                    'tagline': full_name
                })
                
                cmd = f"{sys.argv[0]}?action=download&id={item['id']}"
                xbmcplugin.addDirectoryItem(handle=handle, url=cmd, listitem=list_item, isFolder=False)
    except: pass
    xbmcplugin.endOfDirectory(handle)

def download_subtitle(sub_id):
    API_KEY = get_api_key()
    if not API_KEY:
        return
    
    url = f"{API_BASE}/subtitle/{sub_id}/download"
    headers = {'X-Subs-Api-Key': API_KEY}
    
    player = xbmc.Player()
    tmp_path = xbmcvfs.translatePath("special://temp/")
    archive = os.path.join(tmp_path, "subs_download.zip")
    target_srt = os.path.join(tmp_path, "forced.romanian.subsro.srt")

    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code != 200:
            handle_api_error(r.status_code)
            return
            
        with open(archive, "wb") as f: f.write(r.content)
        
        with zipfile.ZipFile(archive, 'r') as z:
            srts = sorted([f for f in z.namelist() if f.lower().endswith(('.srt', '.ass'))])
            if not srts: return
            
            if len(srts) > 1:
                dialog = xbmcgui.Dialog()
                display_names = [os.path.basename(f) for f in srts]
                selected = dialog.select("Alege episodul srt:", display_names)
                if selected == -1: return
                f_name = srts[selected]
            else:
                f_name = srts[0]
            
            # Citim conținutul și convertim la UTF-8 pentru diacritice
            content = z.read(f_name)
            try:
                text = content.decode('utf-8')
            except:
                try:
                    text = content.decode('iso-8859-2')
                except:
                    try:
                        text = content.decode('windows-1250')
                    except:
                        text = content.decode('latin1')
            
            # Scriem fișierul în UTF-8
            with open(target_srt, "w", encoding="utf-8") as f: 
                f.write(text)

        xbmc.executebuiltin("Dialog.Close(subtitlesearch)")
        xbmc.sleep(500)
        player.setSubtitles(target_srt)
        
        for _ in range(15): 
            if not player.isPlayingVideo(): break
            streams = player.getAvailableSubtitleStreams()
            for i, s_name in enumerate(streams):
                if "forced.romanian" in s_name.lower() or "external" in s_name.lower():
                    if player.getSubtitleStream() != i:
                        player.setSubtitleStream(i)
                        player.showSubtitles(True)
            xbmc.sleep(400)

        xbmcgui.Dialog().notification("Subs.ro", "Activat: " + os.path.basename(f_name)[:30], xbmcgui.NOTIFICATION_INFO, 2000)

    except: pass

if __name__ == '__main__':
    p = get_params()
    if p.get('action') == 'download': 
        download_subtitle(p.get('id'))
    else: 
        search_subtitles()