FROM python:3.10.12

# install Debian and other dependencies that are required to run python apps(eg. git, python-magic).
RUN apt-get update \
  && apt-get install -y --force-yes \
    chrpath \
    ffmpeg \
    fonts-liberation \
    fontconfig \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

RUN fc-cache -f -v

# Copy the requirements file
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install -r /app/requirements.txt

#RUN apt-get install zlib-dev jpeg-dev gcc musl-dev

# RUN apt-get install -y fontconfig
# RUN apt-get update && apt-get install -y fonts-liberation
# RUN apt-get install -y fonts-freefont-ttf


# RUN pip install bitsandbytes==0.39.0

# Copy over the rest of the files.
COPY contract_interaction.py /app/contract_interaction.py
COPY generate_nft.py /app/generate_nft.py
COPY karaokebackgroundnft.jpg /app/karaokebackgroundnft.jpg
COPY telegram_karaoke_bot.py /app/telegram_karaoke_bot.py
COPY process_audio.py /app/process_audio.py
COPY data/ /app/data/
COPY contract.json /app/contract.json


# Set the working directory
WORKDIR /app

# Expose the port
EXPOSE 8000

# Run the command to start the server
CMD ["python", "telegram_karaoke_bot.py" ]
