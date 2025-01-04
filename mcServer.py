#!/usr/bin/python3

import discord
from discord.ext import commands, tasks
import asyncio
from mcstatus import JavaServer
import subprocess
import os
import git
import time
import signal
import shutil
import socket
import threading

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
log_file = "mc_server_logs.txt"

runCommand = [
	"java", 
	"-Xmx8192M", 
	"-Xms8192M", 
	"-jar", 
	"paper-1.21.3-82.jar"
]

buildCommand = [
	"mvn", 
	"package", 
	"-f", 
	"c:/Users/landonbakken/Documents/GitHub/Modded921-Plugins/modded921/pom.xml"
]

gitRepo = git.cmd.Git(raw_plugin_dir)

#When the ip is changed for the server, you need to edit here, the server config, and both the UDP and TCP port IPs
mcserver = JavaServer(localIP, 4082)

#setup intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=">>", intents=intents)

max_on_time = 30

logBuffer = []
logThread = None

errorInLogs = False
serverStartCtx = None

def readLogs():
	global logBuffer, errorInLogs

	#wait until server is on
	noStdout = True
	while noStdout:
		try:
			server.stdout #checking if stdout has started
			noStdout = False
		except:
			time.sleep(.1) #let the cpu live
	print("Started logging")
	#add to logbuffer until server is stopped
	while server != None:
		line = server.stdout.readline()
		if line:
			logBuffer.append(line.strip())
			
			if "ERROR" in line:
				errorInLogs = True
		else:
			time.sleep(.05) #let the cpu live


	print("Stopped logging")

def serverCommand(command):
	print(f"Sent command to server: \"{command}\"")
	server.stdin.write(command + "\n")
	server.stdin.flush()

def getLogsUntil(seconds = None, line = None, maxTime = 30):
	global logBuffer

	#clear the buffer
	logBuffer = []

	if seconds != None:
		time.sleep(seconds)
		logs = logBuffer
	elif line != None:
		logs = []

		#loop until either keyword is in logs or the max time has passed
		endTime = time.time() + maxTime
		while endTime > time.time():
			if logBuffer:

				#record line
				nextLine = logBuffer.pop(0)
				logs.append(nextLine)

				#exit if keyword is in the log
				if line in nextLine:
					return "\n".join(logs)
	else:
		return "must have end-log condition"

	return "\n".join(logs) if logs else "No new logs."

def serverOnline():
	try:
		mcserver.ping()
		return True
	except (ConnectionRefusedError, OSError) as e:
		return False
	
def stringToDiscordFile(inputString, filename):
	#write string to file
	with open(filename, "w") as file:
		file.write(inputString)
	
	#convert to discord file
	with open(filename, "rb") as file:
		discord_file = discord.File(file, filename=filename)

	return discord_file

def stopServer():
	global server

	#soft stop (so it saves worlds)
	serverCommand("stop")
	server.wait(timeout=20)

	#make sure it's dead
	server.terminate()
	server.wait()
	server = None

def startServer():
	global logThread, logBuffer, server

	server = subprocess.Popen(
		runCommand,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		cwd=f"{baseFolder}/Modded921",
		text=True,
		bufsize=1
	)

	#start logging
	logBuffer = []
	logThread = threading.Thread(target=readLogs, daemon=True)
	logThread.start()

	# Loop until on
	start_time = time.time()
	while time.time() - start_time < 60 and not serverOnline():
		time.sleep(0.5)  # so it doesn't ddos the server

	if time.time() - start_time >= 60:
		return False
	else:
		return True
	
async def sendLogError():
	global serverStartCtx, logBuffer

	logString = "\n".join(logBuffer)
	logBuffer = []

	#send as file since it's probably too big
	file = stringToDiscordFile(logString, "server_logs.txt")
	await serverStartCtx.send(f"The server had an error, here are the logs:", file=file)

@bot.command()
async def server(ctx, *args):
	global mcserver, server, logBuffer, serverStartCtx
 
	arg = args[0].lower()

	if serverOnline():
		if arg == "start":
			await ctx.send("server is already up")
		elif arg == "command":
			command = " ".join(args[1:])
			serverCommand(command)
			await ctx.send("Sent command")
		elif arg == "status":
			#get info
			status = mcserver.status()
			await ctx.send(f"{status.players.online} player{"" if status.players.online == 1 else "s"} with {status.latency} milliseconds of latency")
		elif arg == "logs":
			#log buffer (list) to string
			if len(logBuffer) > 0:
				logString = "\n".join(logBuffer)
				logBuffer = []
			else:
				logString = "No new logs"

			#convert to file since it't probably too big
			file = stringToDiscordFile(logString, "server_logs.txt")
			await ctx.send(f"Here are the logs since they were last given:", file=file)
		elif arg == "stop":
			message = await ctx.send("Stopping server...")

			stopServer()

			await message.edit(content="Server stopped")
	else:
		if arg == "stop":
			await ctx.send("The server was not running")
		elif arg == "start":
			message = await ctx.send("Starting server...")
			started = startServer()

			serverStartCtx = ctx

			if started:
				await message.edit(content="The server has been started")
			else:
				await message.edit(content="Server couldn't start or is taking over a minute to start")

		else:
			await ctx.send("The server is not running")
	
@bot.command()	
async def plugin(ctx, *args):
	arg = args[0].lower()
	fast = len(args) > 1 and args[1].lower() == "fast"
	if arg == "build":
		message = await ctx.send("Building...")

		try:
			subprocess.run(buildCommand, capture_output=True, text=True, check=True, shell=True)
		except subprocess.CalledProcessError as e:
			await message.edit(content="Error building plugin. DM me and don't try to fix the error yet; I want to implement a logging system, but couldn't test becasue I wasn't able to get it to throw an error")
			return

		#get all jar files
		await message.edit(content="Moving jar to server plugin folder...")
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

		#reload server if on, otherwise just notify that they were built
		if serverOnline():
			if fast:
				serverCommand("rl confirm")
				await message.edit(content="Done - Sent reload command, be wary of using this")
			else:
				await message.edit(content="Stopping Server...")
				stopServer()
				await message.edit(content="Restarting Server...")
				started = startServer()

				if started:
					await message.edit(content="Restart Complete")
				else:
					await message.edit(content="Server couldn't start or is taking over a minute to start")
		else:
			await message.edit(content="Plugins built")

@bot.command()
async def git(ctx, arg):
	global mcserver
	arg = arg.lower()
	if arg == "pull":
		try:
			message = await ctx.send("Pulling...")
			gitRepo.pull()
			await message.edit(content="Git pull successful")
		except:
			await message.edit(content="Git was not able to pull")

@bot.event
async def on_ready():
    check_variable_loop.start()  # Start the loop when the bot is ready

@tasks.loop(seconds=1)
async def check_variable_loop():
    global errorInLogs
    # Add your logic here
    if errorInLogs:
        await sendLogError()
    errorInLogs = False

@check_variable_loop.before_loop
async def before_check_variable_loop():
    await bot.wait_until_ready()  # Ensure bot is ready before starting the loop

#starting things
bot.run(token)
