# Importamos librerías necesarias que se utilizaran para las tareas que realiza el script
import boto3
import os
from botocore.exceptions import ClientError
import time

######################################################################################################################################
# 1: CREACION DEL BUCKET Y SUBIDA DE ARCHIVOS AL MISMO
######################################################################################################################################

s3 = boto3.client('s3')

# Variables: Nombre del bucket, carpeta local donde estarán alojados los archivos bajados del repo, carpeta remota del s3 donde se van a subir
bucket_name = 'app-bucket-obligatorio-241688'
carpeta_local = '/home/franco/APP/' #Yo alojé acá los archivos en mi VM, ajustar esta variable al directorio que corresponda
carpeta_remota = 'APP'

# Obtener todos los archivos de la carpeta local
# os.listdir devuelve una lista con los nombres de los archivos y carpetas dentro de un directorio, solo nombres, no devuelve path completo
archivos = os.listdir(carpeta_local)

# Crear bucket si no existe
try:
    s3.create_bucket(Bucket=bucket_name)
    print("")
    print(f"Creando Bucket: {bucket_name}")
except ClientError as e:
    if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
        print(f"Error creando bucket: {e}")
        exit(1)
print("")
print(f"Subiendo archivos a s3://{bucket_name}/{carpeta_remota}/")
print("")
for nombre in archivos:
    arch_local = os.path.join(carpeta_local, nombre) # os.path.join construye rutas de archivos o directorios, de forma segura (evita errores con barras "/"), en este caso arma el path con las 2 variables
    s3_key = f"{carpeta_remota}/{nombre}" # esta variable contiene la ruta remota para los archivos en el bucket, f me permite insertar variables dentro del texto

    try:
        s3.upload_file(arch_local, bucket_name, s3_key)
        print(f"Subido: {arch_local} → s3://{bucket_name}/{s3_key}")
    except FileNotFoundError:
        print(f"El archivo {arch_local} no existe")

    except Exception as e:
        print(f"Error subiendo {arch_local}: {e}")

print("")
print(f"Archivos subidos al bucket: {bucket_name}")
print("")

######################################################################################################################################
# 2: CREACION DE INSTANCIA EC2 Y EJECUCION DE COMANDOS DENTRO DE LA INSTANCIA (INSTALACION DE PAQUETES, MOVER ARCHIVOS, ETC)
######################################################################################################################################

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

# Parte 1: Crear una instancia EC2 asociada al Instance Profile del rol LabRole
response = ec2.run_instances(
    ImageId='ami-06b21ccaeff8cd686',
    InstanceType='t2.micro',
    MinCount=1,
    MaxCount=1,
    IamInstanceProfile={'Name': 'LabInstanceProfile'},
)

# Agregar tag Name: webserver-devops
instance_id = response['Instances'][0]['InstanceId']
ec2.create_tags(
    Resources=[instance_id],
    Tags=[{'Key': 'Name', 'Value': 'webserver-devops'}]
)
print(f"Instancia creada con ID: {instance_id} y tag 'webserver-devops'")
print("")
# Esperar a que la instancia esté en estado running 
ec2.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])

# Parte 2: Enviar comandos y extraer resultados
command = f"""
sudo yum install -y httpd php php-mysqlnd
sudo systemctl enable httpd
sudo systemctl start httpd

# Crear carpetas necesarias
sudo mkdir -p /var/www/html
sudo mkdir -p /var/www

# Copiar DIRECTAMENTE desde S3 los archivos hacia /var/www/html/ menos el archivo de la DB el cual lo copiamos despues a /var/www/
sudo aws s3 sync s3://{bucket_name}/{carpeta_remota}/ /var/www/html/ --exclude "init_db.sql"

sudo aws s3 cp s3://{bucket_name}/{carpeta_remota}/init_db.sql /var/www/

# Ajustar permisos
sudo chown -R apache:apache /var/www

sudo systemctl restart httpd
"""

response = ssm.send_command(
    InstanceIds=[instance_id],
    DocumentName="AWS-RunShellScript",
    Parameters={'commands': [command]}
)
command_id = response['Command']['CommandId']

# Esperar resultado
while True:
    try:
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break
        time.sleep(2)
    except ssm.exceptions.InvocationDoesNotExist:
        # Se agrega esto para evitar errores cuando el comando aún no fue recibido por el agente SSM
        pass
    time.sleep(3)
print("EJECUCION DE COMANDOS E INSTALACION DE PAQUETES:")
print("")
print(output['StandardOutputContent'])
