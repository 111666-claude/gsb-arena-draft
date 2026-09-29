"""命令行入口：跑禁选样例。"""

import argparse

from .draft import Draft, ban, resolve


def build_parser():
    parser = argparse.ArgumentParser(prog="arena-draft", description="禁选阶段")
    parser.add_argument("--sample", default="duplicate", help="duplicate / timeout")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    pool = ["hero1", "hero2", "hero3"]
    if args.sample == "duplicate":
        draft = Draft(pool, deadline=100)
        ban(draft, "a", "hero1", 10)
        ban(draft, "b", "hero1", 20)
        print("bans=%d unique=%d" % (resolve(draft, 30), len(set(draft.bans["a"] + draft.bans["b"]))))
    elif args.sample == "timeout":
        draft = Draft(pool, deadline=100)
        print("bans=%d" % resolve(draft, 500))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
