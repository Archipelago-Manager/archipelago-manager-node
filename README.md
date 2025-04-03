# Archipelago Manger Node
A server node running several [Archipelago](https://github.com/ArchipelagoMW/Archipelago) servers.
Communicates with, and is separated from [Archipelago-Manager/archipelago-manager-backend](https://github.com/Archipelago-Manager/archipelago-manager-backend) because it will be more resource intensive and is made to be separatedly scalable.
It is made to be called from the [archipelago-manager-backend](https://github.com/Archipelago-Manager/archipelago-manager-backend) but could theoretically be used stand-alone.

### The node has(/will have) the following features:
  - [FastAPI](https://github.com/fastapi/fastapi) API that can create, start, stop, send, read commmands, etc. from Archipelago servers
  - Automatic leveraging of open ports, defined using environment variables

## How to run
### Local development
  - Create a virtual environment using python3.10 `python3.10 -m venv env && source env/bin/activate`
  - Install requirements `pip --upgrade pip && pip install -r requirements.txt`
  - Start the development FastAPI server `fastapi dev app/main.py --port 8001` (--port 8001 to not collide with the back end)


### Local deployment
TODO

### Remote deployment
TODO

