import discord
import valve.source.a2s
import paramiko
from threading import Thread
import time
from datetime import datetime, timedelta
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


def ark_ssh_exec(command):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=config['Ark Server']['ip'], username=config['Ark Server']['username'], password=config['Ark Server']['password'])
    ssh_client.exec_command(command)


def ark_get_serverinfo():
    global ark_playercount
    global ark_server_status
    ark_server_status = "unknown"
    server_address = (config['Ark Server']['ip'], int(config['Ark Server']['query_port']))
    while True:
        try:
            with valve.source.a2s.ServerQuerier(server_address) as server:
                ark_playercount = server.info()['player_count']
                ark_server_status = "online"
        except valve.source.NoResponseError:
            if ark_server_status == "starting":
                pass
            else:
                ark_server_status = "offline"
            ark_playercount = 0
        print(ark_server_status)
        print("Players online: {}".format(ark_playercount))
        time.sleep(10)


def ark_start_server():
    global ark_server_status
    ark_server_status = "starting"
    command = "timeout -k 360 300 ./arkserver start"
    ark_ssh_exec(command)
    print("Ark Server has been started!")


def ark_stop_server():
    command = "./arkserver stop"
    ark_ssh_exec(command)
    print("Ark Server has been stopped!")


def ark_get_serveridletime():
    global idle_time
    time_active = datetime.now()
    while True:
        global ark_server_status
        if ark_server_status == "starting":
            time_active = datetime.now()
        elif ark_server_status == "online":
            if ark_playercount > 0:
                time_active = datetime.now()
            idle_time = datetime.now() - time_active
            if idle_time > timedelta(minutes=30):
                print("Server has been idle for over 30 minutes, stopping server")
                ark_server_status = "offline"
                Thread(target=ark_stop_server).start()
            time.sleep(30)
        else:
            idle_time = "none"


thread1 = Thread(target=ark_get_serverinfo, daemon=True)
thread2 = Thread(target=ark_get_serveridletime, daemon=True)
thread1.start()
thread2.start()

client = discord.Client()


@client.event
async def on_ready():
    print(f"logged in as {client.user}")


@client.event
async def on_message(message):
    print(f"{message.channel}: {message.author}: {message.author.name}: {message.content}")

    if message.content.lower() == "!ark status" and str(message.channel) == "ark":
        await message.channel.send("The ark server is status is: {} and there are currently {} player(s) online! Server has been idle for {}".format(ark_server_status, ark_playercount, idle_time))

    if message.content.lower() == "!ark start" and str(message.channel) == str(config['Discord']['channel']):
        if ark_server_status == "starting":
            msg = "The ark server is already being started, this can take upto 2 minutes."
        elif ark_server_status == "online":
            msg = "The ark server is already started."
        elif ark_server_status == "unknown":
            msg = "Waiting for status, please try again in a bit!"
        elif ark_server_status == "offline":
            msg = "The Ark server will be started shortly, this can take upto 2 minutes."
            start_server = Thread(target=ark_start_server)
            start_server.start()
        else:
            msg = "Error, please contact an administrator"
        await message.channel.send(msg)

client.run(config['Discord']['token'])
