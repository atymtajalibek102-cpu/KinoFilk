#!/usr/bin/env python3
"""
KinoFlik — генератор tv.js из iptv-org GitHub
Запуск: python generate_tv_js.py
Результат: tv.js готов к копированию в static/js/
"""

import urllib.request
import re
import json
import sys
import time

# ──────────────────────────────────────────────────────────────
# Источники с GitHub (iptv-org/iptv)
# Добавь/удали строки по желанию
# ──────────────────────────────────────────────────────────────
SOURCES = [
    # Казахстан
    ("https://iptv-org.github.io/iptv/countries/kz.m3u",  "news"),
    # Россия
    ("https://iptv-org.github.io/iptv/countries/ru.m3u",  "general"),
    # По категориям (весь мир)
    ("https://iptv-org.github.io/iptv/categories/news.m3u",         "news"),
    ("https://iptv-org.github.io/iptv/categories/sports.m3u",       "sports"),
    ("https://iptv-org.github.io/iptv/categories/movies.m3u",       "movies"),
    ("https://iptv-org.github.io/iptv/categories/kids.m3u",         "kids"),
    ("https://iptv-org.github.io/iptv/categories/music.m3u",        "music"),
    ("https://iptv-org.github.io/iptv/categories/documentary.m3u",  "documentary"),
    ("https://iptv-org.github.io/iptv/categories/entertainment.m3u","general"),
    ("https://iptv-org.github.io/iptv/categories/education.m3u",    "documentary"),
    ("https://iptv-org.github.io/iptv/categories/cooking.m3u",      "documentary"),
    ("https://iptv-org.github.io/iptv/categories/travel.m3u",       "documentary"),
    ("https://iptv-org.github.io/iptv/categories/science.m3u",      "documentary"),
    # Дополнительные страны СНГ
    ("https://iptv-org.github.io/iptv/countries/ua.m3u",  "news"),
    ("https://iptv-org.github.io/iptv/countries/by.m3u",  "news"),
    ("https://iptv-org.github.io/iptv/countries/uz.m3u",  "news"),
    ("https://iptv-org.github.io/iptv/countries/kg.m3u",  "news"),
    ("https://iptv-org.github.io/iptv/countries/az.m3u",  "news"),
    # Топ стран
    ("https://iptv-org.github.io/iptv/countries/tr.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/de.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/fr.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/gb.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/us.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/it.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/es.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/pl.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/in.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/cn.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/ar.m3u",  "general"),
    ("https://iptv-org.github.io/iptv/countries/br.m3u",  "general"),
]

# Категория → цвет
CAT_COLORS = {
    "news":         "#c8102e",
    "sports":       "#1ea6cb",
    "movies":       "#8b0000",
    "kids":         "#f97316",
    "music":        "#9333ea",
    "documentary":  "#0b3d91",
    "general":      "#333333",
}

def fetch_m3u(url, default_cat):
    """Скачать M3U и вернуть список каналов"""
    channels = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            content = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ОШИБКА: {e}")
        return []

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            # Парсим атрибуты
            name_match = re.search(r',(.+)$', line)
            name = name_match.group(1).strip() if name_match else "Unknown"

            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            logo = logo_match.group(1) if logo_match else ""

            cat_match = re.search(r'group-title="([^"]*)"', line)
            raw_cat = cat_match.group(1).lower() if cat_match else ""

            # Определяем категорию
            if any(k in raw_cat for k in ["news","новост","хабар","жаңал"]):
                cat = "news"
            elif any(k in raw_cat for k in ["sport","спорт","футбол","soccer","football"]):
                cat = "sports"
            elif any(k in raw_cat for k in ["movie","кино","film","cinema"]):
                cat = "movies"
            elif any(k in raw_cat for k in ["kid","детск","child","cartoon","мульт","balapan"]):
                cat = "kids"
            elif any(k in raw_cat for k in ["music","муз","music"]):
                cat = "music"
            elif any(k in raw_cat for k in ["docu","doc","наука","history","travel","nature","food","cook"]):
                cat = "documentary"
            else:
                cat = default_cat

            # URL потока — следующая непустая строка
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                stream_url = lines[i].strip()
                if stream_url and not stream_url.startswith("#") and stream_url.startswith("http"):
                    channels.append({
                        "n": name,
                        "c": cat,
                        "logo": logo,
                        "url": stream_url,
                    })
        i += 1

    return channels


def name_to_color(name, cat):
    """Генерируем цвет из названия канала"""
    h = hash(name) & 0xFFFFFF
    r = (h >> 16) & 0xFF
    g = (h >> 8) & 0xFF
    b = h & 0xFF
    # Делаем цвет темнее (для темной темы)
    r = max(30, min(180, r))
    g = max(30, min(180, g))
    b = max(30, min(180, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def js_escape(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


# ──────────────────────────────────────────────────────────────
# ЗАХАРДКОЖЕННЫЕ КАЗАХСКИЕ/СВОИ каналы (всегда первые)
# ──────────────────────────────────────────────────────────────
OWN_CHANNELS = [
    { "n": "Qazaqstan TV",    "c": "news",    "col": "#c8102e", "url": "https://qazaqstantv-stream.qazcdn.com/qazaqstantv/qazaqstantv/playlist.m3u8" },
    { "n": "Qazaqstan Int",   "c": "news",    "col": "#a00000", "url": "https://qazaqstantv-stream.qazcdn.com/international/international/playlist.m3u8" },
    { "n": "Khabar",          "c": "news",    "col": "#1a3a6e", "url": "https://live-khabar2.cdnvideo.ru/khabar2/khabar2.sdp/playlist.m3u8" },
    { "n": "Khabar 24",       "c": "news",    "col": "#1a3a6e", "url": "https://live-24kz.cdnvideo.ru/24kz/24kz.sdp/playlist.m3u8" },
    { "n": "El Arna",         "c": "news",    "col": "#6a0dad", "url": "https://elarna-live.cdnvideo.ru/elarna/elarna/playlist.m3u8" },
    { "n": "1 канал Евразия", "c": "news",    "col": "#003087", "url": "https://1tvkz-stream.daitsuna.net/1tvkz/1tvkz/playlist.m3u8" },
    { "n": "КТК",             "c": "news",    "col": "#e63900", "url": "https://wz-kt.ktk.kz/ktklive/smil:ktk-live.smil/playlist.m3u8" },
    { "n": "НТК",             "c": "news",    "col": "#00aaff", "url": "https://ucdn.beetv.kz/bpk-tv/000000673/tve/index.m3u8" },
    { "n": "7 канал",         "c": "news",    "col": "#0055a5", "url": "https://stream.tv7.kz/hls/stream.m3u8" },
    { "n": "31 канал",        "c": "news",    "col": "#ff6600", "url": "https://31kz-streams.daitsuna.net/31kz/31kz/playlist.m3u8" },
    { "n": "Almaty TV",       "c": "news",    "col": "#006633", "url": "https://live-almatytv.cdnvideo.ru/almatytv/almatytv.sdp/playlist.m3u8" },
    { "n": "Astana TV",       "c": "news",    "col": "#003087", "url": "https://6mwyl50nbll.a.trbcdn.net/livemaster/u7v3o_live-i59ya936e5f.smil/playlist.m3u8" },
    { "n": "Qostanai TV",     "c": "news",    "col": "#1e40af", "url": "https://stream.kaztrk.kz/regional/kostanaytv/index.m3u8" },
    { "n": "Мир",             "c": "news",    "col": "#1a3a6e", "url": "https://hls-mirtv.cdnvideo.ru/mirtv-parampublish/mirtv_2500/playlist.m3u8" },
    { "n": "QazSport",        "c": "sports",  "col": "#1ea6cb", "url": "https://qazsporttv-stream.qazcdn.com/qazsporttv/qazsporttv/playlist.m3u8" },
    { "n": "QazSport 2",      "c": "sports",  "col": "#1ea6cb", "url": "https://qazsporttv-stream.qazcdn.com/qazsporttv2/qazsporttv2/playlist.m3u8" },
    { "n": "Balapan",         "c": "kids",    "col": "#e19020", "url": "https://balapantv-stream.qazcdn.com/balapantv/balapantv/playlist.m3u8" },
    { "n": "Мульт",           "c": "kids",    "col": "#7c3aed", "url": "https://ucdn.beetv.kz/bpk-tv/000000710/tve/index.m3u8" },
    { "n": "Карусель",        "c": "kids",    "col": "#f97316", "url": "https://hls-mirtv.cdnvideo.ru/karusel/smil:karusel.smil/playlist.m3u8" },
    { "n": "MuzZone",         "c": "music",   "col": "#9333ea", "url": "https://muzzone-stream.daitsuna.net/muzzondvr/muzzone_dvr/playlist_dvr.m3u8" },
]

# ──────────────────────────────────────────────────────────────
# Скачиваем все источники
# ──────────────────────────────────────────────────────────────
print("=" * 60)
print("KinoFlik TV — генератор tv.js")
print("=" * 60)

all_channels = []
seen_names = set(ch["n"].lower() for ch in OWN_CHANNELS)

for url, default_cat in SOURCES:
    print(f"\n📡 {url.split('/')[-1]} [{default_cat}]")
    chs = fetch_m3u(url, default_cat)
    added = 0
    for ch in chs:
        key = ch["n"].lower()
        if key not in seen_names:
            seen_names.add(key)
            all_channels.append(ch)
            added += 1
    print(f"  ✓ {added} новых каналов (всего уникальных: {len(all_channels) + len(OWN_CHANNELS)})")
    time.sleep(0.3)  # вежливая пауза

total = len(OWN_CHANNELS) + len(all_channels)
print(f"\n✅ Итого: {total} каналов")

# ──────────────────────────────────────────────────────────────
# Генерируем tv.js
# ──────────────────────────────────────────────────────────────
print("\n⚙️  Генерирую tv.js...")

lines = []
lines.append("function P(url) { return '/proxy/stream?url=' + encodeURIComponent(url); }")
lines.append("")
lines.append("/* ============================================================")
lines.append(f"   Сгенерировано автоматически: {total} каналов")
lines.append("   Источник: iptv-org.github.io/iptv")
lines.append("")
lines.append("   Удалить канал → удали строку с { n: '...' }")
lines.append("   Добавить канал → добавь строку по образцу")
lines.append("   c: news | sports | movies | kids | music | documentary | general")
lines.append("   ============================================================ */")
lines.append("var CHANNELS = [")
lines.append("")
lines.append("  /* ══ КАЗАХСТАН (свои стримы) ══════════════════════════════ */")

for ch in OWN_CHANNELS:
    n   = js_escape(ch["n"])
    c   = ch["c"]
    col = ch["col"]
    url = js_escape(ch["url"])
    lines.append(f"  {{ n: '{n}', c: '{c}', col: '{col}', url: P('{url}') }},")

lines.append("")
lines.append("  /* ══ iptv-org GitHub: kz, ru + все категории ══════════════ */")

for ch in all_channels:
    n   = js_escape(ch["n"])
    c   = ch["c"]
    col = name_to_color(ch["n"], ch["c"])
    url = js_escape(ch["url"])
    logo = ch.get("logo", "")

    if logo:
        logo_escaped = js_escape(logo)
        lines.append(f"  {{ n: '{n}', c: '{c}', col: '{col}', logo: '{logo_escaped}', url: P('{url}') }},")
    else:
        lines.append(f"  {{ n: '{n}', c: '{c}', col: '{col}', url: P('{url}') }},")

lines.append("")
lines.append("];")
lines.append("")

# Дописываем весь служебный код tv.js
SERVICE_CODE = r"""
var CAT_LABELS = { all:'Все',news:'Новости',sports:'Спорт',movies:'Кино',kids:'Детские',music:'Музыка',documentary:'Документальные',general:'Общие' };
var curCat='all',curQ='',shownCh=[],activeIdx=-1,hls=null,currentQuality=-1,theaterMode=false,currentChName='',epgTimer=null,hideTimer=null;

function getEPG(name){return{cur:{time:'--:--',title:'Прямой эфир',progress:0,end:''},next:[]};}
function renderEPG(name){var el=document.getElementById('kf-epg-inner');if(!el)return;var d=getEPG(name),c=d.cur;el.innerHTML='<div style="padding:20px;color:#555;text-align:center"><i class="fas fa-calendar-alt" style="font-size:32px;margin-bottom:10px"></i><br>Расписание передач<br>недоступно для этого канала</div>';}
function ensureEPG(){var ex=document.getElementById('kf-epg-section');if(ex){ex.style.display='block';return;}var sec=document.createElement('div');sec.id='kf-epg-section';sec.className='kf-epg-section';sec.innerHTML='<div class="kf-epg-title"><i class="fas fa-calendar-alt"></i> Расписание передач</div><div id="kf-epg-inner"></div>';var tp=document.querySelector('.tv-page');if(tp&&tp.parentNode)tp.parentNode.insertBefore(sec,tp.nextSibling);else document.body.appendChild(sec);}
function startEPG(name){clearInterval(epgTimer);ensureEPG();renderEPG(name);}
function toggleTheater(){theaterMode=!theaterMode;var tp=document.querySelector('.tv-page');if(tp)tp.classList.toggle('theater',theaterMode);}
function toggleFullscreen(){var box=document.getElementById('playerBox');if(!box)return;if(!document.fullscreenElement)box.requestFullscreen&&box.requestFullscreen();else document.exitFullscreen&&document.exitFullscreen();}
document.addEventListener('keydown',function(e){var tag=(document.activeElement||{}).tagName;if(tag==='INPUT'||tag==='TEXTAREA')return;var v=document.getElementById('tvV');switch(e.code){case'KeyF':e.preventDefault();toggleFullscreen();break;case'KeyT':e.preventDefault();toggleTheater();break;case'KeyM':e.preventDefault();if(v)v.muted=!v.muted;break;case'Space':e.preventDefault();if(v){v.paused?v.play():v.pause();}break;case'ArrowUp':e.preventDefault();if(v)v.volume=Math.min(1,+(v.volume+0.1).toFixed(1));break;case'ArrowDown':e.preventDefault();if(v)v.volume=Math.max(0,+(v.volume-0.1).toFixed(1));break;case'ArrowRight':e.preventDefault();if(activeIdx<shownCh.length-1)play(activeIdx+1);break;case'ArrowLeft':e.preventDefault();if(activeIdx>0)play(activeIdx-1);break;}});
function render(){var q=curQ.toLowerCase();shownCh=CHANNELS.filter(function(ch){return(curCat==='all'||ch.c===curCat)&&(!q||ch.n.toLowerCase().indexOf(q)!==-1);});document.getElementById('chCount').textContent=shownCh.length+' каналов';var list=document.getElementById('chList');if(!shownCh.length){list.innerHTML='<div class="spinner" style="color:#555"><i class="fas fa-satellite"></i><span>Каналы не найдены</span></div>';return;}list.innerHTML=shownCh.map(function(ch,i){var abbr=ch.n.replace(/[^A-Za-zА-Яа-яЁё0-9]/g,'').substring(0,3).toUpperCase()||'TV';var logoHtml=ch.logo?'<div class="ch-logo" style="background:transparent"><img src="'+ch.logo+'" style="width:100%;height:100%;object-fit:contain;border-radius:4px" alt="'+abbr+'" onerror="this.parentNode.style.background=\''+ch.col+'\';this.remove()"></div>':'<div class="ch-logo" style="background:'+ch.col+'">'+abbr+'</div>';return'<div class="ch-item'+(i===activeIdx?' on':'')+'" onclick="play('+i+')">'+logoHtml+'<div class="ch-info"><div class="ch-name">'+ch.n+'</div><div class="ch-sub">'+(CAT_LABELS[ch.c]||ch.c)+'</div></div><span class="live-pill">LIVE</span></div>';}).join('');}
function buildPlayer(chName){var box=document.getElementById('playerBox');box.innerHTML='';box.style.position='relative';var video=document.createElement('video');video.id='tvV';video.autoplay=true;video.playsInline=true;video.style.cssText='width:100%;height:100%;display:block;cursor:pointer';box.appendChild(video);var ctrl=document.createElement('div');ctrl.id='kfCtrl';ctrl.className='kf-player-controls';var liveRow=document.createElement('div');liveRow.style.cssText='display:flex;align-items:center;gap:10px;margin-bottom:9px';var redBar=document.createElement('div');redBar.className='kf-live-bar';var shine=document.createElement('div');shine.className='kf-live-bar-shine';redBar.appendChild(shine);var lbadge=document.createElement('span');lbadge.className='kf-live-badge';lbadge.textContent='● LIVE';liveRow.appendChild(redBar);liveRow.appendChild(lbadge);var row=document.createElement('div');row.style.cssText='display:flex;align-items:center;gap:8px';var btnPlay=mkB('⏸',function(){var v=document.getElementById('tvV');if(!v)return;v.paused?v.play():v.pause();btnPlay.textContent=v.paused?'▶':'⏸';});var btnMute=mkB('🔊',function(){var v=document.getElementById('tvV');if(!v)return;v.muted=!v.muted;btnMute.textContent=v.muted?'🔇':'🔊';});var volR=document.createElement('input');volR.type='range';volR.min='0';volR.max='1';volR.step='0.05';volR.value='1';volR.className='kf-volume-slider';volR.addEventListener('input',function(){var v=document.getElementById('tvV');if(v){v.volume=+volR.value;v.muted=false;btnMute.textContent='🔊';}});var chLbl=document.createElement('span');chLbl.className='kf-channel-label';chLbl.textContent=chName;var qWrap=document.createElement('div');qWrap.style.position='relative';var qBtn=mkB('⚙ Авто',function(){var m=document.getElementById('kfQMenu');if(m)m.style.display=m.style.display==='none'?'block':'none';});qBtn.id='kfQBtn';qBtn.style.display='none';qBtn.style.fontSize='12px';var qMenu=document.createElement('div');qMenu.id='kfQMenu';qMenu.style.cssText='display:none;position:absolute;bottom:40px;right:0;background:#1a1a1a;border:1px solid #333;border-radius:8px;overflow:hidden;min-width:100px;z-index:20';qWrap.appendChild(qBtn);qWrap.appendChild(qMenu);var btnT=mkB('⊡',toggleTheater);btnT.title='Кинотеатр (T)';btnT.style.fontSize='18px';var btnF=mkB('⛶',toggleFullscreen);btnF.title='Полный экран (F)';btnF.style.fontSize='18px';row.appendChild(btnPlay);row.appendChild(btnMute);row.appendChild(volR);row.appendChild(chLbl);row.appendChild(qWrap);row.appendChild(btnT);row.appendChild(btnF);ctrl.appendChild(liveRow);ctrl.appendChild(row);box.appendChild(ctrl);function showCtrl(){ctrl.style.opacity='1';clearTimeout(hideTimer);hideTimer=setTimeout(function(){ctrl.style.opacity='0';},3500);}box.addEventListener('mousemove',showCtrl);box.addEventListener('touchstart',showCtrl);video.addEventListener('click',function(){var v=document.getElementById('tvV');if(!v)return;v.paused?v.play():v.pause();btnPlay.textContent=v.paused?'▶':'⏸';});try{var sv=localStorage.getItem('kf_vol');if(sv!==null){video.volume=parseFloat(sv);volR.value=video.volume;}if(video.volume===0){video.muted=true;btnMute.textContent='🔇';}}catch(_){}video.addEventListener('volumechange',function(){try{localStorage.setItem('kf_vol',video.volume);}catch(_){}volR.value=video.volume;btnMute.textContent=(video.volume===0||video.muted)?'🔇':'🔊';});btnMute.onclick=function(){var v=document.getElementById('tvV');if(!v)return;v.muted=!v.muted;volR.value=v.muted?0:v.volume;};return video;}
function mkB(txt,fn){var b=document.createElement('button');b.className='kf-player-btn';b.textContent=txt;b.addEventListener('click',fn);return b;}
function updateQualityMenu(){var btn=document.getElementById('kfQBtn'),menu=document.getElementById('kfQMenu');if(!btn||!menu||!hls||!hls.levels||!hls.levels.length){if(btn)btn.style.display='none';return;}btn.style.display='inline-block';var html=qR('Авто',-1,currentQuality===-1);hls.levels.forEach(function(lv,i){var l=lv.height?lv.height+'p':'Q'+i;if(lv.height>=2160)l='4K';else if(lv.height>=1440)l='2K';html+=qR(l,i,currentQuality===i);});menu.innerHTML=html;btn.textContent='⚙ '+(currentQuality===-1?'Авто':(hls.levels[currentQuality]?hls.levels[currentQuality].height+'p':'Авто'));}
function qR(label,lvl,active){return'<div onclick="setQuality('+lvl+')" style="padding:9px 16px;cursor:pointer;font-size:13px;color:'+(active?'#ff6600':'#ccc')+'" onmouseenter="this.style.background=\'rgba(255,255,255,.08)\'" onmouseleave="this.style.background=\'none\'">'+(active?'✓ ':'')+label+'</div>';}
function setQuality(level){currentQuality=level;if(hls)hls.currentLevel=level;updateQualityMenu();var m=document.getElementById('kfQMenu');if(m)m.style.display='none';}
function play(i){var ch=shownCh[i];if(!ch)return;activeIdx=i;currentChName=ch.n;currentQuality=-1;render();var npName=document.getElementById('npName'),npCat=document.getElementById('npCat'),npEl=document.getElementById('nowPlaying');if(npName)npName.textContent=ch.n;if(npCat)npCat.textContent=CAT_LABELS[ch.c]||ch.c;if(npEl)npEl.classList.add('show');try{localStorage.setItem('kf_tv',JSON.stringify({url:ch.url,n:ch.n,c:ch.c}));}catch(_){}if(hls){hls.destroy();hls=null;}var video=buildPlayer(ch.n);function onFail(msg){var box=document.getElementById('playerBox');if(box)box.innerHTML='<div class="player-placeholder"><i class="fas fa-exclamation-triangle" style="color:#f59e0b"></i><h3>'+msg+'</h3><p>Попробуйте другой канал</p></div>';}if(Hls.isSupported()){hls=new Hls({enableWorker:true,lowLatencyMode:true,maxBufferLength:30});hls.loadSource(ch.url);hls.attachMedia(video);hls.on(Hls.Events.MANIFEST_PARSED,function(){video.play().catch(function(){});updateQualityMenu();});hls.on(Hls.Events.ERROR,function(_,d){if(d.fatal)onFail('Канал временно недоступен');});}else if(video.canPlayType('application/vnd.apple.mpegurl')){video.src=ch.url;video.play().catch(function(){});}else{onFail('Браузер не поддерживает HLS');}startEPG(ch.n);}
var sInput=document.getElementById('chSearch');if(sInput)sInput.addEventListener('input',function(e){curQ=e.target.value;activeIdx=-1;render();});
var cTabs=document.getElementById('catTabs');if(cTabs)cTabs.addEventListener('click',function(e){var btn=e.target.closest('.cat-tab');if(!btn)return;document.querySelectorAll('.cat-tab').forEach(function(b){b.classList.remove('on');});btn.classList.add('on');curCat=btn.dataset.c;activeIdx=-1;render();});
var bMenu=document.getElementById('burgerMenu');if(bMenu)bMenu.addEventListener('click',function(){document.getElementById('sidebar').classList.toggle('open');});
render();
try{var last=JSON.parse(localStorage.getItem('kf_tv')||'null');if(last&&last.url){var idx=shownCh.findIndex(function(ch){return ch.url===last.url;});if(idx!==-1)play(idx);}}catch(_){}
fetch('/api/channels').then(function(r){return r.json();}).then(function(data){if(data&&data.length){var dbCh=data.map(function(c){return{n:c.name,c:c.category||'general',col:c.logo_color||'#000',url:P(c.stream_url),logo:c.logo_url};});var dbNames=new Set(dbCh.map(function(ch){return ch.n;}));CHANNELS=dbCh.concat(CHANNELS.filter(function(ch){return!dbNames.has(ch.n);}));render();}}).catch(function(){});
"""

lines.append(SERVICE_CODE)

output = "\n".join(lines)
with open("tv.js", "w", encoding="utf-8") as f:
    f.write(output)

print(f"✅ Файл tv.js сохранён ({len(output):,} байт)")
print(f"📺 Всего каналов: {total}")
print("\n📋 Скопируй tv.js в:")
print("   KinoFlik/static/js/tv.js")