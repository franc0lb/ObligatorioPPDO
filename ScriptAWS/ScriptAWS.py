# Importamos librerias necesarias que se utilizaran para las tareas que realiza el script
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
sudo dnf clean all
sudo dnf makecache
sudo dnf -y update
sudo dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105
sudo systemctl enable --now httpd
sudo systemctl enable --now php-fpm

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



######################################################################################################################################
# 3: CREACION DE SECURITY GROUP
######################################################################################################################################
ec2 = boto3.client('ec2')
# 1. Crear un Security Group que permita tráfico web desde cualquier IP
sg_name = 'web-sg-boto3'
print("Se procede a crear el security group, para habilitar el tráfico web:")
print("")
try:
    response = ec2.create_security_group(
        GroupName=sg_name,
        Description='Permitir trafico web desde cualquier IP'
    )
    sg_id = response['GroupId']
    print(f"Security Group creado: {sg_id}")
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            
            {
                'IpProtocol': 'tcp',
                'FromPort': 3306,
                'ToPort': 3306,
                'UserIdGroupPairs': [{'GroupId': sg_id}]
             }
        ]
    )
except ClientError as e:
    if 'InvalidGroup.Duplicate' in str(e):
        sg_id = ec2.describe_security_groups(GroupNames=[sg_name])['SecurityGroups'][0]['GroupId']
        print(f"Security Group ya existe: {sg_id}")
    else:
        raise

# 2. Asociar el SG a la instancia EC2 creada anteriormente

# Obtener la primera instancia EC2 cuyo tag Name sea 'webserver-devops'
instances = ec2.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['webserver-devops']}])
instance_id = None
for reservation in instances['Reservations']:
    for instance in reservation['Instances']:
        instance_id = instance['InstanceId']
        break
    if instance_id:
        break
if not instance_id:
    raise Exception("No se encontró ninguna instancia con el tag 'webserver-devops'.")

ec2.modify_instance_attribute(InstanceId=instance_id, Groups=[sg_id])
print(f"SG {sg_id} asociado a la instancia {instance_id}")
print("Ahora navegue a la IP pública de la instancia para verificar el acceso web.")
print("")

######################################################################################################################################
# 4: CREACION DE BASE DE DATOS RDS
######################################################################################################################################
# Parámetros
rds = boto3.client('rds')
DB_INSTANCE_ID = 'app-mysql'
DB_NAME = 'app'
DB_USER = 'admin'
# La password debe venir de una variable de entorno
#DB_PASS = os.environ.get('RDS_ADMIN_PASSWORD')
RDS_ADMIN_PASSWORD = 'Hola1122334455'
DB_PASS = RDS_ADMIN_PASSWORD

APP_USER='admin'
APP_PASS='admin123'

print("Se procede a crear la DB:")
print("")
if not DB_PASS:
    raise Exception('Debes definir la variable de entorno RDS_ADMIN_PASSWORD con la contraseña del admin.')
    raise Exception('Se hace ejecutando "export RDS_ADMIN_PASSWORD=****"')

try:
    rds.create_db_instance(
        DBInstanceIdentifier=DB_INSTANCE_ID,
        AllocatedStorage=20,
        DBInstanceClass='db.t3.micro',
        Engine='mysql',
        MasterUsername=DB_USER,
        MasterUserPassword=DB_PASS,
        DBName=DB_NAME,
        PubliclyAccessible=True,
        BackupRetentionPeriod=0
    )
    

    print(f'Instancia RDS {DB_INSTANCE_ID} creada correctamente.')
except rds.exceptions.DBInstanceAlreadyExistsFault:
    print(f'La instancia {DB_INSTANCE_ID} ya existe.')
    print("")

db_info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
DB_HOST = db_info["DBInstances"][0]["Endpoint"]["Address"]

command = f"""
sudo mysql -h {DB_HOST} -u {DB_USER} -p"{DB_PASS}" {DB_NAME} < /var/www/init_db.sql
sudo tee /var/www/.env >/dev/null <<EOF
DB_HOST={DB_HOST}
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASS={DB_PASS}

APP_USER={APP_USER}
APP_PASS={APP_PASS}
EOF

sudo chown apache:apache /var/www/.env
sudo chmod 600 /var/www/.env
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
print("Se crea tabla de la DB y sus datos:")
print("")
print(output['StandardOutputContent'])