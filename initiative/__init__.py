from .initiative import InitiativeTracker

async def setup(bot):
    await bot.add_cog(InitiativeTracker(bot))