FROM python:3.6
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt
RUN git clone https://github.com/ann2014/data602-assignment2 /usr/src/app/tw
EXPOSE 5000
CMD [ "python", "/usr/src/app/tw/app.py"]
