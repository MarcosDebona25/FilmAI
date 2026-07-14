**SEMINARIO INTEGRADOR**

| PLANTILLA 02: ESPECIFICACIÃ“N DE REQUERIMIENTOS |
| :---- |

| Fecha de PresentaciÃ³n |
| :---: |
| 19/10/2025 |

| Integrantes del equipo de trabajo |
| :---- |
| Debona, Marcos. |
| GaitÃ¡n, Gonzalo. |

| 1\. DescripciÃ³n del Alcance del Problema |
| :---- |
| Se trata de una aplicaciÃ³n web centrada en el Ã¡mbito del entretenimiento audiovisual, mÃ¡s especÃ­ficamente en pelÃ­culas y series, que permite a los usuarios descubrir, organizar y opinar sobre pelÃ­culas y series. Cada usuario puede crear una cuenta personal, acceder a un catÃ¡logo actualizado sincronizado con The Movie Database (TMDB), calificar y reseÃ±ar contenidos, y gestionar sus propias listas de favoritos, pendientes, vistas y posibles listas personalizadas. AdemÃ¡s, el sistema incorpora un chatbot con inteligencia artificial que genera recomendaciones personalizadas a partir del historial, las calificaciones y las reseÃ±as del usuario, utilizando un modelo de lenguaje externo al que se le proporcionan datos sensibles de forma anonimizada. TambiÃ©n, incluye gestiÃ³n de usuarios y moderaciÃ³n de reseÃ±as. Desde el punto de vista tÃ©cnico, se garantiza el cifrado de la informaciÃ³n, la validaciÃ³n constante de sesiones y la compatibilidad con navegadores de escritorio y mÃ³viles. El diseÃ±o prioriza tiempos de respuesta bajos tanto en la navegaciÃ³n general como en las consultas procesadas por el chatbot. |

| 2\. Requerimientos Funcionales |
| :---- |
| El sistema deberÃ¡ permitir a los usuarios crear cuentas con credenciales vÃ¡lidas de email, nombre y apellido, fecha de nacimiento, gÃ©nero, nombre de usuario y contraseÃ±a. El sistema deberÃ¡ permitir a los usuarios modificar la informaciÃ³n de su perfil personal incluyendo contraseÃ±a, nombre de usuario, nombre y apellido, y mostrar la informaciÃ³n actualizada en el momento. El sistema deberÃ¡ permitir a los usuarios dar de baja sus cuentas. El sistema deberÃ¡ permitir a los usuarios autenticarse y acceder a sus cuentas usando credenciales vÃ¡lidas. El sistema deberÃ¡ permitir a los usuarios visualizar la informaciÃ³n completa de su perfil y detalles de cuenta. El sistema deberÃ¡ permitir a los usuarios calificar una serie/pelÃ­cula con la opciÃ³n de aÃ±adir una reseÃ±a. El sistema deberÃ¡ permitir a los usuarios modificar el contenido (texto y/o calificaciÃ³n) de sus propias reseÃ±as. El sistema deberÃ¡ permitir a los usuarios eliminar permanentemente sus propias reseÃ±as y/o calificaciones. El sistema deberÃ¡ permitir la navegaciÃ³n entre secciones (Inicio, PelÃ­culas, Series, Listas, Perfil) mediante la barra de navegaciÃ³n. El sistema deberÃ¡ exponer el catÃ¡logo de pelÃ­culas y series actualizado desde la fuente externa integrada (The Movie Database). El sistema deberÃ¡ registrar y almacenar, por usuario, el historial de visualizaciones, calificaciones y reseÃ±as. El sistema deberÃ¡ aplicar control de acceso por roles (usuario, administrador) para las operaciones protegidas. El sistema deberÃ¡ validar que las calificaciones estÃ©n en el rango permitido (1-10). El sistema deberÃ¡ permitir a los usuarios buscar pelÃ­culas y series por nombre. El sistema deberÃ¡ tener listas predeterminadas para favoritos, pendientes y visto. El sistema deberÃ¡ permitir al usuario eliminar pelÃ­culas o series de cualquiera de sus listas (predeterminadas o personalizadas). El sistema deberÃ¡ proporcionar un chatbot accesible desde la pÃ¡gina de inicio para las consultas de usuarios. Mientras el usuario estÃ© autenticado, el sistema deberÃ¡ permitir acciones de gestiÃ³n de perfil, creaciÃ³n/modificaciÃ³n de listas, y gestiÃ³n de reseÃ±as. Mientras el chatbot estÃ© procesando una solicitud de recomendaciÃ³n, el sistema deberÃ¡ mostrar un indicador de progreso y permitir la cancelaciÃ³n de la peticiÃ³n.. Si el usuario intenta publicar o modificar una reseÃ±a sin calificar (o quitando la calificaciÃ³n existente) o con contenido invÃ¡lido, entonces el sistema deberÃ¡ denegar la publicaciÃ³n o modificaciÃ³n. Si el usuario ingresa credenciales incorrectas para el inicio de sesiÃ³n, entonces el sistema deberÃ¡ notificar el error. Cuando el usuario realice una consulta mediante el chatbot, el sistema deberÃ¡ procesar la consulta y devolver una respuesta basada en el historial del usuario, sus reseÃ±as y el dominio almacenado. Cuando el usuario cree o modifique listas personales, el sistema deberÃ¡ actualizar y mostrar dichas listas en la secciÃ³n de Listas. Cuando el usuario marque una pelÃ­cula/serie como vista, el sistema deberÃ¡ registrarla en su historial. Cuando el usuario busque pelÃ­culas/series por nombre, el sistema deberÃ¡ devolver los resultados coicidentes con paginaciÃ³n y, si no hay coincidencias mostrar el resultado vacÃ­o con un aviso. Cuando el usuario publique o modifique una reseÃ±a, el sistema deberÃ¡ almacenar la reseÃ±a y actualizar las reseÃ±as recientes mostradas en su perfil. Cuando el usuario elimine una reseÃ±a, esta deberÃ¡ ser eliminada de las vistas de su perfil. Cuando el usuario cree su cuenta, el sistema deberÃ¡ mandar un correo de confirmaciÃ³n.  |

| 3\. Requerimientos No Funcionales |
| :---- |
| **3.1 RNF \#1:**  |
| El sistema deberÃ¡ ser accesible desde dispositivos de escritorio y mÃ³viles mediante diseÃ±o reponsive. |
| **3.2 RNF \#2** |
| El sistema deberÃ¡ almacenar las contraseÃ±as hasheadas con bcrypt y cifrar los datos sensibles en reposo (a nivel de base de datos). |
| **3.3 RNF \#3** |
| Cuando el chatbot solicite acceso a un modelo LLM externo, el sistema deberÃ¡ anonimizar datos sensibles antes de enviarlos al proveedor del modelo. |
| **3.4 RNF \#4** |
| El sistema deberÃ¡ responder a solicitudes de navegaciÃ³n y bÃºsqueda en menos de 2 segundos para el 90% de las peticiones en condiciones normales de carga. |
| **3.5 RNF \#5** |
| El sistema deberÃ¡ invalidar automÃ¡ticamente la sesiÃ³n del usuario despuÃ©s de 8 horas de inactividad por motivos de seguridad. |
| **3.6 RNF \#6** |
| El sistema deberÃ¡ entregar respuestas del chatbot en menos de 5 segundos para interacciones simples y en menos de 15 segundos para consultas que requieren agregaciÃ³n adicional. |
| **3.7 RNF \#7** |
| Las operaciones de sincronizaciÃ³n con la API externa deberÃ¡n realizarse sin afectar la experiencia del usuario. |
| **3.8 RNF \#8** |
| Las consultas a la API externa deberÃ¡n optimizarse respetando sus lÃ­mites de uso y reutilizando resultados almacenados en cachÃ© para evitar llamadas innecesarias. |
| **3.9 RNF \#9** |
| El sistema deberÃ¡ procesar grandes volÃºmenes de datos de pelÃ­culas y series sin exceder 3 segundos de tiempo de respuesta para consultas de bÃºsqueda. |
| **3.10 RNF \#10** |
| El sistema deberÃ¡ responder a las solicitudes de usuario dentro de 2 segundos bajo condiciones normales de operaciÃ³n. |
| **3.11 RNF \#11** |
| El sistema deberÃ¡ validar tokens de sesiÃ³n de usuario y mantener autenticaciÃ³n segura durante todas las interacciones del usuario. |
| **3.12 RNF \#12** |
| El sistema deberÃ¡ hashear contraseÃ±as con bcrypt y encriptar todos los datos sensibles del usuario incluyendo correos electrÃ³nicos. |
| **3.13 RNF \#13** |
| El sistema deberÃ¡ implementar protecciÃ³n contra vulnerabilidades web comunes (inyecciÃ³n SQL, XSS, CSRF). |
| **3.14 RNF \#14** |
| El sistema deberÃ¡ soportar integraciÃ³n con bases de datos externas de pelÃ­culas a travÃ©s de APIs. |
| **3.15 RNF \#15** |
| El sistema deberÃ¡ ser compatible con navegadores web incluyendo Chrome, Firefox, Safari y Edge. |
| **3.16 RNF \#16** |
| El sistema deberÃ¡ funcionar apropiadamente en navegadores mÃ³viles iOS y Android. |

| 4\. Diagrama de Casos de Uso |
| :---- |
| **Nota:** El diagrama de casos de uso debe regenerarse desde el archivo `03_DiagramaClases_DiagramaTablas.json` para reflejar los cambios acordados. |

| 4\. Fichas de Casos de Uso |
| :---- |
|  |

| ID | CU-001 |
| :---- | :---- |
| **Nombre** | Crear cuenta de usuario. |
| **Breve DescripciÃ³n** | Permite al usuario registrarse en el sistema mediante la creaciÃ³n de una cuenta. Incluye el envÃ­o de un correo electrÃ³nico de confirmaciÃ³n para activar la cuenta. |
| **Prioridad** | Alta. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario no debe tener una cuenta registrada previamente con el mismo correo electrÃ³nico. |
| **Postcondiciones** | **Ã‰xito:**  La cuenta del usuario se registra y queda activa luego de la confirmaciÃ³n del correo. Los datos crÃ­ticos del usuario se almacenan cifrados en la base de datos. |
|  | **Fracaso:** El registro no se completa y la cuenta no se crea si los datos ingresados son invÃ¡lidos, incompletos o el correo ya estÃ¡ registrado. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario selecciona la opciÃ³n â€œCrear cuentaâ€ desde la pÃ¡gina principal. | \- |
| 2\. El sistema presenta la pantalla de registro de usuario solicitando: Nombre. Apellido. Nombre de usuario. Correo electrÃ³nico. Fecha de nacimiento. GÃ©nero. ContraseÃ±a. Confirmar contraseÃ±a. | \- |
| 3\. El usuario completa los campos requeridos y presiona â€œAceptarâ€. | 3.A. El usuario cancela la operaciÃ³n. 3.A.1 El sistema solicita confirmaciÃ³n de cancelaciÃ³n. 3.A.2 Si el usuario confirma, el caso de uso termina. 3.A.3 Si no confirma, se retorna al paso 2 del flujo principal. |
| 4\. El sistema valida la informaciÃ³n ingresada. | 4.A. Ya existe un usuario con el mismo correo electrÃ³nico o nombre de usuario. 4.A.1 El sistema informa la situaciÃ³n. 4.A.2 Se retorna al paso 2\. 4.B. La contraseÃ±a y su confirmaciÃ³n no coinciden. 4.B.1 El sistema informa la situaciÃ³n. 4.B.2 Se retorna al paso 2\. 4.C. El formato del correo es invÃ¡lido. 4.C.1 El sistema informa la situaciÃ³n. 4.C.2 Se retorna al paso 2\. 4.D. Alguno de los campos obligatorios no fue completado o tiene un formato incorrecto. 4.D.1 El sistema muestra un mensaje indicando los campos faltantes o errÃ³neos. 4.D.2 Se retorna al paso 2\. |
| 5\. Si los datos son vÃ¡lidos, el sistema registra la nueva cuenta con estado â€œpendiente de verificaciÃ³nâ€. | \- |
| 6\. include(CU-002): envÃ­a el correo de confirmaciÃ³n y gestiona la activaciÃ³n de la cuenta. | 6.A. El envÃ­o del correo falla. 6.A.1 El sistema muestra un mensaje de error e informa que el intento puede repetirse mÃ¡s tarde. El caso de uso termina. |
| 7\. Dentro del correo, el usuario accede al enlace de confirmaciÃ³n recibido y presiona â€œVerificar cuentaâ€. | \- |
| 8\. El sistema activa la cuenta y muestra un mensaje de confirmaciÃ³n exitosa. | \- |
| 9\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | El usuario puede cancelar la operaciÃ³n en cualquier momento presionando el botÃ³n â€œCancelarâ€. En ese caso, el sistema solicita confirmaciÃ³n. Si la respuesta es afirmativa, muestra â€œOperaciÃ³n canceladaâ€, el usuario presiona â€œAceptarâ€ y el caso de uso finaliza. Si no, la operaciÃ³n continÃºa. |
| **Observaciones** | Todos los campos solicitados en el formulario son obligatorios. La contraseÃ±a se almacena hasheada con bcrypt en la BD. El correo se almacena cifrado. La cuenta no podrÃ¡ utilizarse hasta completar la confirmaciÃ³n del correo electrÃ³nico. Los estados posibles de la cuenta son: pendiente de confirmaciÃ³n, activa y baja.  Restricciones de campos: Nombre/Apellido: sÃ³lo letras, mÃ¡ximo 50 caracteres. Correo electrÃ³nico: formato vÃ¡lido usuario@dominio.com. Nombre de usuario: alfanumÃ©rico, 5â€“25 caracteres, Ãºnico. ContraseÃ±a: 8-20 caracteres, debe contener al menos una mayÃºscula, una minÃºscula, un dÃ­gito y un carÃ¡cter especial (@\#$%&\*). Fecha de nacimiento debe seguir el formato dd/mm/aaaa. No puede ser una fecha futura y el usuario debe tener al menos 13 aÃ±os de edad. |

| ID | CU-002 |
| :---- | :---- |
| **Nombre** | Confirmar cuenta por correo electrÃ³nico. |
| **Breve DescripciÃ³n** | Proceso de verificaciÃ³n y activaciÃ³n de la cuenta del usuario a travÃ©s un enlace enviado a su correo electrÃ³nico. |
| **Prioridad** | Baja. |
| **Complejidad** | Media. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario realizÃ³ el registro de su cuenta a travÃ©s del formulario y el sistema enviÃ³ el correo de confirmaciÃ³n. |
| **Postcondiciones** | **Ã‰xito:** La cuenta del usuario se activa y el estado en la base de datos cambia de "pendiente de verificaciÃ³n" a "activa". |
|  | **Fracaso:** La cuenta permanece en estado "pendiente de verificaciÃ³n". |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario accede a su bandeja de correo electrÃ³nico.  | \- |
| 2\. El usuario hace clic en el enlace de confirmaciÃ³n incluido en el correo. | \- |
| 3\. El sistema valida la confirmaciÃ³n. | \- |
| 4\. El sistema activa la cuenta del usuario. | \- |
| 5\. El sistema muestra un mensaje de confirmaciÃ³n exitosa. | \- |
| 6\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | La confirmaciÃ³n consiste en acceder al enlace (no se emplean cÃ³digos) y a partir de ese momento el estado de la cuenta cambia a â€œactivaâ€. La cuenta no es accesible hasta que se complete la confirmaciÃ³n. El enlace de confirmaciÃ³n es permanente, no tiene vencimiento. |

| ID | CU-003 |
| :---- | :---- |
| **Nombre** | Iniciar sesiÃ³n. |
| **Breve DescripciÃ³n** | Permite al usuario autenticarse y obtener acceso a las funcionalidades de la plataforma. |
| **Prioridad** | Alta. |
| **Complejidad** | Media. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe tener una cuenta registrada y activa. |
| **Postcondiciones** | **Ã‰xito:** El usuario queda autenticado, se inicia una sesiÃ³n vÃ¡lida y se accede a las funcionalidades protegidas. |
|  | **Fracaso:** El usuario permanece en la pantalla de inicio de sesiÃ³n y el sistema notifica el error de autenticaciÃ³n. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario selecciona la opciÃ³n â€œIniciar sesiÃ³nâ€. | \- |
| 2\. El sistema presenta la pantalla de inicio de sesiÃ³n solicitando: Nombre de usuario o correo. ContraseÃ±a. | \- |
| 3\. El usuario ingresa sus credenciales y presiona â€œIniciar sesiÃ³nâ€ | \- |
| 4\. El sistema valida la informaciÃ³n ingresada. | 4.A. El usuario ingresa credenciales incorrectas.  4.A.1. El sistema notifica el error de credenciales incorrectas.  4.A.2.El sistema retorna al paso 2\. |
| 5\. El sistema autentica al usuario. | \- |
| 6\. El sistema redirige al usuario a la pÃ¡gina de inicio. | \- |
| 7\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | El tipeo de la contraseÃ±a deberÃ¡ mostrarse predeterminadamente con \*, dÃ¡ndole la opciÃ³n al usuario de cambiar esto. La sesiÃ³n del usuario tiene una duraciÃ³n de 8 horas. |

| ID | CU-004 |
| :---- | :---- |
| **Nombre** | Cerrar sesiÃ³n. |
| **Breve DescripciÃ³n** | Termina la sesiÃ³n activa del usuario quitÃ¡ndole el acceso a las operaciones del sistema. |
| **Prioridad** | Media. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado y tener una sesiÃ³n activa. |
| **Postcondiciones** | **Ã‰xito:** La sesiÃ³n del usuario finaliza. |
|  | **Fracaso:** La sesiÃ³n no se cierra y el usuario permanece autenticado. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario autenticado selecciona la opciÃ³n â€œCerrar sesiÃ³nâ€. | \- |
| 2\. El sistema pregunta al usuario: â€œÂ¿EstÃ¡ seguro que desea cerrar sesiÃ³n?â€. | \- |
| 3\. El usuario confirma la acciÃ³n y el sistema finaliza la sesiÃ³n activa del usuario. | 3.A El usuario cancela la acciÃ³n 3.A.1 Su sesiÃ³n continÃºa activa. 3.A.2 El caso de uso termina. |
| 4\. El sistema redirige al usuario a la pÃ¡gina de inicio. | \- |
| 5\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | El sistema debe validar la finalizaciÃ³n segura del token de sesiÃ³n.  DespuÃ©s de cerrar sesiÃ³n, las secciones de Inicio, PelÃ­culas, Series, Listas y Perfil serÃ¡n inaccesibles hasta que el usuario inicie sesiÃ³n nuevamente. |

| ID | CU-005 |
| :---- | :---- |
| **Nombre** | Acceder a la secciÃ³n de perfil de usuario. |
| **Breve DescripciÃ³n** | Permite al usuario visualizar su informaciÃ³n personal y detalles de la cuenta como, al igual que sus reseÃ±as recientes. |
| **Prioridad** | Media. |
| **Complejidad** | Media. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado (sesiÃ³n activa). |
| **Postcondiciones** | **Ã‰xito:** El sistema carga y presenta la secciÃ³n de perfil con la informaciÃ³n del usuario actualizada. |
|  | **Fracaso:** El acceso no es posible o la informaciÃ³n no se carga correctamente. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario selecciona la opciÃ³n â€œPerfilâ€ en la barra de navegaciÃ³n.  | \- |
| 2\. El sistema recupera la informaciÃ³n completa del perfil y detalles de cuenta del usuario. | \- |
| 3\. El sistema presenta la secciÃ³n de perfil con la siguiente informaciÃ³n:  InformaciÃ³n personal: nombre, apellido, nombre de usuario, fecha de nacimiento, gÃ©nero y correo electrÃ³nico. ReseÃ±as recientes. | \- |
| 4\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | La informaciÃ³n de perfil debe mostrarse actualizada despuÃ©s de cualquier modificaciÃ³n por parte del usuario.  La navegaciÃ³n se realiza estrictamente a travÃ©s de la barra de navegaciÃ³n. Si la sesiÃ³n del usuario expira, es redirigido a la pÃ¡gina de inicio de sesiÃ³n. Se pueden aplicar operaciones de gestiÃ³n a las reseÃ±as recientes. |

| ID | CU-006 |
| :---- | :---- |
| **Nombre** | Modificar perfil. |
| **Breve DescripciÃ³n** | Permite al usuario autenticado actualizar su informaciÃ³n personal y detalles de cuenta. |
| **Prioridad** | Media. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado. |
| **Postcondiciones** | **Ã‰xito:** La informaciÃ³n del perfil del usuario se actualiza en la base de datos e inmediatamente se muestra renovada. |
|  | **Fracaso:** Los cambios no se aplican porque la validaciÃ³n falla o el usuario cancela la operaciÃ³n. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. extend(CU-005).  | \- |
| 2\. El usuario selecciona la opciÃ³n â€œModificar perfilâ€. | \- |
| 3\. El sistema presenta el formulario de modificaciÃ³n de perfil, permitiendo cambiar: ContraseÃ±a. Nombre de usuario. Nombre y apellido. | \- |
| 4\. El usuario modifica los campos deseados y presiona â€œGuardarâ€.  | \- |
| 5\. El sistema valida la informaciÃ³n y el formato de los campos.  | 5.A. La validaciÃ³n de los datos falla. 5.A.1. El sistema informa el error especÃ­fico. 5.A.2. Se retorna al paso 3\. |
| 6\. Si la informaciÃ³n es vÃ¡lida, el sistema actualiza la base de datos con la nueva informaciÃ³n | \- |
| 7\. El sistema muestra los cambios en el momento y notifica el Ã©xito de la modificaciÃ³n. | \- |
| 8\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | El usuario puede cancelar la operaciÃ³n en cualquier momento. El sistema solicita confirmaciÃ³n de cancelaciÃ³n y, si el usuario confirma, los datos no se guardan y el caso de uso finaliza. |
| **Observaciones** | El sistema debe cifrar la nueva informaciÃ³n sensible.  Los cambios deben mostrar la informaciÃ³n actualizada en el momento.  Las restricciones de campos igual que en el CU-001. |

| ID | CU-007 |
| :---- | :---- |
| **Nombre** | Dar de baja la cuenta. |
| **Breve DescripciÃ³n** | Permite al usuario eliminar permanentemente su cuenta. |
| **Prioridad** | Baja. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado. |
| **Postcondiciones** | **Ã‰xito:** La cuenta del usuario es eliminada permanentemente del sistema y la sesiÃ³n se cierra automÃ¡ticamente. |
|  | **Fracaso:** El estado de la cuenta no se modifica porque el usuario cancela la operaciÃ³n o la baja no puede realizarse. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. extend(CU-005). | \- |
| 2\. El usuario selecciona la opciÃ³n â€œDar de bajaâ€.  | \- |
| 3\. El sistema solicita confirmaciÃ³n para la baja de la cuenta.  | \- |
| 4\. El usuario confirma la baja de la cuenta apretando el botÃ³n â€œConfirmarâ€.  | 4.A. El usuario cancela la operaciÃ³n de baja. 4.A.1 Se retorna al paso 1, manteniendo al usuario en la secciÃ³n del perfil. |
| 5\. El sistema elimina la cuenta del usuario y notifica la baja exitosa. | \- |
| 6\. El sistema finaliza la sesiÃ³n y redirige al usuario a la pÃ¡gina de inicio. | \- |
| 7\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | Por un error de sistema la baja no puede ser procesada al llegar al paso 5, entonces el sistema debe informar al usuario del fallo y mantener la cuenta activa. |
| **Observaciones** | El borrado es lÃ³gico, por lo que hay que modificar el campo de estado de la cuenta de â€œactivaâ€ a â€œbajaâ€. |

| ID | CU-008 |
| :---- | :---- |
| **Nombre** | Visualizar CatÃ¡logo. |
| **Breve DescripciÃ³n** | Permite al usuario acceder al catÃ¡logo general de pelÃ­culas y series proveniente de la base de datos externa (TMDB), visualizando la informaciÃ³n detallada de cada Ã­tem con opciones de filtrado y bÃºsqueda. |
| **Prioridad** | Alta. |
| **Complejidad** | Alta. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | API externa (TMDB). |
| **Precondiciones** | El sistema debe estar conectado a la API externa y disponer de datos actualizados del catÃ¡logo. |
| **Postcondiciones** | **Ã‰xito:**  El sistema muestra el catÃ¡logo actualizado con las pelÃ­culas y series disponibles. El usuario puede navegar, filtrar o consultar detalles individuales de los Ã­tems. |
|  | **Fracaso:** El sistema no logra recuperar datos del catÃ¡logo o la API externa estÃ¡ fuera de servicio. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario selecciona la opciÃ³n â€œPelÃ­culasâ€ o â€œSeriesâ€ desde la barra de navegaciÃ³n. | \- |
| 2\. El sistema solicita los datos del catÃ¡logo a la API TMDB o desde cachÃ© local. | 2.A. No se puede establecer conexiÃ³n con la API externa. 2.A.1 El sistema recupera el catÃ¡logo almacenado localmente (Ãºltima sincronizaciÃ³n disponible). |
| 3\. El sistema presenta la lista paginada de Ã­tems con informaciÃ³n bÃ¡sica: TÃ­tulo. Imagen (poster). AÃ±o de lanzamiento. | \- |
| 4\. El usuario puede aplicar filtros o realizar una bÃºsqueda por nombre. | 4.A. No existen coincidencias para la bÃºsqueda. 4.A.1 El sistema muestra el mensaje â€œNo se encontraron resultados para su bÃºsquedaâ€. |
| 5\. El usuario selecciona un Ã­tem del catÃ¡logo. | \- |
| 6\. El sistema muestra la ficha completa del Ã­tem seleccionado con: Sinopsis. Reparto principal. DuraciÃ³n/Cantidad de episodios. GÃ©neros asociados. CalificaciÃ³n global y botÃ³n de calificar. | 6.A. El usuario cancela la visualizaciÃ³n detallada. 6.A.1 El sistema retorna al listado general. |
| 7\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | Si ocurre un error de conexiÃ³n con la API y no hay datos en cachÃ©, el sistema muestra el mensaje â€œNo se pudo recuperar el catÃ¡logo. Intente nuevamente mÃ¡s tardeâ€, y finaliza el caso de uso. |
| **Observaciones** | No se permite utilizar el buscador hasta que se ingrese texto en Ã©l. Campos de la vista de catÃ¡logo: tÃ­tulo, aÃ±o, imagen. Filtros disponibles: tipo (pelÃ­cula/serie), gÃ©nero, aÃ±o, calificaciÃ³n mÃ­nima. Restricciones: El campo de bÃºsqueda acepta texto alfanumÃ©rico (mÃ¡x. 50 caracteres). La actualizaciÃ³n con TMDB debe respetar lÃ­mites de uso de la API y emplear cachÃ© local. Tiempo mÃ¡ximo de respuesta para carga inicial: 2 segundos (90 % de las solicitudes). El sistema debe mantener la consistencia de los datos mostrados con la informaciÃ³n mÃ¡s reciente disponible. |

| ID | CU-009 |
| :---- | :---- |
| **Nombre** | Consultar Listas. |
| **Breve DescripciÃ³n** | Permite al usuario visualizar las listas de su cuenta, mostrando la informaciÃ³n bÃ¡sica de cada elemento y permitiendo acceder al detalle de cada pelÃ­cula o serie. |
| **Prioridad** | Alta. |
| **Complejidad** | Alta. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado en el sistema. Deben existir listas asociadas al usuario (predeterminadas o personalizadas). |
| **Postcondiciones** | **Ã‰xito:**  El sistema muestra las listas del usuario con sus respectivos elementos actualizados. El usuario puede acceder al detalle de los Ã­tems listados. |
|  | **Fracaso:** El sistema no muestra las listas si ocurre un error al recuperarlas. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario accede a la opciÃ³n â€œListasâ€ desde la barra de navegaciÃ³n. | \- |
| 2\. El sistema solicita al backend las listas asociadas al usuario autenticado. | \- |
| 3\. El sistema muestra las listas disponibles del usuario, tanto las predeterminadas como las personalizadas. | \- |
| 4\. El usuario selecciona una lista para visualizar su contenido.  | 4.A. La lista seleccionada estÃ¡ vacÃ­a. 4.A.1. El sistema muestra el mensaje â€œLa lista seleccionada no contiene elementosâ€. 4.A.2. El sistema retorna al paso 3\. |
| 5\. El sistema presenta la lista seleccionada con los Ã­tems asociados, mostrando: TÃ­tulo. Imagen (poster). AÃ±o de lanzamiento. | \- |
| 6\. El usuario selecciona un Ã­tem de la lista. | 6.A. El usuario cancela la visualizaciÃ³n del Ã­tem. 6.A.1. El sistema retorna a la visualizaciÃ³n de la lista. |
| 7\. El sistema muestra la informaciÃ³n detallada del Ã­tem (sinopsis, reparto, gÃ©neros, duraciÃ³n, etc.). | \- |
| 8\. El usuario puede regresar a la vista general de listas. | \- |
| 9\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | Si ocurre un error de conexiÃ³n o falla en la recuperaciÃ³n de datos, el sistema muestra el mensaje â€œNo se pudieron recuperar las listas". Intente nuevamente mÃ¡s tarde.â€ y finaliza el caso de uso. |
| **Observaciones** | Dentro de la vista de listas, se muestran los siguientes campos: tÃ­tulo, imagen, aÃ±o, de lanzamiento y fecha de agregado. Restricciones: El usuario solo puede consultar listas propias. Los nombres de listas personalizadas pueden tener hasta 80 caracteres alfanumÃ©ricos. La actualizaciÃ³n de las listas debe ser instantÃ¡nea al agregar o eliminar Ã­tems. |

| ID | CU-010 |
| :---- | :---- |
| **Nombre** | Buscar PelÃ­culas/Series por Nombre. |
| **Breve DescripciÃ³n** | Permite al usuario realizar una bÃºsqueda de pelÃ­culas o series dentro del catÃ¡logo, escribiendo un texto parcial o completo del tÃ­tulo.  |
| **Prioridad** | Alta. |
| **Complejidad** | Media. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | API externa (TMDB). |
| **Precondiciones** | El usuario debe estar posicionado en la secciÃ³n de â€œPelÃ­culasâ€ o â€œSeriesâ€. El sistema debe tener conexiÃ³n con la API externa o disponer de resultados almacenados en cachÃ©. |
| **Postcondiciones** | **Ã‰xito:**  El sistema muestra los resultados coincidentes con el texto de bÃºsqueda. El usuario puede seleccionar un Ã­tem y ver su detalle. |
|  | **Fracaso:** El sistema no encuentra coincidencias o no puede obtener resultados debido a una falla de conexiÃ³n. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. include(CU-008): el usuario estÃ¡ presente en el catÃ¡logo de Peliculas o Series. | \- |
| 2\. El usuario ingresa un texto parcial o completo en el campo de bÃºsqueda y presiona el botÃ³n â€œBuscarâ€. | \- |
| 3\. El sistema envÃ­a la consulta a la API externa o recupera resultados de la cachÃ© local. | 3.A. Ocurre un error de conexiÃ³n con la API y no hay resultados en cachÃ©. 3.A.1. El sistema muestra el mensaje â€œNo se pudo realizar la bÃºsqueda. Intente nuevamente mÃ¡s tarde.â€ 3.A.2. El caso de uso termina. |
| 4\. El sistema muestra los resultados paginados con los siguientes datos: Imagen (poster). TÃ­tulo. AÃ±o de lanzamiento. CalificaciÃ³n promedio. | \- |
| 5\. El usuario selecciona un Ã­tem de la lista.  | 5.A. El usuario cancela la visualizaciÃ³n del Ã­tem. 5.A.1. El sistema retorna a los resultados de bÃºsqueda. |
| 6\. El sistema muestra la ficha completa del Ã­tem seleccionado con detalles obtenidos de la API. | \- |
| 7\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | No se permite utilizar el buscador hasta que se ingrese texto en Ã©l. Campo de bÃºsqueda: texto alfanumÃ©rico (mÃ¡x. 50 caracteres). No se permiten caracteres especiales fuera del alfabeto estÃ¡ndar. El sistema debe mantener la paginaciÃ³n y filtros aplicados hasta que se limpie la bÃºsqueda o se abandone la secciÃ³n. Los resultados se muestran en una lista paginada. |

| ID | CU-011 |
| :---- | :---- |
| **Nombre** | Marcar pelÃ­cula/serie como vista. |
| **Breve DescripciÃ³n** | Permite al usuario aÃ±adir una pelÃ­cula o serie a su historial de visualizaciones, actualizando su lista de â€œVistasâ€. |
| **Prioridad** | Baja. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado en el sistema. |
| **Postcondiciones** | **Ã‰xito:** El Ã­tem se registra y se aÃ±ade a la lista de vistas. |
|  | **Fracaso:** La lista del usuario no se modifica y el sistema informa de un error. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. extend(CU-008). | \- |
| 2\. El usuario selecciona la opciÃ³n "Marcar como vista". | \- |
| 3\. El sistema registra el Ã­tem en el historial de visualizaciones del usuario.  | \- |
| 4\. El sistema notifica el Ã©xito: "Elemento aÃ±adido al historial". | \- |
| 5\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | Si ocurre un error de conexiÃ³n con la base de datos durante el paso 3, el sistema muestra el mensaje de error "No se pudo actualizar el historial. Intente nuevamente." y el caso de uso finaliza. |
| **Observaciones** | La acciÃ³n de marcar como visto actualiza automÃ¡ticamente la lista "Vistas" en la secciÃ³n de Listas del usuario. La opciÃ³n de "Marcar como vista" permite alternar el estado en el historial del elemento en cuestiÃ³n, ya sea aÃ±adiÃ©ndolo o eliminÃ¡ndolo. Para desmarcar un elemento previamente marcado como "Visto", el sistema debe verificar si el elemento ha sido calificado. Si el elemento tiene una calificaciÃ³n asociada, se debe informar al usuario que es necesario eliminar dicha calificaciÃ³n antes de poder proceder con la acciÃ³n de desmarcar. Desde la ficha de cada pelÃ­cula/serie (CU-008) tambiÃ©n se podrÃ¡ acceder a botones de acciÃ³n directa para agregar o quitar de las listas predeterminadas "Favoritos", "Vistos" y "Pendientes", asÃ­ como a un menÃº desplegable tipo checklist para agregar a listas personalizadas. Las listas no son mutuamente excluyentes: un mismo Ã­tem puede pertenecer simultÃ¡neamente a varias listas del usuario. |

| ID | CU-012 |
| :---- | :---- |
| **Nombre** | Gestionar listas. |
| **Breve DescripciÃ³n** | Permite al usuario crear, modificar (renombrar, sacar peliculas/series) y eliminar sus listas personales. AdemÃ¡s, se permite eliminar items de cualquier lista del usuario. |
| **Prioridad** | Media. |
| **Complejidad** | Alta. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado y haber accedido a la secciÃ³n â€œListasâ€. |
| **Postcondiciones** | **Ã‰xito:** La lista es creada, actualizada o eliminada, o un Ã­tem es removido de una lista. El cambio se refleja inmediatamente en la interfaz. |
|  | **Fracaso:** No se realizan cambios en las listas. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. extend(CU-009). | \- |
| 2\. El usuario selecciona una opciÃ³n de gestiÃ³n sobre una lista personal: "Crear Nueva Lista", "Renombrar" o "Eliminarâ€.  | \- |
| 3\. Si es "Crear Nueva Lista":  El sistema solicita el nombre para la nueva lista.  El usuario lo ingresa y presiona "Aceptar".  | \- |
| 4\. Si es "Renombrar":  El sistema solicita el nuevo nombre para la lista seleccionada.  El usuario lo ingresa y presiona "Aceptar". | 4.A. El nombre de la lista es invÃ¡lido o ya existe.  4.A.1. El sistema muestra un mensaje de error especificando el problema.  4.A.2. Se retorna al paso 1\. |
| 5\. Si es "Eliminar Lista":  El sistema solicita confirmaciÃ³n: "Â¿Desea eliminar esta lista permanentemente? Esta acciÃ³n no puede deshacerse".  El usuario presiona "Confirmar".  | 5.A El usuario cancela la eliminaciÃ³n.  5.A.1. El sistema cierra el modal de confirmaciÃ³n y la operaciÃ³n no se realiza.  5.A.2. El caso de uso termina. |
| 6\. Si el usuario, dentro de la lista, selecciona la opciÃ³n para eliminar cierto item: El sistema solicita confirmaciÃ³n: "Â¿EstÃ¡ seguro que desea quitar este elemento de la lista?".  El usuario presiona "Confirmar".  | 6.A El usuario cancela la eliminaciÃ³n.  6.A.1. El sistema cierra el modal de confirmaciÃ³n y la operaciÃ³n no se realiza.  6.A.2. El caso de uso termina. |
| 7\. El sistema actualiza la vista y muestra una notificaciÃ³n de Ã©xito. | \- |
| 8\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | El usuario puede cancelar cualquier operaciÃ³n en cualquier momento. El sistema solicitarÃ¡ confirmaciÃ³n y, si el usuario acepta, finalizarÃ¡ el caso de uso sin guardar cambios. Si ocurre un error de base de datos el sistema notificarÃ¡ el fallo y no aplicarÃ¡ el cambio. |
| **Observaciones** | Las listas predeterminadas ("Favoritos", "Pendientes", "Vistas") no pueden ser renombradas ni eliminadas, pero sÃ­ se pueden eliminar Ã­tems de ellas. La eliminaciÃ³n de una lista personal es permanente y elimina todos los Ã­tems en ella. Restricciones de campos: Nombre de lista: Texto alfanumÃ©rico, longitud mÃ¡xima de 80 caracteres. No puede estar vacÃ­o. |

| ID | CU-013 |
| :---- | :---- |
| **Nombre** | Interactuar con el chatbot. |
| **Breve DescripciÃ³n** | Permite al usuario realizar consultas y solicitar recomendaciones de pelÃ­culas/series a travÃ©s del chatbot, que utiliza el contexto del usuario para generar respuestas personalizadas. |
| **Prioridad** | Alta. |
| **Complejidad** | Alta. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | API del LLM del Chatbot. |
| **Precondiciones** | El usuario estÃ¡ situado en la pÃ¡gina de inicio, donde el chatbot es accesible. |
| **Postcondiciones** | **Ã‰xito:** El sistema procesa la consulta del usuario y entrega una respuesta/ recomendaciÃ³n en la interfaz del chatbot. |
|  | **Fracaso:** El sistema informa que no puede procesar la solicitud o que ha ocurrido un error de conexiÃ³n. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El usuario abre la interfaz del chatbot accesible en la pÃ¡gina. | \- |
| 2\. El sistema muestra un mensaje de bienvenida. | \- |
| 3\. El usuario escribe una consulta en el campo de texto y la envÃ­a. | \- |
| 4\. El sistema muestra un indicador para mostrar que el chatbot estÃ¡ procesando la solicitud. | 4.A El usuario cancela la solicitud. 4.A.1: Se activa el CU-014. |
| 5\. include(CU-018): El sistema procesa la consulta, anonimiza datos sensibles y la envÃ­a a la API del LLM junto con el contexto del usuario (historial, reseÃ±as). | 5.A. La API del LLM no estÃ¡ disponible o devuelve un error.  5.A.1. El sistema muestra el mensaje: "No podemos procesar tu solicitud. Intenta mÃ¡s tarde".  5.A.2. El caso de uso termina. |
| 6\. El sistema recibe la respuesta de la API del LLM. | \- |
| 7\. El sistema muestra la respuesta formateada al usuario en la ventana del chat. | \- |
| 8\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | El chatbot solo estÃ¡ disponible para usuarios autenticados. Los datos sensibles del usuario (email, nombre, apellido.) deben ser anonimizados antes de ser enviados al proveedor del LLM.  Tiempos de respuesta esperados: Menos de 5 segundos para interacciones simples. Menos de 15 segundos para consultas complejas que requieran agregaciÃ³n de datos. |

| ID | CU-014 |
| :---- | :---- |
| **Nombre** | Cancelar recomendaciÃ³n en curso. |
| **Breve DescripciÃ³n** | Permite al usuario interrumpir una solicitud de recomendaciÃ³n enviada al chatbot mientras esta se encuentra en estado de procesamiento. |
| **Prioridad** | Baja. |
| **Complejidad** | Baja. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario ha enviado una consulta al chatbot y el sistema estÃ¡ procesÃ¡ndola, mostrando un indicador de progreso. |
| **Postcondiciones** | **Ã‰xito:** La solicitud en curso es cancelada, el indicador de progreso desaparece y la interfaz del chatbot vuelve a estar disponible para una nueva consulta. |
|  | **Fracaso:** La cancelaciÃ³n no se procesa a tiempo y el sistema muestra la respuesta de la solicitud. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. extend(CU-013). | \- |
| 2\. El usuario selecciona la opciÃ³n "Cancelar" disponible junto al indicador de progreso.  | 2.A. El usuario presiona "Cancelar" pero la respuesta del sistema llega en el mismo instante.  2.A.1. El sistema prioriza la acciÃ³n de cancelaciÃ³n, descarta la respuesta recibida y continÃºa con el paso 3 del flujo principal. |
| 3\. El sistema detiene el procesamiento de la solicitud actual. | \- |
| 4\. El sistema oculta el indicador de progreso. | \- |
| 5\. El sistema muestra el mensaje "Solicitud cancelada" en el chat y habilita nuevamente el campo de entrada. | \- |
| 6\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | Si ocurre un error de comunicaciÃ³n que impide cancelar la solicitud en el backend, el sistema podrÃ­a eventualmente mostrar la respuesta una vez que llegue, aunque el usuario haya intentado cancelar. |

| ID | CU-015 |
| :---- | :---- |
| **Nombre** | Gestionar ReseÃ±a y CalificaciÃ³n (ABM). |
| **Breve DescripciÃ³n** | Permite al usuario publicar, modificar y eliminar sus propias reseÃ±as y calificaciones (rango de 1 a 10 estrellas). |
| **Prioridad** | Alta. |
| **Complejidad** | Alta. |
| **Actor principal** | Usuario. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El usuario debe estar autenticado y estar visualizando la ficha detallada de una pelÃ­cula o serie. |
| **Postcondiciones** | **Ã‰xito:** La calificaciÃ³n y/o reseÃ±a se almacenan, modifican o eliminan en el sistema. Las reseÃ±as recientes se actualizan en el perfil del usuario |
|  | **Fracaso:** La publicaciÃ³n, modificaciÃ³n o eliminaciÃ³n no se realiza. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1.El usuario accede a la funcionalidad de gestiÃ³n de calificaciones/reseÃ±as(desde CU-008 o CU-005). | \- |
| 2\. El usuario selecciona una opciÃ³n de gestiÃ³n: "Publicar ReseÃ±a", "Modificar ReseÃ±a" o "Eliminar ReseÃ±a". | \- |
| 3\. Si es "Publicar ReseÃ±a": El usuario ingresa la calificaciÃ³n (1- 10). Opcionalmente, el usuario ingresa el contenido de la reseÃ±a. El usuario presiona "Publicar". | 3.A. El usuario cancela la publicaciÃ³n. 3.A.1. El sistema cierra el modal de publicaciÃ³n. 3.A.2. El caso de uso termina. 3.B El usuario intenta publicar sin calificar.  3.B.1. El sistema deniega la publicaciÃ³n y notifica el error. 3.B.2. Se retorna al paso 2\. |
| 4\. Si es "Modificar ReseÃ±a": El sistema presenta la interfaz con la calificaciÃ³n y texto actuales. El usuario modifica la calificaciÃ³n (1 \- 10\) y/o el texto. El usuario presiona "Actualizar". | 4.A El usuario cancela la modificaciÃ³n: 3.A.1. El sistema cierra el modal de modificaciÃ³n. 3.A.2. El caso de uso termina. 4.B. La validaciÃ³n falla (ej. calificaciÃ³n 0). 4.B.1. El sistema informa el error. 4.B.2. Se retorna al paso 2\.  |
| 5\. Si es "Eliminar ReseÃ±a": El sistema solicita confirmaciÃ³n: "Â¿Desea eliminar esta reseÃ±a permanentemente?". El usuario presiona "Confirmar". | 5.A. El usuario cancela la eliminaciÃ³n. 5.A.1. El sistema cierra el modal de confirmaciÃ³n. 5.A.2. El caso de uso termina. |
| 6\. El sistema valida la informaciÃ³n (si aplica) y la almacena, modifica o elimina en la base de datos. | \- |
| 7\. El sistema actualiza la vista (ej. perfil ) y notifica el Ã©xito de la operaciÃ³n. | \- |
| 8\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | Si ocurre un error de conexiÃ³n o base de datos al intentar almacenar, modificar o eliminar la reseÃ±a/calificaciÃ³n, el sistema notifica el fallo y el caso de uso finaliza sin guardar los datos. |
| **Observaciones** | La calificaciÃ³n debe estar en el rango de 1 a 10\. La realizaciÃ³n de una reseÃ±a es opcional. |

| ID | CU-016 |
| :---- | :---- |
| **Nombre** | Gestionar usuarios. |
| **Breve DescripciÃ³n** | Permite al administrador realizar operaciones sobre las cuentas de usuario. |
| **Prioridad** | Media. |
| **Complejidad** | Media. |
| **Actor principal** | Administrador. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El actor debe estar autenticado con el rol de Administrador.  El Administrador debe acceder al mecanismo de gestiÃ³n (BD o API). |
| **Postcondiciones** | **Ã‰xito:** La cuenta del usuario es modificada, eliminada o su estado actualizado en la base de datos. |
|  | **Fracaso:** La gestiÃ³n no se realiza por error de acceso o datos invÃ¡lidos. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El Administrador accede a la herramienta de gestiÃ³n de usuarios (BD o API). | \- |
| 2\. El Administrador aplica la operaciÃ³n de gestiÃ³n deseada (ej: bÃºsqueda, modificaciÃ³n de datos, cambio de estado, eliminaciÃ³n). | \- |
| 3\. El sistema valida la solicitud y aplica el control de acceso por rol. | 3.A. El Administrador intenta una operaciÃ³n no permitida. 3.A.1. El sistema deniega la operaciÃ³n y notifica el error de acceso.  3.A.2. Se retorna al paso 2\. |
| 4\. El sistema ejecuta la operaciÃ³n en la base de datos. | 4.A. Ocurre un error al ejecutar la operaciÃ³n en la BD. 4.A.1. El sistema notifica al Administrador sobre el fallo. 4.A.2. El caso de uso termina. |
| 5\. El sistema notifica al Administrador el Ã©xito de la operaciÃ³n. | \- |
| 6\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | El Administrador realiza sus acciones directamente a travÃ©s de la BD o API, no tiene pantallas especÃ­ficas de gestiÃ³n. El sistema debe aplicar control de acceso para operaciones protegidas. |

| ID | CU-017 |
| :---- | :---- |
| **Nombre** | Moderar reseÃ±as. |
| **Breve DescripciÃ³n** | Permite al Administrador revisar, editar o eliminar reseÃ±as de pelÃ­culas/series publicadas por los usuarios. |
| **Prioridad** | Baja. |
| **Complejidad** | Media. |
| **Actor principal** | Administrador. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El actor debe estar autenticado con el rol de Administrador.  Deben existir reseÃ±as publicadas por usuarios. |
| **Postcondiciones** | **Ã‰xito:** La reseÃ±a es modificada o eliminada de la base de datos. |
|  | **Fracaso:** La moderaciÃ³n no se realiza. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. El Administrador accede a la herramienta de gestiÃ³n de reseÃ±as (BD o API). | \- |
| 2\. El Administrador selecciona una reseÃ±a para revisar. | \- |
| 3\. El Administrador aplica la acciÃ³n de moderaciÃ³n deseada (ej: eliminar o editar contenido). | \- |
| 4\. El sistema valida la solicitud y aplica el control de acceso por rol. | \- |
| 5\. El sistema ejecuta la operaciÃ³n en la base de datos. | 5.A. Ocurre un error al ejecutar la operaciÃ³n en la BD. 5.A.1. El sistema notifica al Administrador sobre el fallo. 5.A.2. El caso de uso termina. |
| 6\. El sistema notifica al Administrador el Ã©xito de la moderaciÃ³n. | \- |
| 7\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | El Administrador realiza sus acciones a travÃ©s de la BD o API. El sistema debe aplicar control de acceso por rol. Esta moderaciÃ³n es independiente de la gestiÃ³n que el usuario realiza sobre sus propias reseÃ±as (CU-015). |

| ID | CU-018 |
| :---- | :---- |
| **Nombre** | Entrega respuestas basadas en historial y reseÃ±as. |
| **Breve DescripciÃ³n** | Permite a la API del LLM procesar la consulta del usuario usando el historial de visualizaciones y reseÃ±as para generar una respuesta/recomendaciÃ³n contextualizada. |
| **Prioridad** | Alta. |
| **Complejidad** | Alta. |
| **Actor principal** | API LLM de Chatbot. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | El sistema debe haber enviado una solicitud de consulta/recomendaciÃ³n a la API del LLM.  El contexto del usuario (historial, reseÃ±as) debe haber sido anonimizado antes de ser enviado. |
| **Postcondiciones** | **Ã‰xito:** La API del LLM devuelve la respuesta o recomendaciÃ³n basada en el contexto dado. |
|  | **Fracaso:** La API del LLM devuelve un error o no responde. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. La API del LLM recibe la consulta del usuario, junto con los datos del historial, reseÃ±as y dominio almacenado. | \- |
| 2\. La API del LLM procesa la solicitud utilizando el contexto proporcionado. | \- |
| 3\. La API del LLM genera una respuesta o recomendaciÃ³n. | \- |
| 4\. La API del LLM entrega la respuesta al sistema. | 4.A. La API del LLM devuelve un error o el tiempo de respuesta excede el lÃ­mite. 4.A.1. El sistema muestra un mensaje de error. 4.A.2 El caso de uso termina. |
| 5\. El caso de uso termina. | \- |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | Este caso de uso es invocado por el CU-013. Los datos sensibles del usuario (email, nombre, apellido.) deben ser anonimizados antes de ser enviados al proveedor del LLM.  Tiempos de respuesta esperados: Menos de 5 segundos para interacciones simples. Menos de 15 segundos para consultas complejas que requieran agregaciÃ³n de datos. |

| ID | CU-019 |
| :---- | :---- |
| **Nombre** | Exponer CatÃ¡logo. |
| **Breve DescripciÃ³n** | Permite a la API de The Movie Database proveer el catÃ¡logo actualizado de pelÃ­culas y series al sistema. |
| **Prioridad** | Alta. |
| **Complejidad** | Media. |
| **Actor principal** | API TMBD. |
| **Actores secundarios** | Ninguno. |
| **Precondiciones** | La API de TMDB debe estar operativa y el sistema debe realizar una solicitud de catÃ¡logo. |
| **Postcondiciones** | **Ã‰xito:** La API de TMDB devuelve los datos del catÃ¡logo solicitados. |
|  | **Fracaso:** La API de TMDB no responde o devuelve un error de conexiÃ³n. |
| **Flujo Principal** | **Flujo Alternativo** |
| 1\. La API de TMDB recibe la solicitud de catÃ¡logo (pelÃ­culas o series). | \- |
| 2\. La API de TMDB procesa la solicitud. | \- |
| 3\. La API de TMDB devuelve el catÃ¡logo actualizado. | \- |
| 4\. El caso de uso termina. | 4.A. La API de TMDB no estÃ¡ disponible o el tiempo de respuesta excede el lÃ­mite.  4.A.1. El sistema intenta recuperar datos desde la cachÃ© local.  4.A.2. Si falla la recuperaciÃ³n en cachÃ©, el sistema notifica el error.  4.A.3. El caso de uso termina. |
| **Flujos de excepciÃ³n** | \- |
| **Observaciones** | Este caso de uso es invocado por el CU-008. La sincronizaciÃ³n con la API externa debe optimizarse mediante cachÃ© local para respetar lÃ­mites de uso y evitar llamadas innecesarias.  Las operaciones de sincronizaciÃ³n no deben afectar la experiencia del usuario. |

