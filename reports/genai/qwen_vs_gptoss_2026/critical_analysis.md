# Análisis crítico de la comparación generativa

## Qué miden y qué no miden los indicadores

Los indicadores son verificaciones automáticas del validador de PRUNIN: forma JSON, citas de evidencia permitidas y con procedencia correcta, ausencia de cifras no presentes en la evidencia, ausencia de contradicciones detectables por reglas, acciones que empiezan con verbo ejecutable y seguimiento verificable. Detectan errores verificables, pero **no** juzgan utilidad gerencial, priorización correcta ni calidad de redacción. Esa evaluación requiere expertos humanos y **no se realizó**.

## Riesgos técnicos

- **Razonamiento obligatorio de GPT-OSS**: con `think=false` Ollama devuelve contenido vacío; se usó `think=low`. GPT-OSS generó en promedio 77.9 caracteres de razonamiento (Qwen: 0.0). Este razonamiento consume el mismo presupuesto `num_predict`.
- **Cifras no soportadas**: tasa de 0.0 % en GPT-OSS y 0.0 % en Qwen. Una cifra inventada en una recomendación de proyecto puede inducir decisiones erróneas; por eso el validador bloquea la respuesta y PRUNIN cae a la recomendación determinista.
- **Memoria**: GPT-OSS ocupa más memoria residente; en 24 GB compite con el navegador y el backend, lo que puede aumentar la latencia en uso real.
- **Cola de latencia**: la relación p95/mediana es 2.44 en Qwen y 1.52 en GPT-OSS; la cola larga, no la mediana, determina la espera percibida en la demostración.
- **No determinismo**: con temperatura 0,1 el texto varía entre ejecuciones: respuestas idénticas en 80.0 % de los casos repetidos con Qwen y 20.0 % con GPT-OSS, aunque la aceptación, las señales citadas y las prioridades se mantuvieron en 100.0 % y 100.0 % de los casos, respectivamente.

## Riesgos éticos

- Las recomendaciones automáticas pueden percibirse como juicio sobre personas o equipos; PRUNIN las presenta como apoyo y siempre con la evidencia citada.
- La aceptación por el validador no garantiza ausencia de sesgo ni corrección causal; el responsable del proyecto conserva la decisión.
- Ambos modelos se ejecutan localmente: ningún dato de proyecto sale del equipo.

## Amenazas a la validez

- **Interna**: el prompt incluye la directiva `/no_think` pensada para Qwen; el nivel de razonamiento difiere por limitación de GPT-OSS; los tokenizadores difieren, por lo que los tokens/s no son estrictamente comparables. El orden de ejecución (primero Qwen, luego GPT-OSS) puede introducir efectos térmicos del equipo.
- **Del constructo**: el validador es conservador (por ejemplo, rechaza un umbral numérico razonable no presente en la evidencia); mide adherencia al contrato de PRUNIN, no calidad general del modelo.
- **Externa**: 30 casos de un único dataset (Mendeley) y un solo equipo; los resultados no se generalizan a otros dominios ni hardware.
- **Estadística**: con 30 casos pareados la potencia es limitada. Prueba de McNemar exacta sobre la aceptación pareada de los 30 casos: 1 caso aceptado solo por Qwen3 8B y 0 casos solo por GPT-OSS 20B; p = 1.0000. Con 30 casos la diferencia de aceptación no es estadísticamente significativa (α = 0,05); el resultado debe leerse como evidencia direccional.
- **Repetibilidad**: 5 casos × 3 repeticiones es una muestra pequeña de la variabilidad.
