"""禁选阶段：双方轮流禁英雄，超时给默认禁选。

缺陷：同一英雄可被双方重复禁、超时不做默认禁选、提交不校验英雄池。
"""


class DraftError(ValueError):
    """输入不合法。缺陷：不带英雄名。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Draft:
    """一次禁选。"""

    def __init__(self, pool, deadline=0):
        self.pool = list(pool)
        self.deadline = deadline
        self.bans = {"a": [], "b": []}


def ban(draft, side, hero, now):
    """禁一个英雄。缺陷：不校验英雄池、不拦重复、不看是否超时。"""
    draft.bans[side].append(hero)
    return draft


def resolve(draft, now):
    """统计禁选结果。缺陷：超时不做默认禁选，只返回已有数量。"""
    return sum(len(items) for items in draft.bans.values())
