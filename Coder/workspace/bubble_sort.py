#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冒泡排序 —— 完整生产级实现

包含：
  - 标准冒泡排序（提前终止优化）
  - 鸡尾酒排序（双向冒泡）
  - 完整的类型注解与错误处理
  - doctest 可测试用例

运行方式：
    python bubble_sort.py          # 执行内置测试
    python -m doctest bubble_sort.py -v  # 运行 doctest
"""

from typing import Any, Callable, List, Optional, TypeVar

T = TypeVar("T")


# ============================================================================
# 内部辅助
# ============================================================================

def _default_key(x: T) -> Any:
    """默认排序键函数：返回元素自身。"""
    return x


def _validate_sequence(data: Any, func_name: str) -> None:
    """
    校验输入是否为可索引的序列类型。

    Args:
        data: 待校验输入
        func_name: 调用方函数名，用于错误信息

    Raises:
        TypeError: 输入类型不支持
    """
    if not hasattr(data, "__getitem__") or not hasattr(data, "__len__"):
        raise TypeError(
            f"{func_name}() 期望一个可索引序列，但收到了 {type(data).__name__}"
        )


# ============================================================================
# 标准冒泡排序
# ============================================================================

def bubble_sort(
    data: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
    inplace: bool = True,
) -> Optional[List[T]]:
    """
    冒泡排序（带提前终止优化）。

    核心思路：
        重复遍历序列，比较相邻元素，若顺序错误则交换。
        若某趟遍历没有发生任何交换，说明已有序，提前终止。

    时间复杂度：
        - 最坏 O(n²)（完全逆序）
        - 最佳 O(n) （已有序）
    空间复杂度：O(1)
    稳定性：✅ 稳定（相等元素不交换）

    Args:
        data:   待排序列表
        key:    排序键函数，类似 sorted() 的 key 参数
        reverse: True 表示降序，False 表示升序（默认）
        inplace: True 原地排序（默认），False 返回新列表

    Returns:
        若 inplace=True 返回 None（原地修改）；
        若 inplace=False 返回排序后的新列表。

    Raises:
        TypeError: data 不可索引

    Examples:
        >>> bubble_sort([3, 1, 2])
        [1, 2, 3]

        >>> bubble_sort([3, 1, 2], reverse=True)
        [3, 2, 1]

        >>> lst = [3, 1, 2]
        >>> bubble_sort(lst, inplace=True)  # 返回 None
        >>> lst
        [1, 2, 3]

        >>> bubble_sort(["aa", "b", "ccc"], key=len)
        ['b', 'aa', 'ccc']

        >>> bubble_sort([])
        []

        >>> bubble_sort([42])
        [42]
    """
    _validate_sequence(data, "bubble_sort")

    # 决定是否复制
    arr = data if inplace else data[:]
    n = len(arr)
    if n <= 1:
        return None if inplace else arr

    # 解析 key
    kf = key if key is not None else _default_key

    # ---- 冒泡核心 ----
    for i in range(n - 1):
        swapped = False
        # 第 i 趟：后 i 个元素已就位
        for j in range(n - 1 - i):
            a_val = kf(arr[j])
            b_val = kf(arr[j + 1])

            # 判断是否需要交换
            if reverse:
                need_swap = a_val < b_val
            else:
                need_swap = a_val > b_val

            if need_swap:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True

        if not swapped:  # 提前终止：本趟零交换
            break

    return None if inplace else arr


# ============================================================================
# 鸡尾酒排序（双向冒泡）
# ============================================================================

def cocktail_sort(
    data: List[T],
    key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False,
    inplace: bool = True,
) -> Optional[List[T]]:
    """
    鸡尾酒排序 —— 冒泡排序的双向变体。

    每轮：
      1. 从左到右冒泡，将最大值推到右边界
      2. 从右到左冒泡，将最小值推到左边界
    双向收缩，对接近有序的数据略优。

    时间复杂度：同冒泡排序 O(n²) / O(n)
    空间复杂度：O(1)
    稳定性：✅ 稳定

    Args:
        data / key / reverse / inplace: 同 bubble_sort

    Returns:
        同 bubble_sort

    Examples:
        >>> cocktail_sort([3, 1, 2])
        [1, 2, 3]

        >>> cocktail_sort([5, 1, 4, 2, 8])
        [1, 2, 4, 5, 8]

        >>> cocktail_sort([], inplace=False)
        []
    """
    _validate_sequence(data, "cocktail_sort")

    arr = data if inplace else data[:]
    n = len(arr)
    if n <= 1:
        return None if inplace else arr

    kf = key if key is not None else _default_key

    left, right = 0, n - 1

    while left < right:
        swapped = False

        # 正向：左 → 右
        for i in range(left, right):
            a_val = kf(arr[i])
            b_val = kf(arr[i + 1])
            if reverse:
                need_swap = a_val < b_val
            else:
                need_swap = a_val > b_val
            if need_swap:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                swapped = True
        right -= 1

        if not swapped:
            break

        swapped = False
        # 反向：右 → 左
        for i in range(right, left, -1):
            a_val = kf(arr[i - 1])
            b_val = kf(arr[i])
            if reverse:
                need_swap = a_val < b_val
            else:
                need_swap = a_val > b_val
            if need_swap:
                arr[i - 1], arr[i] = arr[i], arr[i - 1]
                swapped = True
        left += 1

        if not swapped:
            break

    return None if inplace else arr


# ============================================================================
# 便捷别名
# ============================================================================

def bubble_sort_new(data: List[T], **kwargs) -> List[T]:
    """便捷函数：始终返回新列表。"""
    return bubble_sort(data, inplace=False, **kwargs)  # type: ignore[return-value]


# ============================================================================
# 内置测试
# ============================================================================

def _run_tests() -> None:
    """运行一组功能测试，覆盖主要场景。"""
    import sys

    tests_passed = 0
    tests_failed = 0

    def test(name: str, actual, expected) -> None:
        nonlocal tests_passed, tests_failed
        if actual == expected:
            tests_passed += 1
            print(f"  ✅ {name}")
        else:
            tests_failed += 1
            print(f"  ❌ {name}")
            print(f"     期望: {expected!r}")
            print(f"     实际: {actual!r}")

    print("=" * 60)
    print("冒泡排序 功能测试")
    print("=" * 60)

    # ---- 基础功能 ----
    print("\n📌 基础升序")
    test("普通列表", bubble_sort_new([3, 1, 2]), [1, 2, 3])
    test("已有序", bubble_sort_new([1, 2, 3]), [1, 2, 3])
    test("逆序", bubble_sort_new([3, 2, 1]), [1, 2, 3])
    test("含重复", bubble_sort_new([3, 1, 3, 2, 1]), [1, 1, 2, 3, 3])

    # ---- 降序 ----
    print("\n📌 降序 (reverse=True)")
    test("普通列表", bubble_sort_new([3, 1, 2], reverse=True), [3, 2, 1])
    test("已有序", bubble_sort_new([3, 2, 1], reverse=True), [3, 2, 1])

    # ---- key 函数 ----
    print("\n📌 key 函数")
    test("按长度", bubble_sort_new(["aa", "b", "ccc"], key=len), ["b", "aa", "ccc"])
    test("按绝对值", bubble_sort_new([-3, 1, -2], key=abs), [1, -2, -3])

    # ---- 边界 ----
    print("\n📌 边界条件")
    test("空列表", bubble_sort_new([]), [])
    test("单元素", bubble_sort_new([42]), [42])
    test("两元素有序", bubble_sort_new([1, 2]), [1, 2])
    test("两元素逆序", bubble_sort_new([2, 1]), [1, 2])

    # ---- 原地排序 ----
    print("\n📌 原地排序 (inplace=True)")
    lst = [3, 1, 2]
    ret = bubble_sort(lst, inplace=True)
    test("返回 None", ret, None)
    test("原地修改", lst, [1, 2, 3])

    # ---- 稳定性验证 ----
    print("\n📌 稳定性")
    # 用 (值, 标签) 元组，按值排序，相同值的标签顺序应不变
    unstable_input = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]
    stable_output = bubble_sort_new(unstable_input, key=lambda x: x[0])
    # 值为 1 的：("b") 应在 ("d") 之前
    ones = [t for t in stable_output if t[0] == 1]
    test("稳定性(1)", ones[0][1], "b")
    test("稳定性(2)", ones[1][1], "d")

    # ---- 鸡尾酒排序 ----
    print("\n📌 鸡尾酒排序")
    test("基础", cocktail_sort([3, 1, 2], inplace=False), [1, 2, 3])
    test("逆序", cocktail_sort([5, 4, 3, 2, 1], inplace=False), [1, 2, 3, 4, 5])

    # ---- 类型错误 ----
    print("\n📌 错误处理")
    try:
        bubble_sort(42)  # type: ignore[arg-type]
        test("类型错误检测", "未抛出异常", "应抛出 TypeError")
    except TypeError:
        test("类型错误检测", "TypeError", "TypeError")

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    total = tests_passed + tests_failed
    print(f"结果: {tests_passed}/{total} 通过, {tests_failed} 失败")
    if tests_failed > 0:
        sys.exit(1)


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    _run_tests()
