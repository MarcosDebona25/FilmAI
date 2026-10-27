"""Calificaciones y reseñas del usuario (C-08, CU-015).

Separado de `views.py` a propósito: esas vistas son el passthrough de TMDB
(públicas, y que nunca deben romperse por un problema nuestro), y estas
escriben en nuestra base, exigen sesión y **fallan fuerte**. Si la producción
no se pudo guardar, la calificación no puede existir y no hay respuesta
alternativa que sirva; así que se deja propagar, al revés que en C-03.

El recurso público es la dupla «calificación + texto opcional», que CU-015
trata como una sola cosa que el usuario publica. El `{id}` de la ruta es la pk
de la `Calificacion`, porque la nota es lo que siempre existe: la `Resena` es
un 1:1 opcional que cuelga de ella.

Los dos borrados hacen cosas distintas a propósito (decisión del 26/09/2026):

- `DELETE /api/reviews/{id}/texto/` borra el texto y **conserva la nota**. Es
  el 🗑️ del modal de §5d.
- `DELETE /api/reviews/{id}/` borra la nota, y el texto cae por CASCADE. Es lo
  que el 409 de L-01 le pide al usuario para poder quitar algo de «Vistas».

**Calificada ⇒ en «Vistas»** (regla del 30/09/2026): calificar agrega la
producción a «Vistas» y borrar la calificación la saca, cada una en la misma
transacción que la nota. Editar y borrar solo el texto no la tocan. La vuelta
no rige: se puede marcar como vista sin calificar. Las escrituras en `Tiene`
pasan por `listas/services.py`, porque la tabla es de ese módulo.
"""

from typing import ClassVar

from django.db import IntegrityError, transaction
from django.db.models import BigIntegerField, Exists, ExpressionWrapper, F, OuterRef, Q
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.exceptions import CalificacionDuplicada
from catalogo.models import Calificacion, ProduccionTraduccion, Resena
from catalogo.pagination_reviews import ResenaCursorPagination
from catalogo.presupuesto import TopesTMDBMixin
from catalogo.serializers_reviews import (
    ActualizarCalificacionSerializer,
    CalificacionSerializer,
    ComunidadQuerySerializer,
    CrearCalificacionSerializer,
    MiResenaSerializer,
    MisResenasQuerySerializer,
    ProduccionQuerySerializer,
    ResenaComunidadSerializer,
)
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.materialization import materializar
from filmai.idioma import idioma_efectivo
from filmai.throttles import EscrituraThrottle
from listas.services import agregar_a_vistas, quitar_de_vistas


def _produccion_pedida(request):
    """`(id_tmdb, tipo_dominio)` de los query params, validados."""
    query = ProduccionQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    datos = query.validated_data
    return datos["id_tmdb"], tmdb_a_dominio(datos["tipo"])


def _calificacion_propia(request, calificacion_id):
    """La calificación del usuario autenticado, o 404.

    La de otra persona es 404 y no 403, igual que en L-01: un 403 confirmaría
    que esa fila existe. Para quien no es su dueño, no existe.
    """
    return get_object_or_404(
        Calificacion.objects.select_related("resena", "produccion"),
        pk=calificacion_id,
        usuario=request.user,
    )


# Orden de la comunidad (C-07) y de «Mis reseñas», que siguen el mismo
# criterio. Los de nota usan una clave única anotada: el cursor de DRF se ubica
# con el primer campo y desempata con un offset, que se degrada cuando miles de
# reseñas tienen el mismo 8. `valor * 10^9 + id` ordena igual que (valor, id) y
# no se repite.
_ORDENES = {
    "fecha-desc": ("-fecha", "-id"),
    "fecha-asc": ("fecha", "id"),
    "nota-desc": ("-clave_nota",),
    "nota-asc": ("clave_nota",),
}


def _clave_nota(campo_valor):
    """La clave `valor * 10^9 + id` sobre la nota en `campo_valor`.

    `Cast` antes de multiplicar: `valor` es un entero de 32 bits en Postgres y
    10 * 10^9 se pasa de rango (`ExpressionWrapper` solo declara el tipo final).
    """
    return ExpressionWrapper(
        Cast(campo_valor, BigIntegerField()) * 1_000_000_000 + F("id"),
        output_field=BigIntegerField(),
    )


def _filtrar_nota(qs, datos, campo):
    """`nota_min` y `nota_max` (inclusivos) sobre la nota en `campo`."""
    if "nota_min" in datos:
        qs = qs.filter(**{f"{campo}__gte": datos["nota_min"]})
    if "nota_max" in datos:
        qs = qs.filter(**{f"{campo}__lte": datos["nota_max"]})
    return qs


class CalificacionesView(TopesTMDBMixin, APIView):
    """Reseñas de la comunidad sobre una producción, y alta de la propia."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    pagination_class = ResenaCursorPagination

    def get_permissions(self):
        # Leer es público desde el 14/10/2026 (C-07): la ficha se ve sin sesión
        # y las reseñas son públicas. Calificar sigue exigiendo sesión.
        if self.request.method == "GET":
            return [AllowAny()]
        return super().get_permissions()

    def get(self, request):
        """Las reseñas de los **demás** sobre una producción (§5c).

        Tres exclusiones, cada una con su motivo:

        - **Sin texto**: una nota sin escribir no tiene nada que leer.
        - **Moderadas** (`activa=False`): decisión del 26/09/2026, solo su autor
          las ve.
        - **La de quien pregunta**: la ficha la muestra aparte, arriba, en su
          propia card. Mandarla dos veces obligaría a deduplicar a cada
          consumidor, y una lista paginada no puede prometer que la propia caiga
          en la primera página.
        """
        query = ComunidadQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        datos = query.validated_data
        resenas = Resena.objects.filter(
            calificacion__produccion__id_tmdb=datos["id_tmdb"],
            calificacion__produccion__tipo=tmdb_a_dominio(datos["tipo"]),
            activa=True,
            calificacion__activa=True,
        )
        # Sin sesión no hay reseña propia que sacar.
        if request.user.is_authenticated:
            resenas = resenas.exclude(calificacion__usuario=request.user)
        total_comunidad = resenas.count()

        resenas = _filtrar_nota(resenas, datos, "calificacion__valor")
        resenas = resenas.annotate(
            clave_nota=_clave_nota("calificacion__valor")
        ).select_related(
            # Sin esto, serializar N reseñas dispara 2N consultas para traer la
            # calificación y el usuario de cada una (el problema N+1).
            "calificacion__usuario"
        )

        paginator = self.pagination_class()
        paginator.ordering = _ORDENES[datos["orden"]]
        paginator.total_comunidad = total_comunidad
        pagina = paginator.paginate_queryset(resenas, request, view=self)
        return paginator.get_paginated_response(
            ResenaComunidadSerializer(pagina, many=True).data
        )

    def post(self, request):
        entrada = CrearCalificacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        # Validar ANTES de materializar: un valor fuera de rango no tiene por
        # qué costar tres llamadas a TMDB ni dejar una producción escrita de
        # rebote.
        produccion = materializar(datos["id_tmdb"], datos["tipo"])

        texto = datos.get("texto")
        try:
            with transaction.atomic():
                calificacion = Calificacion.objects.create(
                    usuario=request.user, produccion=produccion, valor=datos["valor"]
                )
                if texto:
                    Resena.objects.create(calificacion=calificacion, texto=texto)
                # Si la calificaste, la viste (regla del 30/09/2026). Dentro
                # del mismo atomic: sin «Vistas» no queda una nota a medias.
                agregar_a_vistas(request.user, produccion)
        except IntegrityError:
            # `uq_calificacion_usuario_produccion`. El atomic() es el savepoint
            # que deja la transacción usable después del error (en PostgreSQL,
            # un error la aborta entera), el mismo patrón que `materializar()`.
            raise CalificacionDuplicada from None

        return Response(
            CalificacionSerializer(calificacion).data, status=status.HTTP_201_CREATED
        )


class CalificacionDetailView(APIView):
    """Actualiza o elimina una calificación propia."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def put(self, request, calificacion_id):
        calificacion = _calificacion_propia(request, calificacion_id)
        entrada = ActualizarCalificacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        with transaction.atomic():
            if "valor" in datos:
                calificacion.valor = datos["valor"]
                calificacion.save(update_fields=["valor"])
            if "texto" in datos:
                # `update_or_create` cubre los dos casos con una sola llamada:
                # cambiar el texto, y escribirlo por primera vez cuando la
                # calificación se creó sin nada escrito.
                Resena.objects.update_or_create(
                    calificacion=calificacion, defaults={"texto": datos["texto"]}
                )

        calificacion.refresh_from_db()
        return Response(CalificacionSerializer(calificacion).data)

    def delete(self, request, calificacion_id):
        """Borra la calificación, su texto (por CASCADE) y el ítem de «Vistas».

        Es físico, no lógico: CU-015 pide eliminar «permanentemente», y
        `activa` ya significa una sola cosa —moderada por un administrador
        (AD-01')—. Con dos sentidos, «¿por qué no se ve esta reseña?» no
        tendría respuesta.

        Sacarla de «Vistas» es la regla del 30/09/2026: el modal lo avisa antes
        de confirmar, y el usuario puede volver a marcarla. Termina en el mismo
        estado que quitar de «Vistas» con `?borrar_calificacion=true` (L-01).
        """
        calificacion = _calificacion_propia(request, calificacion_id)
        with transaction.atomic():
            quitar_de_vistas(request.user, calificacion.produccion)
            calificacion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResenaTextoView(APIView):
    """Borra el texto de una calificación propia, conservando la nota."""

    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]

    def delete(self, request, calificacion_id):
        calificacion = _calificacion_propia(request, calificacion_id)
        # Idempotente: borrar el texto de una calificación que no lo tiene no
        # es un error que describa ningún problema, y así el frontend puede
        # reintentar sin interpretar un 404 ambiguo (¿no existe la calificación
        # o no existía el texto?).
        Resena.objects.filter(calificacion=calificacion).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisCalificacionesView(APIView):
    """Las calificaciones propias: la lista de P-06, o la de una ficha.

    Una sola ruta con dos formas de respuesta según los query params:

    - **Sin filtro** → la lista paginada de «Mis reseñas» (P-06).
    - **Con `id_tmdb` y `tipo`** → un objeto solo, porque el UNIQUE
      `(usuario, produccion)` garantiza que no puede haber más de una. Devolver
      `{"results": [...]}` obligaría al frontend a desempacar algo que nunca
      tiene dos elementos.

    Medio filtro es un 400 y no «todas»: un bug del frontend que olvide `tipo`
    devolvería la lista entera y la ficha mostraría la calificación de otra
    película, que es peor que un error visible.

    A diferencia de la comunidad, acá entran las calificaciones sin texto (desde
    P-06 se pueden editar) y las moderadas (su autor las sigue viendo).
    """

    pagination_class = ResenaCursorPagination

    def get(self, request):
        propias = (
            Calificacion.objects.filter(usuario=request.user, activa=True)
            .select_related("produccion", "resena")
            .prefetch_related("produccion__traducciones")
            .order_by("-fecha", "-id")
        )
        # El cursor de paginación no solicita una ficha individual. Solo los
        # filtros de producción cambian la respuesta de listado a objeto.
        if "id_tmdb" in request.query_params or "tipo" in request.query_params:
            id_tmdb, tipo = _produccion_pedida(request)
            calificacion = get_object_or_404(
                propias, produccion__id_tmdb=id_tmdb, produccion__tipo=tipo
            )
            return Response(
                MiResenaSerializer(
                    calificacion, context={"idioma": idioma_efectivo(request)}
                ).data
            )

        query = MisResenasQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        datos = query.validated_data
        total_propias = propias.count()
        propias = _filtrar_propias(propias, datos)

        paginator = self.pagination_class()
        paginator.ordering = _ORDENES[datos["orden"]]
        paginator.total_propias = total_propias
        pagina = paginator.paginate_queryset(propias, request, view=self)
        return paginator.get_paginated_response(
            MiResenaSerializer(
                pagina, many=True, context={"idioma": idioma_efectivo(request)}
            ).data
        )


def _filtrar_propias(propias, datos):
    """Aplica los filtros de «Mis reseñas» y anota la clave de orden por nota."""
    q = (datos.get("q") or "").strip()
    if q:
        # El título canónico o el de alguna traducción, sin acentos ni
        # mayúsculas. `Exists` y no un JOIN: con varias traducciones, el JOIN
        # repetiría la calificación.
        traducido = ProduccionTraduccion.objects.filter(
            produccion=OuterRef("produccion"), titulo__unaccent__icontains=q
        )
        propias = propias.filter(
            Q(produccion__titulo__unaccent__icontains=q) | Exists(traducido)
        )
    if datos.get("texto") == "con":
        propias = propias.filter(resena__isnull=False)
    elif datos.get("texto") == "sin":
        propias = propias.filter(resena__isnull=True)
    if "clase" in datos:
        propias = propias.filter(produccion__tipo=tmdb_a_dominio(datos["clase"]))
    propias = _filtrar_nota(propias, datos, "valor")
    # Mismo criterio que la comunidad, sobre la calificación: el orden por nota
    # usa una clave única para que el cursor no se pierda entre empates.
    return propias.annotate(clave_nota=_clave_nota("valor"))
