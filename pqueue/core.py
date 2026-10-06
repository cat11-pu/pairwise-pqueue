"""pqueue：可合并优先队列内核（左偏树）。

结构约定
--------
* 条目是一个 Entry：key 是排序键（int），value 是载荷，seq 是条目创建时领到的
  到达号。排序用 (key, seq) 这个全序：键小的排前面，键相同时先到的排前面，
  所以重复键各自独立，出队次序稳定。
* 堆是左偏树形式的极小堆。每个结点带 npl（null path length）：空结点记 0，
  叶子记 1，非叶结点 npl 等于右孩子的 npl 加一；同时要求左孩子的 npl 不小于
  右孩子。这条左偏性质把右脊长度压在 O(log n)，合并只沿右脊递归。
* 合并是唯一的结构操作：插入、取最小、批量归并、键值下调最终都落在它上面。
* 调用方拿到的句柄就是堆里的条目对象。decrease_key 就地把键改小并恢复堆序，
  句柄始终有效；被 pop 取出的条目与堆彻底脱钩。
* 全程只依赖调用参数与内部状态：不读时钟、不做 I/O、不用随机数、不起线程。
"""

import itertools

__all__ = ["Entry", "LeftistHeap", "merge_all"]

_ARRIVAL = itertools.count()


def _check_key(key):
    """键必须是 int，bool 不算。"""
    if isinstance(key, bool) or not isinstance(key, int):
        raise TypeError("键必须是 int")


def _rank(node):
    """结点的 npl；空结点记 0。"""
    return 0 if node is None else node.rank


def _before(first, second):
    """first 是否排在 second 前面。"""
    return first.key <= second.key


def _join(a, b):
    """合并两棵左偏树，返回新的子树顶；返回值的父指针留给调用方补。"""
    if a is None:
        return b
    if b is None:
        return a
    if _before(b, a):
        a, b = b, a
    a.right = _join(a.right, b)
    if a.right is not None:
        a.right.parent = a
    if _rank(a.left) > _rank(a.right):
        a.left, a.right = a.right, a.left
    a.rank = _rank(a.right) + 1
    return a


class Entry:
    """堆里的一个条目，同时是调用方手里的句柄。

    key 与 value 是业务字段；seq 是到达号；left、right、parent、rank 是左偏树
    的链接与 npl，只读即可，调用方不需要改动它们。
    """

    __slots__ = ("key", "value", "seq", "left", "right", "parent", "rank")

    def __init__(self, key, value=None):
        self.key = key
        self.value = value
        self.seq = next(_ARRIVAL)
        self.left = None
        self.right = None
        self.parent = None
        self.rank = 1

    def __repr__(self):
        return "Entry(key=%r, value=%r, seq=%r)" % (self.key, self.value, self.seq)


class LeftistHeap:
    """左偏树实现的极小堆，支持合并与键值下调。

    语义：
        push(key, value)         放入一个条目，返回它的句柄
        peek()                   最小条目；空堆返回 None
        pop()                    取出最小条目；空堆返回 None
        decrease_key(entry, k)   把 entry 的键下调到 k（只许调小），就地更新
        merge(other)             把 other 的条目并进本堆，other 被清空
        drain()                  按升序取出全部条目，堆被清空
        __len__()                堆里的条目数
        is_empty()               是否空堆
    """

    def __init__(self):
        self.root = None
        self.size = 0

    def __len__(self):
        return self.size

    def is_empty(self):
        return self.root is None

    def __repr__(self):
        return "LeftistHeap(size=%d)" % self.size

    def peek(self):
        """最小条目；空堆返回 None。"""
        return self.root

    def push(self, key, value=None):
        """放入一个条目并返回句柄；键必须是 int。"""
        _check_key(key)
        entry = Entry(key, value)
        self.root = _join(self.root, entry)
        self.root.parent = None
        self.size += 1
        return entry

    def pop(self):
        """取出最小条目；空堆返回 None。"""
        if self.root is None:
            return None
        entry = self.root
        self.root = _join(entry.left, entry.right)
        if self.root is None:
            return entry
        self.root.parent = None
        entry.left = None
        entry.right = None
        entry.parent = None
        entry.rank = 1
        self.size -= 1
        return entry

    def merge(self, other):
        """把 other 的条目并进本堆（other 清空），返回自身。"""
        if not isinstance(other, LeftistHeap):
            raise TypeError("只能合并另一个 LeftistHeap")
        if other is self:
            raise ValueError("不能把堆并进它自己")
        if other.root is not None:
            self.root = _join(self.root, other.root)
            self.root.parent = None
            self.size += other.size
        return self

    def decrease_key(self, entry, new_key):
        """把 entry 的键下调到 new_key；键变大抛 ValueError。

        条目对象原地更新，句柄不变，条目的数量也不变。
        """
        if not isinstance(entry, Entry):
            raise TypeError("entry 必须是堆里的条目")
        _check_key(new_key)
        if new_key > entry.key:
            raise ValueError("新键不能大于旧键")
        if new_key == entry.key:
            return
        entry.key = new_key
        parent = entry.parent
        if parent is None or _before(entry, parent):
            return
        self._lift(entry, parent)

    def _lift(self, entry, parent):
        """把 entry 从 parent 下面摘出来，再并回堆顶。"""
        stand_in = _join(entry.left, entry.right)
        if parent.left is entry:
            parent.left = stand_in
        else:
            parent.right = stand_in
        if stand_in is not None:
            stand_in.parent = parent
        self._fix_up(parent)
        entry.left = None
        entry.right = None
        entry.parent = None
        entry.rank = 1

    def _fix_up(self, node):
        """从 node 出发沿父链把 npl 与左偏性质修好，到 rank 不再变化为止。"""
        while node is not None:
            rank = _rank(node.right) + 1
            if rank == node.rank:
                return
            node.rank = rank
            node = node.parent

    def drain(self):
        """按升序取出所有条目，堆被清空。"""
        out = []
        while self.root is not None:
            out.append(self.pop())
        return out


def merge_all(heaps):
    """把 k 个堆并成一个新堆；每个输入堆都被清空。"""
    heaps = list(heaps)
    if not heaps:
        return LeftistHeap()
    total = heaps[0]
    for heap in heaps[1:]:
        total.merge(heap)
    return total
