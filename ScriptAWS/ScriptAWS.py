import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

bucket_name = 'app-bucket-obligatorio-241688'
carpeta = '/home/franco/APP'

# Carpeta que se creará dentro del bucket para alojar archivos
carpeta_remota = "APP"

# Archivos locales que se van a subir
archivos = {
    f"{carpeta}/index.html": "index.html",
    f"{carpeta}/login.php": "login.php",
    f"{carpeta}/app.css": "app.css",
    f"{carpeta}/app.js": "app.js",
    f"{carpeta}/config.php": "config.php",
    f"{carpeta}/index.php": "index.php",
    f"{carpeta}/login.css": "login.css",
    f"{carpeta}/login.html": "login.html",
    f"{carpeta}/login.js": "login.js",
    f"{carpeta}/init_db.sql": "init_db.sql",
}

# Crear bucket (si no existe)
try:
    s3.create_bucket(Bucket=bucket_name)
    print(f"Bucket creado: {bucket_name}")
except ClientError as e:
    if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
        print(f"El bucket {bucket_name} ya existe y es tuyo.")
    else:
        print(f"Error creando bucket: {e}")
        exit(1)

print(f"Subiendo archivos a S3 carpeta: {carpeta_remota}/")

# Se suben los archivos al bucket dentro de /APP/
for local_path, file_name in archivos.items():

    # Key final: APP/archivo.extension
    s3_key = f"{carpeta_remota}/{file_name}"

    try:
        s3.upload_file(local_path, bucket_name, s3_key)
        print(f"Subido: {local_path}  →  s3://{bucket_name}/{s3_key}")
    except FileNotFoundError:
        print(f"ERROR: No existe el archivo local: {local_path}")
    except ClientError as e:
        print(f"ERROR subiendo {local_path}: {e}")

print("\nTodos los archivos fueron subidos correctamente.")
print(f"Carpeta remota en S3: s3://{bucket_name}/{carpeta_remota}/")

##### En esta parte el script va a crear un instancia EC2, y mover los archivos de la APP a sus directorios correspondientes

import boto3
import time

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

# Crear una instancia EC2 asociada al Instance Profile del rol LabRole
response = ec2.run_instances(
    ImageId='ami-06b21ccaeff8cd686',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.micro',
    IamInstanceProfile={'Name': 'LabInstanceProfile'},
)
instance_id = response['Instances'][0]['InstanceId']
print(f"Instancia creada con ID: {instance_id}")

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

# Copiar DIRECTAMENTE desde S3 al webroot
sudo aws s3 cp s3://{bucket_name}/{carpeta_remota}/ /var/www/html/ --recursive

# Mover init_db.sql FUERA del webroot
if [ -f /var/www/html/init_db.sql ]; then
    sudo mv /var/www/html/init_db.sql /var/www/
fi

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
    output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
    if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
        break
    time.sleep(2)
print("Output:")
print(output['StandardOutputContent'])