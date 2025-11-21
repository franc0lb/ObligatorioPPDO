# Importamos librerias necesarias que se utilizaran para las tareas que realiza el script
import boto3
import os
from botocore.exceptions import ClientError
import time 
import requests # libreria para bajar archivos desde github
# librerias para maniuplar archivos zi
import zipfile
import io

####################################################################################
# CHEQUEO DE VARIABLES DE ENTORNO
####################################################################################
# La password de la app y de la db deben venir de variables de entorno
DB_PASS = os.environ.get('RDS_ADMIN_PASSWORD')
APP_PASS= os.environ.get('RDS_APP_PASSWORD')

# Si no se definen las variables de entorno entonces da error
if not DB_PASS:
    print("")
    raise Exception('Debes definir la variable de entorno RDS_ADMIN_PASSWORD con la contraseña del admin, se hace ejecutando "export RDS_ADMIN_PASSWORD=****"')
if not APP_PASS:
    print("")
    raise Exception('Debes definir la variable de entorno RDS_APP_PASSWORD con la contraseña para user admin de la app, se hace ejecutando "export RDS_APP_PASSWORD=****"')

######################################################################################################################################
# 1: CREACION DEL BUCKET Y SUBIDA DE ARCHIVOS AL MISMO
######################################################################################################################################

s3 = boto3.client('s3')

# Defino nombre del bucket, carpeta local donde voy a alojar los archivos de la app y la carpeta remota que es la carpeta del S3 donde voy a subir los archivos
bucket_name = 'app-bucket-obligatorio-241688'
carpeta_base = '/tmp/archivosRepo'
carpeta_remota = 'APP'
# Defino una variable que contiene el link de descarga de mi repo zipeado
github_zip_url = "https://github.com/franc0lb/ObligatorioPPDO/archive/refs/heads/main.zip"

print("Descargando repo desde GitHub...")
# La variable r baja el repo
r = requests.get(github_zip_url)
# La variable z abre el zip
z = zipfile.ZipFile(io.BytesIO(r.content))

# Crear la carpeta base
os.makedirs(carpeta_base, exist_ok=True)

# Extraer ZIP dentro de la carpeta base (local)
z.extractall(carpeta_base)

# repo_root arma la ruta a la carpeta principal del repo extraido en la carpeta local - /tmp/archivosRepo/ObligatorioPPDO-main/
repo_root = os.path.join(carpeta_base, "ObligatorioPPDO-main")

# Acá armo la ruta hacia la subcarpeta del repo - /tmp/archivosRepo/ObligatorioPPDO-main/ScriptAWS/archivosSubir , donde se alojan los archivos de la app
carpeta_local = os.path.join(repo_root, "ScriptAWS", "archivosSubir")

# Listar archivos (solo nombres) de los archivos alojados en /tmp/archivosRepo/ObligatorioPPDO-main/ScriptAWS/archivosSubir
archivos = os.listdir(carpeta_local)
# Hago un print para mostrar por pantalla que archivos que corresponde a la app se bajaron
print(f"Archivos de la APP que se bajaron de GitHub: {archivos}")
print("")

# Se crea el bucket si no existe
try:
    s3.create_bucket(Bucket=bucket_name)
    print(f"Creando Bucket: {bucket_name}")
except ClientError as e:
    if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
        print(f"Error creando bucket: {e}")
        exit(1)

print("")
print(f"Subiendo archivos a s3://{bucket_name}/{carpeta_remota}/")
print("")

# Como ya tengo localizados y descargados los archivos en la carpeta local entonces procedo a subirlos uno por uno hacia el S3 en una carpeta llamada APP
# El for recorre la lista archivos, y setea la variable nombre que en cada iteración su valor es el nombre de los archivos que se van a subir, la lista archivos contiene todos los nombres de los archivos que están en la carpeta local
for nombre in archivos:
    arch_local = os.path.join(carpeta_local, nombre) # Se arma la ruta de cada uno de los archivos, carpeta_local es la ruta al directorio en el tmp, nombre toma el valor del archivo, se unen y generan la ruta completa a ese archivo específico
    s3_key = f"{carpeta_remota}/{nombre}" # Esta es la ruta remota en el S3, que corresponde a APP/archivo

    # Se sube uno por uno los archivos
    try:
        s3.upload_file(arch_local, bucket_name, s3_key) # Se indica que se suba el archivo (ruta completa alojada en arch_local), al bucket S3 previamente creado, en la ruta remota contenida en s3_key
        print(f"Subido: {arch_local} → s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"ERROR subiendo {arch_local}: {e}")

print("")
print(f"Archivos subidos correctamente a {bucket_name}")
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

# Esperar a que la instancia esté en estado running, si no no podemos correr comandos todavía
ec2.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])

# Parte 2: Enviar comandos y extraer resultados
# Estoy instalando los paquetes necesarios, carpetas, y descargando y moviendo los archivos
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

# El comando sync baja todos los archivos alojados en APP en el S3 dentro de /var/www/html menos el de la DB porque no lo queremos en esa ubicación
sudo aws s3 sync s3://{bucket_name}/{carpeta_remota}/ /var/www/html/ --exclude "init_db.sql"
sudo aws s3 cp s3://{bucket_name}/{carpeta_remota}/init_db.sql /var/www/

# Se setea propietario de la carpeta, que debe ser el usuario apache
sudo chown -R apache:apache /var/www

# Reiniciamos servicio de apache
sudo systemctl restart httpd
"""

# Los comandos se ejecutan usando ssm, se le indica ID de la instancia
response = ssm.send_command(
    InstanceIds=[instance_id],
    DocumentName="AWS-RunShellScript",
    Parameters={'commands': [command]}
)
# El id del comando me permite luego preguntar si el comando terminó, falló o está corriendo
command_id = response['Command']['CommandId']

# Esperar resultado de los comandos
while True:
    try:
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break
        time.sleep(2)
    except ssm.exceptions.InvocationDoesNotExist:
        # Se agrega esto para evitar errores cuando el comando aún no fue recibido por el agente SSM, el pass hace que se ignore que el comando todavía no fue recibido y vuelva a intentar
        pass
    time.sleep(3) # Se hace un pequeño delay antes de volver al bucle
# Una vez se ejecutaron los comandos se muestra por pantalla sus salidas
print("EJECUCION DE COMANDOS E INSTALACION DE PAQUETES:")
print("")
print(output['StandardOutputContent'])



######################################################################################################################################
# 3: CREACION DE SECURITY GROUPS
######################################################################################################################################

ec2 = boto3.client('ec2')

print("Creación de Security Groups:")
print("")

#######################################################################
# SG 1 → Security Group para la instancia EC2
#######################################################################
sg_ec2_name = 'web-sg-boto3' # se crea sg para la instancia de ec2 con el nombre web-sg-boto3

try:
    response = ec2.create_security_group(
        GroupName=sg_ec2_name,
        Description='Permitir HTTP y permitir salida hacia RDS'
    )
    sg_ec2_id = response['GroupId']
    print(f"Security Group EC2 creado: {sg_ec2_id}")

    # Reglas de entrada (inbound) HTTP
    # Se define que se permita el tráfico tcp hacia el puerto 80 de la instancia desde cualquier red
    ec2.authorize_security_group_ingress(
        GroupId=sg_ec2_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

# Se manda un error en caso de que ya exista el sg
except ClientError as e:
    if 'InvalidGroup.Duplicate' in str(e):
        sg_ec2_id = ec2.describe_security_groups(GroupNames=[sg_ec2_name])['SecurityGroups'][0]['GroupId']
        print(f"Security Group EC2 ya existe: {sg_ec2_id}")
    else:
        raise

#######################################################################
# SG 2 → Security Group exclusivo para RDS (permite conexión desde EC2)
#######################################################################
sg_rds_name = 'rds-mysql-sg'   # Este es el sg para la instancia rds donde corre la db, se debe permitir el tráfico tcp hacia el puerto de mysql desde el sg de ec2

# Creo el sg para ec2
try:
    response = ec2.create_security_group(
        GroupName=sg_rds_name,
        Description='Permitir MySQL desde la instancia EC2'
    )
    sg_rds_id = response['GroupId']
    print(f"Security Group RDS creado: {sg_rds_id}")

    # Permitir tráfico de MySQL desde el SG de la instancia EC2
    ec2.authorize_security_group_ingress(
        GroupId=sg_rds_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 3306,
                'ToPort': 3306,
                'UserIdGroupPairs': [{'GroupId': sg_ec2_id}]
            }
        ]
    )
    
# Si ya existe el sg de rds se manda error
except ClientError as e:
    if 'InvalidGroup.Duplicate' in str(e):
        sg_rds_id = ec2.describe_security_groups(GroupNames=[sg_rds_name])['SecurityGroups'][0]['GroupId']
        print(f"Security Group RDS ya existe: {sg_rds_id}")
    else:
        raise

print("")
print("Los Security Groups están creados y configurados correctamente.")
print("")

#######################################################################
# Asociar SG EC2 a la instancia
#######################################################################
print("")
print(f"Usando instancia creada anteriormente: {instance_id}")
print("")
print("Esperando que la instancia esté en estado 'running' para asociar SG...")
ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
print("Instancia en estado running.")

# Asociar
ec2.modify_instance_attribute(InstanceId=instance_id, Groups=[sg_ec2_id])
print(f"SG {sg_ec2_id} asociado a la instancia {instance_id}")
print("")



######################################################################################################################################
# 4: CREACION DE BASE DE DATOS RDS
######################################################################################################################################
# Parámetros
rds = boto3.client('rds')
DB_INSTANCE_ID = 'app-mysql'
DB_NAME = 'app'
DB_USER = 'admin'
APP_USER='admin'
# Las contraseñas se setearon al principio del script, son variables de entorno
# VpcSecurityGroupIds es la lista de sg asignados a rds, osea los que se pueden conectar a la base
try:
    rds.create_db_instance(
        DBInstanceIdentifier=DB_INSTANCE_ID,
        VpcSecurityGroupIds=[sg_rds_id],
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

# Espero a que RDS esté activo para proceder a extraer info de la instancia rds (el endpoint)
rds.get_waiter('db_instance_available').wait(DBInstanceIdentifier=DB_INSTANCE_ID)
db_info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
DB_HOST = db_info["DBInstances"][0]["Endpoint"]["Address"]
# Corro comandos dentro de la instancia RDS
command = f"""
# Me conecto a la base mysql, y le ejecuto init_db.sql para cargar tablas, usuarios etc
sudo mysql -h {DB_HOST} -u {DB_USER} -p"{DB_PASS}" {DB_NAME} < /var/www/init_db.sql 
# Creo el archivo .env que contiene las variables de entorno que va a usra la app web
sudo tee /var/www/.env >/dev/null <<EOF  
DB_HOST={DB_HOST}
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASS={DB_PASS}
APP_USER={APP_USER}
APP_PASS={APP_PASS}
EOF
# Asingacion de permisos/propietarios
sudo chown apache:apache /var/www/.env
sudo chmod 600 /var/www/.env
"""
# Se envían los comandos por ssm
response = ssm.send_command(
    InstanceIds=[instance_id],
    DocumentName="AWS-RunShellScript",
    Parameters={'commands': [command]}
)
command_id = response['Command']['CommandId']

while True:
    try:
        output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )

        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break

    except ssm.exceptions.InvocationDoesNotExist:
        # El comando todavía no está listo, misma lógica que con la instancia ec2
        pass

    time.sleep(2) 
