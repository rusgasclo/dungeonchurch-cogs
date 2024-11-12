from .augury import Augury

async def setup(bot):
    await bot.add_cog(Augury(bot))