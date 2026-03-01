RULES = {
    "STP_DEMO": [
        {
            "rule": "BOD_MODERATE_SPIKE",
            "feature": "BOD_mg_L",
            "comparison": ">",
            "threshold": 30.0,
            "confidence_delta": 0.4,
            "explanation": "BOD exceeded 30 mg/L (Moderate Exposure)"
        },
        {
            "rule": "BOD_EXTREME_SPIKE",
            "feature": "BOD_mg_L",
            "comparison": ">",
            "threshold": 60.0,
            "confidence_delta": 0.4,
            "explanation": "BOD exceeded 60 mg/L (Extreme Violation)"
        },
        {
            "rule": "COD_CRITICAL_SPIKE",
            "feature": "COD_mg_L",
            "comparison": ">",
            "threshold": 250.0,
            "confidence_delta": 0.5,
            "explanation": "COD exceeded 250 mg/L limit"
        },
        {
            "rule": "pH_ACIDIC_DRIFT",
            "feature": "pH",
            "comparison": "<",
            "threshold": 6.5,
            "confidence_delta": 0.3,
            "explanation": "pH dropped below acidic limit (6.5)"
        },
        {
            "rule": "pH_ALKALINE_DRIFT",
            "feature": "pH",
            "comparison": ">",
            "threshold": 8.5,
            "confidence_delta": 0.3,
            "explanation": "pH rose above alkaline limit (8.5)"
        },
        {
            "rule": "TSS_OVERLOAD",
            "feature": "TSS_mg_L",
            "comparison": ">",
            "threshold": 100.0,
            "confidence_delta": 0.25,
            "explanation": "Total Suspended Solids (TSS) exceeded 100 mg/L"
        },
        {
            "rule": "TEMP_ABNORMAL",
            "feature": "temperature_C",
            "comparison": ">",
            "threshold": 40.0,
            "confidence_delta": 0.2,
            "explanation": "Temperature exceeded 40°C threshold"
        }
    ]
}
