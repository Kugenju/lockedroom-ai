"""终端试玩客户端（LockedRoom AI）。

先启动服务（另一个终端）：
    .venv\\Scripts\\python.exe -m uvicorn app.api.app:create_app --factory --app-dir backend --port 18000
然后运行：
    .venv\\Scripts\\python.exe scripts\\play.py
"""

import argparse
import sys

import httpx


def main() -> None:
    ap = argparse.ArgumentParser(description="LockedRoom AI 终端试玩")
    ap.add_argument("--base", default="http://127.0.0.1:18000", help="后端地址")
    ap.add_argument("--script", default="snow-night-villa", help="剧本 id")
    ap.add_argument("--no-self-intro", action="store_true", help="跳过角色自我介绍")
    args = ap.parse_args()

    client = httpx.Client(base_url=args.base, timeout=180)

    game = client.post("/api/games", json={"script_id": args.script})
    game.raise_for_status()
    game = game.json()
    gid = game["game_id"]
    chars = game["characters"]

    print(f"\n=== {game['title']} ===")
    print(game["brief"])
    print("\n在场可问询角色：")
    for i, c in enumerate(chars, 1):
        print(f"  {i}. {c['name']}（{c['role']}）— {c['personality']}")

    def advance(target: str) -> None:
        r = client.post(f"/api/games/{gid}/phase", json={"target": target})
        r.raise_for_status()

    input("\n[背景介绍完毕，回车进入自我介绍阶段]")

    if not args.no_self_intro:
        advance("self_intro")
        print()
        for c in chars:
            print(f"【{c['name']}】", end="", flush=True)
            r = client.post(
                f"/api/games/{gid}/talk",
                json={"character_id": c["id"], "message": "请用第一人称做一段简短的自我介绍。"},
            )
            r.raise_for_status()
            print(r.json()["reply"])

    input("\n[进入搜证阶段，回车继续]")
    advance("evidence")
    print("\n（搜证线索板将在后续版本开放，目前直接进入自由调查）")

    advance("investigation")
    print("\n=== 自由调查阶段：向角色提问收集线索（输入 q 退出）===\n")

    while True:
        for i, c in enumerate(chars, 1):
            print(f"  {i}. {c['name']}")
        choice = input("选择角色编号（q 退出）: ").strip()
        if choice.lower() == "q":
            break
        if not choice.isdigit() or not (1 <= int(choice) <= len(chars)):
            print("无效输入\n")
            continue
        c = chars[int(choice) - 1]
        message = input(f"你对{c['name']}说: ").strip()
        if not message:
            continue
        try:
            r = client.post(
                f"/api/games/{gid}/talk",
                json={"character_id": c["id"], "message": message},
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            print(f"请求失败：{e}\n")
            continue
        data = r.json()
        print(f"{c['name']}: {data['reply']}\n")
        if data["rewritten"]:
            print("  [InfoGuard] 该回复曾触发泄露检测，已被拦截重写\n")
        if data["fell_back"]:
            print("  [InfoGuard] 该回复多次触发泄露，已降级为安全回复\n")

    print("对局结束。复盘与评估系统（ReplayEval）将在后续版本开放。")
    print(f"事件流留档：GET {args.base}/api/games/{gid}/events")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
        sys.exit(0)
