from mcp_server_wechat.WechatServer import WeChatServer

async def serve(default_folder_path=None):
    """启动微信MCP服务器"""
    server = WeChatServer(default_folder_path=default_folder_path)
    await server.serve()

def main():
    """提供微信交互功能的MCP服务器"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="给模型提供微信聊天记录获取和消息发送功能的MCP服务器"
    )
    parser.add_argument("--folder-path", default=None,
                        help="默认保存聊天记录的文件夹路径")
    args = parser.parse_args()

    asyncio.run(serve(default_folder_path=args.folder_path))

if __name__ == "__main__":
    main()