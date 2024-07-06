import discord
from discord.ext import commands
import subprocess
import os
import git
import time

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix=">>", intents=intents)

processes = {}

class Process:
	def __init__(self, process):
		self.startTime = time.time
		self.process = process

def cleanUp():
	for serverKey in processes:
		server = processes[serverKey]
		server.process.terminate()
		print(server.process.wait())

def command(args):
	process = subprocess.Popen(args)
	processes.append(process)

#events
@bot.event
async def on_ready():
	print('Bot started')

@bot.command()
async def run(ctx, arg):
	if arg in os.listdir("Repos"):
		if "run.txt" in os.listdir("Repos/" + arg):
			await ctx.send("Starting...")
			try:
				#cd so it is executed in it's folder
				cdCommand = "cd Repos/" + arg

				#get run command
				runFile = open("Repos/" + arg + "/run.txt")
				content = runFile.readlines()
				runCommand = content[0]

				fullCommand = cdCommand + " && " + runCommand
				process = subprocess.Popen(fullCommand, shell=True)

				processes[arg] = Process(process)
				await ctx.send("Server started")
			except Exception as e:
				await ctx.send("Couldn't start server:\n" + str(e))
		else:
			await ctx.send("Run file not present")
	else:
		await ctx.send(f"Git repo \"{arg}\" not cloned")
	return

@bot.command()
async def update(ctx, arg):
	return

@bot.command()
async def clone(ctx, *args):
	await ctx.send("Cloning...")
	try:
		git.Repo.clone_from(args[0], "Repos/" + args[1])
		await ctx.send("Successfully cloned repo")
	except Exception as e:
		await ctx.send("Failed to clone:\n" + e)
	return

@bot.command()
async def listCloned(ctx):
	await ctx.send("Cloned Repos:\n" + "\n".join(os.listdir("Repos")))
	return

@bot.command()
async def listRunning(ctx):
	await ctx.send("Running Servers:\n" + "\n".join(list(processes.keys())))
	return

#commands
@bot.command()
async def clean(ctx, *args):
	cleanUp()
	await ctx.send("Cleaned up processes")

#starting things
tokenFile = open("token.txt") #discord bot token (hidden)
content = tokenFile.readlines()
bot.run(content[0])