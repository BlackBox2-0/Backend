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

### 1. Agente Collector

Solo recibe y normaliza los eventos entrantes (de cualquier fuente: API, WebSocket, simulación)

### 2. Agente Activity Monitor

Monitorea acciones productivas del trabajador (recursos accedidos, sistemas usados, frecuencia de trabajo).

### 2.1. Agente Risk Analyst

 Gemini analiza el evento en profundidad, considera contexto histórico del usuario, hora, tipo de acción, y genera un score con explicación

### 2.1. Agente Enforcer

Toma una decisión final: BLOCK o ESCALATE (requiere aprobación humana), y registra en el audit log para ambos se envia un evento.


### 3. Agente Productivity Detector

Detecta cuando el trabajador está inactivo, en sitios no relacionados al trabajo, o con patrones de baja productividad.


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
