from .dragonchess import DragonChess

async def setup(bot):
    await bot.add_cog(DragonChess(bot))