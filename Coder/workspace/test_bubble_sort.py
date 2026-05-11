#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冒泡排序 —— 简单验证用例

运行方式：
    python test_bubble_sort.py
"""

from bubble_sort import bubble_sort_new


def main():
    """运行全部测试，输出直观对比结果。"""
    test_cases = [
        ([3, 1, 2],                      "普通乱序列表"),
        ([5, 4, 3, 2, 1],                "完全逆序列表"),
        ([1, 2, 3, 4, 5],                "已有序列表"),
        ([3, 1, 3, 2, 1],                "含重复元素"),
        ([],                              "空列表"),
        ([42],                            "单元素列表"),
        ([2, 1],                          "两元素逆序"),
    ]

    all_ok = True

    for arr, description in test_cases:
        original = arr[:]                   # 保留原始数据
        result = bubble_sort_new(arr)       # 排序
        expected = sorted(original)         # Python 内置排序作为标准答案
        status = "✅" if result == expected else "❌"

        if result != expected:
            all_ok = False

        print(f"{status} {description}")
        print(f"   原始: {original}")
        print(f"   结果: {result}")
        print(f"   期望: {expected}")
        print()

    # 额外验证：稳定性
    print("--- 稳定性验证 ---")
    data = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]
    result = bubble_sort_new(data, key=lambda x: x[0])
    ones = [t[1] for t in result if t[0] == 1]
    stable_ok = ones == ["b", "d"]
    all_ok = all_ok and stable_ok
    print(f"{'✅' if stable_ok else '❌'} 稳定性: 值为1的元素顺序 {'保持' if stable_ok else '被破坏'} (b 在 d 前)")
    print()

    # 额外验证：降序
    print("--- 降序验证 ---")
    desc_result = bubble_sort_new([3, 1, 2], reverse=True)
    desc_ok = desc_result == [3, 2, 1]
    all_ok = all_ok and desc_ok
    print(f"{'✅' if desc_ok else '❌'} 降序: [3, 1, 2] -> {desc_result}")
    print()

    # 总结
    print("=" * 40)
    if all_ok:
        print("🎉 全部测试通过！冒泡排序实现正确。")
    else:
        print("💥 存在失败用例，请检查实现。")


if __name__ == "__main__":
    main()
