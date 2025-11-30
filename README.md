# NFA → DFA → 最小化 DFA（Python实现）

一个小工具：

* 支持 **ε-NFA（用 `eps` 表示 ε）→ DFA（子集构造）**
* 再进行 **DFA 最小化**
* 输出 **两次结果**（DFA 与最小化 DFA）。

---

## 1. 运行环境

* Python 3.8+
* Graphviz（用于把 `.dot` 渲染为 `.png`）

  * macOS: `brew install graphviz`
  * Ubuntu/Debian: `sudo apt-get install graphviz`
  * Windows:

    1. 安装 Graphviz（[https://graphviz.org](https://graphviz.org)），
    2. 将安装目录下的 `bin` 加入 `PATH`（确保 `dot -V` 有输出）。

---

## 2. 使用方法

把脚本保存为 `nfa2dfa_min.py`，准备好 `input.json`，然后在终端执行：

```bash
# 生成两次输出（DFA 与最小化 DFA）
python nfa2dfa_min.py input.json out_prefix

# 稍等片刻，再将 .dot 渲染为 .png
dot -Tpng out_prefix.dfa.dot -o dfa.png
dot -Tpng out_prefix.min.dot -o dfa_min.png
```

生成的文件：

* `out_prefix.dfa.json` / `out_prefix.dfa.dot`：NFA → DFA 的首次输出
* `out_prefix.min.json` / `out_prefix.min.dot`：最小化 DFA 的二次输出
* `dfa.png` / `dfa_min.png`：对应的渲染图片

> 说明：脚本内部会临时补一个 sink 以保证最小化正确性，但**导出时会自动删除 sink 和相关边**，所以最终文件里没有 sink、没有多余节点。

---

## 3. 输入格式（`input.json`）

```json
{
  "states": ["q0", "q1", "q2"],
  "alphabet": ["a", "b", "eps"],
  "start": "q0",
  "accepts": ["q2"],
  "transitions": [
    {"from": "q0", "symbol": "a", "to": "q1"},
    {"from": "q0", "symbol": "b", "to": "q0"},
    {"from": "q1", "symbol": "a", "to": "q1"},
    {"from": "q1", "symbol": "b", "to": "q2"},
    {"from": "q2", "symbol": "a", "to": "q2"},
    {"from": "q2", "symbol": "b", "to": "q2"}
  ]
}
```

* `alphabet` 中不要写 `ε`，统一用 `"eps"`；若写了 `ε`，脚本也会自动转为 `eps`。
* `transitions` 允许多条，`symbol` 取自 `alphabet` 或 `"eps"`。

---

## 4. 输出说明

* **状态命名**

  * 第一次输出（DFA）：`D0, D1, ...`
  * 最小化后：按起点 BFS 顺序重命名为 `M0, M1, ...`
* **字符集**：全 ASCII，边标签形如 `a,b`；无 `{q0,q1}` 这种集合花括号。
* **DFA 完全性**：输出允许**缺边**（partial DFA），不强制存在死状态。
* **JSON 字段**

  * `states`, `alphabet`, `start`, `accepts`, `transitions`（列表，元素含 `from/symbol/to`）

---

## 5. 示例（快速验证）

示例用于识别包含子串 `ab` 的串（最小化后 3 个状态）：

`input.json`

```json
{
  "states": ["q0", "q1", "q2"],
  "alphabet": ["a", "b"],
  "start": "q0",
  "accepts": ["q2"],
  "transitions": [
    {"from": "q0", "symbol": "a", "to": "q1"},
    {"from": "q0", "symbol": "b", "to": "q0"},
    {"from": "q1", "symbol": "a", "to": "q1"},
    {"from": "q1", "symbol": "b", "to": "q2"},
    {"from": "q2", "symbol": "a", "to": "q2"},
    {"from": "q2", "symbol": "b", "to": "q2"}
  ]
}
```

运行命令（同上）后，你会得到 `out_prefix.dfa.*` 和 `out_prefix.min.*` 两套结果，图片 `dfa.png` 与 `dfa_min.png` 清晰可渲染。

---

## 6. 常见问题（FAQ）

* **渲染乱码/看不到箭头文字？**
  输出全 ASCII，通常是 Graphviz 未正确安装或 `.dot` 未完整写入。先检查 `dot -V`，再确认 `.dot` 文件内容完整。

