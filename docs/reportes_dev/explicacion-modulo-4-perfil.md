# Modulo 4: perfil, preferencias y cuenta de usuario

Informe de desarrollo del Modulo 4 de FilmAI. Explica la teoria, la
arquitectura y el codigo de cada pieza que compone la gestion del perfil
propio, las preferencias, los avatares, las contraseñas y la baja logica de
cuenta.

Archivos que participan:

| Capa | Archivos |
|------|----------|
| Backend (Django/DRF) | `usuarios/perfil.py`, `usuarios/cuenta.py`, `usuarios/avatares.py`, `usuarios/passwords.py`, `usuarios/authentication.py`, `usuarios/serializers.py`, `usuarios/validators.py`, `usuarios/exceptions.py`, `usuarios/test_perfil.py` |
| Migracion | `usuarios/migrations/0006_normalizar_nombres.py` |
| Script | `scripts/sync_avatars.py` |
| Frontend (Next.js) | `app/perfil/page.tsx`, `app/preferencias/page.tsx`, `app/mis-resenas/page.tsx`, `components/AccountProvider.tsx`, `components/Avatar.tsx`, `components/Navbar.tsx`, `lib/validation.ts`, `lib/dialog-focus.ts`, `lib/api.ts` |
| Tests E2E | `e2e/cuenta.ts`, `e2e/cuenta.spec.ts`, `e2e/perfil.spec.ts`, `e2e/preferencias.spec.ts` |
| Infra | `playwright.config.ts`, `next.config.ts`, `.github/workflows/ci.yml` |

---

## 1. Arquitectura general

```
┌──────────────────────────────────────────────────────────┐
│  Navegador (Next.js)                                     │
│                                                          │
│  /perfil ──► AccountProvider ──► apiFetch ──┐            │
│  /preferencias ──────────────────────────────┤            │
│  Navbar (avatar + menu) ─────────────────────┤            │
│                                              ▼            │
│                                     Cookie access JWT     │
└──────────────────────────────────────────────┬────────────┘
                                               │ HTTP
                                               ▼
┌──────────────────────────────────────────────────────────┐
│  Django / DRF                                            │
│                                                          │
│  GET/PUT  /api/profile/         → PerfilView             │
│  GET      /api/avatars/         → AvataresView           │
│  POST     /api/profile/change-password/ → CambiarContr.  │
│  GET/PUT  /api/preferences/     → PreferenciasView       │
│  POST     /api/account/deactivate/ → DesactivarCuenta    │
│                                                          │
│  JWTAuthentication ──► CHECK_REVOKE_TOKEN                │
│  CookieTokenRefreshSerializer ──► CSRF + hash check      │
│                                              │            │
└──────────────────────────────────────────────┼────────────┘
                                               │ SQL
                                               ▼
                                         PostgreSQL 16
                                    (tabla usuarios_usuario)
```

El frontend hace peticiones HTTP al backend de Django con tokens JWT que
viajan en cookies HttpOnly. Cada endpoint de DRF verifica la autenticacion
mediante `JWTAuthentication`, que compara el hash de contraseña contenido en
el token (`CHECK_REVOKE_TOKEN`) con el hash actual en la base de datos. Si
alguien cambio la contraseña, los tokens viejos se invalidan sin necesidad de
una tabla de revocacion.

Las cookies HttpOnly significan que JavaScript no puede leer el token
directamente. Cuando la autenticacion viaja en cookie, las mutaciones (PUT,
POST) requieren un header `X-CSRFToken` para proteger contra ataques CSRF
(Cross-Site Request Forgery, donde un sitio externo intenta hacer peticiones
usando las cookies del usuario).

---

## 2. Backend: perfil propio

### 2.1 El serializer `UsuarioPerfilSerializer`

Un serializer de DRF traduce entre el modelo de Django y el JSON que recibe o
envia la API. `UsuarioPerfilSerializer` define que campos se exponen al
frontend y cuales son de solo lectura:

```python
class UsuarioPerfilSerializer(serializers.ModelSerializer):
    tiene_contrasena_local = serializers.SerializerMethodField()
    nombre_usuario = serializers.RegexField(USERNAME_REGEX, max_length=25)

    class Meta:
        model = Usuario
        fields = (
            "pk", "correo", "nombre_usuario", "nombre", "apellido",
            "fecha_nacimiento", "genero", "avatar_id", "estado",
            "fecha_registro", "tiene_contrasena_local",
        )
        read_only_fields = (
            "pk", "correo", "fecha_nacimiento", "genero",
            "estado", "fecha_registro",
        )
```

`read_only_fields` es la lista de campos que el serializer va a ignorar
cuando llegan datos del cliente. Si alguien manda `{"correo": "otro@x.com"}`
en un PUT, el serializer lo descarta: el correo no se puede cambiar desde el
perfil.

`SerializerMethodField` es un campo que no existe en el modelo, sino que se
calcula en tiempo de lectura. `tiene_contrasena_local` llama a
`has_usable_password()` de Django para saber si la cuenta tiene una contraseña
que se pueda verificar (las cuentas creadas solo con Google tienen una
contraseña "inutilizable" que marca que no se puede usar para login local).

Los cuatro campos editables son: `nombre`, `apellido`, `nombre_usuario` y
`avatar_id`. Cada uno tiene su validacion.

### 2.2 Validacion de nombres compuestos

El CU-001 establece que nombre y apellido aceptan solo letras. Pero "Juan
Carlos" o "De la Cruz" son nombres reales que necesitan espacios entre
palabras. La solucion:

```python
# validators.py
def normalizar_nombre(valor):
    """Quita espacios sobrantes y conserva uno entre partes del nombre."""
    return " ".join(valor.split())

def validar_nombre_persona(valor):
    """Valida el nombre ya normalizado y devuelve el valor para persistir."""
    valor = normalizar_nombre(valor)
    if (
        not valor
        or len(valor) > 50
        or not all(parte.isalpha() for parte in valor.split(" "))
    ):
        raise ValidationError(
            "Solo letras y espacios entre palabras, maximo 50 caracteres."
        )
    return valor
```

`" ".join(valor.split())` hace dos cosas: `split()` sin argumentos parte la
cadena por cualquier cantidad de espacios en blanco y devuelve una lista
de las partes no vacias. Luego `" ".join()` las une con exactamente un
espacio. Asi `"  Juan   Carlos  "` se convierte en `"Juan Carlos"`.

Despues, `all(parte.isalpha() for parte in valor.split(" "))` verifica que
cada palabra contiene solo letras. Si alguien manda `"Ana2"`, la parte `"Ana2"`
no pasa `isalpha()`.

La misma funcion se reutiliza para el apellido sin duplicar codigo:

```python
def validate_apellido(self, value):
    return self.validate_nombre(value)
```

### 2.3 La vista `PerfilView`

```python
class PerfilView(GenericAPIView):
    serializer_class = UsuarioPerfilSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(self.get_serializer(request.user).data)

    def put(self, request):
        try:
            with transaction.atomic():
                usuario = bloquear_usuario(request)
                serializer = self.get_serializer(
                    usuario, data=request.data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
        except IntegrityError:
            raise NombreUsuarioOcupado() from None
        return Response(serializer.data)
```

`GenericAPIView` es la clase base de DRF que conecta un serializer con los
metodos HTTP. `permission_classes = [IsAuthenticated]` hace que cualquier
peticion sin JWT valido reciba un 401.

`partial=True` en el serializer permite actualizacion parcial: si el usuario
solo manda `{"nombre": "Jose"}`, los demas campos no se tocan.

`transaction.atomic()` abre una transaccion de base de datos. Si cualquier
cosa falla dentro del bloque, todos los cambios se revierten (rollback). Esto
evita estados inconsistentes si, por ejemplo, la validacion pasa pero la
escritura falla.

`bloquear_usuario` toma un bloqueo de fila con `select_for_update()`. Esto
es una consulta SQL que le dice a PostgreSQL "dame esta fila y no dejes que
nadie mas la modifique hasta que termine mi transaccion". Sirve para evitar
carreras: si dos peticiones intentan cambiar el username al mismo tiempo, la
segunda espera a que la primera termine y despues verifica de nuevo.

El `IntegrityError` lo atrapa el bloque externo. Si la restriccion UNIQUE
de la base de datos rechaza un username duplicado que paso la validacion del
serializer (porque otra peticion se adelanto entre la validacion y la
escritura), se devuelve un 409 Conflict con `NombreUsuarioOcupado`.

### 2.4 Unicidad de nombres de usuario

La migracion `0005` agrego un indice `UniqueConstraint` con `Lower` en
PostgreSQL:

```sql
CREATE UNIQUE INDEX ... ON usuarios_usuario (LOWER(nombre_usuario));
```

Esto significa que `"JuanPerez"` y `"juanperez"` no pueden coexistir, porque
`LOWER()` los convierte a la misma cadena. El serializer hace una
comprobacion previa con `filter(nombre_usuario__iexact=value)`, pero la
restriccion de BD es la barrera real que cubre escrituras concurrentes.

La excepcion personalizada:

```python
class NombreUsuarioOcupado(APIException):
    status_code = 409
    default_detail = {"nombre_usuario": "El nombre de usuario ya esta registrado."}
    default_code = "nombre_usuario_ocupado"
```

DRF convierte las `APIException` en respuestas HTTP automaticamente. Un
`status_code = 409` indica conflicto, distinto del 400 de validacion.

---

## 3. Backend: avatares

### 3.1 Catalogo cerrado con IDs estables

Los avatares no son subidas de archivo del usuario. Son 26 imagenes que viven
en `frontend/public/avatars/recortados/`. El script `sync_avatars.py` genera un
JSON (`avatar_catalog.json`) que asigna un ID numerico a cada archivo:

```json
[
  {"id": 1, "filename": "avatar (1).png", "active": true},
  {"id": 2, "filename": "avatar (2).png", "active": true},
  ...
]
```

Las reglas del script:

1. Si un archivo ya tiene ID en el catalogo, lo conserva.
2. Si un archivo es nuevo, intenta usar el numero del parentesis (ej: `avatar (27).png` recibe ID 27) si esta libre.
3. Si se borra un archivo del directorio, su entrada queda con `"active": false` en lugar de borrarse. Asi un usuario que eligio ese avatar conserva su referencia en la BD.

Esto resuelve un problema real: si renumeramos los IDs cada vez que se agrega
un avatar, los usuarios que ya eligieron el avatar 5 de repente verian otro
avatar.

### 3.2 Lectura en el backend

```python
# avatares.py
_catalogo = json.loads(
    Path(__file__).with_name("avatar_catalog.json").read_text(encoding="utf-8")
)
AVATARES = {
    item["id"]: {
        "id": item["id"],
        "src": f"/avatars/recortados/{quote(item['filename'])}",
    }
    for item in _catalogo
    if item.get("active", True)
}
AVATAR_IDS_VALIDOS = set(AVATARES)
```

`AVATARES` es un diccionario que se carga una sola vez cuando Django
arranca, no en cada request. `Path(__file__).with_name(...)` busca el
archivo JSON en el mismo directorio que el modulo Python. `quote()` codifica
caracteres especiales en la URL (los parentesis del nombre de archivo).

La validacion del perfil usa el mismo set:

```python
def validate_avatar_id(self, value):
    if not es_avatar_valido(value):
        raise serializers.ValidationError(
            f"avatar_id invalido. Debe ser uno de: {sorted(AVATAR_IDS_VALIDOS)}"
        )
    return value
```

El endpoint `/api/avatars/` expone la lista para que el selector del frontend
tenga las mismas opciones que acepta la validacion.

---

## 4. Backend: cambio de contraseña

### 4.1 Flujo con revocacion de sesiones

Cambiar la contraseña cierra las sesiones de todos los dispositivos. El
flujo:

```
  Usuario autenticado
        │
        ▼
  POST /api/profile/change-password/
  {old_password, password1, password2}
        │
        ▼
  transaction.atomic()
  ├─ select_for_update(pk=user.pk)    ← bloqueo de fila
  ├─ check_password(old_password)     ← verifica la actual
  ├─ validate_password(password1)     ← politica de CU-001
  ├─ set_password(password1)          ← cambia el hash
  └─ save(update_fields=["password"])
        │
        ▼
  on_commit → send_mail(notificacion)
        │
        ▼
  cerrar_sesion(request)
  ├─ logout(request)                  ← limpia sesion Django
  └─ unset_jwt_cookies(response)      ← pone max-age=0 en cookies
```

`set_password()` de Django hashea la contraseña con PBKDF2 (un algoritmo que
transforma la contraseña en un hash irreversible). Al cambiar el hash, todos
los JWT que contengan el hash viejo fallan la comprobacion
`CHECK_REVOKE_TOKEN` de SimpleJWT.

`on_commit` programa una funcion para ejecutarse despues de que la
transaccion se confirme. Si la transaccion falla y hace rollback, el correo
no se envia. Si la transaccion se confirma pero el correo falla, la
contraseña ya esta cambiada y se loguea el error sin revertir.

### 4.2 Cuentas Google sin contraseña local

Una cuenta creada con Google tiene `has_usable_password() == False`. Intentar
cambiar la contraseña con el formulario normal da un error 400 que explica que
debe usar recuperacion por correo. El frontend muestra un boton "Enviar enlace
por correo" en lugar del formulario de cambio.

```python
if not usuario.has_usable_password():
    raise serializers.ValidationError({
        "old_password": "Tu cuenta no tiene contraseña local. Podes establecerla "
                        "mediante recuperacion por correo.",
    })
```

### 4.3 Refresh seguro con CSRF

```python
# authentication.py
class RefreshSesionSerializer(CookieTokenRefreshSerializer):
    def validate(self, attrs):
        request = self.context["request"]
        if not request.data.get("refresh"):
            SessionAuthentication().enforce_csrf(request)
        token = self.extract_refresh_token()
        refresh = self.token_class(token)
        JWTAuthentication().get_user(refresh)
        return TokenRefreshSerializer.validate(self, {"refresh": token})
```

SimpleJWT verifica el hash de contraseña en el access token, pero no en el
refresh. Este serializer agrega esa comprobacion: `get_user(refresh)` busca el
claim de revocacion en el refresh y lo compara con el hash actual. Si no
coincide, lanza 401.

`enforce_csrf` se aplica solo cuando el refresh viaja en cookie (no en el
body). Si el cliente manda el refresh como campo JSON, CSRF no hace falta
porque un sitio externo no puede leer ni armar ese JSON.

---

## 5. Backend: preferencias y baja logica

### 5.1 Preferencias parciales

```python
class PreferenciasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            "tema", "perfil_publico", "notif_recomendaciones",
            "notif_resenas", "notif_novedades",
        )

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save(update_fields=list(validated_data))
        return instance
```

`update_fields` le dice a Django que solo escriba en la BD las columnas que
cambiaron, no todas. Si el usuario solo cambia el tema, el SQL es
`UPDATE ... SET tema='claro' WHERE pk=1` en lugar de reescribir todos los
campos.

El `PUT` acepta un subconjunto de campos (`partial=True` en la vista).
Cambiar el tema no toca las notificaciones.

### 5.2 Baja logica de cuenta

```python
class DesactivarCuentaView(GenericAPIView):
    def post(self, request):
        with transaction.atomic():
            usuario = bloquear_usuario(request)
            usuario.estado = EstadoCuenta.BAJA
            usuario.save(update_fields=["estado"])
            for token in OutstandingToken.objects.filter(user=usuario).iterator():
                BlacklistedToken.objects.get_or_create(token=token)
            return cerrar_sesion(
                request, "Tu cuenta fue dada de baja. Tus datos se conservan."
            )
```

"Baja logica" significa que el registro no se borra de la BD. El campo
`estado` cambia a `"baja"`, y esto bloquea el acceso:

1. `is_active` del modelo devuelve `False` cuando el estado no es `ACTIVA`.
2. `JWTAuthentication` rechaza los access tokens de usuarios inactivos.
3. Todos los refresh tokens se agregan a la blacklist (una tabla de
   `django-simplejwt` que guarda tokens revocados).
4. El login local y el login con Google rechazan cuentas en baja.

Nada se borra: listas, reseñas, calificaciones, mensajes y el perfil quedan
intactos. La decision fue no destruir contenido del usuario para cumplir con
CU-007, que pide baja con conservacion de datos.

`iterator()` en la consulta de tokens evita cargar todos los tokens en
memoria de una vez. Los procesa uno por uno, lo que importa si un usuario tuvo
muchas sesiones.

---

## 6. Migracion de datos existentes

```python
# 0006_normalizar_nombres.py
def normalizar_nombres(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    for usuario in Usuario.objects.all().iterator():
        nombre = " ".join(usuario.nombre.split())
        apellido = " ".join(usuario.apellido.split())
        if nombre != usuario.nombre or apellido != usuario.apellido:
            Usuario.objects.filter(pk=usuario.pk).update(
                nombre=nombre, apellido=apellido
            )
```

Esta migracion recorre todos los usuarios existentes y les aplica la misma
normalizacion que va a aplicar la API en adelante. Si un nombre tenia espacios
dobles (`"Juan  Carlos"`), se corrige a `"Juan Carlos"`.

La migracion usa `apps.get_model()` en lugar de importar el modelo
directamente. Esto es obligatorio en migraciones de Django: si el modelo
cambia despues (se agrega un campo, se renombra), la migracion sigue
funcionando con la version del modelo que existia en ese punto del historial.

`RunPython.noop` como segundo argumento permite que la migracion se pueda
revertir sin hacer nada (la normalizacion no tiene sentido de revertir).

---

## 7. Frontend: AccountProvider

`AccountProvider` es un contexto de React que carga los datos de la cuenta
una sola vez y los comparte con toda la aplicacion. Evita que cada pagina haga
sus propias peticiones a `/api/profile/` y `/api/preferences/`.

```
AccountProvider (contexto global)
   ├── perfil: {pk, nombre, apellido, nombre_usuario, correo, ...}
   ├── avatares: [{id, src}, ...]
   ├── preferencias: {tema, perfil_publico, notif_*, ...}
   ├── cargando, error
   ├── actualizarPerfil(perfil)
   ├── actualizarPreferencia(campo, valor)
   ├── recargar()
   └── limpiar()
```

### 7.1 Carga y redireccion

```tsx
useEffect(() => {
  if (["/login", "/register", "/completar-google"].includes(pathname)) {
    setCargando(false);
    return;
  }
  void recargar();
}, [pathname, recargar]);
```

`useEffect` con `pathname` como dependencia ejecuta la recarga cada vez que
la ruta cambia. En las paginas publicas de login y registro no intenta cargar
el perfil porque el usuario todavia no esta autenticado.

Si la peticion falla con 401, el provider redirige a `/login` solo si la
ruta actual requiere sesion (`/perfil`, `/preferencias`, `/mis-resenas`).

### 7.2 Actualizacion optimista del tema

```tsx
async function actualizarPreferencia<K extends keyof Preferencias>(
  campo: K, valor: Preferencias[K]
) {
  const anterior = preferencias;
  const optimista = { ...anterior, [campo]: valor };
  setPreferencias(optimista);
  if (campo === "tema") aplicarTema(valor as Preferencias["tema"]);
  try {
    const confirmada = await apiFetch<Preferencias>("/api/preferences/", {
      method: "PUT", body: { [campo]: valor },
    });
    setPreferencias(confirmada);
    aplicarTema(confirmada.tema);
  } catch {
    setPreferencias(anterior);
    aplicarTema(anterior.tema);
    throw err;
  }
}
```

"Optimista" significa que la UI cambia inmediatamente sin esperar la
respuesta del servidor. El tema se aplica al instante para que el usuario vea
el cambio. Si el servidor falla, se revierte al estado anterior.

`aplicarTema` modifica la clase CSS del documento:

```tsx
function aplicarTema(tema: Preferencias["tema"]) {
  document.documentElement.classList.toggle("dark", tema === "oscuro");
  document.documentElement.style.colorScheme = tema === "oscuro" ? "dark" : "light";
}
```

Tailwind CSS usa la clase `dark` en el elemento `<html>` para activar los
colores oscuros. `colorScheme` le dice al navegador que los controles nativos
(scrollbars, selects) tambien usen el tema correspondiente.

---

## 8. Frontend: pagina de perfil

La pagina `/perfil` tiene dos modos: lectura y edicion. El estado `editando`
controla cual se muestra.

### 8.1 Formulario con borrador

```tsx
type Borrador = Pick<Perfil, "nombre" | "apellido" | "nombre_usuario" | "avatar_id">;

function iniciarEdicion() {
  setBorrador({
    nombre: perfil.nombre,
    apellido: perfil.apellido,
    nombre_usuario: perfil.nombre_usuario,
    avatar_id: perfil.avatar_id,
  });
  setErrores({});
  setEditando(true);
}
```

`Pick<Perfil, ...>` es un tipo de TypeScript que extrae solo las propiedades
indicadas de otro tipo. El borrador contiene una copia de los campos
editables, separada del perfil original. Asi el usuario puede escribir
cambios sin afectar lo que se muestra en el resto de la UI hasta que confirme.

### 8.2 Normalizacion en frontend

```tsx
// validation.ts
const NOMBRE_REGEX = /^\p{L}+(?: \p{L}+)*$/u;

export function normalizarNombre(valor: string): string {
  return valor.trim().replace(/\s+/g, " ");
}

export function validarNombre(valor: string): string | null {
  const v = normalizarNombre(valor);
  if (!v) return "Campo obligatorio.";
  if (v.length > 50) return "Maximo 50 caracteres.";
  if (!NOMBRE_REGEX.test(v)) return "Solo letras y espacios entre palabras.";
  return null;
}
```

`\p{L}` es una clase de caracteres Unicode que acepta cualquier letra de
cualquier idioma (español, frances, arabe, etc.). La flag `u` activa el modo
Unicode del regex. Asi "Jose" y "Jose" y "Müller" son todos validos.

La normalizacion es la misma que en el backend: quitar espacios de los
extremos y comprimir multiples espacios en uno solo. Se aplica en el `onBlur`
de los inputs para que el usuario vea el resultado normalizado al salir del
campo.

### 8.3 Verificacion debounced de username

```tsx
useEffect(() => {
  // Solo verificar si el username cambio respecto al original
  if (borrador.nombre_usuario === perfil.nombre_usuario || validarNombreUsuario(borrador.nombre_usuario)) {
    setDisponibilidad("idle");
    return;
  }
  setDisponibilidad("checking");
  const controller = new AbortController();
  const timer = setTimeout(async () => {
    const res = await fetch(
      apiUrl(`/api/auth/username-available/?username=${encodeURIComponent(borrador.nombre_usuario)}`),
      { signal: controller.signal }
    );
    const data = await res.json();
    setDisponibilidad(data.disponible ? "available" : "taken");
  }, 400);
  return () => { clearTimeout(timer); controller.abort(); };
}, [borrador?.nombre_usuario, editando, perfil, borrador]);
```

"Debounced" significa que la verificacion no se dispara con cada tecla, sino
400ms despues de que el usuario deja de escribir. `setTimeout` programa la
peticion y la funcion de limpieza del `useEffect` (el `return`) la cancela si
el usuario sigue escribiendo.

`AbortController` cancela la peticion HTTP si el componente se desmonta o el
efecto se re-ejecuta. Sin esto, una respuesta tardia podria actualizar un
componente que ya no existe.

### 8.4 Advertencia de cambios sin guardar

```tsx
useEffect(() => {
  // Solo si hay cambios pendientes
  function avisarSalida(event: BeforeUnloadEvent) {
    event.preventDefault();
  }
  function avisarEnlace(event: MouseEvent) {
    const enlace = (event.target as Element).closest("a[href]");
    if (!enlace || window.confirm("¿Descartar los cambios del perfil?")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  function avisarHistorial() {
    if (!window.confirm("¿Descartar los cambios del perfil?")) window.history.forward();
  }
  window.addEventListener("beforeunload", avisarSalida);
  document.addEventListener("click", avisarEnlace, true);
  window.addEventListener("popstate", avisarHistorial);
  return () => { /* remover listeners */ };
}, [editando, borrador, perfil]);
```

Se cubren tres caminos de salida:

1. `beforeunload`: cerrar la pestaña o recargar la pagina. El navegador
   muestra un dialogo generico.
2. Click en un enlace: se intercepta con `closest("a[href]")` en fase de
   captura (`true` en `addEventListener`) antes de que el navegador navegue.
3. Boton "atras" del navegador: `popstate` se dispara cuando el historial
   cambia. Si el usuario cancela, `history.forward()` lo devuelve a la pagina
   actual.

### 8.5 Selector de avatares

```tsx
<fieldset className="mt-4">
  <legend className="mb-2 text-sm font-medium">Elegi un avatar</legend>
  <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
    {avatares.map((avatar) => (
      <label key={avatar.id} className="...">
        <input
          type="radio"
          name="avatar_id"
          value={avatar.id}
          checked={borrador.avatar_id === avatar.id}
          onChange={() => setBorrador({ ...borrador, avatar_id: avatar.id })}
          className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
          aria-label={`Avatar ${avatar.id}`}
        />
        <Image src={avatar.src} alt="" width={72} height={72} />
      </label>
    ))}
  </div>
</fieldset>
```

Los 26 avatares se muestran como radio buttons HTML nativos con
`opacity-0`. El input invisible cubre toda el area del avatar con `absolute
inset-0`, asi el usuario puede hacer click en cualquier parte de la imagen.
La label marcada con `has-[:checked]:bg-primary/20` recibe un fondo de color
cuando esta seleccionada, usando un selector de Tailwind que se activa cuando
el hijo tiene el estado `:checked`.

Cada avatar tiene un `aria-label` para accesibilidad: los lectores de
pantalla anuncian "Avatar 1", "Avatar 2", etc.

---

## 9. Frontend: pagina de preferencias

### 9.1 Estructura de la pagina

La pagina esta dividida en cuatro secciones:

1. Apariencia: selector de tema oscuro/claro con radio buttons.
2. Privacidad: checkbox de perfil publico.
3. Notificaciones: checkboxes de recomendaciones, reseñas y novedades.
4. Cuenta: boton de baja con modal de confirmacion.

Las secciones de privacidad y notificaciones muestran un aviso:

```tsx
<p role="note">
  Estas preferencias se guardan, pero todavia no cambian la visibilidad de
  reseñas o listas ni activan correos.
</p>
```

Esto es intencional: los controles se persisten en la BD para que el usuario
pueda configurarlos, pero la logica de fondo (ocultar perfil, enviar emails)
todavia no esta implementada. Cuando se implemente, los valores ya estaran
guardados.

### 9.2 Modal de baja con focus trap

```tsx
// dialog-focus.ts
export function mantenerFocoEnDialogo(event: KeyboardEvent, dialogo: HTMLElement | null) {
  if (event.key !== "Tab" || !dialogo) return;
  const controles = Array.from(
    dialogo.querySelectorAll<HTMLElement>(
      "a[href], button:not([disabled]), input:not([disabled]), ..."
    )
  );
  if (!controles.length) return;
  const primero = controles[0];
  const ultimo = controles[controles.length - 1];
  if (event.shiftKey && document.activeElement === primero) {
    event.preventDefault();
    ultimo.focus();
  } else if (!event.shiftKey && document.activeElement === ultimo) {
    event.preventDefault();
    primero.focus();
  }
}
```

Un focus trap asegura que al presionar Tab dentro de un dialogo modal, el foco
no se escape a los elementos de atras. Cuando el foco llega al ultimo boton
y se presiona Tab, vuelve al primero. Con Shift+Tab desde el primero, va al
ultimo. Esto es un requisito de accesibilidad WCAG 2.1 para dialogos modales.

El modal tambien se cierra con Escape (salvo durante el proceso de baja) y
enfoca el boton "Cancelar" al abrirse para que un usuario de teclado pueda
interactuar inmediatamente.

---

## 10. Frontend: componente Avatar

```tsx
export function Avatar({ perfil, avatares, size = 40 }) {
  const [srcFallida, setSrcFallida] = useState<string | null>(null);
  const avatar = avatares.find((item) => item.id === perfil.avatar_id);
  const iniciales = `${perfil.nombre.charAt(0)}${perfil.apellido.charAt(0)}`.toUpperCase();

  if (!avatar || srcFallida === avatar.src) {
    return (
      <span aria-label={`Avatar de ${perfil.nombre} ${perfil.apellido}`}>
        {iniciales}
      </span>
    );
  }

  return (
    <Image
      src={avatar.src}
      alt={`Avatar de ${perfil.nombre} ${perfil.apellido}`}
      width={size}
      height={size}
      onError={() => setSrcFallida(avatar.src)}
    />
  );
}
```

El componente tiene un fallback de dos niveles: primero intenta cargar la
imagen del avatar. Si la carga falla (`onError`), muestra las iniciales del
usuario en un circulo coloreado. Esto cubre el caso donde el archivo de imagen
falta o esta corrupto sin romper la UI.

`onError` solo se guarda una vez por src, evitando un bucle infinito si la
imagen falla repetidamente.

---

## 11. Tests del backend

Los tests estan en `test_perfil.py` y cubren tres areas. Lo que verifica cada
test:

### PerfilTests

| Test | Que verifica |
|------|-------------|
| `test_get_requiere_sesion_y_devuelve_solo_perfil_propio` | Un request anonimo recibe 401. Pasar el PK de otro usuario no devuelve sus datos. No se filtran campos sensibles (password, is_staff). |
| `test_put_parcial_actualiza_los_cuatro_campos_editables` | Cada campo editable se puede cambiar individualmente sin afectar los demas. |
| `test_nombres_compuestos_se_normalizan_sin_perder_espacios_intermedios` | `"  Juan   Carlos  "` se normaliza a `"Juan Carlos"` tanto en la BD como en la respuesta. |
| `test_catalogo_expone_todos_los_avatares_y_rechaza_ids_ajenos` | El endpoint de avatares expone 26 opciones con IDs del 1 al 26 y rutas que empiezan con `/avatars/recortados/`. El avatar 27 se rechaza con 400. |
| `test_campos_manipulados_no_modifican_identidad_permisos_ni_preferencias` | Enviar campos como `pk`, `correo`, `password`, `estado`, `is_staff`, `is_superuser`, `groups`, `tema` no cambia nada en la BD. |
| `test_validaciones_no_dejan_guardado_parcial` | Si un campo falla la validacion, ningun campo se guarda (atomicidad). |
| `test_username_duplicado_409_y_mismo_usuario_permitido` | Un username ocupado (sin importar mayusculas) devuelve 409. Reenviar el propio username funciona. |
| `test_unicidad_en_bd_cubre_escrituras_concurrentes` | La restriccion de PostgreSQL rechaza inserciones que pasarian la validacion del serializer. |
| `test_error_integridad_devuelve_conflicto_sin_guardar` | Si `IntegrityError` ocurre despues de la validacion, se devuelve 409 y se revierten los cambios. |
| `test_cookie_exige_csrf_y_header_bearer_no` | Un PUT con cookie sin CSRF recibe 403. Con header Bearer no hace falta CSRF. |

### ContrasenaTests

| Test | Que verifica |
|------|-------------|
| `test_cambio_requiere_sesion` | Un request anonimo recibe 401. |
| `test_errores_no_cambian_contrasena_ni_revocan_sesion` | Contraseña actual incorrecta, confirmacion distinta, y cada regla de politica (largo, mayuscula, minuscula, digito, especial) devuelven 400 sin cambiar el hash ni invalidar la sesion. |
| `test_cambio_revoca_todos_los_dispositivos_y_notifica_sin_login` | Despues del cambio, los JWT de todos los dispositivos fallan (access y refresh). Las cookies se limpian. Se envia email. Se puede hacer login con la nueva contraseña. |
| `test_tokens_sin_claim_previo_al_despliegue_se_rechazan` | Tokens JWT emitidos antes de activar `CHECK_REVOKE_TOKEN` reciben 401. |
| `test_refresh_valido_rota_y_cookie_exige_csrf` | Renovar un token por cookie exige CSRF. El refresh viejo se invalida (rotacion). |
| `test_google_sin_password_indica_recuperacion` | Una cuenta sin contraseña local recibe 400 con mensaje de recuperacion por correo. |
| `test_fallo_persistencia_no_cambia_password_ni_notifica` | Si `save()` falla, el hash original se mantiene, no se envia email y la sesion sigue activa. |
| `test_fallo_notificacion_no_revierte_password` | Si el email falla despues del commit, la contraseña ya esta cambiada (no se revierte). |

### RecuperacionSesionTests

| Test | Que verifica |
|------|-------------|
| `test_recuperacion_revoca_access_refresh_y_token_reutilizado` | Restablecer consume el enlace (segundo uso da 400), revoca todos los JWT y envia notificacion. |
| `test_enlace_vencido_y_confirmaciones_distintas_no_cambian_password` | Un enlace de mas de 1 hora y contraseñas distintas no cambian el hash. |
| `test_dos_validaciones_previas_no_permiten_dos_consumos` | Dos serializers que validan el mismo token: el segundo falla al guardar por el bloqueo de fila. |
| `test_enlace_emitido_antes_de_baja_o_pendiente_se_rechaza` | Un enlace previo a la baja no reactiva la cuenta. |
| `test_google_agrega_password_por_email_sin_perder_vinculo` | Restablecer contraseña en cuenta Google conserva el PK, el vinculo social y permite login con ambos metodos. |

---

## 12. Tests E2E con Playwright

### 12.1 Configuracion

Playwright abre un navegador real y simula interacciones del usuario. La
configuracion en `playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://127.0.0.1:3100",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- -p 3100",
    url: "http://127.0.0.1:3100",
    env: {
      NEXT_DIST_DIR: ".next-e2e",
    },
  },
});
```

`NEXT_DIST_DIR: ".next-e2e"` hace que Playwright use su propia carpeta de
compilacion, separada de la carpeta `.next` que usa `next dev` en
desarrollo. Sin esto, si corres Playwright mientras estas desarrollando, la
compilacion de Playwright sobreescribe los archivos de `.next` y el
servidor de desarrollo se cuelga porque le faltan los manifests.

### 12.2 Helper de cuenta simulada

```typescript
// cuenta.ts
export async function prepararCuenta(page: Page) {
  let perfil = { ...initialProfile };
  let preferencias = { tema: "oscuro", perfil_publico: true, ... };

  // Simular cookies de sesion
  await page.context().addCookies([
    { name: "access", value: "test-session", url: "http://127.0.0.1:3100" },
    { name: "csrftoken", value: "test-csrf", url: "http://127.0.0.1:3100" },
  ]);

  // Interceptar llamadas a la API y devolver datos simulados
  await page.route("**/api/profile/", async (route) => {
    if (route.request().method() === "PUT")
      perfil = { ...perfil, ...route.request().postDataJSON() };
    await route.fulfill({ json: perfil });
  });
  // ... igual para /api/avatars/, /api/preferences/, /api/auth/username-available/
  return { getPerfil: () => perfil, getPreferencias: () => preferencias };
}
```

`page.route()` intercepta las peticiones HTTP del navegador antes de que
salgan a la red y las responde con datos fijos. Esto permite probar el
frontend sin necesitar el backend corriendo. Los datos simulados se actualizan
cuando el test hace un PUT, asi las verificaciones posteriores reflejan el
cambio.

### 12.3 Lo que prueban los tests

| Test | Que verifica |
|------|-------------|
| `perfil.spec.ts` test 1 | Editar nombre compuesto con espacios extras (`"  Juan   Carlos  "` a `"Juan Carlos"`), seleccionar avatar 26 de 26, guardar y verificar que la navbar refleja el nuevo avatar y nombre. |
| `perfil.spec.ts` test 2 | Escribir un apellido invalido (`"123"`), verificar que el foco va al campo con error y que se muestra el mensaje de error. Intentar navegar con cambios sin guardar muestra un dialogo de confirmacion. |
| `preferencias.spec.ts` | Cambiar el tema a "Claro", verificar que `<html>` ya no tiene la clase `dark`, verificar que la preferencia se guardo en el backend simulado, y tras recargar la pagina, verificar que el radio "Claro" sigue seleccionado. |
| `cuenta.spec.ts` | Navegar por el menu de usuario con teclado y verificar que `/mis-resenas` muestra el aviso de seccion pendiente. |

---

## 13. Tareas pendientes del modulo

El Modulo 4 esta completo salvo por una pieza:

- P-06 (`/mis-resenas`): es un placeholder que muestra "Esta seccion todavia
  no esta implementada". Depende del Modulo 2 tarea C-08 (calificar y
  reseñar), que todavia no se implemento. Cuando C-08 exista, P-06 podra
  listar las reseñas del usuario.

Los switches de privacidad y notificaciones se guardan pero no tienen efecto
todavia. La logica de fondo (ocultar perfil publico, enviar emails) se
implementara cuando se desarrollen los modulos correspondientes.
