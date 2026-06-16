import json
from typing import Any, Sequence, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource, ErrorData, TextResourceContents, \
    BlobResourceContents
from mcp.shared.exceptions import McpError

from .WechatClient import WeChatClient


class WeChatServer:
    """
    微信服务器
    提供微信聊天记录获取和消息发送功能的API接口
    """

    def __init__(self, default_folder_path: Optional[str] = None):
        """
        初始化微信服务器

        参数:
        - default_folder_path: 默认保存聊天记录的文件夹路径
        """
        self.wechat_client = WeChatClient(default_folder_path=default_folder_path)

    async def serve(self):
        """启动微信服务器"""
        server = Server("WeChatServer")

        @server.list_resources()
        async def handle_list_resources():
            """列出可用的微信资源"""
            return [
                {
                    "uri": "wechat://chats/history",
                    "name": "微信聊天记录",
                    "description": "获取微信聊天记录",
                    "mimeType": "application/json",
                }
            ]

        @server.read_resource()
        async def handle_read_resource(uri: str) -> List[TextResourceContents | BlobResourceContents]:
            """读取指定的微信资源"""
            if uri.startswith("wechat://"):
                return [
                    TextResourceContents(
                        uri=uri,
                        mimeType="application/json",
                        text=json.dumps({"message": "请使用工具接口获取微信聊天记录"}, ensure_ascii=False)
                    )
                ]
            raise ValueError(f"不支持的URI: {uri}")

        @server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用的微信工具"""
            return [
                Tool(
                    name="wechat_get_chat_history",
                    description="获取特定日期的微信聊天记录",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to_user": {
                                "type": "string",
                                "description": "好友或群聊备注或昵称",
                            },
                            "target_date": {
                                "type": "string",
                                "description": "目标日期，格式为YY/M/D，如25/3/22",
                            },
                        },
                        "required": ["to_user", "target_date"],
                    }
                ),
                Tool(
                    name="wechat_send_message",
                    description="向单个微信好友发送单条消息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to_user": {
                                "type": "string",
                                "description": "好友或群聊备注或昵称",
                            },
                            "message": {
                                "type": "string",
                                "description": "要发送的消息",
                            }
                        },
                        "required": ["to_user", "message"],
                    }
                ),
                Tool(
                    name="wechat_send_multiple_messages",
                    description="向单个微信好友发送多条消息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to_user": {
                                "type": "string",
                                "description": "好友或群聊备注或昵称",
                            },
                            "messages": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要发送的消息列表 (用英文逗号分隔的字符串输入)",
                            }
                        },
                        "required": ["to_user", "messages"],
                    }
                ),
                Tool(
                    name="wechat_send_to_multiple_friends",
                    description="向多个微信好友发送单条或者多条消息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to_user": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "好友或群聊备注或昵称列表 (用英文逗号分隔的字符串输入)",
                            },
                            "message": {
                                "type": "string",
                                "description": "要发送的消息 (单条消息（xxx）会发给所有好友；多条消息（xxx,xxx,xxx）用英文逗号分隔且数量与好友数相同时，将分别发送给对应好友)",
                            }
                        },
                        "required": ["to_user", "message"],
                    }
                )
            ]

        @server.call_tool()
        async def call_tool(
                name: str, arguments: Dict[str, Any]
        ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
            try:
                if name == "wechat_get_chat_history":
                    friend = arguments.get("to_user")
                    target_date = arguments.get("target_date")
                    if not friend or not target_date:
                        raise ValueError("缺少必要参数: to_user 或 target_date")

                    folder_path = arguments.get("folder_path")
                    search_pages = arguments.get("search_pages", 5)
                    scroll_delay = arguments.get("scroll_delay", 0.01)
                    chat_history = self.wechat_client.get_chat_history_by_date(
                        friend=friend,
                        target_date=target_date,
                        folder_path=folder_path,
                        search_pages=search_pages,
                        scroll_delay=scroll_delay
                    )
                    records = json.loads(chat_history)
                    output = f"获取到 {len(records)} 条与 {friend} 在 {target_date} 的聊天记录\n\n"

                    for record in records:
                        output += f"发送者: {record['发送者']}\n"
                        output += f"时间: {record['时间']}\n"
                        output += f"消息: {record['消息']}\n"
                        output += "-" * 30 + "\n"

                    return [TextContent(type="text", text=output)]

                elif name == "wechat_send_message":
                    friend = arguments.get("to_user")
                    message = arguments.get("message")
                    if not friend or not message:
                        raise ValueError("缺少必要参数: to_user 或 message")

                    delay = arguments.get("delay", 1)
                    search_pages = arguments.get("search_pages", 0)

                    result = self.wechat_client.send_message_to_friend(
                        friend=friend,
                        message=message,
                        delay=delay,
                        search_pages=search_pages
                    )

                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

                elif name == "wechat_send_multiple_messages":
                    friend = arguments.get("to_user")
                    messages = arguments.get("messages")

                    if not friend or not messages:
                        raise ValueError("缺少必要参数: to_user 或 messages")

                    if isinstance(messages, str):
                        try:
                            messages = json.loads(messages)
                        except json.JSONDecodeError:
                            for separator in ['，', '；', ';', '\n']:
                                messages = messages.replace(separator, ',')
                            messages = [msg.strip() for msg in messages.split(',')]
                            messages = [msg for msg in messages if msg]

                    if not isinstance(messages, list):
                        messages = [messages]

                    delay = arguments.get("delay", 1)
                    search_pages = arguments.get("search_pages", 0)

                    result = self.wechat_client.send_messages_to_friend(
                        friend=friend,
                        messages=messages,
                        delay=delay,
                        search_pages=search_pages
                    )

                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

                elif name == "wechat_send_to_multiple_friends":
                    friends = arguments.get("to_user")
                    message = arguments.get("message")

                    if not friends or not message:
                        raise ValueError("缺少必要参数: to_user 或 message")

                    if isinstance(friends, str):
                        try:
                            friends = json.loads(friends)
                        except json.JSONDecodeError:
                            friends = [f.strip() for f in friends.split(',')]

                    if not isinstance(friends, list):
                        friends = [friends]

                    if isinstance(message, str):
                        if message.count('","') > 0 and message.count('","') == (len(friends) - 1):
                            try:
                                parsed_messages = json.loads(f'[{message}]')
                                messages = parsed_messages
                            except json.JSONDecodeError:
                                messages = []
                                msg_parts = message.split('","')
                                for i, part in enumerate(msg_parts):
                                    if i == 0 and part.startswith('"'):
                                        part = part[1:]
                                    if i == len(msg_parts) - 1 and part.endswith('"'):
                                        part = part[:-1]
                                    messages.append(part)
                        else:
                            messages = [message] * len(friends)
                    elif isinstance(message, list):
                        messages = message
                    else:
                        messages = [str(message)] * len(friends)

                    if len(messages) < len(friends):
                        last_message = messages[-1] if messages else ""
                        messages.extend([last_message] * (len(friends) - len(messages)))
                    elif len(messages) > len(friends):
                        messages = messages[:len(friends)]

                    delay = arguments.get("delay", 1)

                    result = self.wechat_client.send_message_to_friends(
                        friends=friends,
                        message=messages,
                        delay=delay
                    )

                    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

                return [TextContent(type="text", text=f"不支持的工具: {name}")]

            except Exception as e:
                error = ErrorData(message=f"微信服务错误: {str(e)}", code=-32603)
                raise McpError(error)

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )