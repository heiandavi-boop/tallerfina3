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