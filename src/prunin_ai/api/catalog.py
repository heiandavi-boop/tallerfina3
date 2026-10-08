from __future__ import annotations

FIELD_CATALOG = [
    {"name":"planned_duration_weeks","label":"Duración planificada","group":"Proyecto","type":"number","unit":"semanas","min":1,"max":520,"step":1,"reference":52,"description":"Duración base del proyecto."},
    {"name":"planned_budget","label":"Presupuesto planificado","group":"Proyecto","type":"number","unit":"COP","min":1,"max":200000000000,"step":1000000,"reference":1000000000,"description":"Presupuesto de línea base. La moneda es contextual; el modelo usa magnitud y relaciones aprendidas."},
    {"name":"baseline_scope_units","label":"Alcance base","group":"Proyecto","type":"number","unit":"unidades","min":1,"max":100000,"step":1,"reference":1000,"description":"Unidades de alcance definidas en la línea base."},
    {"name":"sector","label":"Sector","group":"Proyecto","type":"select","options":["banking","healthcare","manufacturing","research","technology","telecom"],"reference":"technology","description":"Sector del proyecto."},
    {"name":"project_type","label":"Tipo de proyecto","group":"Proyecto","type":"select","options":["data_ai","infrastructure","process","research","software","transformation"],"reference":"software","description":"Naturaleza principal del proyecto."},
    {"name":"methodology","label":"Metodología","group":"Proyecto","type":"select","options":["hybrid","kanban","scrum","stage_gate","waterfall"],"reference":"hybrid","description":"Método de ejecución."},
    {"name":"complexity","label":"Complejidad","group":"Proyecto","type":"select","options":["low","medium","high","very_high"],"reference":"medium","description":"Nivel de complejidad estructurado."},
    {"name":"criticality","label":"Criticidad","group":"Proyecto","type":"select","options":["low","medium","high","mission_critical"],"reference":"medium","description":"Impacto de negocio si el proyecto falla."},

    {"name":"true_progress","label":"Avance real","group":"Ejecución","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.50,"format":"percent","description":"Avance evidenciado por los datos; no avance declarado."},
    {"name":"spi","label":"SPI","group":"Ejecución","type":"range","min":0.1,"max":1.5,"step":0.01,"reference":1.0,"description":"Índice de desempeño del cronograma."},
    {"name":"cpi","label":"CPI","group":"Ejecución","type":"range","min":0.1,"max":1.5,"step":0.01,"reference":1.0,"description":"Índice de desempeño del costo."},
    {"name":"team_utilization","label":"Utilización del equipo","group":"Equipo","type":"range","unit":"%","min":0,"max":1.5,"step":0.01,"reference":0.85,"format":"percent","description":"Carga asignada respecto de la capacidad."},
    {"name":"team_capacity_ratio","label":"Capacidad / demanda","group":"Equipo","type":"range","min":0,"max":2,"step":0.01,"reference":1.0,"description":"Capacidad disponible dividida por demanda."},
    {"name":"average_productivity","label":"Productividad relativa","group":"Equipo","type":"range","min":0,"max":1.5,"step":0.01,"reference":1.0,"description":"Productividad comparada con la referencia del proyecto."},
    {"name":"team_stability","label":"Estabilidad del equipo","group":"Equipo","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.90,"format":"percent","description":"Señal operativa opcional para Team Health; no se usa como feature ML supervisada."},
    {"name":"collaboration_level","label":"Colaboración","group":"Equipo","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.85,"format":"percent","description":"Señal operativa opcional para Team Health; no se usa como feature ML supervisada."},

    {"name":"defect_rate","label":"Tasa de defectos","group":"Calidad y alcance","type":"range","unit":"%","min":0,"max":0.5,"step":0.005,"reference":0.04,"format":"percent","description":"Proporción de defectos respecto del trabajo observado."},
    {"name":"rework_ratio","label":"Retrabajo","group":"Calidad y alcance","type":"range","unit":"%","min":0,"max":0.5,"step":0.005,"reference":0.05,"format":"percent","description":"Proporción de esfuerzo consumido en correcciones/retrabajo."},
    {"name":"scope_growth_ratio","label":"Crecimiento del alcance","group":"Calidad y alcance","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.02,"format":"percent","description":"Crecimiento acumulado del alcance frente a la línea base."},

    {"name":"dependency_delay_days","label":"Retraso por dependencias","group":"Riesgo y gobierno","type":"range","unit":"días","min":0,"max":365,"step":1,"reference":1,"description":"Días de afectación atribuible a dependencias conocidas."},
    {"name":"normalized_risk_exposure","label":"Exposición al riesgo","group":"Riesgo y gobierno","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.12,"format":"percent","description":"Exposición al riesgo normalizada entre 0 y 1."},
    {"name":"governance_health_score","label":"Salud de gobierno","group":"Riesgo y gobierno","type":"range","unit":"%","min":0,"max":1,"step":0.01,"reference":0.75,"format":"percent","description":"Indicador observable de gobierno del proyecto."},
]

FIELD_MAP = {item["name"]: item for item in FIELD_CATALOG}

PRESETS = {
    "healthy": {
        "planned_duration_weeks": 40, "planned_budget": 1200000000, "baseline_scope_units": 900,
        "sector": "technology", "project_type": "software", "methodology": "scrum", "complexity": "medium", "criticality": "medium",
        "true_progress": 0.58, "spi": 1.04, "cpi": 1.02, "team_utilization": 0.80, "team_capacity_ratio": 1.08,
        "average_productivity": 1.02, "defect_rate": 0.025, "rework_ratio": 0.035, "scope_growth_ratio": 0.015,
        "dependency_delay_days": 0.5, "normalized_risk_exposure": 0.07, "governance_health_score": 0.88,
        "team_stability": 0.94, "collaboration_level": 0.92,
    },
    "at_risk": {
        "planned_duration_weeks": 52, "planned_budget": 2500000000, "baseline_scope_units": 1500,
        "sector": "banking", "project_type": "transformation", "methodology": "hybrid", "complexity": "high", "criticality": "high",
        "true_progress": 0.47, "spi": 0.82, "cpi": 0.91, "team_utilization": 0.96, "team_capacity_ratio": 0.82,
        "average_productivity": 0.74, "defect_rate": 0.08, "rework_ratio": 0.13, "scope_growth_ratio": 0.09,
        "dependency_delay_days": 8, "normalized_risk_exposure": 0.31, "governance_health_score": 0.56,
        "team_stability": 0.76, "collaboration_level": 0.68,
    },
    "critical": {
        "planned_duration_weeks": 78, "planned_budget": 7000000000, "baseline_scope_units": 3200,
        "sector": "telecom", "project_type": "infrastructure", "methodology": "waterfall", "complexity": "very_high", "criticality": "mission_critical",
        "true_progress": 0.39, "spi": 0.61, "cpi": 0.72, "team_utilization": 1.18, "team_capacity_ratio": 0.58,
        "average_productivity": 0.52, "defect_rate": 0.16, "rework_ratio": 0.25, "scope_growth_ratio": 0.18,
        "dependency_delay_days": 24, "normalized_risk_exposure": 0.62, "governance_health_score": 0.31,
        "team_stability": 0.55, "collaboration_level": 0.48,
    },
}
