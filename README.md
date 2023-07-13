# Crashary-MI

This repository is an open source copy of the Crashary Mass Inviter bot. The bot is designed to facilitate inviting members to a Minecraft realm. This README provides an overview of the script and instructions for running it.

## Requirements
- Python 3.7 or above
- `py-cord` library
- `msal` library
- `sqlite3` library
- `aiohttp` library
- `dotenv` library

## Setup

1. Clone the repository:
```
git clone https://github.com/Crashary/Crashary-MI.git
```

2. Install the required libraries:
```
pip install -r requirements.txt
```

3. Create a `.env` file in the project directory and add the following variables:
```
TOKEN=your_discord_bot_token
```

4. Create a file named `playerxuids.txt` and add the Xuids of the players you want to invite, each on a separate line.

6. Create a SQLite database file named `UserInfo.db` in the project directory with the relevant tables and fields.

8. Run the `main.py` script:
```
python main.py
```

## Usage

The Crashary Mass Inviter bot responds to various slash commands in Discord. Here are the available commands:

- `/link`: Link your Discord account to the bot.
- `/unlink`: Remove your account from the bot's database.
- `/queryinvites`: Check your invite statistics.
- `/updateinvites`: Give invites to a user (admin command).
- `/sendinvites`: Invite users to your Minecraft realm.
- `/claimdaily`: Claim your daily invites.

## Contributing

Contributions to this project are welcome. If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the BSD 3-Clause License.