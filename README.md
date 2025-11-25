# Obligatorio Programación para DevOps – Agosto 2025

## Parte 1 - AWS - Automatización de Infraestructura AWS con Boto3

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
