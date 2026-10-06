"""pqueue.core 的行为测试：合并、取最小、键值下调、稳定性与结构不变量。"""

import unittest

from pqueue.core import LeftistHeap, merge_all


def shuffled(count):
    """1..count 的固定乱序：用乘法散列排序，跨平台每次一样。"""
    keys = list(range(1, count + 1))
    keys.sort(key=lambda key: (key * 2654435761) % 4294967296)
    return keys


class LeftistHeapTest(unittest.TestCase):
    """可合并优先队列内核。"""

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def build(self, keys):
        heap = LeftistHeap()
        for key in keys:
            heap.push(key, "v%d" % key)
        return heap

    def values(self, entries):
        return [entry.value for entry in entries]

    def check_shape(self, heap, expected=None):
        """核对左偏性质、父指针、堆序，以及结点数与条数是否一致。"""
        root = heap.root
        if root is None:
            self.assertEqual(len(heap), 0, "空堆的条数必须是 0")
            if expected is not None:
                self.assertEqual(expected, 0)
            return
        self.assertIsNone(root.parent, "堆顶不该有父指针")
        seen = set()
        stack = [root]
        count = 0
        while stack:
            node = stack.pop()
            self.assertNotIn(id(node), seen, "同一个结点不能在树里出现两次")
            seen.add(id(node))
            count += 1
            for child in (node.left, node.right):
                if child is None:
                    continue
                self.assertIs(child.parent, node, "孩子的父指针必须指回父亲")
                self.assertGreater((child.key, child.seq), (node.key, node.seq),
                                   "堆序：父必须排在子前面")
                stack.append(child)
            left = 0 if node.left is None else node.left.rank
            right = 0 if node.right is None else node.right.rank
            self.assertGreaterEqual(left, right, "npl 左偏性质：右孩子不能比左孩子深")
            self.assertEqual(node.rank, right + 1, "结点的 npl 必须等于右孩子 npl 加一")
        self.assertEqual(count, len(heap), "树里的结点数必须等于堆的条数")
        if expected is not None:
            self.assertEqual(len(heap), expected)

    # ------------------------------------------------------------------
    # 用例
    # ------------------------------------------------------------------
    def test_01_empty_heap_and_arguments(self):
        """空堆的边界行为，以及非法参数的类型/取值校验。"""
        heap = LeftistHeap()
        self.assertEqual(len(heap), 0)
        self.assertTrue(heap.is_empty())
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.pop())
        self.assertEqual(heap.drain(), [])
        self.assertEqual(len(heap), 0)
        for bad in ("7", 2.5, None, True, (1,)):
            with self.assertRaises(TypeError):
                heap.push(bad, "x")
        self.assertEqual(len(heap), 0)
        entry = heap.push(5, "five")
        self.assertIs(heap.peek(), entry)
        with self.assertRaises(TypeError):
            heap.decrease_key(entry, "3")
        with self.assertRaises(ValueError):
            heap.decrease_key(entry, 6)
        self.assertEqual(heap.peek().key, 5)
        with self.assertRaises(TypeError):
            heap.merge(5)
        with self.assertRaises(ValueError):
            heap.merge(heap)
        self.assertEqual(heap.peek().key, 5)
        self.assertEqual(len(heap), 1)

    def test_02_single_entry_and_small_heap_counters(self):
        """单元素堆与取空之后的条数：len 必须跟着条目走。"""
        heap = LeftistHeap()
        entry = heap.push(4, "four")
        self.assertEqual(len(heap), 1)
        self.assertIs(heap.peek(), entry)
        self.assertIs(heap.pop(), entry)
        self.assertEqual(len(heap), 0)
        self.assertTrue(heap.is_empty())
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.pop())
        small = self.build([7, 3, 9])
        self.assertEqual(len(small), 3)
        self.assertEqual(self.values(small.drain()),
                         ["v3", "v7", "v9"])
        self.assertEqual(len(small), 0)
        self.assertTrue(small.is_empty())
        late = small.push(1, "v1")
        self.assertEqual(len(small), 1)
        self.assertIs(small.pop(), late)
        self.assertEqual(len(small), 0)

    def test_03_equal_keys_leave_in_arrival_order(self):
        """同键条目按到达先后出队，不受堆形影响。"""
        heap = LeftistHeap()
        for key, value in ((4, "a"), (1, "b"), (4, "c"), (2, "d"), (1, "e"),
                           (4, "f"), (2, "g"), (1, "h"), (4, "i"), (1, "j"),
                           (2, "k"), (4, "l")):
            heap.push(key, value)
        self.assertEqual(self.values(heap.drain()),
                         ["b", "e", "h", "j", "d", "g", "k", "a", "c", "f", "i", "l"])
        second = LeftistHeap()
        for value in ("first", "second", "third"):
            second.push(0, value)
        self.assertEqual(self.values(second.drain()),
                         ["first", "second", "third"])
        third = LeftistHeap()
        handles = [third.push(9, "w%d" % index) for index in range(4)]
        third.decrease_key(handles[3], 9)
        self.assertEqual(self.values(third.drain()), ["w0", "w1", "w2", "w3"])

    def test_04_leftist_shape_after_pushes_and_pops(self):
        """建堆与取最小之后，npl / 父指针 / 堆序都必须站得住。"""
        keys = shuffled(240)
        heap = self.build(keys)
        self.check_shape(heap, expected=240)
        for _ in range(80):
            heap.pop()
        self.check_shape(heap, expected=160)
        rest = [entry.key for entry in heap.drain()]
        self.assertEqual(rest, sorted(keys)[80:])

    def test_05_decrease_key_moves_the_key_to_the_front(self):
        """下调键之后条目还在堆里，新键立刻在堆顶可见。"""
        heap = LeftistHeap()
        handles = {}
        for key in range(1, 121):
            handles[key] = heap.push(key, "v%d" % key)
        target = handles[97]
        heap.decrease_key(target, 0)
        self.assertIs(heap.peek(), target)
        self.assertEqual(heap.peek().key, 0)
        self.assertEqual(len(heap), 120)
        entries = heap.drain()
        self.assertEqual(len(entries), 120)
        self.assertIn(target, entries)
        self.assertEqual([entry.key for entry in entries],
                         sorted(entry.key for entry in entries))
        self.assertEqual(entries[0].key, 0)
        self.assertEqual(entries[0].value, "v97")

    def test_06_decrease_key_keeps_the_leftist_shape(self):
        """连续下调之后，树仍然是左偏树：npl、父指针与条数都对得上。"""
        heap = LeftistHeap()
        handles = {}
        for key in range(1, 101):
            handles[key] = heap.push(key, "v%d" % key)
        self.check_shape(heap, expected=100)
        for key in (88, 64, 32, 12, 4):
            heap.decrease_key(handles[key], -key)
        self.check_shape(heap, expected=100)
        self.assertIs(heap.peek(), handles[88])
        keys = [entry.key for entry in heap.drain()]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(keys[:5], [-88, -64, -32, -12, -4])

    def test_07_merge_empties_the_source_heap(self):
        """归并之后源堆被清空，两边不再共用条目。"""
        left = self.build([1, 5, 9, 13, 17])
        right = LeftistHeap()
        for value in ("r1", "r2", "r3"):
            right.push(4, value)
        left.merge(right)
        self.assertEqual(len(left), 8)
        self.assertEqual(len(right), 0)
        self.assertTrue(right.is_empty())
        self.assertIsNone(right.peek())
        self.assertIsNone(right.pop())
        self.assertEqual(right.drain(), [])
        self.assertEqual(len(left), 8)
        drained = left.drain()
        self.assertEqual([entry.key for entry in drained],
                         [1, 4, 4, 4, 5, 9, 13, 17])
        self.assertEqual(sorted(self.values(drained)[1:4]), ["r1", "r2", "r3"])
        self.assertEqual(len(right), 0)

    def test_08_merge_all_consumes_k_heaps(self):
        """批量归并 k 个堆：结果条数不变，每个输入堆都被清空。"""
        heaps = [LeftistHeap() for _ in range(4)]
        expected = []
        for index, heap in enumerate(heaps):
            for key in (index + 1, index + 5, index + 9):
                expected.append((key, "h%d" % index))
                heap.push(key, "h%d" % index)
        total = merge_all(heaps)
        self.assertEqual(len(total), 12)
        for heap in heaps:
            self.assertEqual(len(heap), 0)
            self.assertTrue(heap.is_empty())
        drained = total.drain()
        self.assertEqual(len(drained), 12)
        self.assertEqual([entry.key for entry in drained],
                         sorted(key for key, _ in expected))
        self.assertEqual(merge_all([]).drain(), [])

    def test_09_duplicate_keys_survive_a_long_run(self):
        """长序列里的重复键一个不丢，取出顺序非递减且同键先到先出。"""
        heap = LeftistHeap()
        keys = shuffled(200)
        marks = []
        for step, key in enumerate(keys):
            marks.append((key // 7, "m%d" % step))
            heap.push(key // 7, "m%d" % step)
        self.check_shape(heap, expected=200)
        drained = heap.drain()
        self.assertEqual(len(drained), 200)
        self.assertEqual([entry.key for entry in drained],
                         sorted(key for key, _ in marks))
        same_key = [entry.value for entry in drained if entry.key == 3]
        self.assertEqual(same_key,
                         [mark for key, mark in marks if key == 3])


if __name__ == "__main__":
    unittest.main()
