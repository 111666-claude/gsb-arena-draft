"""禁选阶段：双方轮流禁英雄，超时给默认禁选。

口径（见 README）：
- 同一英雄全场只能被禁一次，重复禁（无论哪一方）报 DraftError；
- 不在英雄池里的提交报 DraftError，且不改变禁选状态；
- now > deadline 之后，未满额的一方由系统默认禁掉池里第一个未被禁的；
- 不变量：禁选互不重复、每方不超过 limit、resolve 可重复调用结果相同。
"""


class DraftError(ValueError):
    """输入不合法。消息里带英雄名，方便定位是哪次提交出了问题。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Draft:
    """一次禁选。

    - pool: 英雄池，顺序即超时默认禁选的优先顺序；
    - deadline: 提交截止时间，deadline <= 0 表示不限时；
    - limit: 每一方禁选数的约定上限。
    """

    def __init__(self, pool, deadline=0, limit=1):
        self.pool = list(pool)
        self.deadline = deadline
        self.limit = limit
        self.bans = {"a": [], "b": []}
        self._pool_set = frozenset(self.pool)
        self._banned = set()


def _timed_out(draft, now):
    return draft.deadline > 0 and now > draft.deadline


def ban(draft, side, hero, now):
    """禁一个英雄。

    超时、池外英雄、重复禁选、超过单方上限都报 DraftError；
    先校验后落库，报错时不改变禁选状态。
    """
    if side not in draft.bans:
        raise DraftError("unknown side %r for hero %r" % (side, hero))
    if _timed_out(draft, now):
        raise DraftError(
            "ban %r too late: now=%s deadline=%s" % (hero, now, draft.deadline)
        )
    if hero not in draft._pool_set:
        raise DraftError("hero %r not in pool" % (hero,))
    if hero in draft._banned:
        raise DraftError("hero %r already banned" % (hero,))
    if len(draft.bans[side]) >= draft.limit:
        raise DraftError(
            "side %s reached ban limit %d, cannot ban %r" % (side, draft.limit, hero)
        )
    draft.bans[side].append(hero)
    draft._banned.add(hero)
    return draft


def _default_hero(draft):
    """英雄池里第一个未被禁的英雄；池子禁完了返回 None。"""
    for hero in draft.pool:
        if hero not in draft._banned:
            return hero
    return None


def resolve(draft, now):
    """统计禁选结果。

    now > deadline 时，为还没禁满的一方补上默认禁选（池里第一个未被禁的）。
    可重复调用：补满之后再次调用不改变状态，结果相同。
    """
    if _timed_out(draft, now):
        for side in ("a", "b"):
            while len(draft.bans[side]) < draft.limit:
                hero = _default_hero(draft)
                if hero is None:
                    break
                draft.bans[side].append(hero)
                draft._banned.add(hero)
    return sum(len(items) for items in draft.bans.values())
