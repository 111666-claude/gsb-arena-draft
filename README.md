# arena-draft

禁选阶段：双方轮流禁英雄、超时默认禁选，只用 Python 标准库。

```
python3 -m arenadraft.cli --sample duplicate
python3 -m arenadraft.cli --sample timeout
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **同一英雄只能被禁一次**：第二次禁同一个英雄（无论哪一方）都要报 `DraftError`。
  `--sample duplicate`（a 禁 hero1、b 也禁 hero1）按口径是 `bans=1 unique=1`，现在给 `bans=2`。
- **超时要有默认禁选**：`now > deadline` 之后还没禁选的一方由系统默认禁掉英雄池里第一个未被禁的。
  `--sample timeout`（都没提交就超时）按口径是 `bans=2`，现在给 `bans=0`。
- **英雄必须在池里**：不在英雄池里的提交要报错，且不改变禁选状态。
- 不变量：所有禁选英雄互不重复；每一方的禁选数不超过约定上限；同一批提交重复处理结果相同。
- 规模：单次禁选 200 个英雄、10 万次提交 1 秒内完成，内存 O(英雄池)。

## 现在的行为

- `ban` 直接 append，不看英雄池、不看重复、不看超时。
- `resolve` 只统计已有禁选数，超时不做默认禁选。

## 输出

```
bans=1 unique=1
bans=2
```

## 目录

```
arenadraft/draft.py   禁选状态机
arenadraft/cli.py     命令行入口
tests/                unittest 用例
```
