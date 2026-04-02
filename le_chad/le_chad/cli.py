import argparse
import json
import sys

import httpx

BASE = "http://localhost:8000"


def cmd_tasks(args):
    r = httpx.get(f"{BASE}/tasks")
    tasks = r.json()
    for t in tasks:
        print(f"  [{t['id']}] [{t['priority']}] {t['title']} ({t['status']}) - {t['comment_count']} comments")


def cmd_task(args):
    r = httpx.get(f"{BASE}/tasks/{args.id}")
    data = r.json()
    print(json.dumps(data, indent=2))


def cmd_create(args):
    r = httpx.post(f"{BASE}/tasks", json={"title": args.title, "description": args.description})
    print(r.json())


def cmd_users(args):
    r = httpx.get(f"{BASE}/users")
    for u in r.json():
        print(f"  [{u['id']}] {u['username']} ({u['email']})")


def cmd_standups(args):
    r = httpx.get(f"{BASE}/standups")
    for s in r.json():
        print(f"  [{s['user']}] yesterday: {s['yesterday']} | today: {s['today']}")


def cmd_stats(args):
    r = httpx.get(f"{BASE}/stats")
    print(json.dumps(r.json(), indent=2))


def cmd_search(args):
    r = httpx.get(f"{BASE}/tasks/search", params={"q": args.query})
    for t in r.json():
        print(f"  [{t['id']}] {t['title']} ({t['status']})")


def main():
    parser = argparse.ArgumentParser(description="le Chad CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("tasks")
    sub.add_parser("users")
    sub.add_parser("standups")
    sub.add_parser("stats")

    p = sub.add_parser("task")
    p.add_argument("id", type=int)

    p = sub.add_parser("create")
    p.add_argument("title")
    p.add_argument("--description", default="")

    p = sub.add_parser("search")
    p.add_argument("query")

    args = parser.parse_args()

    commands = {
        "tasks": cmd_tasks,
        "task": cmd_task,
        "create": cmd_create,
        "users": cmd_users,
        "standups": cmd_standups,
        "stats": cmd_stats,
        "search": cmd_search,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
