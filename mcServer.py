#!/usr/bin/python3

import discord
from discord.ext import commands
from mcstatus import JavaServer
import subprocess
import os
import git
import time
import signal
import shutil
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
localIP = s.getsockname()[0]
s.close()

#discord bot token and base folder (hidden) 
hiddenInfo = open("hiddenInfo.txt").readlines()
token = hiddenInfo[0]
baseFolder = hiddenInfo[1].strip() #strip is for possible return chars

start_file_dir = baseFolder + "/Modded921/start.bat"
plugin_dir = baseFolder + "/Modded921/plugins"
plugin_xml_dir = baseFolder + "/Modded921-Plugins/modded921/pom.xml"
raw_plugin_dir = baseFolder + "/Modded921-Plugins"

build_dir = baseFolder + "/Modded921-Plugins/modded921/target"
target_dir = baseFolder + "/Modded921/plugins"

buildCommand = [
    "mvn", 
    "package", 
    "-f", 
    r"c:\Users\landonbakken\Documents\GitHub\Modded921-Plugins\modded921\pom.xml"
]
print(buildCommand)

gitRepo = git.cmd.Git(raw_plugin_dir)

#When the ip is changed for the server, you need to edit here, the server config, and both the UDP and TCP port IPs
mcserver = JavaServer(localIP, 4082)

#setup intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=">>", intents=intents)

max_on_time = 30

def serverCommand(command):
	print(f"Did command \"{command}\"")
	server.stdin.write(command + "\n")
	server.stdin.flush()

def countForServer(server):
	global mcserver, max_on_time
	on_time = 0
	time.sleep(30) #wait untill the server is actually on
	while on_time < max_on_time:
		try:
			if mcserver.status.players.online == 0:
				on_time += 1
				time.sleep(1)
			else:
				on_time = 0
		except:
			return
	os.killpg(os.getpgid(server.pid), signal.SIGTERM)


def start_server():
	server = subprocess.Popen(
		["cmd.exe", "/c", start_file_dir],  # Replace with your script name
		stdin=subprocess.PIPE,
		#stdout=subprocess.PIPE,
		#stderr=subprocess.PIPE,
		text=True,
		bufsize=1,
	)
	return server

@bot.command()
async def server(ctx, *args):
	global mcserver, server
 
	arg = args[0].lower()
 
	if arg == "start":
		try:
			mcserver.ping()
			await ctx.send("server is already up")
		except ConnectionRefusedError:
			await ctx.send("Starting server...")
			server = start_server()
			time.sleep(10)
			await ctx.send("The server is up")
	elif arg == "stop":
		try:
			mcserver.ping()
			await ctx.send("Stopping server...")
			serverCommand("stop")
			server.wait(timeout=10)
			server.terminate()
			server.wait()
			await ctx.send("Server stopped")
		except ConnectionRefusedError:
			await ctx.send("The server was not running")
	elif arg == "command":
		try:
			mcserver.ping()
			command = " ".join(args[1:])
			serverCommand(command)
		except ConnectionRefusedError:
			await ctx.send("The server is not running")
	elif arg == "status":
		try:
			status = mcserver.status()
			if status.players.online == 1:
				await ctx.send(f"{status.players.online} player with {status.latency} milliseconds of latency")
			else:
				await ctx.send(f"{status.players.online} players with {status.latency} milliseconds of latency")
		except ConnectionRefusedError:
			await ctx.send("The server is not running")
	
@bot.command()	
async def plugin(ctx, *args):
	arg = args[0].lower()
	if arg == "build":
		await ctx.send("Building...")

		try:
			result = subprocess.run(buildCommand, capture_output=True, text=True, check=True, shell=True)
			print("Command executed successfully!")
			print("Output:\n", result.stdout)
		except subprocess.CalledProcessError as e:
			print("Error executing command.")
			print("Return Code:", e.returncode)
			print("Error Output:\n", e.stderr)

		await ctx.send("Moving Plugin File...")

		#get all jar files
		jar_files = [f for f in os.listdir(build_dir) if f.endswith('.jar')]

		# Find the newest file
		newest_file = max(
			jar_files,
			key=lambda f: os.path.getctime(os.path.join(build_dir, f))
		)

		# Construct full paths
		source_path = os.path.join(build_dir, newest_file)
		destination_path = os.path.join(target_dir, newest_file)

		# Move the file
		shutil.move(source_path, destination_path)

		try:
			mcserver.ping()
			await ctx.send("Reloading Server Plugins...")
			command = " ".join(args[1:])
			serverCommand(command)
		except ConnectionRefusedError:
			await ctx.send("Plugins built")
			return
		
		await ctx.send("Plugins built and refreshed")
		






@bot.command()
async def git(ctx, arg):
	global mcserver
	arg = arg.lower()
	if arg == "pull":
		try:
			gitRepo.pull()
			await ctx.send("Git pull successful")
		except:
			await ctx.send("Git was not able to do a pull request")

@bot.command()
async def die(ctx):
	await ctx.send("Bye (:")
	exit()

#starting things
bot.run(token)
