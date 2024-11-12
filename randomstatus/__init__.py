from .randomstatus import RandomStatus

async def setup(bot):
    await bot.add_cog(RandomStatus(bot))