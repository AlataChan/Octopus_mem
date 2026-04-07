#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json

from . import MemoryManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="octopus-mem")
    subparsers = parser.add_subparsers(dest="command", required=True)

    store_parser = subparsers.add_parser("store")
    store_parser.add_argument("content")
    store_parser.add_argument("--type", dest="memory_type", choices=["daily", "long_term"], default="daily")
    store_parser.add_argument("--skill")

    retrieve_parser = subparsers.add_parser("retrieve")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--skill")
    retrieve_parser.add_argument("--limit", type=int, default=5)

    subparsers.add_parser("stats")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manager = MemoryManager(base_path=".")

    if args.command == "store":
        memory_id = manager.store_memory(
            args.content,
            memory_type=args.memory_type,
            skill_name=args.skill,
        )
        print(memory_id)
        return 0

    if args.command == "retrieve":
        results = manager.retrieve_memory(
            args.query,
            skill_name=args.skill,
            limit=args.limit,
        )
        for result in results:
            print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "stats":
        print(json.dumps(manager.get_memory_statistics(), ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
