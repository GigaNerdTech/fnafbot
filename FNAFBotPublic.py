import discord
import re
import mysql.connector
from mysql.connector import Error
import subprocess
import time
import requests
import random
from discord.utils import get
import discord.utils
from datetime import datetime
import asyncio

intents = discord.Intents.all()
client = discord.Client(heartbeat_timeout=600,intents=intents)

connection = mysql.connector.connect(host='localhost', database='FNAFBot', user='REDACTED', password='REDACTED') 

game_results = ["You failed to stop Foxy and he hooked you. Game Over!","You stopped Foxy right in time and he returned to Pirate's Cove. You survived the night.","You failed to keep Freddy away and he stuffed you into a suit. Game over!","You stopped Freddy by freezing him via the cameras. You survived the night.","You failed at keeping Chica from finding you and her cupcake ate you. Game over!","Chica was stopped by the lights near your office. You survived the night.","Bonnie caught you watching him on the cameras. Game over!","Bonnie was avoided and he  searched for you elsewhere. You survived the night!"]

number_of_wins = {}

def reconnect_db():
    global connection
    if connection is None or not connection.is_connected():
        connection = mysql.connector.connect(host='localhost', database='AuthorMatonTest', user='REDACTED', password='REDACTED')
    return connection
  
async def log_message(log_entry):
    current_time_obj = datetime.now()
    current_time_string = current_time_obj.strftime("%b %d, %Y-%H:%M:%S.%f")
    print(current_time_string + " - " + log_entry, flush = True)
    
async def commit_sql(sql_query, params = None):
    global connection
    await log_message("Commit SQL: " + sql_query + "\n" + "Parameters: " + str(params))
    try:
        connection = reconnect_db()
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        connection.commit()
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
                
async def select_sql(sql_query, params = None):
    global connection
    await log_message("Select SQL: " + sql_query + "\n" + "Parameters: " + str(params))
    try:
        connection = reconnect_db()
        cursor = connection.cursor()
        result = cursor.execute(sql_query, params)
        records = cursor.fetchall()
        await log_message("Returned " + str(records))
        return records
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return None
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
			
async def execute_sql(sql_query):
    try:
        connection = reconnect_db()
        cursor = connection.cursor()
        result = cursor.execute(sql_query)
        return True
    except mysql.connector.Error as error:
        await log_message("Database error! " + str(error))
        return False
    finally:
        if(connection.is_connected()):
            cursor.close()
            connection.close()
            
            
async def send_message(message, response):
    await log_message("Message sent back to server " + message.guild.name + " channel " + message.channel.name + " in response to user " + message.author.name + "\n\n" + response)
    message_chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
    for chunk in message_chunks:
        await message.channel.send(">>> " + chunk)
        time.sleep(1)

@client.event
async def on_ready():
    global number_of_wins
    for guild in client.guilds:
        number_of_wins[guild.id] = {}
        for user in guild.members:
            number_of_wins[guild.id][user.id] = 0
            
    await log_message("Logged in!")		
	 
@client.event
async def on_guild_join(guild):
    number_of_wins[guild.id] = {}
    for user in guild.members:
        number_of_wins[guild.id][user.id] = 0
        
    await log_message("Joined guild " + guild.name)

@client.event
async def on_guild_remove(guild):
    await log_message("Left guild " + guild.name)

    
    
@client.event
async def on_member_remove(member):
    await log_message("Member " + member.name + " left guild " + member.guild.name)

    
@client.event
async def on_message(message):
    global game_results
    global number_of_wins
    
    if message.author == client.user:
        return
    if message.author.bot:
        return

            
    if message.content.startswith('~'):


        command_string = message.content.split(' ')
        command = command_string[0].replace('~','')
        parsed_string = message.content.replace("~" + command + " ","")
        if parsed_string == ',' + command:
            parsed_string = ''
            
        username = message.author.name
        server_name = message.guild.name

        await log_message("Command " + message.content + " called by " + username + " from " + server_name)
        if (command == 'sayhi'):
            await message.channel.send("Hello there, " + username + "!")
                
        elif (command == 'info' or command == 'help'):
            await send_message(message, "FNAF Bot\n\nCommands:\n`~play`: Play the game.\n`~stats`: Show your stats.")

        elif command == 'play':
            game_text = random.choice(game_results)
            if re.search("game over", game_text, re.IGNORECASE):
                number_of_wins[message.guild.id][message.author.id] = 0
            elif number_of_wins[message.guild.id][message.author.id] < 4:
                number_of_wins[message.guild.id][message.author.id] = number_of_wins[message.guild.id][message.author.id] + 1
            else:
                game_text = game_text + "\nYou've won five games in a row! Congratulations!"
                records = await select_sql("""SELECT FiveRuns FROM Stats WHERE ServerId=%s AND UserId=%s;""",(str(message.guild.id),str(message.author.id)))
                if not records:
                    result = await commit_sql("""INSERT INTO Stats (ServerId, UserId, FiveRuns) VALUES (%s, %s, %s);""",(str(message.guild.id),str(message.author.id),'0'))
                else:
                    for row in records:
                        new_count = int(row[0]) + 1
                    result = await commit_sql("""UPDATE Stats SET=%s WHERE ServerId=%s AND UserId=%s;""",(str(new_count),))
                number_of_wins[message.guild.id][message.author.id] = 0   
            
            await send_message(message, game_text)
            
        elif command == 'stats':
            records = await select_sql("""SELECT FiveRuns FROM Stats WHERE ServerId=%s AND UserId=%s;""",(str(message.guild.id),str(message.author.id)))
            if not records:
                await send_message(message, "No stats. Win five games in a row for a score.")
                return
            for row in records:
                stat = str(row[0])
            await send_message(message, "Your current five run stat is: " + stat)
        elif command == 'scoreboard':
            records = await select_sql("""SELECT UserId,FiveRuns FROM Stats WHERE ServerId=%s ORDER BY FiveRuns DESC;""",(str(message.guild.id),))
            if not records:
                await send_message(message, "Your server has no stats.")
                return
            response = "Server Leaderboard:\n\n"
            for row in records:
                response = response + discord.utils.get(message.guild.members, id=int(row[0])).name + " - " + str(row[1]) + "\n"
                
            await send_message(message, response)
            
        elif command == 'invite':
            await send_message(message, "Invite me: https://discord.com/api/oauth2/authorize?client_id=771555614966415372&permissions=536996928&scope=bot")
            
			
client.run('REDACTED')