import os
import fastf1
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from groq import Groq

matplotlib.rcParams['font.family'] = 'Arial Unicode MS'
import os
os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

st.title("F1 賽事報告")

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

if st.button("產生賽事報告"):

    # 載入資料
    with st.spinner("載入賽事資料中..."):
        session = fastf1.get_session(year, race, 'R')
        support_laps = year >= 2018
        session.load(
            laps=support_laps,
            telemetry=False,
            weather=False,
            messages=support_laps
        )
        results = session.results[['Abbreviation', 'TeamName', 'Position', 'Status']].copy()
        results['Position'] = results['Position'].astype(str)
        laps = session.laps if support_laps else None

    # 最終成績
    st.subheader("最終成績")
    st.dataframe(results, width=800)

    pit_text = "無資料"
    penalty_text = "無資料"

    if laps is not None:

        # 圈速圖表
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

        # 名次變化
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

        # Pit Stop 策略
        st.subheader("Pit Stop 策略")
        try:
            pit_laps = laps[laps['PitOutTime'].notna()][['Driver', 'LapNumber', 'Compound']].dropna()
            st.dataframe(pit_laps, width=600)
            pit_text = pit_laps.to_string()
        except Exception as e:
            st.warning(f"Pit Stop 資料無法顯示：{e}")

        # 事故與安全車
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

    # AI 報告
    st.subheader("賽事報告")
    results_text = results.to_string()
    prompt = f"""
你是一位 F1 賽事記者，請根據以下 {year} {race} GP 的真實資料，
用繁體中文寫一篇約 400 字的詳細賽事報告。

報告需要包含：
1. 比賽結果前三名
2. 各車手的輪胎策略（如有資料）
3. 安全車、旗號與事故（如有資料）
4. 任何判罰或關鍵事件
5. 比賽中的名次變化亮點

最終成績：
{results_text}

Pit Stop 與輪胎資料：
{pit_text}

事故與安全車：
{penalty_text}
"""
    with st.spinner("AI 正在撰寫報告..."):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    st.write(response.choices[0].message.content)