from .aidm import AiDm

async def setup(bot):
    await bot.add_cog(AiDm(bot))