"""
明日方舟终末地抽卡模拟器 - 主程序入口

运行此文件以执行完整的模拟分析
"""


"""
明日方舟终末地抽卡蒙特卡洛模拟器
用于计算限时抽相当于多少限定抽

核心模拟思路：
1. 模拟两年内的36个卡池的抽卡全生命周期
2. 假设抽卡资源无限，想出的池子必须抽出up，不想出的池子，除上期卡池满60赠送的限定抽和策划给的十限时福利抽外，不投入任何限定抽。
3. 首个卡池初始化为小保底0，大保底0。
4. 如果跳过的池子中很不幸用免费抽抽出本池up，则不影响周期内卡池原规划（如三抽一变成三抽二），但计入up数统计结果，标记为意外up。
5. 小保底如果歪出往期up角色，不重置小保底计数器，但计入意外up统计。（对有规划的下池无任何作用）

核心规则：
1. 基础概率 0.8%
2. 80抽小保底必出6星（跨池继承）
3. 120抽大保底必得UP 6星（仅当期有效，下期清零）
4. 六星为当期UP的概率 50%
5. 65抽后未出6星，从下一抽开始每抽增加概率5%
6. 本期卡池满30抽送10抽（特殊抽，不计入保底，出货不清空小保底和大保底，不干涉小保底跨池继承和大保底跨池清空）
7. 前一个卡池抽满60抽，本期赠送正常10连抽（计入保底和总抽数计数，不算入实际投入抽数）
8. 赠送10抽必须一次性抽完，不能中途停止
9. 120抽大保底同样会清空80小保底水位

策划额外投入每卡池十抽福利方案对比：
方案1: 每卡池赠送当期卡池限定十抽福利，并随卡池过期而过期；
    该十抽计入小保底
    要求先于一般限定抽使用，即需等到第七天领完赠送10单抽，并且全部用完。
    如果同期卡池有上期满60赠送的10抽，则作为总计20抽一起抽掉。
方案2: 每卡池赠送十抽福利，但不限时，玩家可在任意卡池使用；
    该十抽计入小保底
    玩家可在任意卡池使用，要求在60赠抽和30赠抽消耗完后使用。


重要逻辑：
- 小保底：出6星后重置为0，可跨池继承
- 大保底：出UP后重置为0，仅当期有效
- 特殊10抽：完全不影响保底计数，出货不清空小保底，小保底可继承到下一卡池
- 正常10抽：每一抽都计入保底，出货重置相应保底
"""


import pickle
from config import GachaConfig
from strategy_simulator import StrategySimulator


def main():
    """主函数"""
    config = GachaConfig()
    
    print("=" * 60)
    print("明日方舟终末地 - 抽卡策略模拟器")
    print("=" * 60)
    print("\n当前规则:")
    print(f"  • 6星基础概率: {config.base_ssr_rate * 100}%")
    print(f"  • 小保底: {config.small_pity}抽必出6星（跨池继承）")
    print(f"  • 大保底: {config.large_pity}抽必出UP 6星（仅当期）")
    print(f"  • UP概率: {config.up_rate * 100}%")
    print(f"  • 递增保底: {config.increase_threshold}抽后每抽+{config.increase_rate * 100}%")
    print(f"  • 奖励机制: 本期满30抽送{config.bonus_30_pulls}抽（特殊）")
    print(f"  • 奖励机制: 上期满60抽送{config.bonus_60_pulls_prev}抽（正常）")
    print()
    
    
    # 运行策略模拟(执行5000次策略模拟)
    strategy_sim = StrategySimulator(config, iterations=5000)
    
    num_pools = 36  # 模拟36个池子（约2年）
    
    print("\n" + "=" * 60)
    print("策划福利方案效率分析")
    print("=" * 60)
    print("\n每期投入10抽福利，对比两种方案：")
    print("  方案1：限时10抽（随卡池过期）")
    print("  方案2：不限时10抽（可跨期积攒）")
    print()
    
    # 策略1的福利方案对比
    print("\n" + "▶" * 30)
    print("策略1：每期都抽")
    print("▶" * 30)
    
    baseline_1 = strategy_sim.simulate_strategy_1_every_pool(num_pools, welfare_mode=None)
    limited_1 = strategy_sim.simulate_strategy_1_every_pool(num_pools, welfare_mode='limited')
    permanent_1 = strategy_sim.simulate_strategy_1_every_pool(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略1：每期都抽", baseline_1, limited_1, permanent_1, num_pools)
    
    # 策略2的福利方案对比
    print("\n" + "▶" * 30)
    print("策略2：抽1跳1循环")
    print("▶" * 30)
    
    baseline_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode=None)
    limited_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode='limited')
    permanent_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略2：抽1跳1循环", baseline_2, limited_2, permanent_2, num_pools)
    
    # 策略3的福利方案对比
    print("\n" + "▶" * 30)
    print("策略3：两池周期随机选一")
    print("▶" * 30)
    
    baseline_3 = strategy_sim.simulate_strategy_3_random_two(num_pools, welfare_mode=None)
    limited_3 = strategy_sim.simulate_strategy_3_random_two(num_pools, welfare_mode='limited')
    permanent_3 = strategy_sim.simulate_strategy_3_random_two(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略3：两池周期随机选一", baseline_3, limited_3, permanent_3, num_pools)
    
    # 策略4的福利方案对比
    print("\n" + "▶" * 30)
    print("策略4：抽1跳2循环")
    print("▶" * 30)
    
    baseline_4 = strategy_sim.simulate_strategy_4_skip_two(num_pools, welfare_mode=None)
    limited_4 = strategy_sim.simulate_strategy_4_skip_two(num_pools, welfare_mode='limited')
    permanent_4 = strategy_sim.simulate_strategy_4_skip_two(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略4：抽1跳2循环", baseline_4, limited_4, permanent_4, num_pools)
    
    # 策略5的福利方案对比
    print("\n" + "▶" * 30)
    print("策略5：三池周期随机选一")
    print("▶" * 30)
    
    baseline_5 = strategy_sim.simulate_strategy_5_random_three_pick_one(num_pools, welfare_mode=None)
    limited_5 = strategy_sim.simulate_strategy_5_random_three_pick_one(num_pools, welfare_mode='limited')
    permanent_5 = strategy_sim.simulate_strategy_5_random_three_pick_one(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略5：三池周期随机选一", baseline_5, limited_5, permanent_5, num_pools)
    
    # 策略6的福利方案对比
    print("\n" + "▶" * 30)
    print("策略6：三池周期随机选二")
    print("▶" * 30)
    
    baseline_6 = strategy_sim.simulate_strategy_6_random_three_pick_two(num_pools, welfare_mode=None)
    limited_6 = strategy_sim.simulate_strategy_6_random_three_pick_two(num_pools, welfare_mode='limited')
    permanent_6 = strategy_sim.simulate_strategy_6_random_three_pick_two(num_pools, welfare_mode='permanent')
    
    strategy_sim.print_welfare_comparison("策略6：三池周期随机选二", baseline_6, limited_6, permanent_6, num_pools)
    
    # ========== 保存模拟结果 ==========
    print("\n" + "=" * 60)
    print("保存模拟结果")
    print("=" * 60)
    
    # 整合所有策略数据
    all_strategies_data = {
        '策略1：每期都抽': {
            'baseline': baseline_1,
            'limited': limited_1,
            'permanent': permanent_1
        },
        '策略2：抽1跳1': {
            'baseline': baseline_2,
            'limited': limited_2,
            'permanent': permanent_2
        },
        '策略3：随机2选1': {
            'baseline': baseline_3,
            'limited': limited_3,
            'permanent': permanent_3
        },
        '策略4：抽1跳2': {
            'baseline': baseline_4,
            'limited': limited_4,
            'permanent': permanent_4
        },
        '策略5：随机3选1': {
            'baseline': baseline_5,
            'limited': limited_5,
            'permanent': permanent_5
        },
        '策略6：随机3选2': {
            'baseline': baseline_6,
            'limited': limited_6,
            'permanent': permanent_6
        }
    }
    
    # 保存为pickle文件
    simulation_results = {
        'all_strategies_data': all_strategies_data,
        'num_pools': num_pools,
        'config': {
            'base_ssr_rate': config.base_ssr_rate,
            'small_pity': config.small_pity,
            'large_pity': config.large_pity,
            'up_rate': config.up_rate,
            'increase_threshold': config.increase_threshold,
            'increase_rate': config.increase_rate
        }
    }
    
    output_file = 'simulation_results.pkl'
    with open(output_file, 'wb') as f:
        pickle.dump(simulation_results, f)
    
    print(f"\n✓ 模拟结果已保存至: {output_file}")
    print(f"  包含数据: {len(all_strategies_data)} 个策略，每个策略 3 种福利模式")
    print(f"  模拟池数: {num_pools}")
    print(f"\n提示: 运行 'python visualizer.py' 生成可视化图表")



if __name__ == "__main__":
    main()
