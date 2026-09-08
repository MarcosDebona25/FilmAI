```
@startuml
skinparam linetype ortho
skinparam monochrome true
skinparam backgroundColor #FDFDFD

left to right direction
' Nota: "Administrador" es un ROL del Usuario (is_staff/is_superuser), gestionado vía Django Admin nativo.
actor "Usuario" as usuario
actor "Administrador" as admin
actor "API LLM de Chatbot" as llm
actor "API TMDB" as tmdb
actor "Sistema (Celery Beat)" as sistema

rectangle "Sistema" {
  usecase "CU-001: Crear cuenta de usuario" as CU001
  usecase "CU-002: Confirmar cuenta por correo electrónico" as CU002
  usecase "CU-003: Iniciar sesión" as CU003
  usecase "CU-004: Cerrar sesión" as CU004
  usecase "CU-005: Acceder a la sección de perfil de usuario" as CU005
  usecase "CU-006: Modificar perfil" as CU006
  usecase "CU-007: Dar de baja la cuenta" as CU007
  usecase "CU-008: Visualizar Catálogo" as CU008
  usecase "CU-009: Consultar listas" as CU009
  usecase "CU-010: Buscar peliculas/series por nombres" as CU010
  usecase "CU-011: Marcar pelicula/serie como vista" as CU011
  usecase "CU-012: Gestionar listas" as CU012
  usecase "CU-013: Interactuar con chatbot" as CU013
  usecase "CU-014: Cancelar recomendación en curso" as CU014
  usecase "CU-015: Gestionar Reseña y Calificación" as CU015
  usecase "CU-016: Gestionar usuarios" as CU016
  usecase "CU-017: Moderar reseñas" as CU017
  usecase "CU-018: Entregar respuestas basadas en historial y reseñas" as CU018
  usecase "CU-019: Exponer Catálogo" as CU019
  usecase "CU-020: Recuperar contraseña" as CU020
  usecase "CU-021: Sincronizar catálogo con TMDB" as CU021
}

usuario --> CU001
usuario --> CU003
usuario --> CU004
usuario --> CU005
usuario --> CU008
usuario --> CU009
usuario --> CU010
usuario --> CU011
usuario --> CU012
usuario --> CU013
usuario --> CU015
usuario --> CU020

admin --> CU016
admin --> CU017

llm --> CU018
tmdb -left-> CU019
sistema --> CU021

CU001 --> CU002 : <<include>>
CU005 <|-- CU006 : <<extend>>
CU005 <|-- CU007 : <<extend>>
CU013 --> CU018 : <<include>>
CU013 <|-- CU014 : <<extend>>
CU008 --> CU019 : <<include>>
CU010 --> CU008 : <<include>>
CU008 <|-- CU011 : <<extend>>
CU009 <|-- CU012 : <<extend>>
CU021 --> CU019 : <<include>>
@enduml
```
