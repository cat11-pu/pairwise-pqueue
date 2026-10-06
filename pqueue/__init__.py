"""pqueue：可合并优先队列内核（左偏树 + 稳定次序 + 键值下调）。

对外入口：
    Entry       堆里的一个条目，也是调用方手里的句柄
    LeftistHeap 左偏树极小堆：合并、插入、取最小、键值下调
    merge_all   把 k 个堆一次并成一个新堆
"""

from .core import Entry, LeftistHeap, merge_all

__all__ = ["Entry", "LeftistHeap", "merge_all"]
