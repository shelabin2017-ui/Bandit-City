"""Bandit City enhanced launcher.

Keeps bot.py as the stable core and loads gameplay and phone input fixes.
"""

import bot
import enhancements
import phone_fix

enhancements.apply(bot)
phone_fix.apply(bot)
bot.main()
