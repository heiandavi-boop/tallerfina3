# Validación de la promesa original — PRUNIN AI Core

## Pregunta evaluada

La promesa original se operacionaliza como: **detectar tempranamente al menos el 75 % de los proyectos críticos o en alto riesgo**.

Para medirla sin cambiar el modelo, se deriva una vista binaria de las mismas predicciones Health:

- **No Risk Alert:** Healthy.
- **Risk Alert:** At Risk o Critical.

Esta agregación no reemplaza la clasificación multiclase y no modifica labels, features, pesos, thresholds ni TEST.

## Resultado final TEST

Sobre 600 proyectos TEST, 473 pertenecen realmente a At Risk o Critical. PRUNIN detecta 390 de ellos como At Risk/Critical.

| Métrica | Resultado |
|---|---:|
| Risk Alert Recall | 82.45 % |
| Risk Alert Precision | 92.20 % |
| Risk Alert F1 | 87.05 % |
| Specificity | 74.02 % |
| False Negative Rate | 17.55 % |
| Exact Critical Recall | 56.82 % |

## Detección temporal

Para evitar que la cobertura desigual infle el resultado temprano se reportan dos métricas distintas:

1. **Risk Alert Recall entre elegibles:** desempeño dentro de proyectos con snapshot disponible antes del cutoff.
2. **Detección de cohorte completa:** TP/473, contando como no detectados los proyectos finales en riesgo que todavía no tienen snapshot elegible.

| Avance | Cobertura TEST | Recall entre elegibles | Detección de toda la cohorte riesgosa |
|---:|---:|---:|---:|
| 20 % | 39.33 % | 71.05 % | 28.54 % |
| 40 % | 77.17 % | 79.95 % | 64.06 % |
| 60 % | 96.00 % | 78.73 % | **75.90 %** |
| 80 % | 99.83 % | 79.92 % | 79.92 % |
| Final | 100 % | 82.45 % | 82.45 % |

La primera medición previa al cierre que supera la meta sobre **toda la cohorte final de riesgo** es el **60 % de avance**: 359/473 = 75.90 %, con 576/600 = 96 % de cobertura TEST.

## Interpretación defendible

**Dentro del entorno experimental sintético**, PRUNIN alcanza la meta original. Esto no demuestra generalización empresarial ni alta precisión de todos los subcomponentes. Delay sigue mostrando una mejora marginal frente a baseline; Cost conserva el caveat estructural EVM/CPI; la severidad Critical exacta mantiene recall 56.82 %.

## Integridad metodológica

- TEST continúa congelado.
- No hubo reentrenamiento.
- No se cambiaron targets, features, pesos ni thresholds.
- Las matrices fuente ya estaban versionadas.
- La evaluación temporal usa como máximo un snapshot por proyecto y no selecciona observaciones posteriores al cutoff.

**Veredicto:** PROMESA PRINCIPAL DEMOSTRADA EN EL ENTORNO EXPERIMENTAL.
