from .q3stat import Q3stat

async def setup(bot):
    await bot.add_cog(Q3stat(bot))