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
- `prediction_id`.

### 2. Ejecutar “En riesgo”

Seleccionar el preset **En riesgo** → **Analizar proyecto**.

Mostrar:

- Health;
- probabilidades;
- Delay;
- Cost;
- Final Status;
- Team Health;
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
- Team Health = variable derivada;
- Health/Delay/Cost/Status = predicciones ML;
- Drivers = sensibilidad local;
- Recomendaciones = capa explicativa fundamentada / IA generativa opcional.

## Si algo falla

- Si Internet falla: la demo local sigue funcionando.
- Si Ollama falla: se activa el fallback fundamentado.
- Si no existe el modelo académico: se usa el demo sintético y queda rotulado como tal.
- Si un CSV tiene pocas variables: la fila se bloquea si no alcanza 60 % de cobertura.
- Si Node no está instalado: no importa; `frontend/dist` ya viene listo.
