import asyncio

from mcp import Client


async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:

        tools = await client.list_tools()

        print("Available tools:")
        for tool in tools.tools:
            print("-", tool.name)

        result = await client.call_tool(
            "reference_range_lookup",
            {"test_name": "Ferritin"}
        )

        print("\nLookup result:")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())