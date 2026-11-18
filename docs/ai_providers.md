# Proveedores de IA generativa: Ollama y OpenAI

PRUNIN AI Core mantiene sus tres modelos predictivos LightGBM sin modificación. Solo la **capa generativa de recomendaciones** selecciona un proveedor por solicitud.

## Uso rápido

1. Ejecutar PRUNIN mediante `./scripts/run_playground.sh`.
2. En la página principal, ubicar **Proveedor de IA** y seleccionar **Ollama — local**, **OpenAI — API de ChatGPT** o **Solo predicción**.
3. Si seleccionas OpenAI, introduce el **identificador de modelo** disponible en tu cuenta (predeterminado `gpt-4.1`) y pega la API key en el campo protegido. También se puede configurar `OPENAI_API_KEY` en el entorno **del proceso de FastAPI**; no necesita estar presente en el frontend. No pegar secretos en este repositorio ni en el chat.
4. Ejecutar **Analizar**. La recomendación muestra el motor utilizado, procedencia de evidencia, acciones y seguimiento.

### Ollama

Debe estar instalado y ejecutándose en el servidor de PRUNIN. Por defecto usa `qwen3:8b` y `http://localhost:11434/api/chat`; personalizar mediante `PRUNIN_OLLAMA_MODEL` y `PRUNIN_OLLAMA_URL`. La selección del navegador puede habilitar Ollama para esa solicitud aunque `PRUNIN_ENABLE_OLLAMA=0`, sin cambiar el estado global de otros usuarios.

### OpenAI

PRUNIN utiliza `POST https://api.openai.com/v1/chat/completions` desde el **backend** y nunca expone la clave al proveedor desde JavaScript directamente. El campo clave mantiene su contenido **solo en memoria de la pestaña**: no se escribe en `localStorage`, archivos, cookies ni JSON exportado. Si la clave se configura en el servidor con `OPENAI_API_KEY`, puede omitirse en la UI. Se recomienda usar un token específico del proyecto con presupuesto y límites de uso.

```bash
# Ejemplo: configurar en el entorno, no en un archivo versionado
export OPENAI_API_KEY='TU_CLAVE_SECRETA'
export PRUNIN_OPENAI_MODEL='gpt-4.1'
export PRUNIN_OPENAI_TIMEOUT_SECONDS=120
./scripts/run_playground.sh
```

El modelo seleccionado debe estar disponible en la cuenta API del usuario y admitir el formato JSON de Chat Completions. Los modelos de ChatGPT y los nombres de API no son necesariamente idénticos; consultar [modelos disponibles](https://platform.openai.com/docs/models). La **API de OpenAI se cobra por separado** de la suscripción ChatGPT: ver [precios oficiales](https://platform.openai.com/pricing).

### Capacidades y límites de PRUNIN

- Ollama mantiene el contrato anterior: hasta **4 acciones** y **180 caracteres** de resumen.
- OpenAI admite hasta **8 acciones con evidencia** y **1.200 caracteres** de resumen. No se impone un límite pequeño de tokens de salida ni se desactiva el razonamiento del modelo; el contrato acota el **formato de la respuesta de negocio**, no la capacidad del modelo. Los límites reales dependen de la API, contexto del modelo, permisos, cuota y presupuesto.
- Las acciones siempre pasan por validación de procedencia y cifras; un resultado rechazado activa **fallback determinístico** sin alterar predicciones.
- Para un análisis conversacional ilimitado, herramientas o búsqueda web, se requeriría ampliar el producto con endpoints y permisos explícitos adicionales; no se atribuyen esas capacidades a esta integración.

### Seguridad de la API key

- No abrir PRUNIN remoto en HTTP si se va a pegar una clave; la UI bloquea esa configuración en direcciones no locales sin HTTPS.
- Para operar con otros usuarios se deben añadir autenticación, aislamiento, rate limits, HTTPS, CORS restringido y política explícita de registro/redacción de cabeceras.
- El backend **no registra el valor** `X-PRUNIN-OpenAI-Key` ni lo devuelve en resultados.
- La clave sí debe viajar al backend por cada solicitud desde la pestaña; como toda clave introducida en una interfaz web, es accesible a scripts maliciosos en esa misma página. No instalar extensiones no confiables ni servir código de terceros.
- En modo OpenAI, indicadores estructurados del proyecto son enviados a OpenAI para su tratamiento. Revisar clasificación y reglas de protección de datos antes de enviar información empresarial confidencial.

### Diagnóstico

`GET /api/genai-status` conserva exactamente el estado tradicional de Ollama. El nuevo `GET /api/genai-providers` devuelve ambos estados (`ollama`, `openai`) y únicamente indica configuración; **no** comprueba autenticación ni facturación.

Ante errores de OpenAI, el resultado indica `failure_code` como `openai_key_missing`, `openai_auth_error`, `openai_rate_limit`, `openai_timeout` o `openai_unavailable`. En estos casos la salida predictiva funciona y las acciones provienen del respaldo trazable.

> **Importante:** no pegar nunca una clave API en mensajes de soporte, capturas de pantalla, variables Vite (`VITE_*`), código frontend o commits.
