FROM python:3.10

WORKDIR /archipelago-manager-node
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Install Archipelago
RUN wget -O arch.tar.gz https://github.com/ArchipelagoMW/Archipelago/releases/download/0.6.0/Archipelago_0.6.0_linux-x86_64.tar.gz && tar -xzf arch.tar.gz && cp -r Archipelago/ /opt/ && rm -rf Archipelago arch.tar.gz
RUN cp scripts/ArchipelagoServer /usr/bin/

CMD ["fastapi", "run", "app/main.py"]
