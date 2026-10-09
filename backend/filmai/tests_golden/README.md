# Referencias de la API antes de multiidioma

OT-01 captura 91 escenarios independientes de `filmai.tests_contrato`. Cada JSON
contiene el estado HTTP y el cuerpo completo observado; no contiene el request,
por lo que fechas de nacimiento, IDs y tokens variables no requieren reemplazos.
El roundtrip por JSON convierte los `ErrorDetail` de DRF a las cadenas que recibe
el cliente. Todos los escenarios fijan `DEBUG=False` y el idioma actual `es-ar`.

Para comparar sin modificar referencias:

```sh
python manage.py test filmai.tests_contrato
```

Para regenerarlas explícitamente y revisar el diff:

```sh
REGENERAR_REFERENCIAS_API=1 python manage.py test filmai.tests_contrato
```

| Grupo de escenarios                                                                  | Origen real y motivo                                                                                                                                  |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `registro_*`, `login_incorrecto`                                                     | Endpoints de registro y login; errores propios y validaciones de DRF/dj-rest-auth.                                                                    |
| `catalogo_*`                                                                         | Endpoints públicos; mantienen las cadenas inglesas por campo, sin convertirlas a listas.                                                              |
| `confirmacion_*`, `restablecimiento_*`                                               | Endpoints de enlaces; cubren las respuestas que usan solo `codigo` y las validaciones de contraseña.                                                  |
| `exito_*`, `recuperacion_respuesta`                                                  | Respuestas exitosas con texto que también identifica el inventario 2.4. Cambio de contraseña y baja usan sesiones JWT reales.                         |
| `google_*`                                                                           | Serializer real con frontera OAuth aislada. Captura fallos en verificación, completar login y persistencia, campos faltantes, conflictos y permisos.  |
| `GoogleSocialLoginSerializer_*`, `UsuarioPerfilSerializer_*`, `perfil_*`, `cambio_*` | Validadores y serializers reales para perfil, Google y cambio de contraseña.                                                                          |
| `lista_nombre_*`, `resena_actualizacion_vacia`                                       | Validadores reales de listas y reseñas, incluidos errores generales y por campo.                                                                      |
| `tmdb_*`                                                                             | Cliente HTTP real con `httpx.MockTransport`, sin llamadas de red ni esperas de reintento. Captura mensajes producidos por el cliente y su mapeo HTTP. |
| Autenticación, permisos, conflictos, método, límites, servidor                       | Excepciones de producción pasadas al manejador real; no se sustituye el texto de respuesta.                                                           |
| `ruta_inexistente`, `servidor_django`, `documentacion_staff`                         | Handlers y endpoint de documentación fuera del manejador DRF.                                                                                         |

Las invocaciones directas son deliberadas: los validadores de fecha del perfil
están declarados para un campo de solo lectura; el nombre vacío de listas suele
ser rechazado por DRF antes del validador propio; las ramas sin adapter/token de
Google son defensivas. `tmdb_presupuesto` fuerza un presupuesto agotado porque
con la configuración vigente las excepciones de cada intento salen antes de esa
rama final. No se presentan esos casos como flujos HTTP alcanzables.

La ayuda de `ComplejidadContrasenaValidator.get_help_text()` y el detalle interno
que solo se emite con `DEBUG=True` no son respuestas del contrato de producción.
Las cinco restricciones de contraseña sí se capturan desde el registro.
Los 91 escenarios cubren orígenes y formas diferentes, no pretenden igualar el
conteo agregado de textos únicos del plan.

OT-82 migró estas referencias al contrato por códigos mientras se emitían ambas formas. OT-83 retira las claves anteriores: los errores registran `code`, `params` y `errors`; los éxitos conservan datos de máquina y `code`. El ejecutor comprueba además que ningún 4xx/5xx de `/api/` tenga claves extra. Los HTTP y las matrices de credenciales/validación siguen siendo el oráculo.
