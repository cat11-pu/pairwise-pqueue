# pqueue

一个纯标准库、可确定复现的可合并优先队列内核：左偏树形式的极小堆，支持两个堆归并、
k 个堆批量归并、插入与取最小、句柄式的键值下调，以及同键条目的稳定出队次序。
内核不读时钟、不起线程、不做 I/O，也不使用随机数。

## 目录

- `pqueue/core.py`：内核实现（`Entry` 句柄、`LeftistHeap`、`merge_all`）
- `tests/test_core.py`：行为与结构不变量测试

## 语义约定

- 每个条目是一个 `Entry`：`key` 是排序键（int），`value` 是载荷，`seq` 是条目创建时
  领到的到达号。排序用 `(key, seq)` 这个全序：键小的排前面，键相同时先到的排前面。
- 堆是左偏树：每个结点带 `npl`（null path length），空结点记 0，叶子记 1，
  `npl` 等于右孩子的 `npl` 加一，并且左孩子的 `npl` 不小于右孩子。
- 对外接口：

      heap = LeftistHeap()
      entry = heap.push(3, "three")   # 返回句柄
      heap.peek()                     # 最小条目；空堆返回 None
      heap.pop()                      # 取出最小条目；空堆返回 None
      heap.decrease_key(entry, 1)     # 只许把键调小，条目对象就地更新
      heap.merge(other)               # 把 other 并进本堆，other 被清空
      heap.drain()                    # 按升序取出全部条目
      len(heap)                       # 堆里的条目数
      merge_all([a, b, c])            # 批量归并成新堆，输入堆被清空

## 怎么跑测试

在项目根目录执行：

    python3 -m unittest discover -s tests -v

Windows 上把 `python3` 换成你的解释器路径，例如：

    C:/Users/<你>/AppData/Local/Programs/Python/Python313/python.exe -m unittest discover -s tests -v

只依赖 Python 3 标准库，不需要装任何包，也不需要联网。
