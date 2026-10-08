# PRUNIN AI Core · Academic + Live Playground

Repositorio autocontenido para entrenar, validar y demostrar públicamente el AI Core de PRUNIN.

La demo **no contiene resultados hardcodeados**: cada análisis llama al backend FastAPI, ejecuta los artefactos `.joblib` cargados y devuelve un `prediction_id`, versión del modelo, tiempos, probabilidades, drivers y recomendaciones.

## Entrenamiento académico reproducible

```bash
source .venv/bin/activate
./scripts/train_all.sh
```

El pipeline ejecuta DOWNLOAD → VALIDATION → PREPARATION → AUDIT → READINESS → SPLIT/LEAKAGE → TRAINING → EVALUATION → TEMPORAL EVALUATION → REPORT/FIGURES → TESTS → PLAYGROUND PREFLIGHT. Mendeley v2 es la única fuente de `0.9.0-academic`; las demás fuentes son opcionales y no se mezclan. Los informes ligeros se exportan a `reports/0.9.0-academic/`; datasets y modelos pesados permanecen locales.

## Inicio rápido en Mac / VS Code

### Opción más simple

1. Descomprime el ZIP.
2. Abre la carpeta raíz en VS Code.
3. Abre Terminal → New Terminal.
4. Ejecuta:

```bash
chmod +x scripts/*.sh INICIAR_DEMO.command
./scripts/setup_playground.sh
./scripts/preflight_demo.sh
./scripts/run_playground.sh
```

5. Abre `http://localhost:8000`.

También puedes hacer doble clic en `INICIAR_DEMO.command` en macOS. Si el entorno `.venv` todavía no existe, lo prepara primero.

## Qué valida el preflight

```bash
./scripts/preflight_demo.sh
```

Comprueba:

- frontend precompilado;
- directorio de artefactos;
- modelos Health / Final Status / Delay / Cost;
- endpoint de esquema;
- inferencia real;
- salida de Health, Delay, Cost y Team Health.

El resultado esperado es:

```text
RESULTADO: LISTO PARA DEMO
```

## Selección automática del modelo

La aplicación elige los artefactos en este orden:

1. `PRUNIN_ARTIFACT_DIR`, si se configura explícitamente.
2. `artifacts/0.9.0-academic`, si ya entrenaste la versión académica.
3. `artifacts/demo-0.1.0`, como fallback funcional.

El fallback está entrenado con datos sintéticos de smoke test y la interfaz lo marca de forma visible como **MODELO DEMO SINTÉTICO**. No se presenta como resultado académico definitivo.

## Variables disponibles en la demo

### Proyecto

- `planned_duration_weeks`
- `planned_budget`
- `baseline_scope_units`
- `sector`
- `project_type`
- `methodology`
- `complexity`
- `criticality`

### Ejecución

- `true_progress`
- `spi`
- `cpi`

### Equipo

- `team_utilization`
- `team_capacity_ratio`
- `average_productivity`
- `team_stability` *(solo Team Health)*
- `collaboration_level` *(solo Team Health)*

### Calidad y alcance

- `defect_rate`
- `rework_ratio`
- `scope_growth_ratio`

### Riesgo y gobierno

- `dependency_delay_days`
- `normalized_risk_exposure`
- `governance_health_score`

### Variables eliminadas de V8.6.3

No se muestran ni se inventan:

- `reported_progress`
- `critical_path_delay_days`
- `team_morale`

`team_morale` fue sustituida conceptualmente por `team_health_index`, calculado con señales observables. `team_stability` y `collaboration_level` complementan ese índice, pero no se introducen en los modelos supervisados mientras no exista histórico emparejado con outcomes.

## Funciones del Playground

- tres escenarios precargados: saludable, en riesgo y crítico;
- edición manual de todas las variables;
- validaciones de rango en frontend y backend;
- Health con probabilidades;
- Final Status con probabilidades;
- retraso estimado;
- sobrecosto estimado;
- Team Health Index;
- riesgo fusionado;
- sensibilidad local de variables;
- recomendaciones fundamentadas;
- modo `What-if`;
- carga CSV de hasta 100 filas;
- plantilla CSV descargable;
- panel técnico con JSON completo;
- descarga del resultado JSON;
- QR generado con la URL actual o `PRUNIN_PUBLIC_URL`;
- identificación visible de versión y tipo de modelo;
- protección contra inferencias con menos del 60 % de cobertura de features entrenadas.

## Valores faltantes

La interfaz manual envía todas las variables del preset. Para CSV/API se permite información parcial, pero de forma explícita:

- se muestra `missing_trained_features`;
- se calcula `coverage`;
- el pipeline usa la misma imputación de entrenamiento (`median` numérica / `mode` categórica);
- si la cobertura baja del 60 %, la inferencia se bloquea en lugar de emitir una predicción débil.

Puedes cambiar el umbral:

```bash
export PRUNIN_MIN_FEATURE_COVERAGE=0.70
```

## Probar desde celulares en la misma red

`./scripts/run_playground.sh` escucha en `0.0.0.0` e intenta mostrar una URL LAN, por ejemplo:

```text
Red LAN: http://192.168.1.25:8000
```

Abre esa URL en el computador que proyectará la demo. El QR del panel técnico usará la URL actual y los asistentes conectados a la misma red podrán escanearla.

Para una URL pública de Internet, despliega `Dockerfile.playground` y define:

```bash
export PRUNIN_PUBLIC_URL=https://tu-dominio.com
```

## IA generativa sin romper la demo

La demo funciona aunque no haya LLM disponible. Por defecto usa un motor de recomendaciones fundamentado en drivers del modelo.

Si quieres activar Ollama local:

```bash
export PRUNIN_ENABLE_OLLAMA=1
export PRUNIN_OLLAMA_MODEL=qwen3:8b
./scripts/run_playground.sh
```

Si Ollama falla o excede el timeout, se utiliza automáticamente el fallback fundamentado.

## Entrenamiento académico

El uso manual queda como flujo avanzado; para un entrenamiento reproducible usa `./scripts/train_all.sh`.

```bash
source .venv/bin/activate
python scripts/download_datasets.py
python scripts/prepare_datasets.py
python scripts/audit_dataset.py --input data/processed/mendeley_core.csv
python scripts/data_readiness.py
python scripts/verify_split.py
python scripts/train_core.py --input data/processed/mendeley_core.csv --version 0.9.0-academic
python scripts/evaluate_temporal.py
python scripts/export_report.py
python scripts/generate_evaluation_plots.py
```

Mendeley v2 no contiene una etiqueta independiente de Final Status. El API conserva el campo como estado de negocio derivado de Health, y el Playground lo identifica como `Derived business status`.

Para abrir el Playground tras el entrenamiento:

```bash
./scripts/run_playground.sh
```

## Pruebas

```bash
source .venv/bin/activate
pytest -q
```

Los resultados de evaluación de cada ejecución se exportan a `reports/0.9.0-academic/`; no se fija aquí un número de tests.

## Docker

```bash
docker build -f Dockerfile.playground -t prunin-ai-playground .
docker run --rm -p 8000:8000 prunin-ai-playground
```

## Archivos útiles

- `docs/playground.md`: arquitectura y comportamiento de la demo.
- `DEMO_PRESENTACION.md`: secuencia recomendada para la sustentación.
- `data/processed/playground_examples.csv`: tres escenarios listos para probar.
- `artifacts/playground_input_template.csv`: plantilla CSV de una fila.
- `.env.playground.example`: configuración opcional.
