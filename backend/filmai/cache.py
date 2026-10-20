"""Serializador JSON para la caché de Django respaldada por Redis.

`RedisCache` guarda cada valor con `pickle` por defecto. `pickle.loads` puede
ejecutar código arbitrario si los bytes los escribió un tercero, así que quien
llegue a Redis podría tomar el control del proceso web. JSON solo describe
datos: lo peor que puede traer un valor ajeno es un valor inesperado.

Los enteros se guardan crudos porque `cache.incr` (contadores de throttle) usa
`INCR` de Redis, que solo entiende números sin envoltorio.
"""

import json
import logging

logger = logging.getLogger(__name__)


class JSONRedisSerializer:
    def dumps(self, obj):
        if type(obj) is int:
            return obj
        return json.dumps(obj).encode()

    def loads(self, data):
        try:
            return int(data)
        except ValueError:
            pass
        try:
            return json.loads(data)
        except ValueError:
            # Bytes que no son JSON (por ejemplo un valor pickle de antes de
            # este cambio, o uno ajeno): se tratan como ausentes, nunca se
            # interpretan.
            logger.warning("Valor de caché ilegible descartado")
            return None
