"""禁选阶段：双方轮流禁英雄，超时给默认禁选。

口径：
- 同一英雄只能被禁一次，重复禁（无论哪一方）报 DraftError。
- 不在英雄池里的提交报 DraftError，且不改变禁选状态。
- deadline 为正且 now > deadline 之后仍未禁满的一方，由系统默认禁掉
  英雄池里第一个未被禁的；deadline 为 0 表示不限时。
- 不变量：禁选英雄互不重复；每方禁选数不超过 limit；重复处理结果相同。
"""


class DraftError(ValueError):
    """输入不合法。"""

    def __init__(self, message, hero=None):
        super().__init__(message)
        self.message = message
        self.hero = hero


class Draft:
    """一次禁选。"""

    SIDES = ("a", "b")

    def __init__(self, pool, deadline=0, limit=1):
        self.pool = list(pool)
        self.deadline = deadline
        self.limit = limit
        self.bans = {"a": [], "b": []}
        self._pool_set = set(self.pool)
        self._banned = set()


def _expired(draft, now):
    return bool(draft.deadline) and now > draft.deadline


def _apply_defaults(draft):
    """给未禁满的一方补上默认禁选：英雄池里第一个未被禁的。幂等。"""
    for side in Draft.SIDES:
        missing = draft.limit - len(draft.bans[side])
        if missing <= 0:
            continue
        for hero in draft.pool:
            if hero in draft._banned:
                continue
            draft.bans[side].append(hero)
            draft._banned.add(hero)
            missing -= 1
            if missing == 0:
                break


def ban(draft, side, hero, now):
    """禁一个英雄。非法提交报 DraftError 且不改变禁选状态。"""
    if side not in draft.bans:
        raise DraftError("unknown side: %r" % (side,), hero)
    if hero not in draft._pool_set:
        raise DraftError("hero not in pool: %r" % (hero,), hero)
    if _expired(draft, now):
        _apply_defaults(draft)
        raise DraftError("submission after deadline: %r" % (hero,), hero)
    if hero in draft._banned:
        raise DraftError("hero already banned: %r" % (hero,), hero)
    if len(draft.bans[side]) >= draft.limit:
        raise DraftError(
            "side %r reached ban limit %d" % (side, draft.limit), hero)
    draft.bans[side].append(hero)
    draft._banned.add(hero)
    return draft


def resolve(draft, now):
    """统计禁选结果；超时后未禁满的一方由系统默认禁选。"""
    if _expired(draft, now):
        _apply_defaults(draft)
    return sum(len(items) for items in draft.bans.values())
