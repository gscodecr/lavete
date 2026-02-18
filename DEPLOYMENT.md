# Guía de Despliegue en AWS Lightsail (Ubuntu)

Esta guía describe paso a paso cómo desplegar la aplicación **La Vete** en un servidor AWS Lightsail utilizando **Ubuntu 22.04 LTS** (o superior).

---

## 1. Prerrequisitos

- Cuenta activa en AWS Console.
- Dominio comprado (opcional pero recomendado para HTTPS).

### 1.1 Crear Instancia
1. Ir a **AWS Lightsail**.
2. Click en **Create instance**.
3. Seleccionar **Platform**: Linux/Unix.
4. Seleccionar **Blueprint**: **OS Only** -> **Ubuntu 22.04 LTS** (o 24.04).
5. Elegir un plan (el de $5 o $10 USD suele ser suficiente para empezar).
6. Darle un nombre a la instancia (ej: `lavete-prod`) y crear.

### 1.2 Configurar Networking
1. Entrar a la instancia creada en Lightsail.
2. Ir a la pestaña **Networking**.
3. En **IPv4 Firewall**, asegurarse de tener abiertos los puertos:
   - **SSH (22)**
   - **HTTP (80)**
   - **HTTPS (443)**
4. (Recomendado) Crear una **Static IP** y adjuntarla a la instancia.

---

## 2. Configuración Inicial del Servidor

Conéctate a tu instancia vía SSH (usando el botón "Connect using SSH" del navegador o tu terminal).

### 2.1 Actualizar el Sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Instalar Herramientas Necesarias
Instalaremos Python, pip, entorno virtual, Nginx (servidor web) y Git.
```bash
sudo apt install -y python3-pip python3-venv nginx git acl
```

---

## 3. Instalación de la Aplicación

### 3.1 Clonar el Repositorio
Usaremos el directorio `/var/www/lavete`.

```bash
# Crear directorio y asignar permisos (reemplaza 'ubuntu' si tu usuario es otro)
sudo mkdir -p /var/www/lavete
sudo chown ubuntu:ubuntu /var/www/lavete
cd /var/www/lavete

# Clonar repositorio (usa tu URL de Github/Bitbucket)
# Si es privado, necesitarás configurar una SSH Key o usar Token
git clone https://github.com/TU_USUARIO/lavete-admin.git .
```

### 3.2 Configurar Entorno Python
```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar e instalar dependencias
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn uvloop # Recomendado para producción
```

### 3.3 Configurar Variables de Entorno
Crea el archivo `.env` de producción.
```bash
cp .env.example .env
nano .env
```
Edita los valores, especialmente:
- `DATABASE_URL`: Si usas SQLite local, `sqlite+aiosqlite:////var/www/lavete/lavete.db` (nota las 4 barras para ruta absoluta). Si usas PostgreSQL (recomendado), pon la URL de conexión.
- `SECRET_KEY`: Genera una clave segura.

### 3.4 Configurar Base de Datos

Tienes tres opciones principales:

#### Opción A: SQLite (Más simple - Archivo Local)
Ideal para prototipos o bajo tráfico. No requiere instalación extra.
1. Edita tu `.env`:
   ```bash
   DATABASE_URL=sqlite+aiosqlite:////var/www/lavete/lavete.db
   ```
   *(Nota: Son 4 barras `/` al inicio para indicar ruta absoluta)*

#### Opción B: AWS Managed Database (PostgreSQL) - *Recomendado para Prod*
1. Crea la DB en la consola de Lightsail (Pestaña Databases).
2. Copia el Endpoint, Usuario y Password.
3. Actualiza tu `.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://dbmasteruser:password@ls-xxx.region.rds.amazonaws.com:5432/dbmaster
   ```

#### Opción C: PostgreSQL Local (Self-Hosted)
Si deseas PostgreSQL sin pagar extra por el servicio gestionado:

1. **Instalar**: `sudo apt install -y postgresql postgresql-contrib libpq-dev`
2. **Configurar**:
   ```bash
   sudo -u postgres psql
   # En psql:
   CREATE DATABASE lavetedb;
   CREATE USER laveteuser WITH PASSWORD 'tu_password';
   GRANT ALL PRIVILEGES ON DATABASE lavetedb TO laveteuser;
   -- Para Postgres 15+:
   GRANT ALL ON SCHEMA public TO laveteuser;
   \q
   ```
3. **Actualizar .env**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://laveteuser:tu_password@localhost/lavetedb
   ```

### 3.5 Inicializar Base de Datos
```bash
alembic upgrade head
```

---

## 4. Configurar el Servicio (Systemd)

Para que la aplicación corra siempre (incluso si se reinicia el servidor).

### 4.1 Crear archivo de servicio
```bash
sudo nano /etc/systemd/system/lavete.service
```

Pega el siguiente contenido:

```ini
[Unit]
Description=Gunicorn instance to serve La Vete
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/lavete
Environment="PATH=/var/www/lavete/.venv/bin"
ENVIRONMENT_FILE=/var/www/lavete/.env
ExecStart=/var/www/lavete/.venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```
*(Ajusta `User` si es diferente a `ubuntu`)*.

### 4.2 Iniciar el servicio
```bash
sudo systemctl start lavete
sudo systemctl enable lavete
sudo systemctl status lavete
```
*(Deberías ver "Active: active (running)")*

---

## 5. Configurar Nginx (Reverse Proxy)

Nginx recibirá las peticiones del exterior (puerto 80) y las pasará a nuestra app (puerto 8000).

### 5.1 Crear configuración de sitio
```bash
sudo nano /etc/nginx/sites-available/lavete
```

Pega el siguiente contenido (reemplaza `tu-dominio.com` o la IP pública):

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com; # O tu IP pública si no tienes dominio

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Opcional: Servir archivos estáticos directamente con Nginx para mejor rendimiento
    location /static {
        alias /var/www/lavete/app/static;
    }
}
```

### 5.2 Activar sitio
```bash
sudo ln -s /etc/nginx/sites-available/lavete /etc/nginx/sites-enabled/
sudo nginx -t # Verificar sintaxis
sudo systemctl restart nginx
```

Ahora deberías poder acceder a tu aplicación vía HTTP usando tu IP o dominio.

---

## 6. Configurar SSL (HTTPS)

Si tienes un dominio apuntando a tu IP, usa Certbot para activar HTTPS gratis.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```
Sigue las instrucciones y elige "Redirect" para forzar HTTPS.

---

## 7. Pasos para Futuros Deploys (Actualizaciones)

Cada vez que hagas cambios en tu código y los subas a GitHub, sigue estos pasos en el servidor para actualizar:

### Script Rápido (Opcional)
Puedes crear un script `deploy.sh` en `/var/www/lavete`:

```bash
#!/bin/bash
cd /var/www/lavete
echo "Descargando cambios..."
git pull origin main

echo "Actualizando dependencias..."
source .venv/bin/activate
pip install -r requirements.txt

echo "Ejecutando migraciones..."
alembic upgrade head

echo "Reiniciando servicio..."
sudo systemctl restart lavete

echo "Deployment finalizado con éxito!"
```

Dale permisos de ejecución: `chmod +x deploy.sh`.

### Ejecución Manual
Simplemente corre los comandos del script:
1. `cd /var/www/lavete`
2. `git pull`
3. `source .venv/bin/activate && pip install -r requirements.txt` (si hubo cambios en librerías)
4. `alembic upgrade head` (si hubo cambios en BD)
5. `sudo systemctl restart lavete`
