import docker
from docker.errors import DockerException
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker")


def get_client():
    """延迟初始化 Docker client，避免服务在启动阶段因 socket/权限问题直接崩溃。"""
    try:
        return docker.from_env()
    except DockerException as exc:
        raise RuntimeError(f"Docker 不可用: {exc}") from exc

@mcp.tool()
def docker_ps(all: bool = False):
    """列出 Docker 容器。all=True 显示所有容器（包括已停止的）。"""
    try:
        client = get_client()
        containers = client.containers.list(all=all)
        return [{"id": c.short_id, "name": c.name, "status": c.status, "image": c.image.tags} for c in containers]
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def docker_logs(container_name: str, tail: int = 100):
    """获取容器日志。"""
    try:
        client = get_client()
        container = client.containers.get(container_name)
        return container.logs(tail=tail).decode("utf-8")
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def docker_inspect(container_name: str):
    """获取容器详细信息。"""
    try:
        client = get_client()
        container = client.containers.get(container_name)
        return container.attrs
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
