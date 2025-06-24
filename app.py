import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import urllib.parse
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections.abc import MutableMapping

########## --- MongoDB Setup ---############
@st.cache_resource(ttl=600)
def get_mongo_client():
    uri = st.secrets["mongodb"]["uri"]
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    try:
        client.server_info()
        return client
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
        return None
################---Definition of Variable----#############
@st.cache_data
def load_cities(filepath="https://raw.githubusercontent.com/ogatech4real/smart-energy-optimiser/main/worldcities.csv", limit=5000):
    try:
        df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines='skip')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding="ISO-8859-1", on_bad_lines='skip')
    except pd.errors.ParserError:
        st.error("🚨 Error parsing the cities CSV file. Some rows were skipped due to malformed structure.")
        st.stop()

    # Validate required columns
    required_columns = {'city', 'iso2', 'population'}
    if not required_columns.issubset(df.columns):
        st.error(f"❌ CSV is missing required columns: {required_columns - set(df.columns)}")
        st.stop()

    df_sorted = df.sort_values(by="population", ascending=False).head(limit)
    df_sorted["display_name"] = df_sorted["city"].str.strip() + ", " + df_sorted["iso2"].str.strip()
    return df_sorted

def fetch_weather(location_param, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location_param, "appid": api_key, "units": "metric"}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.sidebar.error(f"Weather API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.sidebar.error(f"Weather API Exception: {e}")
        return None

def log_environment_data(location, weather_data):
    try:
        client = get_mongo_client()
        db = client.smart_energy_db
        telemetry = db.environment_telemetry
        doc = {
            "location": location,
            "timestamp": datetime.utcnow(),
            "temperature": weather_data.get("Temperature (°C)"),
            "humidity": weather_data.get("Humidity (%)"),
            "cloud_cover": weather_data.get("Cloud Cover (%)"),
            "solar_irradiance": weather_data.get("Solar Irradiance (Est) W/m²")
        }
        telemetry.insert_one(doc)
    except Exception as e:
        st.sidebar.error(f"Failed to log telemetry data: {e}")

def ensure_timeseries_collection():
    client = get_mongo_client()
    db = client.smart_energy_db
    if "environment_telemetry_ts" not in db.list_collection_names():
        try:
            db.create_collection(
                "environment_telemetry_ts",
                timeseries={"timeField": "timestamp", "metaField": "location", "granularity": "hours"}
            )
        except Exception as e:
            st.sidebar.warning(f"Timeseries collection creation warning: {e}")

def fetch_telemetry_history(limit=48):
    client = get_mongo_client()
    db = client.smart_energy_db
    telemetry = db.environment_telemetry
    data = list(telemetry.find().sort("timestamp", -1).limit(limit))
    return pd.DataFrame(data)

def log_user_profile(appliances, battery_capacity, solar_capacity):
    client = get_mongo_client()
    db = client.smart_energy_db
    usage_profiles = db.usage_profiles
    profile = {
        "timestamp": datetime.utcnow(),
        "appliances": appliances,
        "system_config": {
            "battery_capacity_Wh": battery_capacity,
            "solar_capacity_W": solar_capacity
        }
    }
    usage_profiles.insert_one(profile)

def log_ai_decision(input_summary, recommendation, confidence=1.0, model="heuristic", reason=None):
    client = get_mongo_client()
    db = client.smart_energy_db
    decisions = db.ai_decision_log
    log = {
        "timestamp": datetime.utcnow(),
        "input_summary": input_summary,
        "recommendation": recommendation,
        "confidence_score": confidence,
        "decision_model": model,
        "explanation": reason or "Rule-based heuristic"
    }
    decisions.insert_one(log)
###############################################################################
### --- App Config ---####
st.set_page_config(page_title="Smart Energy Optimiser", layout="wide")
st.title("🔋Smart Energy Optimiser")

########## --- Main App Execution Function ---################################
def main():
    # Sidebar System Configuration
    st.sidebar.header("⚙️Configure System")
    st.sidebar.caption("🔌Insert your System Details Here")
    solar_capacity = st.sidebar.number_input("Solar Panel Capacity (Watts)", 100, 10000, 2000)
    battery_capacity = st.sidebar.number_input("Battery Bank Capacity (Wh)", 500, 20000, 5000)
    panel_efficiency = st.sidebar.slider("Panel Efficiency (%)", 10, 25, 18)
    st.sidebar.caption("🔌Third-Party info, Refresh if unavailable")

    ########## Section 1: Appliance, Simulation, & Forecast (two columns) -------######
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏠Appliance")
        appliance_categories = {
            "Lighting": ["LED Bulb (10W)", "Tube Light (40W)"],
            "Electronics": ["TV (100W)", "Laptop (60W)", "WiFi Router (10W)"],
            "Motors/Compressors": ["Refrigerator (150W)", "Washing Machine (500W)", "Water Pump (800W)"],
            "Heating/Cooling": ["Electric Heater (1500W)", "Fan (70W)", "Air Conditioner (2000W)"],
            "OtherApliance": ["Other (W)"]
        }
        selected_appliances = {}
        st.caption("🔌Select Appliances and Estimate Hourly Usage")
        for category, items in appliance_categories.items():
            with st.expander(category):
                for item in items:
                    ap_col1, ap_col2, ap_col3 = st.columns([3, 2, 1])
                    with ap_col1:
                        use = st.checkbox(item, key=item)
                    with ap_col2:
                        if "Other" in item:
                            custom_watt = st.number_input(f"Wattage", min_value=1, max_value=5000, value=100, key=f"{item}_watt")
                        else:
                            custom_watt = int(item.split("(")[1].split("W")[0])
                    with ap_col3:
                        hours = st.number_input(f"Hours", min_value=0.0, max_value=24.0, value=4.0, step=0.5, key=f"{item}_hrs")
                    if use:
                        selected_appliances[item] = {"watt": custom_watt, "hours": hours}

    # ---- Section 2: Simulation Engine ----
    with col2:
        st.subheader("🔋Simulation")
        st.caption("🔌Today's Estimated Load & Forecasted Energy")
        total_load_wh = sum(a['watt'] * a['hours'] for a in selected_appliances.values())
        solar_input_kwh = (solar_capacity * (panel_efficiency / 100)) * 5 / 1000  # Assuming 5 sun hours
        total_available_energy = min(battery_capacity / 1000 + solar_input_kwh, battery_capacity / 1000)
        remaining_energy = total_available_energy - (total_load_wh / 1000)

        st.metric("Total Estimated Load", f"{total_load_wh:.1f} Wh")
        st.metric("Estimated Daily Solar Generation", f"{solar_input_kwh:.2f} kWh")
        st.metric("Projected Battery + Solar Energy", f"{total_available_energy:.2f} kWh")
        st.metric("Energy After Usage", f"{remaining_energy:.2f} kWh")

# ---- Section 3: Advisory Engine ----
    st.subheader("🧠 Smart Advisory")
    st.caption("🔌 You will get an intelligent advice based on Forecast")
    
    # 👉 Move location selector OUTSIDE conditional block to always define location_param
    st.sidebar.caption("📍 Weather Forecast Location")
    cities_df = load_cities()
    city_options = cities_df["display_name"].tolist()
    default_city = "Middlesbrough, GB"
    selected_city = st.sidebar.selectbox(
        "Select Location (City, Country):",
        options=city_options,
        index=city_options.index(default_city) if default_city in city_options else 0
    )
    city, country = selected_city.split(", ")
    location_param = f"{city},{country}"
    
    # ✅ Weather fetch now happens outside too — ensures consistent weather_data access
    weather_data_raw = fetch_weather(location_param, st.secrets["openweathermap"]["api_key"])
    weather_data = {}
    if weather_data_raw:
        weather_data = {
            "Temperature (°C)": weather_data_raw['main']['temp'],
            "Humidity (%)": weather_data_raw['main']['humidity'],
            "Cloud Cover (%)": weather_data_raw['clouds']['all'],
            "Solar Irradiance (Est) W/m²": max(0, (100 - weather_data_raw['clouds']['all']) * 10)
        }
        for k, v in weather_data.items():
            st.sidebar.metric(label=k, value=v)
    
    # 💡 Smart advisory logic follows now
    if remaining_energy < 0:
        st.warning("⚠️ Energy Deficit Detected! Reduce load or reschedule usage to peak solar hours.")
        high_consumers = sorted(selected_appliances.items(), key=lambda x: x[1]['watt'], reverse=True)
        st.subheader("Suggested Load Rationalization:")
        for item, data in high_consumers[:3]:
            st.write(f"• Consider reducing hours for **{item}** ({data['watt']}W)")
    else:
        st.success("✅ Energy is sufficient for today's usage pattern.")
        if remaining_energy > 1:
            st.info("🔋 You have surplus energy. Consider running optional appliances or charging devices during the day.")
    
    # ⏱ Ensure MongoDB telemetry collection
    ensure_timeseries_collection()

    #### -- Final Decision Logging --########
    decision_note = "Reduce load or reschedule" if remaining_energy < 0 else "Run optional devices"
    log_ai_decision(
        input_summary={"total_load_Wh": total_load_wh, "remaining_energy_kWh": remaining_energy},
        recommendation=decision_note,
        confidence=0.95,
        model="heuristic",
        reason="based on solar input and usage profile"
    )
###############-------------------------####################################
    # -------- Tomorrow's Forecast Advisory --------
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🌤️Next-Day Forecast")
        st.caption("🔌Tomorrow's Solar Forecast and Expected Energy")
        @st.cache_data(ttl=3600)
        def fetch_tomorrow_weather_forecast(location_param, api_key):
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {"q": location_param, "appid": api_key, "units": "metric"}
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                tomorrow = datetime.utcnow().date() + timedelta(days=1)
                return [entry for entry in data["list"] if datetime.utcfromtimestamp(entry["dt"]).date() == tomorrow]
            else:
                st.error(f"Forecast API error: {response.status_code}")
                return []

        def estimate_tomorrow_solar_kwh(forecast_list, solar_capacity, efficiency_percent):
            irradiance_estimates = []
            for entry in forecast_list:
                clouds = entry["clouds"]["all"]
                est_irradiance = max(0, (100 - clouds) * 10)  # W/m²
                irradiance_estimates.append(est_irradiance)
            if irradiance_estimates:
                avg_irradiance = np.mean(irradiance_estimates)
                # Estimate equivalent full-sun hours from average irradiance (assuming 1000 W/m² as 1 sun hour)
                sun_hours = avg_irradiance / 1000 * len(irradiance_estimates) / 3  # 3-hour intervals
                return round((solar_capacity * (efficiency_percent / 100) * sun_hours) / 1000, 2)  # kWh
            return 0.0

        # --- Execute Forecast Advisory ---
        tomorrow_forecast = fetch_tomorrow_weather_forecast(location_param, st.secrets["openweathermap"]["api_key"])
        if tomorrow_forecast:
            est_solar_kwh = estimate_tomorrow_solar_kwh(tomorrow_forecast, solar_capacity, panel_efficiency)
            est_total_energy_kwh = min(battery_capacity / 1000 + est_solar_kwh, battery_capacity / 1000)
            tomorrow_remaining_energy = est_total_energy_kwh - (total_load_wh / 1000)

            st.metric("☀️ Forecasted Solar Input", f"{est_solar_kwh:.2f} kWh")
            st.metric("🔋 Available Energy (Est.)", f"{est_total_energy_kwh:.2f} kWh")
            st.metric("🧮 Expected Surplus/Deficit", f"{tomorrow_remaining_energy:.2f} kWh")

            if tomorrow_remaining_energy < 0:
                st.warning("⚠️ Projected energy shortfall tomorrow. Consider adjusting appliance usage.")
                high_drain = sorted(selected_appliances.items(), key=lambda x: x[1]['watt'], reverse=True)
                st.markdown("**🔧 Suggested Adjustments for Tomorrow:**")
                for item, data in high_drain[:3]:
                    st.write(f"• Reduce usage of **{item}** ({data['watt']}W x {data['hours']}h)")

                log_ai_decision(
                    input_summary={
                        "forecasted_solar_kWh": est_solar_kwh,
                        "expected_total_energy": est_total_energy_kwh,
                        "tomorrow_remaining_energy": tomorrow_remaining_energy
                    },
                    recommendation="Reduce or shift high-power appliances",
                    confidence=0.90,
                    model="forecast-advisor",
                    reason="based on tomorrow's irradiance forecast"
                )
            else:
                st.success("✅ Sufficient energy expected tomorrow based on forecast.")
                st.info("📌 Consider shifting some flexible loads to tomorrow if surplus persists.")

                log_ai_decision(
                    input_summary={
                        "forecasted_solar_kWh": est_solar_kwh,
                        "expected_total_energy": est_total_energy_kwh,
                        "tomorrow_remaining_energy": tomorrow_remaining_energy
                    },
                    recommendation="Optional appliance usage encouraged",
                    confidence=0.90,
                    model="forecast-advisor",
                    reason="adequate energy projected for next day"
                )

    with col2:
        st.header("📅Energy Budgeting")
        st.caption("🔌Daily Appliance Scheduler based on available solar power")
        selected_date = st.date_input("Select Day", datetime.now().date())
        available_appliances = ["Washing Machine", "Iron", "Kettle", "Fridge", "Heater"]
        selected_appliance = st.selectbox("Select Appliance", available_appliances)
        start_time = st.time_input("Start Time", value=datetime.now().replace(hour=8, minute=0).time())
        duration_hours = st.slider("Usage Duration (hrs)", 0.5, 4.0, 1.0, step=0.5)
        expected_kWh = st.number_input("Estimated Energy Consumption (kWh)", min_value=0.1, value=0.8)

        if st.button("Add to Schedule"):
            # Placeholder logic for storing to MongoDB
            st.success(f"{selected_appliance} scheduled for {start_time} for {duration_hours} hrs on {selected_date}")

##########################------------------------#####################################
    # Section 3: Predictive Anomaly Alerts
    st.header("🔍 Predictive Anomaly Insights")
    st.caption("🔌Get intelligent advice based on today's & tomorrow's data")
    today_cloud = 15  # % (dynamic from DB)
    tomorrow_cloud = 85  # % (dynamic from forecast API)
    deviation = abs(tomorrow_cloud - today_cloud)
    threshold = 50
    if deviation >= threshold:
        st.error(
            f"⚠️ Anomaly Detected: Cloud cover change = {deviation}%. Solar energy expected to drop sharply tomorrow.")
        st.markdown("👉 Consider shifting high-load appliances to today.")
        st.code(f"Today Cloud Cover: {today_cloud}%, Tomorrow: {tomorrow_cloud}%", language="json")
    else:
        st.success("✅ Solar conditions are stable for the next 24 hours.")

    # Forecast Chart
    st.subheader("📊Energy Flow Forecast")
    st.caption("🔌The chart shows your Load impact on you solar generation.")
    st.bar_chart(pd.DataFrame({
        "Solar Generation (kWh)": np.linspace(0, solar_input_kwh, 24),
        "Load Consumption (kWh)": np.linspace(0, total_load_wh / 1000, 24)
    }, index=[(datetime.now() + timedelta(hours=i)).strftime("%H:%M") for i in range(24)]))

    # -- Historical Trend Visualization --
    st.subheader("📊Telemetry History & Solar Trend")
    st.caption("🔌The chart shows the Trend of temperature & solar strength")
    history_df = fetch_telemetry_history()
    if not history_df.empty:
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
        history_df = history_df.sort_values("timestamp")
        st.line_chart(
            history_df.set_index("timestamp")[["temperature", "solar_irradiance"]].rename(columns={
                "temperature": "Temp (°C)",
                "solar_irradiance": "Solar (W/m²)"
            })
        )

    st.markdown("### 📊 Energy Budget vs Appliance Load")
    st.caption("🔌Simulated bar chart for planned vs available energy")
    budget_df = pd.DataFrame({
        "Time Block": ["Morning", "Afternoon", "Evening"],
        "Solar Forecast (kWh)": [3.5, 2.0, 1.0],
        "Scheduled Load (kWh)": [2.0, 2.5, 0.5],
    })
    fig2 = px.bar(
        budget_df.melt(id_vars="Time Block", var_name="Metric", value_name="kWh"),
        x="Time Block", y="kWh", color="Metric", barmode="group",
        title="Solar Generation vs Appliance Load"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Log user configuration
    st.session_state.user_profile = log_user_profile(selected_appliances, battery_capacity, solar_capacity)
    st.write("User profile logged:", st.session_state.user_profile)

    # Log telemetry asynchronously or synchronously here
    log_environment_data(location_param, weather_data)

st.caption("Smart Energy Usage Optimiser – Leveraging on Google Cloud Solutions")
st.markdown("An interactive app that helps off-grid and solar-powered homes optimize energy use through real-time forecasts, solar modeling, and intelligent load management: https://shorturl.at/D9JQj")
if __name__ == "__main__":
    main()

    # Footer Section
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; font-size: 14px;'>
            Developed by <strong>Adewale Ogabi</strong> | 
            <a href='https://www.linkedin.com/in/ogabiadewale' target='_blank'>LinkedIn Profile</a>
        </div>
        """,
        unsafe_allow_html=True
    )
