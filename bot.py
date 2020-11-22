import discord                      # Discord API
from dotenv import load_dotenv      # To load .env
import os
import difflib                      # Find close matches
import random
import datetime
import traceback                    # Provide traceback errors
import sqlite3                      # Database
import json
import functools
import time
import logging
import subprocess

import additional


class Jaegerbomb(discord.Client):
    def setup(self):
        # CONSTANTS
        self.PREFIX = "ereh"
        self.TALK_ACTIVE = False
        self.cmdMapping = {
            'help': {
                'description': 'Show help for all commands',
                'long_description': 'Show help for all commands',
                'arguments': f'{self.PREFIX} help [command]\n{self.PREFIX} help AI',
                'long_arguments': f'{self.PREFIX} help [command]\n{self.PREFIX} help say',
                'function': self.help,
                'visible': True
            },
            'say': {
                'description': 'Say some text',
                'long_description': 'Your message will be deleted and\nthe bot will say the text.',
                'arguments': f'{self.PREFIX} say <text>',
                'long_arguments': f'{self.PREFIX} say <text>\n{self.PREFIX} say Hello there',
                'function': self.say,
                'visible': True
            },
            'come back': {
                'description': 'hmm',
                'long_description': 'Tell ereh to come back',
                'arguments': f'{self.PREFIX} come back',
                'long_arguments': f'{self.PREFIX} come back',
                'function': self.comeback,
                'visible': False
            },
            'howgay': {
                'description': 'Rate gay percentage of you/someone accurately',
                'long_description': 'Accurately find the percentage of gay\nsomeone is (or yourself)',
                'arguments': f'{self.PREFIX} howgay [user]',
                'long_arguments': f'{self.PREFIX} howgay [user]\n{self.PREFIX} howgay (if you want yourself)',
                'function': self.douid,
                'visible': True
            }
        }

        self.defaultCmdData = {
            'lastCalled': 0,
            'callAmount': 1,
            'enabled': True
        }

        self.douidBots = additional.uidBots
        self.helpEmbed = self.buildHelpEmbed()
        self.setupDatabase()

        logger.info('Successfully run self.setup()')

    '''
    Decorators
    '''

    def cooldown(min, reply=True):
        def testDeco(func):
            async def wrapper(i, command, message):
                # Get the function Name, and cmdData (so cmdData[funcName] to find data in that function)
                funcName = func.__name__
                userID = message.author.id
                callTime = time.time()
                logger.info(f'Attempting cooldown of {funcName} by userID {userID} of {min}{"(Reply enabled)" if reply else ""}')

                createNew = False   # Create a new row in the database for the user

                try:
                    client.c.execute('SELECT * FROM cooldowns WHERE userID = ' + str(userID))
                    cmdData = client.c.fetchone()
                    logger.info(f'({userID}) Fetched cmdData from cooldowns table')
                    logger.debug(f'({userID}) cmdData raw: {cmdData}')
                    if isinstance(cmdData, tuple):  # Will return None if nothing fetched
                        cmdData = json.loads(cmdData[1])    # Get cmdData rather than userID
                        # Check if they wait long enough
                        lastCalled = int(cmdData[funcName]['lastCalled'])
                        nextAvailable = lastCalled + min + 1

                        logger.debug(f'({userID}) Last called: {lastCalled}\n({userID}) Next available: {nextAvailable}')

                        if nextAvailable > callTime:
                            logger.info(f'({userID}) Called too early')
                            # Need to call at 3s but called at 2s for example
                            # So if they called early
                            if reply:
                                return await message.channel.send(f'<@{userID}>, you need to wait {round(nextAvailable - callTime)}s before you can call this command again.')
                                logger.info(f'({userID}) Sent early message')
                        else:
                            logger.info(f'({userID}) Called on time')
                            # Called on time
                            cmdData[funcName]['lastCalled'] = callTime
                            logger.debug(f'({userID}) Changing callTime for {funcName} to {callTime}')
                            # Replace the values in that v row
                            client.c.execute('UPDATE cooldowns SET cmdData = ? WHERE userID = ?', (json.dumps(cmdData), int(userID)))
                            logger.info(f'({userID}) Updated cooldowns for cmdData')
                            logger.debug(f'cmdData: {json.dumps(cmdData)}')
                            client.conn.commit()
                            logger.info(f'({userID}) Committed to database')
                    else:
                        createNew = True
                        logger.info(f'({userID}) Will need to create new row for user')
                except ValueError:
                    logger.warning(f'Error using database:\n{traceback.format_exc()}')
                    createNew = True

                if createNew:
                    logger.info(f'({userID}) Creating a new row for user')
                    newCmdData = client.BuildCmdData()
                    newCmdData[funcName]['lastCalled'] = 0
                    print(f'{json.dumps(newCmdData, indent=4)}')
                    params = (userID, json.dumps(newCmdData))
                    client.c.execute('INSERT INTO cooldowns (userID, cmdData) VALUES (?, ?)', params)
                    client.conn.commit()
                    logger.info(f'({userID}) Committed to database')
                    logger.debug(f'({userID}) cmdData: {json.dumps(cmdData)}')

                await func(i, command, message)
                logger.info(f'Successfully ran {funcName}({i}, {command}, {message})')
            return wrapper
        return testDeco

    '''
    Command functions
    '''
    async def douid(self, cmd, message):
        cmd = cmd.split()
        if len(cmd) > 1:
            # They are referring to someone else
            if len(message.mentions) > 1:
                user = {'id': message.mentions[0].id, 'name': message.mentions[0].name, 'bot': message.mentions[0].bot}
            else:
                try:
                    id = int(cmd[1])
                    name = await self.fetch_user(id)
                    user = {'id': id, 'name': name, 'bot': False}
                except:
                    id = int(cmd[1][3:-1])
                    name = await self.fetch_user(id)
                    user = {'id': id, 'name': name, 'bot': False}
        else:
            # Themselves
            user = {'id': message.author.id, 'name': message.author.name, 'bot': message.author.bot}


        if user['bot'] or user['id'] in self.douidBots.keys():
            # If they are a bot, or have their name in additional
            try:
                results = self.douidBots[user['id']]
            except Exception:
                results = self.douidBots[0]
        else:
            # Regular user, do that
            score = await self.CalcUID(user['id'])
            score = int(score)
            results = {'msg': f'{user["name"]} is {score}% gay!', 'color': await self.JudgePercentageColour(score), 'desc': await self.JudgePercentageDesc(score)}

        embed = discord.Embed(title=results['msg'], color=results['color'])
        embed.add_field(name=results['desc'], value="Ereh has special accurate gaydar")
        embed.set_footer(text="best sexuality is freedom")
        await message.channel.send(embed=embed)

    @cooldown(3)
    async def help(self, cmd, message):
        userID = message.author.id
        defaultImage = "ereh.png"
        defaultImageFile = self.getFile(defaultImage)
        if len(cmd.split()) > 1:
            for c in self.cmdMapping.keys():
                # Check each valid command
                if cmd.endswith(c):
                    # If they are asking for help for that specific command..
                    await self.HelpSpecific(c, message)
                    logger.info(f'({userID}) Ran HelpSpecific() for command specific')
                    return
            # Invalid command, search for the closest one
            closest = difflib.get_close_matches(' '.join(cmd.split()[1:]), self.cmdMapping.keys(), n=1)
            logger.info(f'({userID}) Found closest match for {cmd}: {closest}')
            if len(closest) == 0:
                await message.channel.send(f"Enter `{self.PREFIX} help` for a list of commands")
            else:
                await self.HelpSpecific(closest[0], message, postTitle="(Closest match)")
            logger.info(f'({userID}) Completed specific help')
        else:
            await message.channel.send(embed=self.helpEmbed, file=defaultImageFile)
            logger.info(f'({userID}) Sent default command embed')

    @cooldown(10, reply=False)
    async def comeback(self, cmd, message):
        await message.channel.send('NO')
        logger.info(f'{message.author.id} asked comeback')

    @cooldown(2, reply=False)
    async def say(self, cmd, message):
        userID = message.author.id
        if len(message.mentions) != 0 or message.mention_everyone or len(message.role_mentions) != 0:
            logger.info(f'({userID}) Contained mentions in say()')
            await message.author.send(additional.sayMentionBlock)
            logger.info(f'({userID}) Sent dm to user')
            return
        tosend = cmd.replace('stop', 'YAMEROOOOOO').split()[1:]
        await message.channel.send(' '.join(tosend))
        await message.delete()
        logger.info(f'Completed say()')

    '''
    General functions
    '''

    async def JudgePercentageColour(self, perc):
        if perc < 10:
            return 0x00ff11
        elif perc < 20:
            return 0x44ff00
        elif perc < 30:
            return 0xaaff00
        elif perc < 40:
            return 0xc8ff00
        elif perc < 50:
            return 0xfbff00
        elif perc < 60:
            return 0xeeff00
        elif perc < 70:
            return 0xffd000
        elif perc < 80:
            return 0xff9500
        elif perc < 90:
            return 0xff5900
        else:
            return 0xff0000

    async def JudgePercentageDesc(self, perc):
        if perc < 10:
            return 'hm'
        elif perc < 20:
            return 'Very straight'
        elif perc < 30:
            return 'Straight I guess?'
        elif perc < 40:
            return 'Straight?'
        elif perc < 50:
            return "Hello Armin"
        elif perc < 60:
            return 'It seems Jaegerbomb has seen through you'
        elif perc < 70:
            return 'Gay in denial'
        elif perc < 80:
            return 'Quite gay ngl'
        elif perc < 90:
            return 'Extremely gay'
        else:
            return "I didn't actually think this level of gay is possible\nbut it seems it happened"

    async def CalcUID(self, uid, rounded=0):
        random.seed(uid/19.6)
        seed1 = random.random()
        random.seed(int(uid/2) * (random.randint(1, 54) / 1000))

        encoded = bin(int.from_bytes(str(uid).encode(), 'big'))
        encoded = '0b' + encoded[2:].replace('0', '.').replace('1', '0').replace('.', '1')
        uidInt = int(encoded, 2) ** (seed1*seed1)
        if uidInt > 1:
            while uidInt > 1:
                uidInt *= seed1

        now = datetime.datetime.now()
        avg = (now.day + now.month + now.year-2000 + now.hour)/120
        random.seed(avg + uid)
        seed3 = random.random()
        if round(seed1 * 1000 + int(avg)) % 2 == 0:
            if round(seed3 * 100) % 2 == 1:
                uidInt *= avg
            else:
                uidInt /= avg

        if uidInt > 1:
            uidInt = 1

        return round(uidInt * 100, rounded)

    async def HelpSpecific(self, c, message, postTitle=''):
        defaultImage = "ereh4.jpg"
        defaultImageFile = self.getFile(defaultImage)
        embed = discord.Embed(title=f"Help for `{c}` {postTitle}", description=self.cmdMapping[c]['arguments'], color=0x10ff10)
        embed.add_field(name="Short description", value=self.cmdMapping[c]['long_description'])
        embed.add_field(name="Usage", value=self.cmdMapping[c]['long_arguments'])
        embed.set_thumbnail(url=f"attachment://{defaultImage}")
        embed.set_footer(text='[optional arg] <required arg>\nCase sensitive')
        await message.channel.send(embed=embed, file=defaultImageFile)

    def CleanCommand(self, cmd):
        cmd = cmd.replace(self.PREFIX, '')
        if cmd.startswith(' '):
            cmd = cmd[1:]
        return cmd

    # Setup all images in resources/ to be used
    def getFile(self, fname):
        if os.path.isfile((os.path.join('resources', fname))):
            logger.info(f'getFile(): {fname} is file')
            return discord.File(os.path.join('resources', fname), filename=fname)
        logger.warning(f'getFile(): {fname} either doesnt exist, or is a folder')
        return None

    # Normal help embed (ereh help)
    def buildHelpEmbed(self):
        defaultImage = "ereh.png"
        defaultImageFile = self.getFile(defaultImage)
        embedVar = discord.Embed(title="Jaegerbomb Commands", description=f"Prefix: {self.PREFIX}", color=0x00ff00)
        for cmdName, cmdData in self.cmdMapping.items():
            if cmdData['visible']:
                embedVar.add_field(name=cmdName, value=f"{cmdData['description']}\n`{cmdData['arguments']}`", inline=True)
        embedVar.set_thumbnail(url=f"attachment://{defaultImage}")
        embedVar.set_footer(text='[optional arg] <required arg>\nCase sensitive')
        return embedVar

    def setupDatabase(self):
        new = not os.path.isfile(DATABASE_PATH)
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.c = self.conn.cursor()

        if new:
            self.c.execute('CREATE TABLE cooldowns (userID int, cmdData json)')    # Across all servers
            self.conn.commit()
            logger.info(f'Created new database')

    def BuildCmdData(self):
        funcNames = [i[1] for i in enumerate(self.cmdMapping.keys())]
        cmdData = {}
        for func in funcNames:
            cmdData[func] = self.defaultCmdData
        logger.info(f'BuildCmdData(): Built for {len(funcNames)} functions')
        return cmdData

    async def HandleCommand(self, i, command, message):
        func = self.cmdMapping[i]['function']
        logger.info(f'({message.author.id}) Called {func.__name__} with command {command}')
        return await func(command, message)

    '''
    Events
    '''

    async def on_message(self, message):
        try:
            if message.content.startswith(self.PREFIX) and message.author != client.user:
                # Handle command
                userID = message.author.id
                command = self.CleanCommand(message.content)
                done = False
                for i in self.cmdMapping.keys():
                    if command.startswith(i):
                        logger.info(f'({userID}) Called {i} with command "{command}"')
                        await self.HandleCommand(i, command, message)
                        logger.info(f'({userID}) Completed {i}')
                        done = True
                        break
                if not done and len(command) > 0:
                    logger.info(f'({userID}) Unknown command {"".join(command)}')
                    await message.channel.send(f'Unknown command "{"".join(command)}"')
                elif len(command) == 0:
                    await message.channel.send(f"Try typing ``{self.PREFIX} help`")
        except Exception:
            logger.error(f'({userID}) Error on_message() for message content "{message.content}\n{traceback.format_exc()}"')

    async def on_ready(self):
        logger.info('Bot is ready')

    async def on_connect(self):
        logger.info('Connected to Discord')

    async def on_disconnect(self):
        logger.info('Disconnected from Discord')

    async def on_error(self):
        logger.error()


def setupLogger(name, file, level):
    handler = logging.FileHandler(file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


VERSION = '1.2.0'
DATABASE_PATH = 'files/jaegerbomb.db'
LOGGING_LEVEL = 'debug'

if __name__ == "__main__":
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    now = datetime.datetime.now()
    loggingFn = f'logs/{now.day}-{now.month}-{now.year}.log'
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s', datefmt='%d/%m/%Y %I:%M:%S')

    logger = setupLogger("main", loggingFn, getattr(logging, LOGGING_LEVEL.upper()))

    load_dotenv()
    TOKEN = os.getenv('TOKEN')

    logger.info(f'Jaegerbomb v{VERSION} client starting with logging level {LOGGING_LEVEL.upper()}')
    logger.info(f'Database path: {DATABASE_PATH}')

    client = Jaegerbomb()
    client.setup()
    try:
        client.run(TOKEN)
    except Exception:
        logger.critical(f'Unexpected exception while running client:\n{traceback.format_exc()}')

    logger.info('Client ended')
