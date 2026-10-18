"""Bandit City enhanced launcher.

Loads gameplay extensions in a deterministic order before starting the VK bot.
"""
import bot
import enhancements
import phone_fix
import multi_business

enhancements.apply(bot)
phone_fix.apply(bot)
multi_business.apply(bot)
bot.main()
