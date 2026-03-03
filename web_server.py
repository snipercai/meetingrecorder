"""
Web服务器模块
提供HTTP静态文件服务和WebSocket实时通信功能
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Set

from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)


class WebServer:
    """Web服务器类，提供HTTP和WebSocket服务"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """
        初始化Web服务器

        Args:
            host: 服务器监听地址，默认为0.0.0.0
            port: 服务器监听端口，默认为8080
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.websocket_clients: Set[web.WebSocketResponse] = set()
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self._handle_index)
        self.app.router.add_get("/ws", self._handle_websocket)
        self.app.router.add_static("/static", self._get_static_dir())

    def _get_static_dir(self) -> Path:
        """获取静态文件目录路径"""
        return Path(__file__).parent / "static"

    async def _handle_index(self, request: web.Request) -> web.Response:
        """
        处理首页请求

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象
        """
        index_path = self._get_static_dir() / "index.html"
        if index_path.exists():
            return web.FileResponse(index_path)
        logger.warning("index.html 文件不存在")
        return web.Response(text="欢迎使用会议转写系统", content_type="text/html")

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """
        处理WebSocket连接

        Args:
            request: HTTP请求对象

        Returns:
            WebSocket响应对象
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websocket_clients.add(ws)
        client_ip = request.remote
        logger.info(f"WebSocket客户端已连接: {client_ip}, 当前连接数: {len(self.websocket_clients)}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    logger.debug(f"收到WebSocket消息: {msg.data}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket连接错误: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket连接异常: {e}")
        finally:
            self.websocket_clients.discard(ws)
            logger.info(f"WebSocket客户端已断开: {client_ip}, 当前连接数: {len(self.websocket_clients)}")

        return ws

    async def broadcast_transcription(self, text: str):
        """
        广播转写文字到所有WebSocket客户端

        Args:
            text: 要广播的转写文字
        """
        message = {
            "type": "transcription",
            "content": text,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_message(message)

    async def broadcast_summary(self, summary: str):
        """
        广播会议总结到所有WebSocket客户端

        Args:
            summary: 要广播的会议总结
        """
        message = {
            "type": "summary",
            "content": summary,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_message(message)

    async def _broadcast_message(self, message: dict):
        """
        广播消息到所有WebSocket客户端

        Args:
            message: 要广播的消息字典
        """
        if not self.websocket_clients:
            logger.debug("没有连接的WebSocket客户端，跳过广播")
            return

        message_json = json.dumps(message, ensure_ascii=False)
        disconnected_clients = []

        for ws in self.websocket_clients:
            try:
                await ws.send_str(message_json)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected_clients.append(ws)

        for ws in disconnected_clients:
            self.websocket_clients.discard(ws)
            logger.info(f"移除断开的WebSocket客户端，当前连接数: {len(self.websocket_clients)}")

        logger.info(f"消息已广播到 {len(self.websocket_clients)} 个客户端")

    async def start(self):
        """启动Web服务器"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            logger.info(f"Web服务器已启动: http://{self.host}:{self.port}")
        except OSError as e:
            logger.error(f"服务器启动失败，端口可能被占用: {e}")
            raise
        except Exception as e:
            logger.error(f"服务器启动异常: {e}")
            raise

    async def stop(self):
        """停止Web服务器"""
        logger.info("正在停止Web服务器...")

        for ws in self.websocket_clients:
            try:
                await ws.close()
            except Exception as e:
                logger.error(f"关闭WebSocket连接失败: {e}")

        self.websocket_clients.clear()

        if self.runner:
            await self.runner.cleanup()
            logger.info("Web服务器已停止")


async def main():
    """主函数，用于测试"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    server = WebServer()
    try:
        await server.start()
        logger.info("按 Ctrl+C 停止服务器")
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
