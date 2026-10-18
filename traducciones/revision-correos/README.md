# Revisión de correos

Ocho mensajes de ejemplo: cuatro casos en inglés y español. Se generaron con el servicio real y el transporte en memoria; no se enviaron al exterior. Los enlaces son muestras sin tokens válidos.

Abrí `index.html` para comparar HTML y texto plano. Abrí los archivos `.eml` en un cliente de correo para revisar allí asunto, contenido, enlaces y ancho móvil/escritorio. Registrá cliente, versión y resultado antes de cerrar la aceptación manual de OT-90.

Los tests de Django cubren las ocho variantes, la prioridad del destinatario, las vigencias de configuración y las rutas inglesas. El idioma de la página de destino respeta cookie/navegador, aunque difiera del idioma del mensaje (confirmado por el usuario el 08/10/2026).
