# 明日方舟终末地抽卡模拟器

## 文件结构

项目已重构，按功能模块拆分为多个文件：

### 核心模块

- **`config.py`** - 配置类
  - `GachaConfig`: 抽卡系统的所有配置参数

- **`pool_state.py`** - 状态管理类
  - `PoolState`: 单个卡池的状态管理

- **`simulator_core.py`** - 核心模拟器
  - `GachaSimulator`: 抽卡核心逻辑
    - 单抽模拟
    - 保底机制
    - UP判定
    - 福利管理

- **`monte_carlo_analyzer.py`** - 蒙特卡洛分析器
  - `MonteCarloAnalyzer`: 基础分析工具
    - 单池模拟
    - 结果统计

- **`strategy_simulator.py`** - 策略模拟器
  - `StrategySimulator`: 多池子策略模拟
    - 策略1-6的实现
    - 福利方案对比
    - 结果打印

### 执行文件

- **`main.py`** - 主程序入口
  - 执行完整的6种策略模拟
  - 生成 `simulation_results.pkl`

- **`visualizer.py`** - 可视化工具
  - 读取模拟结果
  - 生成统计图表

### 备份文件

- **`gacha_simulator.py.backup`** - 原始文件备份

## 使用方法

### 1. 运行模拟

```bash
python main.py
```

这将执行所有6种策略的模拟，并保存结果到 `simulation_results.pkl`

### 2. 生成图表

```bash
python visualizer.py
```

读取模拟结果并生成可视化图表

## 模块依赖关系

```
main.py
  ├── config.py (GachaConfig)
  └── strategy_simulator.py (StrategySimulator)
        ├── config.py (GachaConfig)  
        └── simulator_core.py (GachaSimulator)
              ├── config.py (GachaConfig)
              └── pool_state.py (PoolState)

monte_carlo_analyzer.py
  ├── config.py (GachaConfig)
  └── simulator_core.py (GachaSimulator)
```

## 注意事项

1. 所有导入都使用模块名（不使用相对导入）
2. `simulator_core.py` 是 `gacha_simulator.py` 的核心部分
3. 原始的 `gacha_simulator.py` 已备份为 `gacha_simulator.py.backup`
4. 如需使用原版本，可以恢复备份文件

## 概率设置

- **当期UP**: 50%
- **往期UP**: 14.29% (50% × 2/7)
- **常驻六星**: 35.71% (50% × 5/7)
