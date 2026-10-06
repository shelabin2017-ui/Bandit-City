"""Bandit City enhanced launcher.

Keeps bot.py as the stable core and loads enhancements before starting longpoll.
"""

import bot
import enhancements

enhancements.apply(bot)
bot.main()
