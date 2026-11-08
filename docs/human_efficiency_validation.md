# Protocolo de validación de eficiencia humana

## Propósito y límites

Este protocolo futuro mide tiempo y calidad de una decisión asistida por PRUNIN frente a una revisión manual. No hay resultados humanos registrados en el repositorio. La eficiencia operacional del API (latencia, throughput y batch) es una medición distinta y no demuestra ahorro laboral.

## Participantes

- Perfil sugerido: directores de proyecto, analistas PMO o profesionales con experiencia en seguimiento de cronograma/costo.
- Mínimo sugerido: 12 participantes para una primera evaluación descriptiva; no garantiza potencia estadística ni representatividad.
- Registrar experiencia por rangos, sin nombres ni datos de empleador. La participación no debe afectar empleo, evaluación académica o relación jerárquica.

## Tarea y escenario

Usar al menos seis casos sintéticos anonimizados, con señales comparables de avance, SPI, CPI, plazo y presupuesto. No usar datos empresariales identificables en esta prueba. Cada participante revisa casos en dos condiciones: (A) lectura manual de la misma ficha de datos y (B) ficha más salida PRUNIN. El orden de condición y los casos se contrabalancean entre participantes para reducir aprendizaje y fatiga.

En cada caso, el participante registra: si requiere atención, severidad, interpretación de posible retraso y costo, dos señales consideradas, una acción recomendada y nivel de confianza. Debe poder indicar “no sé” y disentir del sistema.

## Procedimiento y medidas

1. Explicar el propósito, riesgos, voluntariedad y consentimiento; no entrenar al participante con las respuestas de los casos.
2. Presentar una práctica que no se puntúa.
3. Cronometrar desde que aparece la ficha hasta que se guarda una decisión completa, por caso y condición. Incluir el tiempo de espera del LLM dentro de la condición PRUNIN.
4. Evaluar calidad con una rúbrica predefinida y ciega a la condición cuando sea posible: alerta correcta, severidad, lectura de retraso/costo, uso de evidencia y acción revisable. Definir antes de recolectar si cada rubro vale 0/1/2.
5. Después de cada caso PRUNIN, preguntar utilidad, claridad y confianza con escala Likert de 1 (nada) a 5 (mucho), y si la persona habría aceptado la recomendación sin revisar evidencia.
6. Reportar diferencias pareadas, mediana, rango intercuartílico, distribución de calidad, fallos y casos donde el sistema empeora la decisión. No inferir causalidad con una muestra pequeña.

SUS puede añadirse opcionalmente como instrumento separado siguiendo su fuente/instrucciones oficiales; no sustituye calidad de decisión ni debe alterarse su puntuación.

## Sesgos, privacidad y consentimiento

Riesgos: efecto de aprendizaje entre condiciones, experiencia desigual, selección de voluntarios, familiaridad con IA, sesgo de autoridad/automation bias, variación en dificultad de casos, efecto del orden y demora del modelo. Contrabalancear, conservar instrucciones idénticas y reportar abandonos y fallos. Obtener consentimiento informado antes de registrar datos; recolectar solo respuestas y tiempos pseudonimizados, limitar acceso, fijar plazo de retención y permitir retiro. No usar resultados para evaluar personas ni empleadores.

## Plantilla y análisis

`reports/human_validation/TEMPLATE_results.csv` está intencionalmente vacío salvo encabezados. `reports/human_validation/README.md` describe su uso. No llenar la plantilla con datos simulados ni confundirla con `reports/efficiency/`, que contiene medición automatizada local.

Reportar número de participantes/casos, exclusiones, consentimiento, equipo, versión PRUNIN, estado de Ollama, orden asignado, tiempos por condición, rúbrica y discrepancias. Publicar agregados anonimizados y dejar claramente descriptivos los resultados exploratorios.

## Plan previo a la recolección

**Estado: NO MEDIDA.** Antes de reclutar, el autor debe completar responsable del estudio, contacto, aprobación institucional requerida, periodo de recolección y plazo de retención. La sugerencia de 12 participantes no sustituye un cálculo de potencia ni una aprobación ética. No reclutar subordinados bajo presión ni vincular resultados a notas o desempeño laboral.

Registrar como variables independientes condición manual/asistida, orden, caso y rango de experiencia; como dependientes, tiempo total en segundos, calidad 0–10, confianza/utilidad/claridad y aceptación sin verificación. Registrar versión del modelo y contrato, disponibilidad de Ollama, fallback y errores. El tiempo incluye esperas, reintentos y lectura; separar latencia técnica solo como medida secundaria.

Preparar dos grupos de tres casos de dificultad comparable, revisados previamente por dos evaluadores ajenos al desarrollo. Congelar fichas, respuesta de referencia y rúbrica antes de observar resultados; no usar la predicción PRUNIN como verdad de referencia. Asignar aleatoriamente secuencias AB/BA y contrabalancear grupos: cada persona ve un caso una sola vez para limitar memoria. Ofrecer práctica distinta, mismas instrucciones y posibilidad de disentir. Registrar la asignación y exclusiones antes del análisis.

| Dimensión | 0 puntos | 1 punto | 2 puntos |
|---|---|---|---|
| Alerta | Incorrecta o sin sustento | Incierta con justificación parcial | Correcta y justificada con ficha |
| Severidad | Incorrecta sin advertencia | Reconoce incertidumbre o aproximación parcial | Lectura compatible con referencia y límites |
| Retraso/costo | Confunde unidades o signo | Interpreta solo uno correctamente | Interpreta ambos y sus límites |
| Evidencia | Inventada o ausente | Una señal relevante | Dos señales pertinentes sin causalidad inventada |
| Acción | Inviable o sin evidencia | Verificación genérica pertinente | Acción concreta, sustentada y con seguimiento |

Dos evaluadores puntúan respuestas desidentificadas y sin marcas de condición cuando sea posible; registrar discrepancias, acuerdo y adjudicación, sin reemplazar retrospectivamente las puntuaciones originales. No revelar las respuestas de referencia durante la tarea.

## Consentimiento y análisis

Texto mínimo a completar y aprobar: «Se me informó el propósito académico, las dos condiciones, el tiempo previsto, los datos recogidos, el riesgo de recomendaciones incorrectas, mi derecho a no responder y retirarme sin consecuencias, el contacto responsable y la fecha de eliminación. Autorizo el análisis pseudonimizado y la publicación únicamente de agregados». Registrar consentimiento por separado de respuestas; no añadir firmas, nombres ni contactos a Git. El responsable completa duración y retención antes del consentimiento, no después.

La unidad primaria es la persona: agregar medianas de tiempo y calidad por condición antes de calcular diferencias pareadas. Reportar N real, IQR, distribución de diferencias, fallos y abandonos; no tratar cada caso de una misma persona como observación independiente. Un intervalo bootstrap, si se usa, remuestrea participantes y fija seed/repeticiones previamente. Definir antes un margen de calidad aceptable y la hipótesis; no declarar productividad por menor tiempo si empeora la calidad. Reportar ambos resultados, incluso nulos o desfavorables. Mantener el estudio exploratorio salvo diseño/potencia aprobados. La plantilla permanece vacía y no se genera ningún resultado humano en esta auditoría.