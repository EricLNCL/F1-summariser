import os
import fastf1
from groq import Groq

# 設定 Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# 載入 2026 摩納哥 GP 資料
fastf1.Cache.enable_cache('cache')
session = fastf1.get_session(2026, 'Monaco', 'R')
session.load()

# 整理最終成績
results = session.results[['Abbreviation', 'TeamName', 'Position', 'Status']]
results_text = results.to_string()

# 整理 Pit Stop 資料
laps = session.laps
pit_laps = laps[laps['PitOutTime'].notna()][['Driver', 'LapNumber', 'Compound']].dropna()
pit_text = pit_laps.to_string()

# 整理判罰資料
try:
    race_control = session.race_control_messages
    penalties = race_control[race_control['Category'] == 'SafetyCar'][['Time', 'Message']].head(10)
    flags = race_control[race_control['Category'].isin(['Flag', 'Incident'])][['Time', 'Message']].head(20)
    penalty_text = "Safety Car:\n" + penalties.to_string() + "\n\n旗號與事故:\n" + flags.to_string()
except:
    penalty_text = "無判罰資料"

# 組成 Prompt（加入判罰）
prompt = f"""
你是一位 F1 賽事記者，請根據以下 2026 摩納哥 GP 的真實資料，
用繁體中文寫一篇約 400 字的詳細賽事報告。

報告需要包含：
1. 比賽結果前三名
2. 各車手的輪胎策略
3. 安全車、旗號與事故
4. 任何判罰或關鍵事件

最終成績：
{results_text}

Pit Stop 與輪胎資料：
{pit_text}

安全車與事故資料：
{penalty_text}
"""