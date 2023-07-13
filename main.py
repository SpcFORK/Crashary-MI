import asyncio
import discord
import os
import sqlite3
import aiohttp
import random
import math

from bs4 import BeautifulSoup

from msal import PublicClientApplication
from threading import Thread, Lock
from dotenv import load_dotenv
from tokenstuff import *
from realmchecking import *
from datetime import datetime, timedelta

# Extract the Xuids to invite from the txt
file_path = "playerxuids.txt"
with open(file_path, "r") as file:
  # Step 2: Initialize an empty list
  playerxuids = []

  # Step 3: Read each line and append its content to the list
  for line in file:
    playerxuids.append(line.strip())

random.shuffle(playerxuids)
# playerxuids = playerxuids[::1]

load_dotenv()

# Get the directory where the Python script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the relative path to the database file
db_file_path = os.path.join(script_dir, "UserInfo.db")
# Connect to the SQLite database
conn = sqlite3.connect(db_file_path)
c = conn.cursor()

# Set currently inviting to false
c.execute("UPDATE invitetable SET currentlyinviting = 'False'")
conn.commit()

bot = discord.Bot()

oxblkey = os.getenv("XBL_IO_KEY")

logschannel = bot.get_partial_messageable(1128355347363541073)

embedthink = discord.Embed(
  title="",
  color=discord.Colour.red(),
)

embedthink.add_field(
  name="The bot is processing your request. This may take up to 5 seconds...",
  value="",
)

# Dictionary to store ongoing link processes
ongoing_processes = {}


# Ansi-Gen
def ansify(col, string):
  reset = "\u001b[0m"
  
  colors = {
    "black": "\u001b[30m",
    "red": "\u001b[31m",
    "green": "\u001b[32m",
    "yellow": "\u001b[33m",
    "blue": "\u001b[34m",
    "magenta": "\u001b[35m",
    "cyan": "\u001b[36m",
    "white": "\u001b[37m",
    "reset": reset
  }

  if col in colors:
    return colors[col] + string + reset
  else:
    return string

# Quicker AIOFetch
async def aiofetch(session, url, headers):
  async with session.get(url, headers=headers) as response:
    return response


# TaskList (class) - Used to store the task and remember it in case of restarts and such
class TaskList:

  def __init__(self, task):
    self.task = task
    self.task_list = []
    self.task_list.append(self.task)

  def add_task(self, task):
    self.task_list.append(task)
    return self.task_list

  def remove_task(self, task):
    self.task_list.remove(task)
    return self.task_list

  def get_task(self):
    return self.task_list

  def get_task_count(self):
    return len(self.task_list)

  def get_task_by_index(self, index):
    return self.task_list[index]

  def get_task_by_name(self, name):
    for task in self.task_list:
      if task.name == name:
        return task
    return None

  def get_task_by_id(self, id):
    for task in self.task_list:
      if task.id == id:
        return task
    return None

  def save_task_list(self):

    """ Structure:
    tasks (
        task_id INTEGER PRIMARY KEY,
        name TEXT,
        function_name TEXT,
        data TEXT,
        start_time TEXT
    )
    """

    # Save the task list to the database
    c.execute("DELETE FROM tasks")
    for task in self.task_list:
      c.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?)", (task.id, task.name, task.function_name, task.data, task.start_time))
      conn.commit()
      print(f"""{ansify("red", "[TaskList]")} Saved task {ansify("green", task.name)}""")


# Task (class) - Used to store the task and remember it in case of restarts and such
class Task:

  def __init__(self, name, id, func, data={}):
    self.name = name
    self.id = id
    self.func = func
    self.data = data
    self.start_time = datetime.now()


# Perm int to perm strings
def convert_permissions(permissions, mode="s"):
  """Converts a permission integer to a discord.PermissionOverwrite object."""

  _PD = {}

  overwrite = discord.PermissionOverwrite()
  for attr, bit in discord.Permissions.all():
    if permissions & bit:
      setattr(overwrite, attr, True)
      _PD[attr] = True

  if mode == "s":
    return overwrite
  if mode == "o":
    return overwrite

# Perm int to perm strings
def convert_permissions(permissions, mode="s"):
  """Converts a permission integer to a discord.PermissionOverwrite object."""

  _PD = {}

  overwrite = discord.PermissionOverwrite()
  for attr, bit in discord.Permissions.all():
    if permissions & bit:
      setattr(overwrite, attr, True)
      _PD[attr] = True

  if mode == "s":
    return overwrite
  if mode == "o":
    return overwrite


# EMERGENCY IF XBL.IO DOESN'T WORK/RATELIMITS
async def fetch_gt(gamertag):
  try:
    async with aiohttp.ClientSession() as session:
      async with session.get('https://cxkes.me/xbox/xuid') as response:
        html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        token = soup.find('input', {'name': '_token'}).get('value')

        urlencoded = {'_token': token, 'gamertag': gamertag, 'rtnType': '1'}

        async with session.post('https://cxkes.me/xbox/xuid',
                                data=urlencoded) as xuid_response:
          if xuid_response.content_type == 'application/json':
            xuid_data = await xuid_response.json()
            # print(xuid_data)
            print(f"{ansify('red', '[XUID]')} Fetched XUID for {ansify('green', gamertag)}: {ansify('yellow', xuid_data['xuid'])}")
            
            return token
          else:
            # print(
            #   f"Unexpected response content type: {xuid_response.content_type}"
            # )
            print(
              f"{ansify('red', '[XUID]')} Failed to fetch XUID for {ansify('green', gamertag)}"
            )

            vil = await xuid_response.text()

            if "Invalid Gamertag or internal error." in vil:
              # print("Invalid Gamertag or internal error.")
              print(f"{ansify('red', '[XUID]')} Invalid Gamertag or internal error.")
              return None

            print(vil)

            # Regex patterns to extract user info
            patterns = {
              'username': r'<h3 class="mt-2">(.*?)</h3>',
              'name': r'<strong>Name<\/strong>: (.*?)\n',
              'xuid_dec': r'<strong>XUID \(DEC\)<\/strong>: (.*?)<br />',
              'xuid_hex': r'<strong>XUID \(HEX\)<\/strong>: (.*?)\n',
              'gamer_score': r'<strong>Gamer Score<\/strong>: (.*?)\n',
              'account_tier': r'<strong>Account Tier<\/strong>: (.*?)\n',
              'following': r'<strong>Following<\/strong>: (.*?)\n',
              'followers': r'<strong>Followers<\/strong>: (.*?)\n'
            }

            user_info = {}

            for key, pattern in patterns.items():
              match = re.search(pattern, vil)
              if match:
                user_info[key] = match.group(1)

            return user_info

  except Exception as e:
    # print('Something went wrong:', str(e))
    print(f"{ansify('red', '[XUID]')} Something went wrong: {ansify('yellow', str(e))}")
    return None


# Date Checker funct
def date_check(name,
               hours=0,
               weeks=0,
               seconds=0,
               minutes=0,
               method="w",
               overide=False):
  """
  Checks if Date in a file is past a certain time
  If it is, return True
  if it isn't, return False
  if you also have method as "w", it will write the date to the file
  """

# Date Checker funct
def date_check(name,
               hours=0,
               weeks=0,
               seconds=0,
               minutes=0,
               method="w",
               overide=False):
  """
  Checks if Date in a file is past a certain time
  If it is, return True
  if it isn't, return False
  if you also have method as "w", it will write the date to the file
  """

  # Get the current time
  now = datetime.now()

  # Get time of last purge from ./lastpurge.txt
  with open(f"./{name}.txt", "r") as f:
    lastpurge = f.read()

  # Get the time of the next purge
  nextpurge = 0

  if overide:
    """
    Instead of adding the values to the current time, 
    we'll make it so it will activate at the time you specify rather 
    """

    nextpurge = datetime.strptime(
      f"{now.year}-{now.month}-{now.day} {hours}:{minutes}:{seconds}",
      "%Y-%m-%d %H:%M:%S")

  else:
    nextpurge = datetime.strptime(lastpurge, "%Y-%m-%d %H:%M:%S") + timedelta(
      hours=hours, weeks=weeks, seconds=seconds, minutes=minutes)

  # If the next event is in the past, Do
  if now > nextpurge:

    # should do case?
    if method == "w":
      # Update the time of the last purge
      with open(f"./{name}.txt", "w") as f:
        f.write(now.strftime("%Y-%m-%d %H:%M:%S"))

    return True

  # If the next purge is in the future.
  else:
    return False


class LinkProcess:

  def __init__(self, ctx):
    self.ctx = ctx
    self.completed = True

  async def start(self):
    client_id = "" # Setup Client ID @ Azure Dev Dashboard
    scopes = ["XboxLive.signin"]
    authority = "https://login.microsoftonline.com/consumers"
    pca = PublicClientApplication(client_id, authority=authority)

    flow = pca.initiate_device_flow(scopes)
    if "message" in flow:
      code = flow["user_code"]
      embed = discord.Embed(
        title="Link Your Microsoft Account.",
        color=discord.Colour.red(),
      )
      embed.add_field(
        name=
        f"> Copy Your Code: {code}\n> Go to https://www.microsoft.com/link\n> Enter Your Unique Code\n> Sign In To Link Accounts",
        value="",
      )
      embed.set_footer(
        text="Crashary Realm Inviter",
        icon_url="https://cdn.crashary.uk/Crashary.webp",
      )
      embed.set_thumbnail(url="https://cdn.crashary.uk/Crashary.webp")

      await self.ctx.respond(embed=embed, ephemeral=True)
      await bot.wait_until_ready()

      embed = discord.Embed(
        title="Link Your Microsoft Account.",
        color=discord.Colour.red(),
      )
      embed.add_field(name=f"Successfully linked account", value="")
      embed.set_footer(
        text="Crashary Realm Inviter",
        icon_url="https://cdn.crashary.uk/Crashary.webp",
      )

      result = await asyncio.to_thread(pca.acquire_token_by_device_flow, flow)
      await self.ctx.edit(embed=embed)

      access_token = result.get("access_token")
      refresh_token = result.get("refresh_token")
      user_id = self.ctx.author.id

      xbl3token = getxbl3(access_token)

      # Store the variables in the database
      c.execute(
        """
                INSERT INTO link_data (user_id, access_token, refresh_token, xbl3token)
                VALUES (?, ?, ?, ?)
            """,
        (user_id, access_token, refresh_token, xbl3token),
      )

      # Check if the user ID is already in the invites table
      c.execute("SELECT user_id FROM invitetable WHERE user_id = ?",
                (user_id, ))
      result = c.fetchone()

      # Insert into the invite table if not already
      if result is None:
        c.execute(
          """
                    INSERT INTO invitetable (user_id, invites, invitesused, currentlyinviting, claimeddaily)
                    VALUES (?, ?, ?, ?, ?)
                """,
          (user_id, 100000000, 0, "False", "False"),
        )

      print(f"""{ansify("yellow", "Successfully linked account")} {ansify("", self.ctx.author.name)}""")
      await logschannel.send(f"{self.ctx.author} just linked their account!")
      conn.commit()

      self.completed = True
    else:
      print(f"{ansify('An error occurred during the device code flow.')} {ansify(self.ctx.author.name)}")

    # Remove the process from the ongoing_processes dictionary
    del ongoing_processes[self.ctx.author.id]


@bot.event
async def on_ready():
  botUser = f"{bot.user}"
  # print(f"{bot.user} is ready and online!")
  print(f"""{ansify("green", botUser)} is ready and online!""")
  #await start_auto_purge()

  # Update the Invites Sent
  c.execute("SELECT invitesused FROM invitetable")
  total = sum(row[0] for row in c.fetchall())
  # Round to nearest 1000
  total = math.ceil(total / 1000)
  await bot.change_presence(activity=discord.Activity(
    name=f"realms get members", type=discord.ActivityType.watching))

  # Run the Daily Event
  await schedule_daily_event()
  await do_auto_purge()


# Link ----------------------------------------------------------------------------------------------------------
@bot.slash_command(name="link", description="Link your account to the bot.")
async def link(ctx):
  # print(f"{ctx.author.name} has just started a link process!")
  print(f"{ansify('green', ctx.author.name)} has just started a link process!")

  # Check if the user is already in the database
  c.execute("SELECT user_id FROM link_data WHERE user_id = ?",
            (int(ctx.author.id), ))
  result = c.fetchone()

  if result is not None:
    await ctx.respond("Your account is already linked.", ephemeral=True)
    return

  if ctx.author.id in ongoing_processes:
    await ctx.respond(
      "A link process is already running. Please wait until it finishes.",
      ephemeral=True,
    )
    return

  process = LinkProcess(ctx)
  ongoing_processes[ctx.author.id] = process

  try:
    await process.start()
  except Exception as e:
    # print(f"An error occurred during the link process: {e}")
    print(f"{ansify('red', 'An error occurred during the link process:')} {e}")
    del ongoing_processes[ctx.author.id]


# UnLink --------------------------------------------------------------------------------------------------------
@bot.slash_command(name="unlink",
                   description="Remove your account from our database.")
async def unlink(ctx):
  user_id = str(ctx.author.id)  # Retrieve the user ID as a string

  # Check if the user ID is already in the database
  c.execute("SELECT user_id FROM link_data WHERE user_id = ?", (user_id, ))
  result = c.fetchone()

  if result is not None:
    # User ID is already linked, remove the record from the database
    c.execute("DELETE FROM link_data WHERE user_id = ?", (user_id, ))
    conn.commit()  # Commit the changes

    await logschannel.send(f"{ctx.author} just unlinked their account!")
    await ctx.respond("Your account has been unlinked.", ephemeral=True)
  else:
    await ctx.respond("Your account is not linked. Type /link to do so.",
                      ephemeral=True)


# Query ---------------------------------------------------------------------------------------------------------
@bot.slash_command(name="queryinvites", description="Check your invite stats")
async def queryinvites(ctx):
  user = ctx.author

  # Check if the user ID is already in the database
  c.execute("SELECT user_id FROM link_data WHERE user_id = ?", (user.id, ))
  result = c.fetchone()

  if result is not None:
    # Get the number of invites the user has
    c.execute("SELECT invites, invitesused FROM invitetable WHERE user_id = ?",
              (user.id, ))
    result = c.fetchone()
    invites = result[0]
    invites_used = result[1]

    embed = discord.Embed(
      title=f"{user.name}'s Invite Statistics",
      color=discord.Colour.red(),
    )
    embed.add_field(
      name=
      f"> Invites To Send - `{invites}`\n> Invites Sent - `{invites_used}`",
      value="",
    )
    embed.set_footer(
      text="Crashary Realm Inviter",
      icon_url="https://cdn.crashary.uk/Crashary.webp",
    )

    await ctx.respond(embed=embed)
  else:
    await ctx.respond("You have not linked your account. Type /link to do so.",
                      ephemeral=True)


# AddInvites ----------------------------------------------------------------------------------------------------
@bot.slash_command(name="updateinvites", description="Give a User Invites")
async def updateinvites(ctx, user: discord.Member, invitestoadd: int):
  sender = ctx.author.id
  user_id = user.id

  if sender == 614570887160791050:
    # Check if the user ID is already in the database
    c.execute("SELECT user_id FROM link_data WHERE user_id = ?", (user_id, ))
    result = c.fetchone()

    if result is not None:
      # Get the number of invites the user has
      c.execute("SELECT invites FROM invitetable WHERE user_id = ?",
                (user_id, ))
      result = c.fetchone()
      current_invites = result[0]

      final_invites = current_invites + invitestoadd

      c.execute(
        "UPDATE invitetable SET invites = ? WHERE user_id = ?",
        (final_invites, user_id),
      )
      await ctx.respond(f"{user.name} now has {final_invites} invites!")
      await logschannel.send(
        f"{ctx.author} just gave {user.name}, {invitestoadd} invites!")
      conn.commit()
    else:
      await ctx.respond("The user has not linked their account",
                        ephemeral=True)

  else:
    await ctx.respond("You do not have permission to run this command!",
                      ephemeral=True)


# SendInvites ---------------------------------------------------------------------------------------------------
async def send_request(self, invitedplayerxuid, counter):
  url = f"https://pocket.realms.minecraft.net/invites/{self.realmid}/invite/update"
  headers = {
    "Accept": "*/*",
    "authorization": f"{self.xbltoken}",
    'client-version': '1.20.0',
    'client-ref': '08bdb049f310d03aeabda3748f857640eb62a733',
    "user-agent": "MCPE/UWP",
    "Accept-Language": "en-GB,en",
    "Accept-Encoding": "gzip, deflate, be",
    "Host": "pocket.realms.minecraft.net",
  }

  data = {"invites": {invitedplayerxuid: "ADD"}}  # or "REMOVE"

  # Begin Request
  # print(f"Begining request to {invitedplayerxuid} ({counter})")")

  try:
    async with aiohttp.ClientSession() as session:
      async with session.put(url, headers=headers, json=data) as response:
        if response.status == 200:
          # print(
          #   f"Request successful for {self.realmname} to PLAYER_XUID: {invitedplayerxuid}"
          # )
          print(
            f"""{ansify("green", f'[{counter}]')} Sent Invite to {invitedplayerxuid}"""
          )
          # print(f"{counter} Invites Sent!")
          print(f"""{ansify("green", f'[{counter}]')} Invites sent!""")

        else:
          print(
            f"Request failed with status code {response.status} for PLAYER_XUID: {invitedplayerxuid}"
          )
  except aiohttp.ClientError as e:
    print(
      f"An error occurred for PLAYER_XUID: {invitedplayerxuid}. Error: {str(e)}"
    )


# Build Invite Class
class CodeRunner:

  def __init__(self, ctx, invitestosend, invitesused, realmid, realmname,
               xbltoken):
    self.ctx = ctx
    self.invitestosend = invitestosend
    self.invitesused = invitesused
    self.realmid = realmid
    self.realmname = realmname
    self.xbltoken = xbltoken
    self.playerxuids = playerxuids
    self.randomnum = 0
    self.tasks = []
    self.counting = 0

    self.embedinvited = discord.Embed(
      title="",
      color=discord.Colour.red(),
    )

  async def run_code_block(self):
    print(self.invitesused)

    # Build and send embed to start inviting
    embedinvited = discord.Embed(
      title="",
      color=discord.Colour.red(),
    )
    embedinvited.add_field(
      name=
      f"Successfully started inviting {self.invitestosend} members to {self.realmname}. You will be notified once it has been completed.",
      value="",
    )
    await self.ctx.edit(embed=embedinvited)

    # Make embed to send in public channel
    embedlogs = discord.Embed(
      title="",
      color=discord.Colour.red(),
    )
    embedlogs.add_field(
      name=
      f"{self.ctx.author} just sent {self.invitestosend} invites for their realm!",
      value="",
    )
    publiclogschannel = bot.get_channel(1128355347363541073)
    await publiclogschannel.send(embed=embedlogs)

    for i in range(self.invitesused, self.invitesused + self.invitestosend +
                   1):  # Ik ur reading this vision...
      self.counting += 1
      player_xuid = playerxuids[i]
      # Thing Runs Here

      xbliohead = {
        # "Accept": "application/json",
        "x-authorization": f"{oxblkey}",
      }

      xbliores = False
      isValidXUID = False

      # Check if we can use this XUID
      async with aiohttp.ClientSession() as session:
        # xbliores = await aiofetch(
        # session, "https://xbl.io/api/v2/account/" + player_xuid, xbliohead)

        task = asyncio.create_task(
          send_request(self, player_xuid, self.counting))
        self.tasks.append(task)

        # Basically stops them getting banned v v v
        await asyncio.sleep(random.uniform(2, 2.8))
        self.randomnum = random.randint(1, 100)
        if self.randomnum >= 95:
          await asyncio.sleep(random.randint(5, 10))

    # Embed to DM when finished.
    embedfinished = discord.Embed(
      title="",
      color=discord.Colour.red(),
    )
    embedfinished.add_field(
      name=
      f"{self.invitestosend} invites have been successfully sent for {self.realmname}. To check how many invites you have type /queryinvites",
      value="",
    )
    await self.ctx.author.send(embed=embedfinished)

    c.execute(
      "UPDATE invitetable SET currentlyinviting = 'False' WHERE user_id = ?",
      (self.ctx.author.id, ),
    )
    conn.commit()
    await asyncio.gather(*self.tasks)


# SendInvites ---------------------------------------------------------------------------------------------------
@bot.slash_command(name="sendinvites",
                   description="Invite Users To Your Realm")
async def sendinvites(ctx, realmcode: str, invitestosend: int):
  user = ctx.author
  user_id = user.id

  # Check if the user ID is already in the database
  c.execute("SELECT user_id FROM 'link_data' WHERE user_id = ?", (user_id, ))
  result = c.fetchone()

  if result is not None:
    # Get the number of invites the user has
    c.execute("SELECT invites, invitesused FROM invitetable WHERE user_id = ?",
              (user_id, ))
    result = c.fetchone()
    invites = result[0]
    invitesused = result[1]

    if invites <= 0:
      channel = bot.get_channel(1128355347363541073)
      await ctx.respond(
        f"You do not have any more invites right now.",
        ephemeral=True,
      )
    else:
      if invitestosend > invites:
        channel = bot.get_channel(1128355347363541073)
        await ctx.respond(
          f"You do not have enough invites to complete this request.",
          ephemeral=True,
        )
      else:
        c.execute(
          "SELECT currentlyinviting FROM 'invitetable' WHERE user_id = ?",
          (user_id, ),
        )
        result = c.fetchone()
        result = result[0]

        if result == "True":
          await ctx.respond(
            f"You are already sending invites to a realm. You will be notified once this has been completed.",
            ephemeral=True,
          )
        else:
          await ctx.respond(embed=embedthink)
          refreshtoken(user_id, conn, c)
          # Get Xbl3Token from the database
          c.execute("SELECT xbl3token FROM link_data WHERE user_id = ?",
                    (user_id, ))
          result = c.fetchone()
          xbl3token = result[0]

          # Get the realm information
          realminfo = getinfofromcode(realmcode, xbl3token)
          if realminfo != False:
            realmid = realminfo["id"]
            # Check if the user is the realm owner
            isowner = checkowner(realmid, xbl3token)
            if isowner != False:
              realmname = realminfo["name"]
              c.execute(
                "UPDATE invitetable SET invites = ? WHERE user_id = ?",
                (invites - invitestosend, user_id),
              )
              conn.commit()
              c.execute(
                "UPDATE invitetable SET invitesused = ? WHERE user_id = ?",
                (invitesused + invitestosend, user_id),
              )
              conn.commit()
              await logschannel.send(
                f"{ctx.author} just sent {invitestosend} invites to {realmname}."
              )

              c.execute(
                "UPDATE invitetable SET currentlyinviting = 'True' WHERE user_id = ?",
                (user_id, ),
              )
              conn.commit()
              # Create an instance of CodeRunner for the user
              runner = CodeRunner(
                ctx,
                invitestosend,
                invitesused,
                realmid,
                realmname,
                xbl3token,
              )

              # Create a task for the user to run the code block
              task = asyncio.create_task(runner.run_code_block())

              # Wait for the task to complete
              await task
            else:
              embednotowner = discord.Embed(
                title="",
                color=discord.Colour.red(),
              )
              embednotowner.add_field(
                name=f"You are not the owner of {realminfo['name']}",
                value="",
              )
              await ctx.edit(embed=embednotowner)

          else:  # Invalid Realm Code Entered
            embedcode = discord.Embed(
              title="",
              color=discord.Colour.red(),
            )
            embedcode.add_field(name=f"{realmcode} is not a valid realm code.",
                                value="")
            await ctx.edit(embed=embedcode)
  else:
    await ctx.respond("You have not linked your account. Type /link to do so.",
                      ephemeral=True)


# Claim Daily Invites -------------------------------------------------------------------------------------------
@bot.slash_command(name="claimdaily", description="Claim your daily invites!")
async def claimdaily(ctx):
  user = ctx.author

  # Check if the user ID is already in the database
  c.execute("SELECT user_id FROM link_data WHERE user_id = ?", (user.id, ))
  result = c.fetchone()

  if result is not None:
    # Check if they have already claimed
    c.execute("SELECT claimeddaily FROM invitetable WHERE user_id = ?",
              (user.id, ))
    result = c.fetchone()[0]

    # Check if false and wtv
    if result == "False":
      c.execute(
        "UPDATE invitetable SET invites = invites + 1000000 WHERE user_id = ?",
        (user.id, ),
      )
      c.execute(
        "UPDATE invitetable SET claimeddaily = 'True' WHERE user_id = ?",
        (user.id, ),
      )
      conn.commit()

      embedclaimed = discord.Embed(
        title="",
        color=discord.Colour.red(),
      )
      embedclaimed.add_field(
        name=
        f"You have successfully claimed your daily invites. Type /queryinvites to find out how many you have.",
        value="",
      )

      await ctx.respond(embed=embedclaimed)
    else:
      channel = bot.get_channel(1128355347363541073)
      await ctx.respond(
        f"You have already claimed your free daily invites today. Go to {channel.mention} to find out how to get more!",
        ephemeral=True,
      )

  else:
    await ctx.respond("You have not linked your account. Type /link to do so.",
                      ephemeral=True)


# Give free invites once a day ----------------------------------------------------------------------------------
async def schedule_daily_event():
  now = datetime.now()
  target_time = datetime.combine(
    datetime.now().date(),
    datetime.now().time().replace(hour=21,
                                  minute=15))  # Set the desired time here

  # Target_time should be value: e.g. 5:04:00 AM => 21:15:**

  # if now > target_time:
  #   target_time += timedelta(
  #     days=1
  #   )  # If the target time has already passed today, schedule it for the next day
  # time_until_event = (target_time - now).total_seconds()
  # print(f"Daily event starts in {time_until_event} seconds")
  # await daily_event()

  if date_check("dailygiveaway", hours=21, minutes=15, overide=True):

    # If the target time has already passed today, schedule it for the next day
    target_time += timedelta(days=1)

  time_until_event = (target_time - now).total_seconds()

  print(f"Daily event starts in {time_until_event} seconds")
  if time_until_event < 1:
    await daily_event()


async def daily_event():
  c.execute("UPDATE invitetable SET claimeddaily = 'False'")
  conn.commit()

  # Build the embed to send
  channeltag = bot.get_channel(1128355347363541073)
  embeddaily = discord.Embed(
    title="",
    color=discord.Colour.red(),
  )
  embeddaily.add_field(
    name=
    f"Everyone can now claim their free 1 million daily invites. Type /claimdaily to claim yours. Go to {channeltag.mention} to find out how to get more invites!",
    value="",
  )

  print("Just sent out the daily 1 million invites.")
  publiclogschannel = bot.get_channel(1128355347363541073)
  await publiclogschannel.send(embed=embeddaily)

async def do_auto_purge():
  async def purge():
    """
    Crashary MI Dev Team Guild: 1128350988798001213
    Crashary LLC Guild: 1118869295770914949
    """

    guild_id = 1118869295770914949
    guild = bot.get_guild(guild_id)

    # Fetch all channels and look for one that has "autopurge=true" in the topic
    for channel in guild.text_channels:
      if channel.topic is not None and "autopurge=true" in channel.topic:
        # Purge the channel
        print(f"""-- {ansify("red", "Purging")} {channel.name} --""")

        # Delete channel and create a new one with all the same settings
        category = channel.category
        overwrites = channel.overwrites
        nsfw = channel.is_nsfw()

        slowmode = channel.slowmode_delay
        topic = channel.topic
        name = channel.name
        slowmode_delay = channel.slowmode_delay

        posit = channel.position

        # Get all Channel permiisions for each role in the guild
        perms = []
        badperms = []
        roles = guild.roles

        for role in roles:
          perm_obj = {
            # Perm : allow?/deny?/idk?
          }

          __a = role._permissions

          perms.append(convert_permissions(__a))
          # print(perms)
          # else:
          #   badperms.append(role.permissions)

        # Now we need to create an overide class for each role
        # overrides = []

        # # Push discord.PermissionOverwrite objects into a list
        # overwrite = discord.PermissionOverwrite()
        # for perm, bperm in zip(perms, badperms):
        #   dictl = perm
        #   bdictl = bperm
        #   # overwrite.update(*dictl)
        #   overwrite.from_pair(dictl, bdictl)
        # I don't actually know what the Dict gets mapped to

        # print(dictl)

        # Set the permissions for the new channel
        new_channel = await guild.create_text_channel(
          name,
          position=posit,
          category=category,
          overwrites=overwrites,
          nsfw=nsfw,
          slowmode_delay=slowmode_delay,
          topic=topic,
        )

        # Set the permissions for the new channel
        role_reqs_tobesent = DISCORD_THROTTLE.rate_calc(len(roles))
        
        for role, perms in zip(roles, perms):
          await new_channel.set_permissions(role, overwrite=perms)
          print(f"""{ansify("green", "Set")} {role.name}'s permissions to {perms}""")
          await asyncio.sleep(role_reqs_tobesent + 2)

        await asyncio.sleep(1)
        await channel.delete()
        # await category.create_text_channel(name, topic=topic)

  # Get the current time
  now = datetime.now()

  # Get time of last purge from ./lastpurge.txt
  with open("./lastpurge.txt", "r") as f:
    lastpurge = f.read()

  # Get the time of the next purge
  nextpurge = datetime.strptime(lastpurge,
                                "%Y-%m-%d %H:%M:%S") + timedelta(hours=6)

  # If the next purge is in the past, purge
  if now > nextpurge:
    await purge()
    # Update the time of the last purge
    with open("./lastpurge.txt", "w") as f:
      f.write(now.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"""-- {ansify("green", "Purge complete")} --""")

  # If the next purge is in the future, non blocking sleep until then
  else:
    await asyncio.sleep((nextpurge - now).total_seconds())
    purge()
    # Update the time of the last purge
    with open("./lastpurge.txt", "w") as f:
      f.write(now.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"""-- {ansify("green", "Purge complete")} --""")

  # Schedule the next purge
  await do_auto_purge()


# Run the bot from the token in ".env"
bot.run(os.getenv("TOKEN"))
