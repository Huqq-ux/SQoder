# 文本反转技能

## 描述
将输入的文本反转返回，支持可选转大写

## 分类
文本处理

## 标签
`测试` `文本` `示例`

## 参数
| 参数名    | 类型 | 必填 | 说明                   |
| --------- | ---- | ---- | ---------------------- |
| text      | str  | 是   | 要处理的文本           |
| uppercase | str  | 否   | 是否大写，填"是"或"否" |

## 代码
```python
def execute(text, uppercase="否"):
    result = text[::-1]
    if uppercase == "是":
        result = result.upper()
    return result
```