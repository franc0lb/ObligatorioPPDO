# Obligatorio Programación para DevOps – Agosto 2025

  
# Parte 1 - Automatización de creación de usuarios en Linux
## Ubicación del archivo: ScriptBash/crearUsers.sh
Este script permite crear usuarios en masa a partir de un archivo de entrada, validando sintaxis, evitando duplicados, aplicando valores por defecto y permitiendo asignar una contraseña inicial.  
Incluye soporte opcional para mostrar por pantalla los detalles de la creación de cada usuario.

---

## Características principales

- Verificación de ejecución como **root** o con **sudo**.  
- Validación estricta del archivo de entrada mediante expresiones regulares.  
- Detección de:
  - Campos vacíos
  - Usuarios duplicados
  - Sintaxis incorrecta
- Creación de usuarios con:
  - Comentario
  - Directorio home
  - Opción de crear/no crear home
  - Shell de inicio
- Valores por defecto cuando los campos están vacíos.
- Opciones:
  - `-c <pass>` asigna una contraseña por defecto.
  - `-i` muestra en pantalla el proceso de creación.
- Impide sobrescribir usuarios ya existentes.
- Reporte final con la cantidad de usuarios creados.

---

## Formato del archivo de entrada

El archivo debe contener **5 campos separados por dos puntos (`:`)**:

```
usuario:comentario:/ruta/home:SI|NO:/ruta/shell
```

### Reglas:

- El **primer campo** (usuario) no puede estar vacío.
- Shell y home, si existen, deben empezar con `/`.
- El campo 4 acepta:
  - `SI` → Crear home  
  - `NO` → No crearlo  
  - vacío → crea el home por defecto
- Campos vacíos se completan con valores por defecto:
  - Comentario: `Comentario por defecto`
  - Home: `/home/<usuario>`
  - Creación del home: `Se aplicará el modificador -m cuando se ejecute useradd (useradd creará el home, la opción por defecto es que el home se cree)`
  - Shell: `/bin/bash`

Ejemplo:

```
juan:Usuario Juan:/home/juan:SI:/bin/bash
maria::/home/maria:NO:/bin/zsh
pedro:DevOps::SI:
lucas:::: 
```

---

## Uso del script

### Ejecución mínima:
```
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear
```

### Crear usuarios con contraseña:
```
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear -c Contraseña123
```

### Mostrar información durante la creación:
```
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear -i
```

### Mostrar creación + contraseña:
```
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear -c 1234 -i
```

También acepta estas variantes equivalentes:
```
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear -ic 1234
sudo ./crearUsers.sh Archivo_con_los_usuarios_a_crear -ci 1234
```

### Contraseña por defecto:
  No existe una contraseña por defecto, el usuario se va a crear con useradd y quedará sin contraseña si no se asignó previamente con el modificador -c

---

## Validaciones realizadas por el script

### 1. Ejecución como root  
Si no se ejecuta con permisos elevados, el script detiene la ejecución:

```
Este script debe ejecutarse como root o con sudo.
```

### 2. Validación de parámetros  
- Mínimo 1 parámetro (archivo)  
- Máximo 4 parámetros

### 3. Validación del archivo  
- Que exista  
- Que sea archivo regular  
- Que tenga permisos de lectura  

### 4. Validación de sintaxis  
El script valida:

- Que cada línea tenga **exactamente 5 campos**
- Que la sintaxis sea válida mediante regex
- Que no existan usuarios repetidos en la lista

### 5. Detección de usuarios ya existentes  
Si el usuario ya existe, no se crea nuevamente.

---

## Códigos de error

El script devuelve distintos códigos según el error detectado:

| Código | Motivo |
|--------|--------|
| 100 | No se ejecutó como root |
| 0   | Faltan parámetros |
| 1   | Demasiados parámetros |
| 2   | Archivo inexistente |
| 3   | No es un archivo regular |
| 4   | Sin permisos de lectura |
| 5   | Sintaxis incorrecta (campos) |
| 20  | Sintaxis incorrecta (regex) |
| 21  | Usuarios duplicados |
| 6   | Falta contraseña después de `-c` |
| 7   | Parámetro 3 inválido |
| 8   | Parámetro 2 inválido |
| 9   | Parámetro 4 inválido |

---

## Valores por defecto asignados

| Campo | Valor por defecto |
|--------|-------------------|
| Comentario | `Comentario por defecto` |
| Home | `/home/<usuario>` |
| Crear home | `SI` |
| Shell | `/bin/bash` |

---

## Resultado final

Al finalizar, el script muestra:

```
Usuarios creados: <n>
```

Donde `<n>` es el total de usuarios creados exitosamente.

---


# Parte 2 - Automatización de Infraestructura AWS con Boto3
## Ubicación del archivo: ScriptAWS/ScriptAWS.py
Este repositorio contiene un script en Python que automatiza la creación completa de una infraestructura básica en AWS, incluyendo:

- Creación de un bucket S3  
- Descarga y despliegue de archivos de una aplicación  
- Creación y configuración de una instancia EC2  
- Configuración y asignación de Security Groups  
- Creación e inicialización de una base de datos MySQL en Amazon RDS  
- Configuración del entorno necesario para que la aplicación funcione  

Todo el proceso se ejecuta automáticamente mediante llamadas a la API de AWS utilizando **boto3** y **AWS Systems Manager (SSM)**.

---

## Requisitos

### Sistema operativo
Un equipo o máquina virtual Linux.

### Paquetes necesarios
- Python 3.6 o superior
- pip
- boto3
- AWS CLI
- requests

### Variables de entorno obligatorias

Antes de ejecutar el script, deben definirse dos contraseñas:

```bash
export RDS_ADMIN_PASSWORD="contraseña_admin_rds"
export RDS_APP_PASSWORD="contraseña_app"
```

El script no avanzará si estas variables no están definidas.

---

## ¿Qué automatiza el script?

### 1. Creación del bucket S3 y subida de archivos
- Descarga automáticamente el repositorio desde GitHub en formato ZIP.  
- Extrae los archivos en un directorio temporal.  
- Identifica la carpeta donde se encuentran los archivos de la aplicación.  
- Crea un bucket S3 (si no existe).  
- Sube todos los archivos a una carpeta llamada `APP` dentro del bucket.

### 2. Creación de la instancia EC2 y configuración inicial
- Crea una instancia **t2.micro** con un role previamente definido (`LabInstanceProfile`).  
- Espera a que la instancia esté lista para recibir comandos.  
- Usa AWS SSM para ejecutar comandos dentro de la instancia:
  - Instalación de Apache, PHP y dependencias  
  - Creación de directorios  
  - Descarga de archivos desde S3  
  - Configuración de permisos  
  - Reinicio de servicios necesarios

### 3. Creación de Security Groups

El script genera dos grupos de seguridad:

#### SG para EC2 (`web-sg-boto3`)
- Permite tráfico HTTP (TCP/80) desde cualquier origen.

#### SG para RDS (`rds-mysql-sg`)
- Permite tráfico MySQL (TCP/3306) únicamente desde el SG de la EC2.

Después de crearlos, el script asigna el SG correspondiente a la instancia EC2.

### 4. Creación e inicialización de la base RDS
- Crea una instancia MySQL RDS accesible públicamente.  
- Asigna el security group que permite conexiones desde la EC2.  
- Espera a que la instancia esté disponible.  
- Obtiene el endpoint de la base.  
- Desde la EC2 (mediante SSM), ejecuta:
  - El archivo SQL que inicializa la base (tablas, usuarios, datos)  
  - La creación del archivo `.env` con variables necesarias  
  - La asignación de permisos adecuados para proteger credenciales

---

## Cómo ejecutar el script

### 1. Configurar las credenciales de AWS:
```bash
aws configure
```

### 2. Exportar las variables de entorno:
```bash
export RDS_ADMIN_PASSWORD="*****"
export RDS_APP_PASSWORD="*****"
```

### 3. Ejecutar el script:
```bash
python ScriptAWS.py
```

---

## Arquitectura resultante

Después de ejecutar el script, se implementa automáticamente esta arquitectura:

- S3 con los archivos de la aplicación  
- EC2 actuando como servidor web con Apache y PHP  
- RDS MySQL inicializado y conectado a EC2  
- Seguridad controlada mediante Security Groups  
- Comunicación RDS ↔ EC2 correctamente configurada  
- Infraestructura completamente reproducible mediante un solo script
