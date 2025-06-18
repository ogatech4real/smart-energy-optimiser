
# Smart Energy Optimiser for Renewable Systems  
**A weather-aware, AI-assisted advisor for optimizing solar energy usage in off-grid and smart homes.**

---

## Overview

The Smart Energy Usage Optimiser is an interactive, cloud-native web application designed to empower households operating on solar and off-grid energy systems. By leveraging real-time weather forecasts, dynamic solar irradiance modeling, battery charge state estimation, and customizable appliance load profiles, the system delivers actionable recommendations to maximize energy efficiency and sustainability.

Built on a scalable architecture utilizing MongoDB Atlas and Streamlit, this prototype exemplifies next-generation decentralized energy management tailored for edge computing environments.

---

## Key Features

-  **Live Weather Forecasting** via OpenWeatherMap API with caching and error handling  
-  **Solar Irradiance Simulation** calibrated for geospatial parameters  
-  **Battery State-of-Charge Modeling** with dynamic load forecasting  
-  **User-Configurable Appliance Profiles** supporting real-time consumption metrics  
-  **Comprehensive Telemetry Logging** into MongoDB Atlas for analytics and audit trails  
-  **Time-Series Data Visualization** (integration via MongoDB Charts)  
-  Fully compatible with cloud deployment and IoT/Smart Grid ecosystem integration  

---

##  System Architecture

```text
User Input (Streamlit UI)
        ↓
Weather Forecast API (OpenWeatherMap)
        ↓
Solar Generation & Irradiance Model
        ↓
Battery Charge Estimation Module
        ↓
Appliance Load Aggregation & Profiling
        ↓
AI/Heuristic Decision Support Engine
        ↓
Telemetry + AI Decision Logging (MongoDB Atlas)
        ↓
Dashboard Display & User Advisory

```

> _Modular backend design allows plug-and-play replacement of AI models, data sources, or simulation engines._

---

## Tech Stack

| Layer           | Technology                         |
|----------------|-------------------------------------|
| Frontend UI              | Streamlit                 |
| Backend Logic   | Python (Solar Modeling, AI Engine) |
| Data Storage    | MongoDB Atlas (Cloud-hosted)       |
| Weather API     | OpenWeatherMap                     |
| Deployment      | Streamlit Cloud / Localhost        |
| Visualization   | Streamlit, Matplotlib, Altair      |

---

##  Setup Instructions

### 1. Clone the repository

```bash
https://gitlab.com/adewaleogabi/smart-energy-optimiser.git
cd smart-energy-optimizer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Secrets

Create a `.streamlit/secrets.toml` file with your credentials:

```
# .streamlit/secrets.toml

mongo_uri = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
weather_api_key = "your_openweathermap_api_key"
```

### 4. Run the App

```
streamlit run app.py
```

---

## MongoDB Collections

| Collection             | Description                                      |
|------------------------|--------------------------------------------------|
| `environment_telemetry` | Stores irradiance, temperature, weather data     |
| `usage_profiles`        | Appliance settings per user session              |
| `ai_decision_log`       | Inference outcomes and rationale from AI engine  |

Supports time-series data operations for predictive analytics and load trend visualization.

---

## AI & Decision Support

The current engine uses a rule-based inference mechanism to assess:

- Forecasted solar energy availability
- Battery charge/discharge cycles and thresholds
- Aggregate appliance load against available capacity
- Load shifting recommendations based on priority and surplus energy.

> Future enhancements will integrate adaptive machine learning models for behavior prediction and adaptive load management.

---

## Architecture Diagram

![System Architecture](s.png)

_This diagram illustrates the modular pipeline from data ingestion, modeling, inference, and UI display._

---

## Use Cases

Renewable-powered smart homes
Remote off-grid solar installations
IoT-enabled microgrid energy management
Predictive scheduling for critical household loads
Energy advisory platforms for emerging markets

---

## Roadmap & Future Enhancements
 Integrate ML-driven predictive load balancing

 Historical data visualization dashboards

 User session management, profile saving, and retrieval

 Advanced weather API caching and fallback strategies

 Expand appliance database and AI reasoning capabilities

---

## Acknowledgements
OpenWeatherMap – Weather API provider
MongoDB Atlas – Cloud database platform
Streamlit – Frontend framework
GitLab – CI/CD and repository management platform
Google Cloud Hackathon Team – Inspiration and collaboration

## Security & Data Privacy
Sensitive credentials managed securely via .streamlit/secrets.toml
No personally identifiable information collected or stored
MongoDB Atlas access controlled by role-based permissions and IP whitelisting

## License
MIT License. See `LICENSE` file for more details.

---

## Contact

**Adewale Ogabi**  
[LinkedIn](https://www.linkedin.com/in/ogabiadewale/) · [Email](ogabi.adewale@gmail.com)
