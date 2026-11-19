# PRUNIN AI Core — guía de defensa verificable para Nivel 4

Esta guía sirve para preparar la **sustentación de Proyecto Aplicado III**. No certifica fluidez, lenguaje no verbal ni respuestas improvisadas; los criterios RA2-F1 a RA2-F7 solo pueden calificarse durante una exposición observada.

## Mensaje central en 40 segundos

PRUNIN combina tres modelos predictivos LightGBM congelados con una capa opcional de recomendaciones generativas locales, validadas frente a evidencia estructurada. En datos sintéticos de Mendeley, la meta operacional se alcanzó para **Risk Alert (At Risk + Critical)**: detecta 359/473 proyectos que finalmente estarán en riesgo a un 60 % de avance, equivalente a 75,90 %, con 96 % de cobertura del TEST en ese corte. No implica 75 % de detección de la clase Critical exacta: ese recall es 56,82 %. El valor demostrado es un prototipo reproducible; la utilidad empresarial, el impacto humano y la validez prospectiva aún requieren pruebas.

Fuentes: [informe](INFORME_FINAL.md), [validación de promesa](../reports/promise_validation/promise_validation_report.md).

## Recorrido de demostración verificable

1. Mostrar [pregunta y objetivo](PRESENTACION_FINAL.md), sin presentar un dataset simulado como historial de una empresa.
2. Mostrar **split disjunto por proyecto** (2.800 TRAIN, 600 VALIDATION, 600 TEST) y modelos congelados; no confundir snapshots con proyectos.
3. Presentar KPI de detección temprana y distinguir Risk Alert de Critical exacto.
4. Analizar un proyecto de ejemplo, mostrar drivers y la fuente de cada recomendación. Demostrar que Ollama deshabilitado mantiene las predicciones y activa respaldo determinístico.
5. Mostrar la [comparación real Qwen3/GPT-OSS](../reports/genai/qwen_vs_gptoss_2026/comparison_report.md) y explicar por qué el puntaje ponderado no define un ganador concluyente.
6. Mostrar el [CI de dos instancias Docker](https://github.com/heiandavi-boop/tallerfina3/actions/runs/44454392965): dos backends 20/20 solicitudes y continuidad al detener uno; **no** afirmar recuperación Kubernetes productiva.
7. Cerrar con limitaciones: productividad humana aún sin medir, datos sintéticos y ausencia de clúster o retraining continuo real.

## Preguntas difíciles con respuestas defendibles

**¿Por qué dicen que cumple 75 % si la clase Critical tiene recall 56,82 %?**  
Porque el indicador original se operacionalizó como detección temprana agregada de proyectos **At Risk o Critical**, no reconocimiento exacto de la clase Critical. Se reportan ambas cifras con denominadores distintos y se reconoce el límite de sensibilidad a Critical.

**¿Por qué no utilizan datos de proyectos reales?**  
No existía autorización y una fuente adecuada de outcomes para validación empresarial. La cohorte Mendeley es sintética y permite reproducibilidad, pero no demuestra generalización; el siguiente estudio exige datos autorizados y una evaluación temporal independiente.

**¿Cuál modelo generativo ganó: Qwen o GPT-OSS?**  
Ninguno con evidencia estadística concluyente. Qwen tuvo 30/30 aceptaciones, GPT-OSS 29/30; GPT-OSS tuvo menor latencia mediana y Qwen menor uso de memoria. La matriz ponderada favorece levemente a GPT-OSS (0,987 frente a 0,981), pero la diferencia 0,006 está bajo el umbral defendible 0,03 y la selección cambia con ciertos pesos. Se mantiene Qwen por continuidad operativa y menor memoria, no por demostrar superioridad.

**¿La generación es una predicción adicional?**  
No. Health, Delay y Cost provienen de LightGBM. Ollama convierte señales y drivers estructurados en texto sujeto a un contrato JSON y validadores de evidencia. Si la salida falla, el modelo predictivo conserva su respuesta y se usa fallback determinístico.

**¿Las recomendaciones son correctas porque pasan grounding?**  
No necesariamente. Grounding es un control proxy de estructura, procedencia y cifras permitidas; no verifica utilidad semántica, causalidad ni efectividad empresarial. Falta juicio humano ciego y seguimiento en condiciones reales.

**¿Qué demostraron en Docker?**  
Construcción y arranque en CI, balanceo nginx de dos contenedores y continuidad al detener uno. La instancia se restauró manualmente; no se probó recuperación automática, HPA ni rollback real en un clúster Kubernetes.

**¿Existe monitorización automática continua y reentrenamiento?**  
Existe un workflow para comprobaciones de drift de **datos sintéticos de demostración** y un gate de selección de candidatos. No existe ingestión continua de nuevos proyectos etiquetados, ground truth empresarial ni promoción automática de nuevos modelos. El artefacto académico congelado no se cambia.

**¿Cuánto aumentó la productividad de las personas?**  
No hay cifra defendible: se registran cero participantes reales. Sí existen mediciones técnicas de latencia/throughput, que no se presentan como ahorro de tiempo humano. El protocolo contrabalanceado y su plantilla están listos para aplicarse a participantes con consentimiento.

**¿Por qué el costo obtiene R² elevado en datos simulados?**  
Porque las variables CPI/EVM del simulador están relacionadas estructuralmente con el outcome, lo que puede facilitar la predicción dentro del mismo generador. No se presume que ese desempeño se transfiera a empresas reales. Además Delay solo mejora marginalmente a su baseline.

## Lista de preparación observacional

- [ ] Ejecutar el mismo commit y los mismos artefactos usados en la presentación.
- [ ] Mostrar al menos un caso de fallback sin motor generativo.
- [ ] Visualizar una figura de detección temporal y una de comparación generativa.
- [ ] Ensayar las preguntas sin leer textualmente las respuestas.
- [ ] Cronometrar la exposición conforme al límite real del profesor.
- [ ] Verificar red, proyector, fuente de alimentación y demo offline.
- [ ] Pedir retroalimentación humana sobre ritmo, claridad, postura y argumentación.

**Estado:** guía preparada; **RA2 sigue sin calificación observada**.
