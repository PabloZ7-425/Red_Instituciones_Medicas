# Contribuir

La [guía de la raíz](README.md) describe cómo descargar, iniciar y recorrer la aplicación. La [documentación de implementación](docs/implementacion/README.md) reúne la arquitectura, los contratos y la evidencia.

Trabaja en una rama desde implementacion y abre un pull request hacia esa rama. Revisa el diff y valida el módulo que cambiaste. Guarda las contraseñas y respaldos fuera del repositorio.

Los cambios de esquema requieren una migración incremental y una validación con volúmenes separados. El contenido de datos de prueba usa los contratos de la aplicación para cargar expedientes ficticios sin reemplazar la estructura de los motores.
