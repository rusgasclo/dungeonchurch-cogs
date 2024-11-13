from .churchmod import ChurchMod

async def setup(bot):
    await bot.add_cog(ChurchMod(bot))