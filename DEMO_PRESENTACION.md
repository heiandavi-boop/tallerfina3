# Guion técnico para la demo de PRUNIN AI Core

## Antes de entrar al salón

Ejecutar:

```bash
./scripts/preflight_demo.sh
```

No presentar hasta obtener `RESULTADO: LISTO PARA DEMO`.

Luego:

```bash
./scripts/run_playground.sh
```

Si el público usará celulares, abrir la URL LAN que muestra la terminal o la URL pública desplegada.

## Secuencia recomendada

### 1. Mostrar que la ejecución es real

Abrir **Detalles de inferencia** y señalar:

- versión del modelo;
- modo (`academic` o `synthetic_demo`);
- `LIVE`;
- tiempo de inferencia;
- `prediction_id`;
- source/type del dataset y lista dinámica de trained features;
- fusion type `operational_heuristic`, `calibrated=false`.

### 2. Ejecutar “En riesgo”

Seleccionar el preset **En riesgo** → **Analizar proyecto**.

Mostrar:

- Health ML (predicción supervisada);
- Riesgo combinado (ML + Team Health heurístico), separado de Health ML;
- probabilidades;
- Delay;
- Cost;
- estado de negocio derivado (Mendeley v2 no tiene target Final Status independiente);
- Team Health con score, level, coverage y components;
- drivers.

### 3. What-if

En el mismo proyecto mejorar gradualmente:

- SPI;
- CPI;
- capacidad del equipo;
- retrabajo;
- defectos;
- exposición al riesgo.

Ejecutar **Simular escenario** y mostrar la comparación.

No prometer que un cambio aislado “causará” el resultado: la demo muestra sensibilidad/predicción del modelo, no causalidad.

### 4. Prueba del público

Mostrar el QR. Un asistente cambia variables o sube un CSV y obtiene un `prediction_id` distinto.

### 5. Trazabilidad

Abrir JSON o descargar resultado. Explicar:

- Inputs = datos observados;
- features ML = campos del manifest del artifact cargado;
- Team Health = señal operativa heurística; no es psicológica ni fue entrenada por LightGBM;
- Health/Delay/Cost = predicciones ML; Final Status = transformación derivada de Health;
- Drivers = sensibilidad local, no causalidad;
- Recomendaciones = capa explicativa fundamentada / IA generativa opcional.

## Si algo falla

- Si Internet falla: la demo local sigue funcionando.
- Si Ollama falla: se activa el fallback fundamentado.
- Si no existe el modelo académico: se usa el demo sintético y queda rotulado como tal.
- Si un CSV tiene pocas variables: la fila se bloquea si no alcanza 60 % de cobertura.
- Si Node no está instalado: no importa; `frontend/dist` ya viene listo.


## Secuencia de sustentación alineada a la rúbrica

### 0. Abrir con el problema, no con la tecnología

Explicar en menos de un minuto:

- el problema es detectar señales de riesgo antes del cierre del proyecto;
- PRUNIN combina modelos predictivos y una capa generativa de explicación;
- la versión académica se valida sobre Mendeley v2, que es sintético externo;
- por tanto, los resultados no equivalen a desempeño productivo.

### 1. Evidencia predictiva

Mostrar únicamente métricas versionadas en `reports/0.9.0-academic/`.

Priorizar:

- Health project-level Macro F1 y balanced accuracy;
- Delay MAE y su debilidad frente al baseline;
- Cost MAE/R² con advertencia sobre la relación estructural EVM;
- evaluación 20/40/60/80 % y cobertura de proyectos.

### 2. IA generativa

Explicar:

- Qwen3 8B fue elegido por ejecución local, español, tamaño y compatibilidad con Ollama;
- recibe solo evidencia estructurada;
- una respuesta que no pasa grounding se descarta;
- el fallback no es IA generativa y se etiqueta como tal;
- las métricas GenAI solo se presentan si `reports/genai/qwen3-8b-evaluation.json` tiene `status=complete`.

### 3. Eficiencia

No decir que la automatización ahorra X % de tiempo salvo que exista un baseline humano medido.

Sí se puede demostrar:

- tiempo de inferencia;
- procesamiento CSV;
- automatización end-to-end;
- capacidad de generar explicación sin intervención manual cuando el LLM está disponible.

### 4. Ética

Mencionar explícitamente:

- dataset sintético;
- humano en el circuito;
- grounding;
- privacidad local;
- no causalidad;
- Team Health no psicológico;
- drift y necesidad de validación real.

### 5. MLOps

Mostrar:

- GitHub Actions verde;
- SHA/manifests;
- `/api/ready`;
- `/api/monitoring`;
- `/metrics`;
- Docker;
- manifiesto Kubernetes con réplicas/HPA.

Aclarar que Kubernetes es diseño desplegable y no un clúster productivo ya operando.

## Preguntas difíciles y respuesta base

**¿Por qué Cost tiene R² tan alto?**  
Porque CPI y el outcome de costo tienen relación estructural dentro del generador EVM sintético. Por eso no lo presentamos como evidencia productiva y damos más peso a la evaluación temporal.

**¿Por qué Delay es débil?**  
El modelo apenas supera el baseline de mediana en TEST. Se probó tuning y otros candidatos usando VALIDATION; ninguno justificó reemplazar de forma segura el incumbent.

**¿Por qué usar un LLM si hay fallback?**  
El fallback garantiza disponibilidad; el LLM agrega capacidad de redacción y contextualización. Se mantienen separados para no confundir determinismo con generación.

**¿Por qué Qwen3 8B?**  
Por privacidad local, soporte de español/multilingüe, tamaño y compatibilidad con Ollama. La selección de calidad se valida con un benchmark específico y no solo con reputación del modelo.

**¿Esto está listo para producción?**  
No. Está listo como prototipo académico reproducible. Falta validación prospectiva con proyectos reales, monitoreo central y calibración/retraining con outcomes PRUNIN.
