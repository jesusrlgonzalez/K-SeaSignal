# Tarjeta de datos — AIS sintético sucio
**Solo simulación. No son buques reales, ni transmisiones de NOAA.**
- Datos: 2312 mensajes de 16 identidades sintéticas, 10 minutos entre observaciones de referencia.
- Alteraciones y mensajes repetidos etiquetados: 122; el archivo `injection_truth_DO_NOT_TRAIN.csv` es exclusivo de evaluación y NO es entrada del auditor.
- Un buque sintético cruza el antimeridiano para comprobar longitudes y cálculo de distancias. Otro contiene diez intervalos sin observación deliberados: NO hay inferencia de causa, intervención ni apagado.
- Hay ausencia de mensajes, no filas perdidas al auditar el CSV recibido.
- Distinción crucial: GPS jump ≠ prueba de manipulación; valores especiales SOG 102.3, COG 360 y Heading 511 indican información no disponible y no deben interpretarse como valores físicos normales.
- Referencias temporales sintéticas: agosto de 2024; ningún buque, MMSI ni anomalía proceden de datos marítimos observados.
- Usos prohibidos: vigilancia de individuos, persecución de embarcaciones y atribución de delito por anomalías.
