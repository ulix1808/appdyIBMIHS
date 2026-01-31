# Alternativas para IHS en HP-UX (sin Apache Agent nativo)

En HP-UX el **Apache Agent** de AppDynamics no está soportado. Esta carpeta contiene los artefactos para la alternativa basada en **mod_status + Machine Agent + Python**.

## Requisitos

- **Host Linux** con **mínimo 1 CPU y 4 GB RAM** (Machine Agent + Python).
- **Python instalado** en el host Linux (Python 3 y `requests`).
- **Conectividad de red:** el host Linux debe poder **alcanzar al IHS** en HP-UX (o viceversa) para recolectar las métricas vía scraping; sin conectividad no hay colección.
- IHS en HP-UX: solo cambios de configuración (mod_status); sin binarios ni forwarders.

## Contenido

| Ruta | Descripción |
|------|-------------|
| [IHSStatus/](IHSStatus/) | Extensión Machine Agent: `monitor.xml`, `ihs_status_to_appd.py`, `env.example`, README |

## Manual de implementación

Pasos completos (config IHS, HTTP Listener, extensión, Metric Browser): **[§2.3 y §2.3.1 del manual de instalación](../MANUAL_INSTALACION_APPDYNAMICS_IHS.md#23-alternativas-para-hp-ux-sin-agente-nativo)**.
