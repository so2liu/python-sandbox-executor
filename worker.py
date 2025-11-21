import asyncio

from job_runner.api import runner


async def main() -> None:
    # Runner already wired with job_store/log_store.
    await runner.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
