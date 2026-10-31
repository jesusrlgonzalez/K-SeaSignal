# SeaSignal · Inteligencia de trayectorias marítimas

**Mejorar la confiabilidad de los datos de navegación AIS para analizar trayectorias, detectar inconsistencias y apoyar investigaciones logísticas y marítimas.**

## Qué resuelve
Procesar datos geoespaciales y temporales, identificar anomalías de posición y movimiento, reconstruir trayectorias y presentar evidencias para interpretación humana.

Auditoría de calidad AIS: valida coordenadas, MMSI, velocidad y tiempos, reconstruye trayectorias y detecta saltos imposibles y huecos de observación para el analista.

## Hacia dónde va
Convertirse en una herramienta analítica de referencia para la evaluación de calidad y comportamiento espacio-temporal de trayectorias marítimas.

**Objetivo:** Construir un sistema de auditoría AIS capaz de identificar registros inválidos y comparar métodos de detección de anomalías con métricas verificables.

**Valor que persigue:** Mejorar la calidad de los análisis marítimos y reducir el esfuerzo dedicado a investigar registros incorrectos.

## Resultados de la demo
Sobre un conjunto de datos sintéticos diseñado con errores y casos difíciles: **2 312 mensajes AIS: 2 190 candidatos, 87 a revisión, 35 en cuarentena; 13 señales (11 saltos imposibles, 2 huecos de observación)**.

## Pruébalo en 2 minutos
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py test     # 66 tests automatizados
python run.py demo     # demo de punta a punta → demo_output/
python run.py api      # API REST → http://127.0.0.1:8000/docs
```

## Diseñado para decisiones responsables
- **Siempre con una persona al mando:** una señal no es evidencia de conducta ilícita; no hay inteligencia operacional de navegación.
- **Trazable:** cada registro conserva su motivo de aceptación, revisión o cuarentena.
- **Probado:** 66 tests automatizados en Linux y Windows en cada cambio.
- **Contenedor:** la imagen Docker se construye en cada cambio.

## Estado
Prototipo funcional demostrado con datos sintéticos. El siguiente paso es un **piloto con datos reales** de su organización, bajo acuerdo de uso y confidencialidad.

**¿Le interesa un piloto?** Contacte a **Kriter Systems**.

---
I28 · Kriter Systems · Los datos incluidos son sintéticos y no representan a personas ni empresas reales.
