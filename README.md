# Secret Hitler: Telegram

**A Telegram bot that allows users to play [Secret Chavez](https://www.secrethitler.com/).**

This is just an Adaptation of the classic game secret hitler, but themed with Venezuelan politics.

## Commands

See [commands.txt](commands.txt) for a list of available commands and descriptions.  Note that some commands are only available to certain players in certain game states.
If you host a bot instance, this files contents can be put into `@BotFather` so that Telegram shows these in the command menu.

## Player Status Abbreviations
- (P) indicates a current president/presidential candidate.
- (C) indicates a current chancellor/chancellor candidate.
- (TL) indicates a term-limited player (ineligible for any chancellor nominations).
- (CNH) indicates a player that is confirmed not to be hitler (by having been elected after 3 fascist policies).
- (RIP) indicates a dead player.

## Configuration

To get the bot working, you need to create the folder `config` and place these files there.

- **API token:** Stored in `config/key` but withheld with `.gitignore`. To replicate this project, make a Telegram bot by messaging `@BotFather` and pasting the resulting API key there.
- **Username:** Stored without the "@" in `config/username`.
- **Devchat:** Stored in `config/devchat` the chat id of a chat where the bot sends its maintenance messages.

## License and Attribution

Secret Hitler is designed by Max Temkin, Mike Boxleiter, Tommy Maranges and illustrated by Mackenzie Schubert.

The game and therefore this bot as well are licensed as per the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/) license.
