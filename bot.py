import discord
from dotenv import load_dotenv
import os
import difflib


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
            }
        }
        self.images = self.setupFiles()
        self.helpEmbed = self.buildHelpEmbed()

    '''
    Command functions
    '''
    async def help(self, cmd, message):
        if len(cmd.split()) > 1:
            for c in self.cmdMapping.keys():
                # Check each valid command
                if cmd.endswith(c):
                    # If they are asking for help for that specific command..
                    await self.HelpSpecific(c, message)
                    return
            # Invalid command, search for the closest one
            closest = difflib.get_close_matches(' '.join(cmd.split()[1:]), self.cmdMapping.keys(), n=1)
            if len(closest) == 0:
                await message.channel.send(f"Enter `{self.PREFIX} help` for a list of commands")
            else:
                await self.HelpSpecific(closest[0], message, postTitle="(Closest match)")
        else:
            await message.channel.send(embed=self.helpEmbed, file=self.images['ereh.png'])

    async def comeback(self, cmd, message):
        await message.channel.send('NO')

    async def say(self, cmd, message):
        tosend = cmd.replace('stop', 'YAMEROOOOOO').split()[1:]
        await message.channel.send(' '.join(tosend))
        await message.delete()

    '''
    General functions
    '''

    async def HelpSpecific(self, c, message, postTitle=''):
        embed = discord.Embed(title=f"Help for `{c}` {postTitle}", description=self.cmdMapping[c]['arguments'], color=0x10ff10)
        embed.add_field(name="Short description", value=self.cmdMapping[c]['long_description'])
        embed.add_field(name="Usage", value=self.cmdMapping[c]['long_arguments'])
        embed.set_thumbnail(url="attachment://ereh4.jpg")
        embed.set_footer(text='[optional arg] <required arg>\nCase sensitive')
        await message.channel.send(embed=embed, file=self.images['ereh4.jpg'])

    def CleanCommand(self, cmd):
        cmd = cmd.replace(self.PREFIX, '')
        if cmd.startswith(' '):
            cmd = cmd[1:]
        return cmd

    # Setup all images in resources/ to be used
    def setupFiles(self):
        returnDict = {}
        files = os.listdir('resources')
        print(files)
        for f in files:
            dFile = discord.File(os.path.join('resources', f), filename=f)
            returnDict[f] = dFile
        print(returnDict)
        return returnDict

    # Normal help embed (ereh help)
    def buildHelpEmbed(self):
        imageName = 'ereh.png'
        embedVar = discord.Embed(title="Jaegerbomb Commands", description=f"Prefix: {self.PREFIX}", color=0x00ff00)
        for cmdName, cmdData in self.cmdMapping.items():
            if cmdData['visible']:
                embedVar.add_field(name=cmdName, value=f"{cmdData['description']}\n`{cmdData['arguments']}`", inline=True)
        embedVar.set_thumbnail(url=f"attachment://{imageName}")
        embedVar.set_footer(text='[optional arg] <required arg>\nCase sensitive')
        return embedVar

    '''
    Events
    '''
    async def on_message(self, message):
        if message.content.startswith(self.PREFIX) and message.author != client.user:
            # Handle command
            command = self.CleanCommand(message.content)
            done = False
            for i in self.cmdMapping.keys():
                if command.startswith(i):
                    await self.cmdMapping[i]['function'](command, message)
                    done = True
                    break
            if not done and len(command) > 0:
                await message.channel.send(f'Unknown command "{" ".join(command)}"')
            elif len(command) == 0:
                await message.channel.send("wat")


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('TOKEN')

    client = Jaegerbomb()
    client.setup()
    client.run(TOKEN)
