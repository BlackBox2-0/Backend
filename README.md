# SentinelDoc

Repositorio base para el desarrollo de una plataforma con servicios separados y componentes de apoyo para evaluación, monitoreo y control operativo.

La idea de este `README` es mantener una referencia útil sin exponer demasiado detalle funcional del proyecto.

## Estructura

```text
sentineldoc/
├── backend/       # API y motor principal en Python
└── lobstertrap/   # Componente auxiliar en Go
```

## Componentes

### `backend/`
Servicio API construido con FastAPI. Centraliza endpoints operativos, evaluación y registro de resultados.

## Agentes previstos

### 0. Agente Orquestador

Coordina el flujo entre agentes y define el orden de ejecución según el contexto.

Automatización disponible en `orchestrator.py`.

- `POST /orchestrator/events`: ejecuta el flujo completo Collector -> Activity Monitor -> Productivity Detector -> Risk Analyst -> Enforcer.
- `GET /orchestrator/runs`: lista las ejecuciones completas del orquestador.

### 1. Agente Collector

Solo recibe y normaliza los eventos entrantes (de cualquier fuente: API, WebSocket, simulación)

Automatización inicial disponible en el backend:

- `POST /collector/events`: recibe un evento crudo y lo normaliza al formato interno `EnterpriseEvent`.
- `GET /collector/events`: lista los eventos ya recolectados en memoria.

Ejemplo:

```bash
curl -X POST http://localhost:8000/collector/events \
  -H "Content-Type: application/json" \
  -d '{
    "source": "simulation",
    "payload": {
      "employee_id": "u-100",
      "position": "Analyst",
      "area": "Finance",
      "event_type": "export_data",
      "target": "quarterly-report.csv",
      "details": "Exportacion solicitada desde simulador"
    }
  }'
```

### 2. Agente Activity Monitor

Monitorea acciones productivas del trabajador (recursos accedidos, sistemas usados, frecuencia de trabajo).

Automatización inicial disponible en el backend:

- `POST /activity/events`: registra directamente un evento normalizado como actividad observada.
- `GET /activity/events`: lista las observaciones de actividad.
- `GET /activity/summary`: resume actividad por trabajador.
- `GET /activity/users/{user}/summary`: resume actividad de un trabajador especifico.

Cuando se registra un evento por `POST /collector/events`, tambien se envia automaticamente al Activity Monitor.

### 2.1. Agente Risk Analyst

 Gemini analiza el evento en profundidad, considera contexto histórico del usuario, hora, tipo de acción, y genera un score con explicación

Automatización disponible en `risk_analyst.py`. Se ejecuta desde `POST /evaluate` y devuelve `risk_score`, `decision`, `reasoning` y `flags`.

### 2.1. Agente Enforcer

Toma una decisión final: BLOCK o ESCALATE (requiere aprobación humana), y registra en el audit log para ambos se envia un evento.

Automatización disponible en `enforcer.py`.

- `POST /enforcer/decisions`: analiza un evento, fuerza la decisión final a `BLOCK` o `ESCALATE`, registra la decisión en `/audit` y emite un evento de enforcement.
- `GET /enforcer/events`: lista los eventos de enforcement emitidos.

`POST /evaluate` tambien ejecuta el Enforcer y devuelve la decisión final auditada.


### 3. Agente Productivity Detector

Detecta cuando el trabajador está inactivo, en sitios no relacionados al trabajo, o con patrones de baja productividad.

Automatización disponible en `productivity_detector.py`.

- `POST /productivity/events`: registra una actividad y genera una detección de productividad.
- `POST /productivity/users/{user}/detect`: genera una detección desde el resumen de actividad del usuario.
- `GET /productivity/detections`: lista las detecciones generadas.
- `GET /productivity/users/{user}/detections`: lista las detecciones de un usuario.


## Ejecución local

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Componente Go

```bash
cd lobstertrap
go run main.go serve
```

## Notas

- Mantener variables sensibles fuera del repositorio.
- Ajustar configuraciones por entorno antes de despliegue.
- Documentar agentes y flujos internos a medida que se definan formalmente.
