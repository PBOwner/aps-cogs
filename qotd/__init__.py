from .qotd import QuestionOfTheDay


async def setup(bot):
    await bot.add_cog(QuestionOfTheDay(bot))
