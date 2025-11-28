# Gestor de Tesis – Sistema de Despliegue Automático de Proyectos
## Descripción General

Este proyecto es una plataforma que permite desplegar automáticamente otros proyectos alojados en repositorios Git. Está diseñado para facilitar la administración, actualización y ejecución de múltiples aplicaciones desde un único backend centralizado.

El sistema detecta si un proyecto utiliza docker-compose.yml o un Dockerfile, ajusta configuraciones como puertos y rutas, y ejecuta los comandos necesarios para levantar los servicios sin intervención manual.

## Problema que Resuelve

Muchos equipos tienen varios proyectos independientes que requieren ambientes similares o automatización al momento de desplegar. Realizar estas tareas manualmente genera errores, consume tiempo y vuelve difícil mantener múltiples instancias funcionando simultáneamente.

Este sistema permite:

* Desplegar proyectos a partir de enlaces Git.

* Ajustar puertos de forma automática.

* Ejecutar docker compose up desde una carpeta padre.

* Estandarizar la ejecución y actualización de proyectos.

* Evitar configuraciones manuales repetitivas.

## Arquitectura del Proyecto

El sistema se compone de:

### Backend (Flask)

Encargado de:

* Recibir solicitudes de despliegue.

* Clonar repositorios en una carpeta padre predefinida.

* Ajustar puertos en archivos docker-compose.yml.

* Levantar servicios con Docker Compose o Dockerfile.

* Mantener logs y reportar errores al usuario.

### Entorno Docker

El backend corre dentro de un contenedor Docker, lo que permite:

* Aislamiento del entorno.

* Reproducibilidad en cualquier servidor.

* Gestión homogénea de dependencias.

### Carpeta de Proyectos

Dentro del servidor, existe un directorio padre (por ejemplo /proyectos/) donde:

* Se almacenan los repos clonado por nombre.

* Se ejecuta docker compose up usando rutas relativas.

# Requisitos Previos

Antes de usar el gestor, se necesita:

1. Docker instalado

2. Docker Compose instalado

3. Puerto libre para alojar el backend (por defecto 5000)

4. Acceso a internet para clonar repositorios Git

# Cómo Ejecutarlo con Docker

1. Moverte a la carpeta donde está el gestor de tesis.

2. Construir la imagen.
docker build -t gestor-tesis

3. Ejecutar el contenedor.

        Ejecuta: docker compose up -d

        El backend quedará disponible en http://localhost:5000

### Cómo Usar el Endpoint de Despliegue

El backend expone un único endpoint principal:

POST /desplegar
Ejemplo del cuerpo JSON:
```
{
  "nombre": "mi_proyecto",
  "link": "https://github.com/usuario/repo.git",
  "puerto": 7000
}
```

### ¿Qué sucede internamente?

Se crea o usa la carpeta:

/proyectos/mi_proyecto


Se clona el repositorio si no existe.

Si hay docker-compose.yml, se edita el puerto y se ejecuta:

docker compose -f ../docker-compose.yml up --build -d

(Ejecutado desde la carpeta padre para soportar rutas relativas.)

Si no hay docker-compose.yml, se construye la imagen desde el Dockerfile y se ejecuta:

docker build -t mi_proyecto-image .
docker run -d -p 7000:5006 --name mi_proyecto-container mi_proyecto-image

Estructura de Carpetas Esperada
/gestor-tesis/
    ├── backend/
    ├── frontend/
    ├── docker-compose-yml
    ├── README.md
    └── ...
    |__ proyectos/
        ├── proyectoA/
        ├── proyectoB/
        └── proyectoC/

Logs

En caso de error, el backend devuelve:

Error en comandos Docker

Logs del servicio que falló

Ubicación del contenedor o archivo que generó el problema

Estado del Proyecto

El proyecto está activo y preparado para extender sus funcionalidades, como:

Autenticación para despliegues

Manejo de dominios

Registro histórico de acciones

Eliminación automática de contenedores antiguos