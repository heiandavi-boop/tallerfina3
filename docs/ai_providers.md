# Motor generativo local — Ollama

PRUNIN AI Core usa **exclusivamente Ollama** para generar recomendaciones. Las predicciones Health, Delay y Cost se ejecutan localmente con los modelos LightGBM congelados; la generación es opcional y su fallo activa una respuesta determinística basada en señales verificadas.

## Uso
1. Iniciar el servidor Ollama en el equipo autorizado e instalar `qwen3:8b`.
2. Configurar `PRUNIN_ENABLE_OLLAMA=1`, `PRUNIN_OLLAMA_MODEL=qwen3:8b` y `PRUNIN_OLLAMA_URL=http://localhost:11434/api/chat`.
3. Iniciar PRUNIN. En la interfaz seleccionar «Ollama — local» o «Solo predicción».
4. Consultar `GET /api/genai-status` o `GET /api/genai-providers` para ver el estado local.

El cliente no puede habilitar la generación si el servidor mantiene `PRUNIN_ENABLE_OLLAMA=0`. El endpoint de proveedores anuncia únicamente el motor local. No existen campos de credenciales ni encabezados de acceso a servicios generativos externos.

## Contrato de recomendaciones
La salida admite hasta cuatro acciones y un resumen de hasta 180 caracteres, bajo validación JSON, procedencia `feature/source`, cifras soportadas y seguimiento verificable. Los drivers representan sensibilidad local, no causalidad. La generación no modifica los resultados de los modelos supervisados. Los errores de conexión, timeout o validación conservan las predicciones y usan `grounded_fallback`.

## Riesgos y operación
El modelo puede generar recomendaciones semánticamente incorrectas aunque cumplan la validación determinística. Se requiere supervisión humana. La ejecución local evita enviar las evidencias a un servicio generativo externo, pero exige controles de acceso, seguridad de red, permisos y protección de los archivos en el servidor. El costo de cómputo y energía sigue existiendo.

## Selección académica
La justificación de Qwen, sus métricas y los resultados de candidatos disponibles están en [selección de modelo](genai_model_selection.md) y [evaluación generativa](genai_evaluation.md). La comparación exhaustiva de modelos locales continúa como actividad experimental, sin atribuir medidas a alternativas no ejecutadas.
