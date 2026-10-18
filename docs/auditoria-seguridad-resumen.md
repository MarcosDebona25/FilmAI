# Auditoría de seguridad: resumen

Resumen para el equipo de la auditoría `standard` de `security-audit` (commit `f7bbb6b`, 18/10/2026). Contiene solo títulos, módulos, estado y prioridad. Los informes completos con la reproducción siguen locales (`security-audit/`, ignorado por git) y se comparten por otro canal si hace falta.

## Cómo se hizo

1. **run-1:** lectura de código. Dejó 11 pistas por validar y 1 rechazada.
2. **run-2:** las 11 pistas se probaron en un sandbox Docker sin acceso a internet (repositorio en solo lectura, TMDB simulado, correo en memoria, Postgres y Redis efímeros, solo datos ficticios). Cada pista la reprodujo un agente validador y la repitió un verificador independiente.

## Resultado

- **11 pistas confirmadas** (ninguna alta ni crítica), **1 rechazada**, 0 pendientes.
- Hay factores de despliegue que el repositorio no muestra y que cambian la probabilidad real: proxy o WAF delante, límites de Resend y de TMDB, quién lee los logs, exposición real del puerto de Redis y permisos de staff concedidos.

## Hallazgos

| # | Módulo | Hallazgo | Estado | Severidad | Prioridad |
|---|---|---|---|---|---|
| F1 | infra / settings | Redis sin contraseña y publicado, con caché que deserializa pickle | Confirmado | Media | 1 |
| F2a | usuarios | Login sin límite de intentos | Confirmado | Media | 1 |
| F2b | usuarios | Reenvío de confirmación y registro sin límite (correo masivo) | Confirmado | Media | 1 |
| F3 | catálogo / settings | Límite del catálogo eludible con `X-Forwarded-For`, con amplificación a TMDB y Redis | Confirmado | Media | 1 |
| F4 | usuarios | Cuenta pendiente sin vencimiento reserva el correo (pre-secuestro) | Confirmado | Media | 2 |
| F5 | usuarios (admin) | Staff con permiso parcial puede escalar privilegios | Confirmado | Media | 2 |
| F6 | catálogo | Parámetros de trending sin validar (rutas hacia otros endpoints de TMDB) | Confirmado | Baja | 3 |
| F7 | catálogo | Alta de reseñas con ids inexistentes o enormes: filas vacías y 500 (Internal Server Error) | Confirmado | Baja | 3 |
| F8 | usuarios | Clave de confirmación de correo escrita en el log | Confirmado | Baja | 3 |
| F9 | frontend | Redirección abierta posterior al login (`next`) | Confirmado | Baja | 3 |
| F10 | catálogo | Moderación de reseñas reversible por el autor | Confirmado | Baja | 4 (decisión de producto) |
| — | frontend | Sin cabeceras anti-framing | Rechazado | — | Endurecimiento opcional |

## Orden sugerido

1. F1 (configuración de Redis).
2. F3 y F2: identidad del cliente y límites de tasa.
3. F9 y F8, que son cambios chicos.
4. F6 y F7 (catálogo).
5. F5 (admin).
6. F4 y F10, después de decidir el comportamiento con el equipo.

Cada fix va como tarea aparte, con su test de regresión y su entrada en `docs/decisiones.md`.
