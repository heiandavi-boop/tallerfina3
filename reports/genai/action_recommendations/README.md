# Evaluación de acciones priorizadas

Corridas nuevas del schema accionable. No sobrescriben `reports/genai/qwen3-8b-evaluation.json`, que conserva el benchmark Qwen oficial congelado.

## Corrida V3

Reporte: `qwen3-8b-actions-v3.json`; casos crudos: `qwen3-8b-actions-v3.csv`. Qwen3 8B, 20 snapshots TEST recientes con drivers que incrementan riesgo, temperatura 0.1, timeout 30 s, respuesta JSON Schema estricta y validador local.

| Métrica | Resultado |
|---|---:|
| Casos | 20 |
| Generation success | 1.000 |
| Schema valid | 1.000 |
| Evidence features valid | 1.000 |
| Grounded proxy | 1.000 |
| Action structure valid | 1.000 |
| Follow-up present | 1.000 |
| Actionability | 1.000 |
| Unsupported numeric claim | 0.000 |
| Timeout | 0.000 |
| Invalid JSON | 0.000 |
| Latencia mediana | 7054.585 ms |
| Latencia p95 | 17741.41 ms |

Ejemplo observado, proyecto sintético `mendeley::PROJ_0760`, evidencia permitida `cpi`:

```json
{
  "priority": "alta",
  "title": "Revisar la proyección de costos",
  "evidence_feature": "cpi",
  "reason": "cpi aparece entre las señales que incrementan el riesgo en esta inferencia.",
  "action": "Analizar el consumo presupuestal y actualizar la estimación al cierre antes de asumir nuevos compromisos de gasto.",
  "follow_up": "Comparar CPI y proyección de costo en el siguiente seguimiento."
}
```

Ejemplo real del fallback determinístico en el preset `critical` con Ollama desactivado: prioridad alta para revisar la proyección de costos, evidencia `cpi`, acción de analizar consumo/estimación al cierre y seguimiento de CPI/proyección. El resultado depende de los drivers locales disponibles.

Las corridas V1/V2 también se preservan como iteraciones: V1 rechazó listas vacías ante drivers; V2 aceptó 16/20 y rechazó cuatro schemas con la clave `follow,up`. V3 usa un JSON Schema estricto. Estos son proxies de estructura/grounding y latencia, no evaluación de utilidad humana, calidad profesional o causalidad.