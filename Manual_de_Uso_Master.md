# 🖥️ Manual de Uso - Synapse Council (Nodo MASTER)

Bienvenido al nodo **Master** de Synapse Council v2.0. Este ordenador será el cerebro orquestador: alojará la base de datos, la interfaz web gráfica (React) y se comunicará con IAs en la nube como OpenRouter.

## Requisitos Previos
1. **Python 3.10+** y **Node.js** instalados.
2. Asegúrate de estar conectado a la misma red local (Wi-Fi o cable) que el ordenador Worker.

## Pasos de Instalación (Solo la primera vez)

Abre una terminal (PowerShell o CMD) en esta carpeta y ejecuta:

```bash
# 1. Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate

# 2. Instalar dependencias del backend
pip install -r backend\requirements.txt

# 3. Instalar dependencias del frontend
cd frontend
npm install
cd ..
```

## Configuración Opcional

Si vas a usar **OpenRouter** para modelos potentes en la nube (ej. Claude 3, GPT-4), abre el archivo `.env` que está en esta carpeta y añade tu clave:
`OPENROUTER_API_KEY=tu_clave_aqui`

## 🚀 Cómo Arrancar el Sistema

Para facilitarte la vida, solo tienes que hacer doble clic en el archivo:
👉 `start_master.bat`

Esto abrirá dos consolas:
1. Una con el **Backend** (FastAPI) en el puerto `8000`.
2. Otra con el **Frontend** (React) en el puerto `5173`.

> [!WARNING]
> La primera vez que lo arranques, el **Firewall de Windows** te pedirá permiso para que Python acceda a la red. Es VITAL que le des a **"Permitir"**, ya que el Master necesita enviar señales a la red local para descubrir automáticamente al Worker.

## Interfaz Web
Una vez arrancado, abre tu navegador y ve a:
👉 **http://localhost:5173**

## ¿Cómo sé si el Worker está conectado?
Gracias al sistema de auto-descubrimiento, no tienes que configurar IPs. 
Si el Worker está encendido en la misma red, el Master lo detectará automáticamente en menos de 5 segundos. Puedes comprobarlo abriendo esta URL en tu navegador:
👉 **http://localhost:8000/api/v1/network/peers**
Si ves la IP de tu otro ordenador ahí, ¡el sistema distribuido está listo para el debate!
