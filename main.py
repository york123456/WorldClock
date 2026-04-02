import json
import time
import os
import requests
import pytz
from datetime import datetime
import folium
from folium import plugins
from folium.features import DivIcon

# Selenium 截圖所需套件
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# 1. 讀取設定檔
# ==========================================
def load_config(filepath="config.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
map_cfg = config["map_settings"]
out_cfg = config["output_settings"]
#api_keys = config["api_keys"]



#if env_owm_key:
api_keys= os.getenv("OWM_API_KEY")


# ==========================================
# 2. 初始化地圖 (關閉縮放控制項，讓圖片更乾淨)
# ==========================================
world_map = folium.Map(location=[20, 0], zoom_start=2.5, tiles=None, zoom_control=False)

# -- 底圖選擇
if map_cfg["base_map"] == "dark":
    folium.TileLayer('cartodbdark_matter', name='Dark').add_to(world_map)
elif map_cfg["base_map"] == "satellite":
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    ).add_to(world_map)
elif map_cfg["base_map"] == "nasa_lights":
    folium.TileLayer(
        tiles='https://map1.vis.earthdata.nasa.gov/wmts-webmerc/VIIRS_CityLights_2012/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg',
        attr='NASA GIBS'
    ).add_to(world_map)

# ==========================================
# 3. 疊加圖層 (根據設定檔決定是否載入)
# ==========================================

# -- [圖層 1] 日夜光線區隔
if map_cfg["show_terminator"]:
    world_map.add_child(plugins.Terminator())

# -- [圖層 2] 世界城市時鐘
if map_cfg["show_cities"]:
    cities = [
    {"name": "台北", "lat": 25.032969, "lon": 121.565418, "tz": "Asia/Taipei"},
    {"name": "舊金山", "lat": 37.7749, "lon": -122.4194, "tz": "America/Los_Angeles"},
    {"name": "紐約", "lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
    {"name": "倫敦", "lat": 51.5074, "lon": -0.1278, "tz": "Europe/London"},
    {"name": "巴黎", "lat": 48.8566, "lon": 2.3522, "tz": "Europe/Paris"},
    {"name": "東京", "lat": 35.6762, "lon": 139.6503, "tz": "Asia/Tokyo"},
    {"name": "雪梨", "lat": -33.8688, "lon": 151.2093, "tz": "Australia/Sydney"},
    {"name": "特拉維夫", "lat": 32.0853, "lon": 34.7818, "tz": "Asia/Jerusalem"},
    {"name": "柏林", "lat": 52.5200, "lon": 13.4050, "tz": "Europe/Berlin"},
    {"name": "新德里", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"},
    {"name": "威靈頓", "lat": -41.2865, "lon": 174.7762, "tz": "Pacific/Auckland"},
    {"name": "朱諾", "lat": 58.3019, "lon": -134.4197, "tz": "America/Juneau"},
    {"name": "努克", "lat": 64.1814, "lon": -51.6941, "tz": "America/Nuuk"},
    {"name": "基輔", "lat": 50.4501, "lon": 30.5234, "tz": "Europe/Kyiv"},
    {"name": "關島", "lat": 13.4443, "lon": 144.7937, "tz": "Pacific/Guam"},
    {"name": "科羅爾", "lat": 7.3422, "lon": 134.4789, "tz": "Pacific/Palau"},
    {"name": "檀香山", "lat": 21.3069, "lon": -157.8583, "tz": "Pacific/Honolulu"},
    {"name": "休士頓", "lat": 29.7604, "lon": -95.3698, "tz": "America/Chicago"},
    {"name": "聖荷西", "lat": 37.3382, "lon": -121.8863, "tz": "America/Los_Angeles"},
    {"name": "鳳凰城", "lat": 33.4484, "lon": -112.0740, "tz": "America/Phoenix"},
    {"name": "曼谷", "lat": 13.7563, "lon": 100.5018, "tz": "Asia/Bangkok"},
    {"name": "奧斯陸", "lat": 59.9139, "lon": 10.7522, "tz": "Europe/Oslo"},
    {"name": "赫爾辛基", "lat": 60.1695, "lon": 24.9354, "tz": "Europe/Helsinki"},
    {"name": "熊本", "lat": 32.8031, "lon": 130.7079, "tz": "Asia/Tokyo"},
    {"name": "德勒斯登", "lat": 51.0504, "lon": 13.7373, "tz": "Europe/Berlin"},
        {"name": "首爾", "lat": 37.5665, "lon": 126.9780, "tz": "Asia/Seoul"}
]
    for city in cities:
        tz = pytz.timezone(city['tz'])
        current_time = datetime.now(tz).strftime('%H:%M')
        
        # 標記點
        folium.CircleMarker(
            location=[city['lat'], city['lon']], radius=3, color='#FF9500',
            fill=True, fill_color='#FF9500', fill_opacity=1, weight=1
        ).add_to(world_map)
        
        # 文字標籤
        label_html = f"""
        <div style="color: white; font-family: sans-serif; font-size: 11px; font-weight: bold; text-shadow: 1px 1px 2px black;">
            {city["name"]} <span style="color: #FF9500;">{current_time}</span>
        </div>
        """
        folium.Marker(
            location=[city['lat'], city['lon']],
            icon=DivIcon(icon_size=(100, 20), icon_anchor=(-5, 10), html=label_html)
        ).add_to(world_map)

# -- [圖層 3] USGS 過去 24 小時地震
if map_cfg["show_earthquakes"]:
    try:
        eq_data = requests.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson").json()
        for feature in eq_data['features']:
            lon, lat, _ = feature['geometry']['coordinates']
            mag = feature['properties']['mag']
            folium.CircleMarker(
                location=[lat, lon], radius=max(mag * 1.5, 3),
                color='red', fill=True, fill_color='red', fill_opacity=0.4, weight=1
            ).add_to(world_map)
    except Exception as e:
        print(f"地震資料獲取失敗: {e}")

# -- [圖層 4] ISS 國際太空站
if map_cfg["show_iss"]:
    try:
        iss_data = requests.get("https://api.wheretheiss.at/v1/satellites/25544").json()
        folium.Marker(
            location=[iss_data['latitude'], iss_data['longitude']],
            icon=DivIcon(html="<div style='font-size: 20px; text-shadow: 0px 0px 5px white;'>🛰️</div>")
        ).add_to(world_map)
    except Exception as e:
        print(f"ISS 資料獲取失敗: {e}")

# -- [圖層 5] NOAA 雲圖
if map_cfg["show_clouds"]:
    folium.raster_layers.WmsTileLayer(
        url='https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r-t.cgi?',
        layers='goes_global_ir', fmt='image/png', transparent=True,
        attr='NOAA', opacity=0.5
    ).add_to(world_map)

# -- [圖層 6] RainViewer 雷達
if map_cfg["show_radar"]:
    try:
        rv_data = requests.get("https://api.rainviewer.com/public/weather-maps.json").json()
        latest_path = rv_data['radar']['past'][-1]['path']
        tile_url = f"{rv_data['host']}{latest_path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
        folium.TileLayer(tiles=tile_url, attr='RainViewer', transparent=True, opacity=0.7).add_to(world_map)
    except Exception as e:
        print(f"RainViewer 資料獲取失敗: {e}")

# -- [圖層 7] OWM 氣溫圖
if map_cfg["show_temperature"] and api_keys["openweathermap"]:
    folium.TileLayer(
     tiles=f"https://tile.openweathermap.org/map/temp_new/{{z}}/{{x}}/{{y}}.png?APPID={api_keys['openweathermap']}",
        attr='OWM', transparent=True, opacity=0.5
    ).add_to(world_map)

# ==========================================
# 4. 輸出 HTML 並使用 Selenium 進行截圖
# ==========================================
temp_html = os.path.abspath(out_cfg["temp_html_filename"])
output_png = out_cfg["image_filename"]

print("正在生成地圖配置...")
world_map.save(temp_html)

print(f"啟動背景瀏覽器進行截圖 (解析度: {out_cfg['resolution']['width']}x{out_cfg['resolution']['height']})...")

chrome_options = Options()
chrome_options.add_argument("--headless") # 無頭模式，不顯示實體視窗
chrome_options.add_argument(f"--window-size={out_cfg['resolution']['width']},{out_cfg['resolution']['height']}")
chrome_options.add_argument("--hide-scrollbars") # 隱藏卷軸

# 自動下載並設定 ChromeDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 載入本地端的 HTML
    driver.get(f"file://{temp_html}")
    
    # 等待圖層與外部 API 圖片加載完成
    wait_time = out_cfg["wait_time_seconds"]
    print(f"等待圖層加載 {wait_time} 秒...")
    time.sleep(wait_time) 
    
    # 儲存截圖
    driver.save_screenshot(output_png)
    print(f"✅ 成功！地圖已儲存為圖片：{output_png}")
finally:
    driver.quit()
    # 選擇性清理暫存檔
    if os.path.exists(temp_html):
        os.remove(temp_html)
