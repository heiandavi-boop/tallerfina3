# Matriz PAIII 2026

La rúbrica utilizada es el texto aportado para esta auditoría; no se asigna nota oficial. La matriz vigente con los 27 criterios, evidencias automatizadas/humanas, estados, gaps y claims seguros/no seguros está en [rubric_final.json](../reports/rubric_final/rubric_final.json) y [rubric_final.md](../reports/rubric_final/rubric_final.md). El SHA final y la corrida CI se registran en [FINAL_READINESS.md](FINAL_READINESS.md), no en una instantánea histórica.

## Estado auditado

| Estado | Criterios | Interpretación |
|---|---:|---|
| DEMONSTRATED | 0 | No se declara Nivel 4 sin límites relevantes pendientes. |
| DEMONSTRATED_WITH_LIMITATION | 20 | Evidencia verificable con limitaciones académicas/operacionales explícitas. |
| PREPARED_HUMAN | 7 | RA2 preparado; depende de actuación real y no se marca demostrado. |
| DESIGN_ONLY | 0 | Los criterios operativos tienen implementación local o verificación estática, pero conservan sus límites en `DEMONSTRATED_WITH_LIMITATION`. |

La auditoría registra el benchmark GenAI comparativo como parcial: Qwen disponible, Gemma 3 4B y Ministral 3 8B `not_available`. La concurrencia se midió localmente y mostró degradación de éxito/timeout; no prueba carga productiva. Kubernetes se validó estáticamente, sin clúster operado. El detector OOD/drift es académico/offline y no modifica predicciones ni activa retraining.

Los siete ítems RA2 son F1 estructura, F2 intención, F3 lenguaje profesional, F4 voz, F5 recursos, F6 lenguaje no verbal y F7 defensa. Estado: **“Preparado para Nivel 4; desempeño depende de la sustentación real.”** Seguir [ENSAYO_SUSTENTACION.md](ENSAYO_SUSTENTACION.md) y registrar tiempos/observaciones, sin declarar ejecución anticipadamente.