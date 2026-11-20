# Protocolo de demostración — PRUNIN AI Core

## Alcance
Comprobar desde la interfaz que PRUNIN recibe datos de un proyecto, calcula sus predicciones académicas y ofrece acciones verificables. Se trata de una demostración técnica reproducible, no de una prueba empresarial ni de la ejecución de una evaluación humana.

## Requisitos
- Python y Node conforme a `requirements.txt` y `frontend/package-lock.json`.
- Artefactos de `0.9.0-academic` en el directorio local configurado; los archivos pesados no se publican en este repositorio.
- Para la generación opcional: servicio Ollama local y modelo configurado disponibles.
- No cargar datos empresariales sensibles ni almacenar credenciales en Git.

## Secuencia verificable
1. Instalar dependencias y ejecutar `./scripts/preflight_demo.sh` y `./scripts/run_playground.sh`.
2. Abrir `http://localhost:8000` y confirmar `/api/ready`.
3. Seleccionar un proyecto de ejemplo o introducir variables del modelo (`planned_duration_weeks`, `planned_budget`, `true_progress`, `spi`, `cpi`, `project_type`, `methodology`).
4. Elegir **Ollama** o **solo predicción**. Con Ollama habilitado, elegir Qwen3 8B o GPT-OSS 20B entre los modelos instalados. La elección afecta las recomendaciones, no Health/Delay/Cost. Para verificar ambos mediante API, ejecutar `python scripts/verify_two_models_live.py --csv /ruta/al/proyecto.csv` con la API y Ollama activos.
5. Ejecutar el análisis y verificar estado Health, probabilidades, retraso, desviación de costo, drivers y calidad de entrada.
6. Revisar recomendaciones: `engine`, prioridad, fuente de evidencia, acción, explicación y seguimiento. Si hay fallo de LLM, verificar el motor `grounded_fallback`.
7. Probar un escenario What-if con variables aprendidas; comprobar que se mantienen independientes las predicciones comparadas.
8. Probar análisis CSV y apertura de una fila; comprobar que el lote no llama automáticamente al LLM.
9. Consultar las evidencias técnicas exportadas y verificar `prediction_id`, versión del artefacto y trazabilidad.
10. Mostrar la ejecución `quality` del commit exacto publicado.

## Criterios de aceptación
- La respuesta predictiva sigue disponible cuando falla el proveedor de texto.
- No se afirma que Team Health ni Final Status sean modelos supervisados.
- La alerta Risk Alert agrupa At Risk y Critical; no equivale a recall de Critical exacto.
- Las recomendaciones basadas en señales operativas no se confunden con variables entrenadas.
- Las salidas se contrastan con su contexto; la validación automática no demuestra causalidad ni utilidad empresarial.

## Alcance de las pruebas generativas
La evaluación de alternativas locales debe registrar modelo, digest, fecha, casos, aceptación, latencia y restricciones de hardware; no se atribuyen resultados a candidatos no ejecutados.

## Referencias de evidencia
- [Informe final](INFORME_FINAL.md)
- [Arquitectura](architecture.md)
- [Selección de proveedores](ai_providers.md)
- [Evaluación GenAI](genai_evaluation.md)
- [Resultados académicos](../reports/0.9.0-academic/)
- [Validación de la promesa](../reports/promise_validation/)
