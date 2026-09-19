"""Errores de dominio que la API de listas comunica como conflictos."""

from typing import ClassVar

from rest_framework.exceptions import APIException


class ListaConflict(APIException):
    """Conflicto de negocio con un código estable para el frontend."""

    status_code = 409
    default_code = "conflicto_lista"


class NombreListaDuplicado(ListaConflict):
    default_code = "nombre_lista_duplicado"
    default_detail: ClassVar[dict[str, str]] = {
        "codigo": default_code,
        "detail": "Ya tenés una lista con ese nombre.",
    }


class ItemDuplicado(ListaConflict):
    default_code = "item_duplicado"
    default_detail: ClassVar[dict[str, str]] = {
        "codigo": default_code,
        "detail": "La producción ya pertenece a esta lista.",
    }


class ListaPredeterminadaProtegida(ListaConflict):
    default_code = "lista_predeterminada_protegida"
    default_detail: ClassVar[dict[str, str]] = {
        "codigo": default_code,
        "detail": "Las listas predeterminadas no se pueden modificar ni eliminar.",
    }


class CalificacionImpideQuitarDeVistas(ListaConflict):
    default_code = "calificacion_impide_quitar_de_vistas"
    default_detail: ClassVar[dict[str, str]] = {
        "codigo": default_code,
        "detail": "Eliminá la calificación antes de quitar esta producción de Vistas.",
    }
