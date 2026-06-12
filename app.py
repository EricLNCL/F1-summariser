import os
import datetime
import fastf1
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from groq import Groq

matplotlib.rcParams['font.family'] = 'Arial Unicode MS'
os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

st.title("F1 賽事報告")

RACE_DATES = {
    2026: {
        "Bahrain Grand Prix": datetime.date(2026, 3, 22),
        "Saudi Arabian Grand Prix": datetime.date(2026, 3, 29),
        "Australian Grand Prix": datetime.date(2026, 4, 5),
        "Japanese Grand Prix": datetime.date(2026, 4, 19),
        "Chinese Grand Prix": datetime.date(2026, 5, 3),
        "Miami Grand Prix": datetime.date(2026, 5, 10),
        "Monaco Grand Prix": datetime.date(2026, 6, 1),
        "Barcelona Grand Prix": datetime.date(2026, 6, 14),
        "Austrian Grand Prix": datetime.date(2026, 6, 28),
        "British Grand Prix": datetime.date(2026, 7, 5),
        "Belgian Grand Prix": datetime.date(2026, 7, 19),
        "Hungarian Grand Prix": datetime.date(2026, 7, 26),
        "Dutch Grand Prix": datetime.date(2026, 8, 23),
        "Italian Grand Prix": datetime.date(2026, 9, 6),
        "Spanish Grand Prix": datetime.date(2026, 9, 13),
        "Azerbaijan Grand Prix": datetime.date(2026, 9, 20),
        "Singapore Grand Prix": datetime.date(2026, 10, 4),
        "United States Grand Prix": datetime.date(2026, 10, 18),
        "Mexico City Grand Prix": datetime.date(2026, 10, 25),
        "São Paulo Grand Prix": datetime.date(2026, 11, 8),
        "Las Vegas Grand Prix": datetime.date(2026, 11, 21),
        "Qatar Grand Prix": datetime.date(2026, 11, 28),
        "Abu Dhabi Grand Prix": datetime.date(2026, 12, 6),
    }
}

@st.cache_data
def get_races(year):
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule['EventName'].tolist()

col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("賽季", list(range(2026, 2012, -1)))
with col2:
    races = get_races(year)
    race = st.selectbox("場次", races)

today = datetime.date.today()
race_date = RACE_DATES.get(year, {}).get(race)

if race_date and race_date > today:
    st.warning(f"⚠️ 此場比賽尚未進行，預定於 {race_date.strftime('%Y年%m月%d日')} 舉行。")

elif st.button("產生賽事報告"):

    with st.spinner("載入賽事資料中..."):
        session = fastf1.get_session(year, race, 'R')
        support_laps = year >= 2018
        session.load(
            laps=support_laps,
            telemetry=False,
            weather=False,
            messages=support_laps
        )
        results = session.results[['Abbreviation', 'FullName', 'TeamName', 'Position', 'Status']].copy()
        results['Position'] = results['Position'].astype(str)
        if support_laps:
            laps = session.laps
        else:
            laps = None

    st.subheader("最終成績")
    st.dataframe(results, width=800)

    pit_text = "無資料"
    penalty_text = "無資料"

    if laps is not None:

        st.subheader("各車手最快圈速")
        try:
            fastest = laps.groupby('Driver')['LapTime'].min().dropna().sort_values()
            fastest_sec = fastest.dt.total_seconds()
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.barh(fastest_sec.index, fastest_sec.values, color='#e10600')
            ax.set_xlabel('秒數')
            ax.set_title('各車手最快圈速')
            ax.invert_yaxis()
            st.pyplot(fig)
        except Exception as e:
            st.warning(f"圈速資料無法顯示：{e}")

        st.subheader("名次變化")
        try:
            position_changes = []
            for driver in results['Abbreviation']:
                driver_laps = laps[laps['Driver'] == driver][['LapNumber', 'Position']].dropna()
                if not driver_laps.empty:
                    start_pos = driver_laps.iloc[0]['Position']
                    end_pos = driver_laps.iloc[-1]['Position']
                    change = int(start_pos - end_pos)
                    position_changes.append({
                        'Driver': driver,
                        'Start': int(start_pos),
                        'Finish': int(end_pos),
                        'Change': change
                    })
            pos_df = pd.DataFrame(position_changes).sort_values('Change', ascending=False)
            st.dataframe(pos_df, width=600)
        except Exception as e:
            st.warning(f"名次資料無法顯示：{e}")

        st.subheader("Pit Stop 策略")
        try:
            pit_laps = laps[laps['PitOutTime'].notna()][['Driver', 'LapNumber', 'Compound']].dropna()
            st.dataframe(pit_laps, width=600)
            pit_text = pit_laps.to_string()
        except Exception as e:
            st.warning(f"Pit Stop 資料無法顯示：{e}")

        try:
            race_control = session.race_control_messages
            incidents = race_control[
                race_control['Category'].isin(['Flag', 'Incident', 'SafetyCar'])
            ][['Time', 'Message']].head(20)
            st.subheader("事故與安全車")
            st.dataframe(incidents, width=800)
            penalty_text = incidents.to_string()
        except Exception as e:
            st.warning(f"事故資料無法顯示：{e}")

    else:
        st.info("2017 年以前的圈速、Pit Stop、事故資料不支援，僅顯示最終成績與賽事報告。")

    st.subheader("賽事報告")
    results_text = results.to_string()
    prompt = f"""
你是一位 F1 賽事記者，請根據以下 {year} {race} GP 的真實資料，
用繁體中文寫一篇約 400 字的詳細賽事報告。

注意：請使用資料中的 FullName 欄位作為車手全名，不要自行猜測或替換車手姓名。

報告需要包含：
1. 比賽結果前三名（請使用完整姓名）
2. 各車手的輪胎策略（如有資料）
3. 安全車、旗號與事故（如有資料）
4. 任何判罰或關鍵事件
5. 比賽中的名次變化亮點

最終成績（包含完整姓名）：
{results_text}

Pit Stop 與輪胎資料：
{pit_text}

事故與安全車：
{penalty_text}
"""
    with st.spinner("正在撰寫賽事報告..."):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    st.write(response.choices[0].message.content)