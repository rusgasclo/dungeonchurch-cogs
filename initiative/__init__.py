from .initiative import RollInitiative

async def setup(bot):
    await bot.add_cog(RollInitiative(bot))