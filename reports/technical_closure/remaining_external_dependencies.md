# Dependencias externas pendientes

Este cierre no inventa resultados de proveedores, participantes ni infraestructura que no estuvieron disponibles.

| Dependencia | Estado observado | Requisito para completar |
|---|---|---|
| Comparación de alternativas locales | Hay resultados reproducibles de Qwen, pero otras alternativas no estuvieron disponibles bajo protocolo homogéneo | Ejecutar modelos locales candidatos en la misma cohorte y contrato y guardar resultados reales |
| Docker local | El sandbox bloqueó la lectura de `~/.docker/config.json`; `/var/run/docker.sock` tampoco existe | Permitir lectura del archivo de configuración Docker y acceso al socket en la política del sandbox; iniciar el daemon Docker. CI de GitHub ya es evidencia separada |
| Kubernetes | Sin contexto ni clúster local | Proveer un clúster autorizado para probar readiness, balanceo, caída de instancia, rollout y rollback |
| Productividad humana | Cero participantes y cero respuestas | Protocolo aprobado, consentimiento y participantes reales; hasta entonces reportar NO MEDIDA |
| Validación empresarial | No hay dataset de proyectos reales autorizado | Aprobación de procedencia, licencia, privacidad, outcomes y plan de evaluación independiente |
| Monitorización productiva | Solo reporte offline y métricas locales por proceso | Scheduler/observabilidad autorizados, almacenamiento central, alertas y ground truth antes de operar drift/degradación |

La política del sandbox no se intentó eludir. La ausencia de una dependencia no altera los resultados existentes ni autoriza a completar métricas por inferencia.
