import os
from openai import AzureOpenAI
from types import SimpleNamespace
from dotenv import load_dotenv


# Load environment variables from .env file in the config folder
load_dotenv(dotenv_path='config/settings.env')

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-08-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)

def get_ai_suggestions(kpi, baseline) -> str:
    """
    Generate AI-based voyage insights comparing the latest KPI data against baseline averages
    and target signals available inside the KPI object.
    """

    try:
        if isinstance(kpi, dict):
            kpi = SimpleNamespace(**kpi)  
        # --- complete structured prompt ---
        prompt = f"""
You are a Marine Efficiency AI Assistant specializing in ship performance benchmarking,
fuel optimization, and waste heat recovery (WHR) analysis. 

Your task: analyze this voyage using the provided **KPI data**, **baseline averages**, and **target values** 
(embedded within the KPIs). Provide a concise yet analytical summary and 3 actionable recommendations.

---

### 🚢 Current Voyage KPI Data
**General Info**
- From: {kpi.port_from}
- To: {kpi.port_to}
- Voyage Start: {kpi.voyage_start}
- Voyage End: {kpi.voyage_end}
- Duration: {kpi.voyage_duration_hours:.2f} h
- Distance: {kpi.distance_nm:.2f} NM
- Avg Speed (SOG): {kpi.avg_sog_kn:.2f} kn
- Max Speed: {kpi.max_sog_kn:.2f} kn

**Fuel Consumption**
- Total Fuel: {kpi.fuel_total_tonnes:.2f} tonnes
- Fuel per NM: {getattr(kpi, 'fuel_tonnes_per_nm', 'N/A')}
- LNG Consumption: {kpi.fuel_by_signal_Total_LNG_Consumption_tonnes:.2f} tonnes
- MGO Consumption: {kpi.fuel_by_signal_Total_MGO_Consumption_tonnes:.2f} tonnes
- Auxiliary Boiler Fuel: {kpi.fuel_by_signal_Total_Auxiliary_Boiler_Fuel_Consumption_tonnes:.2f} tonnes

**Energy & Power**
- Total Energy Produced: {kpi.energy_mwh_prod:.2f} MWh
- Total Energy Output: {kpi.energy_mwh_total:.2f} MWh
- Net Energy: {kpi.energy_mwh_net:.2f} MWh
- Peak Power: {kpi.peak_kw:.2f} kW at {kpi.peak_time}

**Waste Heat Recovery (WHR)**
- WHR Produced: {getattr(kpi, 'whr_total_prod_mwh', 'N/A')}
- WHR Consumed: {kpi.whr_total_cons_mwh:.2f} MWh
- Utilization: {kpi.whr_util_rate_percent:.2f} %
- Losses – HT Dump: {kpi.whr_loss_Total_WHR_Losses_HT_Dump_mwh:.2f} MWh
- Losses – Steam Dump: {kpi.whr_loss_Total_WHR_Losses_Steam_Dump_mwh:.2f} MWh

**WHR Consumers**
- Condensate Heater: {kpi.whr_consumer_WHR_Condensate_Heater_mwh:.2f} MWh
- Evaporators: {kpi.whr_consumer_WHR_Evaporators_mwh:.2f} MWh
- Laundry: {kpi.whr_consumer_WHR_Laundry_mwh:.2f} MWh
- Potable Water Heating: {kpi.whr_consumer_WHR_Potable_Water_Heating_mwh:.2f} MWh
- AC Reheating: {kpi.whr_consumer_WHR_AC_Reheating_mwh:.2f} MWh
- Absorption Chiller: {kpi.whr_consumer_WHR_Absorption_Chiller_mwh:.2f} MWh
- Other Uses: {kpi.whr_consumer_WHR_Other_Uses_mwh:.2f} MWh

**Wind & Environment**
- Relative Wind Speed: {kpi.relative_wind_speed_kn:.2f} kn
- Relative Wind Direction: {kpi.relative_wind_direction_deg:.2f}°
- True North Wind Speed: {kpi.true_north_wind_speed_kn:.2f} kn

**Engine Loads (%)**
- ME1: {kpi.Avg_ME_1_Load_avg_load_percent:.2f}
- ME2: {kpi.Avg_ME_2_Load_avg_load_percent:.2f}
- ME3: {kpi.Avg_ME_3_Load_avg_load_percent:.2f}
- ME4: {kpi.Avg_ME_4_Load_avg_load_percent:.2f}
- ME5: {kpi.Avg_ME_5_Load_avg_load_percent:.2f}
- ME6: {kpi.Avg_ME_6_Load_avg_load_percent:.2f}

**Target Performance Values (Embedded in KPI)**
- Target Fuel: {kpi.target_fuel_tonnes:.2f} tonnes
- Target LNG: {kpi.target_lng_tonnes:.2f} tonnes
- Target Electricity: {kpi.target_electricity_mwh:.2f} MWh
- Target WHR: {kpi.target_whr_mwh:.2f} MWh

---

### ⚙️ Baseline Averages
{baseline}

---

### 🧭 Your Tasks
1. Compare the current voyage performance to baseline averages and target KPIs.
2. Identify where performance was better or worse (fuel, energy, WHR, etc.).
3. If fuel consumption seems higher, analyze whether wind, distance, or engine load justify it.
4. Evaluate WHR utilization efficiency and energy balance (production vs consumption).
5. Provide a **Voyage Summary**, **Key Observations**, and **3 actionable Recommendations**.

Respond in this format:

**Voyage Performance Summary:**  
(Brief 3–5 line summary comparing KPI, baseline, and target.)

**Key Observations:**  
• (Comparison insight)  
• (Insight on fuel or WHR efficiency)  
• (Environmental or operational factor)

**Recommendations:**  
1. (Short actionable improvement)  
2. (Short actionable improvement)  
3. (Short actionable improvement)
"""

        # --- Send to Azure GPT ---
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a maritime performance optimization expert. "
                        "Analyze ship KPIs to assess efficiency, energy, WHR, and environmental impact. "
                        "Use baseline and target comparisons to provide insightful, data-grounded recommendations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"(Error generating AI insights: {e})"
