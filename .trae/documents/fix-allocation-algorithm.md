# 修复抽奖方案算法：高级优先 vs 均衡差异化

## 问题诊断

当前 [budget_allocator.py](file:///D:/Project/PythonProject/birthday%20gift/backend/app/services/budget_allocator.py) 的两个分配函数 `allocate_premium` 和 `allocate_diverse` **结果几乎相同**，都只给每级最多 1 张券：

- `allocate_premium`: A→B→C 各给 1 张（预算够的话）
- `allocate_diverse`: 预算够 A+B+C 最低价之和就给各 1 张，否则和 premium 相同

**两个方案都只是 "1A + 1B + 1C"，没区别。**

## 新算法设计

### 高级优先 (Premium)
最大化高级券数量，从 A 到 C **贪婪分配**：

```
remaining = budget
for tier in [A, B, C]:
    max_count = floor(remaining / min_price[tier])  ← 能买几张买几张
    capped = min(max_count, available_count[tier])  ← 受库存限制
    draws[tier] = capped
    remaining -= capped * min_price[tier]
```

| 预算 | 旧算法 | 新算法 |
|------|--------|--------|
| ¥5000 | 1A+1B+1C = 3抽 | 2A+2B+10C = 14抽 (A优先) |
| ¥10000 | 1A+1B+1C = 3抽 | 5A+0B+0C = 5抽 (全砸A) |

### 均衡多样 (Diverse)
先确保每级 1 张（够的话），剩余预算**优先给便宜等级**，抽奖次数最大化：

```
Phase 1: 保证 1A+1B+1C（预算够的话）
Phase 2: 剩余预算全部给 C 级，C 满了给 B，B 满了给 A
```

| 预算 | 旧算法 | 新算法 |
|------|--------|--------|
| ¥5000 | 1A+1B+1C = 3抽 | 1A+1B+X C = 大量抽 |
| ¥10000 | 1A+1B+1C = 3抽 | 1A+1B+X C = 大量抽 |

### 对比效果（假设 A min=1999, B min=399, C min=19，C 库存 20 个）

| 预算 ¥5000 | 高级优先 | 均衡多样 |
|-----------|---------|---------|
| A 券 | **2** | 1 |
| B 券 | **2** | 1 |
| C 券 | 10 | **20（全满）** |
| 总抽数 | 14 | **22** |
| 风格 | 💎 重高级 | 🎈 重数量 |

— 差异非常明显。

## 实施步骤

### 步骤 1: 重写 `allocate_premium` 函数
- 贪婪分配：从 A→B→C，每级 `floor(remaining/min_price)` 张，受可用数量上限
- 标记 `remaining` 逐步扣减

### 步骤 2: 重写 `allocate_diverse` 函数
- Phase 1: 给每级至少 1 张（预算够 + 有库存）
- Phase 2: 剩余预算从 C→B→A 分配，每个等级能拿多少拿多少
- 结果：总抽奖次数最多

### 步骤 3: 更新 `estimate_cost` 的计算方式
- 多层券时成本 = count * min_price[tier]

### 步骤 4: 验证
- 用实际数据测试两个方案差异明显
- API 返回结构不变（draws 字段天然支持 count > 1）