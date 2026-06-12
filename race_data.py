import fastf1

# 載入 2026 摩納哥 GP 的賽事資料
fastf1.Cache.enable_cache('cache')
session = fastf1.get_session(2026, 'Monaco', 'R')
session.load()

# 看一下資料長什麼樣子
print(session.results[['DriverNumber', 'Abbreviation', 'TeamName', 'Position']])
