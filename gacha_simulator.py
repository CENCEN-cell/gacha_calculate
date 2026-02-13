"""
明日方舟终末地抽卡蒙特卡洛模拟器
用于计算限时抽相当于多少限定抽

核心模拟思路：
1. 模拟两年内的36个卡池的抽卡全生命周期
2. 假设抽卡资源无限，想出的池子必须抽出up，不想出的池子，除上期卡池满60赠送的限定抽和策划给的十限时福利抽外，不投入任何限定抽。
3. 首个卡池初始化为小保底0，大保底0。

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
10. 共模拟两36个池子（以21天为一个池子周期，约两年）

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

import random
from typing import List, Dict, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pickle
import os

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


@dataclass
class GachaConfig:
    """抽卡配置"""
    # 基础概率
    base_ssr_rate: float = 0.008  # 6星基础概率 0.8%
    
    # 保底机制
    small_pity: int = 80  # 80抽小保底必出6星
    large_pity: int = 120  # 120抽大保底必得UP 6星
    
    # UP概率
    up_rate: float = 0.5  # 六星为UP的概率 50%
    
    # 递增保底
    increase_threshold: int = 65  # 65抽后开始递增
    increase_rate: float = 0.05  # 每抽增加5%
    
    # 奖励机制
    bonus_30_pulls: int = 10  # 满30抽送10抽（特殊）
    bonus_60_pulls_prev: int = 10  # 上期满60抽本期送10抽（正常）


class PoolState:
    """单个卡池的状态"""
    def __init__(self):
        self.small_pity_counter = 0  # 小保底计数（跨池继承）
        self.large_pity_counter = 0  # 大保底计数（仅当期）
        self.total_pulls = 0  # 当期总抽数
        self.got_30_bonus = False  # 是否已获得30抽奖励
        self.bonus_10_special = 0  # 特殊10抽剩余
        self.bonus_10_normal = 0  # 正常10抽剩余（来自上期）
        self.welfare_limited = 0  # 策划限时福利抽（仅当期，过期作废）
        self.welfare_permanent = 0  # 策划不限时福利抽（可跨期积攒）


class GachaSimulator:
    """抽卡模拟器"""
    
    def __init__(self, config: GachaConfig):
        self.config = config
        self.state = PoolState()
    
    def reset_for_new_pool(self, prev_pool_pulls: int = 0):
        """
        切换到新卡池
        prev_pool_pulls: 上一个卡池的抽数（用于判断是否送10抽）
        """
        # 小保底水位继承
        old_small_pity = self.state.small_pity_counter
        # 不限时福利需要跨池累积
        old_welfare_permanent = self.state.welfare_permanent
        
        # 重置状态
        self.state = PoolState()
        self.state.small_pity_counter = old_small_pity  # 继承小保底
        self.state.welfare_permanent = old_welfare_permanent  # 不限时福利跨池保留
        
        # 上期满60抽，本期送10正常抽
        if prev_pool_pulls >= 60:
            self.state.bonus_10_normal = 10
    
    def calculate_current_ssr_rate(self) -> float:
        """计算当前6星概率"""
        base_rate = self.config.base_ssr_rate
        
        # 65抽后开始递增
        if self.state.small_pity_counter > self.config.increase_threshold:
            extra_pulls = self.state.small_pity_counter - self.config.increase_threshold
            base_rate += extra_pulls * self.config.increase_rate
        
        assert base_rate <= 1.0, "概率不能超过100%"
        return base_rate
    
    def single_pull_normal(self) -> Tuple[bool, bool]:
        """
        正常单次抽卡（计入保底）
        返回: (是否出6星, 是否是UP角色)
        """
        # 增加保底计数器
        self.state.small_pity_counter += 1
        self.state.large_pity_counter += 1
        self.state.total_pulls += 1
        
        # 检查30抽奖励
        if self.state.total_pulls >= 30 and not self.state.got_30_bonus:
            self.state.got_30_bonus = True
            self.state.bonus_10_special = 10
        
        
        # 大保底：120抽必出UP 6星（优先级最高）
        if self.state.large_pity_counter >= self.config.large_pity:
            self.state.small_pity_counter = 0  # 大保底触发时同时重置小保底
            self.state.large_pity_counter = 0  # 重置大保底
            return True, True  # 必定是UP
        
        
        # 小保底：80抽必出6星
        if self.state.small_pity_counter >= self.config.small_pity:
            is_ssr = True
        else:
            # 正常概率判定
            ssr_rate = self.calculate_current_ssr_rate()
            is_ssr = random.random() < ssr_rate
        
        if not is_ssr:
            return False, False
        
        # 出了6星，重置小保底
        self.state.small_pity_counter = 0
        
        # 判断是否是UP
        is_up = random.random() < self.config.up_rate
        
        if is_up:
            # 出了UP，重置大保底
            self.state.large_pity_counter = 0
        
        return True, is_up
    
    def single_pull_special(self) -> Tuple[bool, bool]:
        """
        特殊10抽（不计入保底，出货不重置保底）
        返回: (是否出6星, 是否是UP角色)
        """
        # 特殊抽不增加任何保底计数器
        # 只使用基础概率判定，不受保底影响
        ssr_rate = self.config.base_ssr_rate
        is_ssr = random.random() < ssr_rate
        
        if not is_ssr:
            return False, False
        
        # 出了6星，判断是否是UP（不重置任何保底）
        is_up = random.random() < self.config.up_rate
        
        return True, is_up
    
    def pull_until_target(self, use_welfare: bool = False) -> Dict:
        """
        抽到目标UP角色为止
        use_welfare: 是否使用策划福利抽（方案2不限时福利）
        
        抽卡优先级规则：
        1. 60送正常10抽 + 限时福利10抽（同一优先级，一起抽完，计入保底）
        2. 30送特殊10抽（一次性抽完，不计入保底）
        3. 永久福利抽（逐个使用，计入保底）
        4. 实际投入抽数（逐个使用，计入保底）
        
        返回: {
            'pulls': 实际消耗的抽数,
            'total_pulls': 总抽数（包括赠送）,
            'bonus_used': 使用的赠送抽数,
            'bonus_normal_used': 60送的正常10抽使用数,
            'bonus_special_used': 30送的特殊10抽使用数,
            'welfare_used': 使用的策划福利抽数,
            'welfare_limited_used': 限时福利使用数,
            'welfare_permanent_used': 永久福利使用数
        }
        """
        actual_pulls = 0  # 实际消耗的抽数
        bonus_used = 0  # 使用的赠送抽数
        bonus_normal_used = 0  # 60送的正常10抽使用数
        bonus_special_used = 0  # 30送的特殊10抽使用数
        welfare_limited_used = 0  # 限时福利使用数
        welfare_permanent_used = 0  # 永久福利使用数
        target_met = False  # 是否已经抽到UP
        
        while True:
            # 优先级1：60送正常10抽 + 限时福利10抽（同一优先级，一起抽完）
            if self.state.bonus_10_normal > 0 or self.state.welfare_limited > 0:
                # 记录要抽的数量（抽之前先记录，因为后面会清零）
                bonus_10_count = self.state.bonus_10_normal  # 比如 10
                welfare_limited_count = self.state.welfare_limited  # 比如 10
                combined_pulls = bonus_10_count + welfare_limited_count  # 总共 20
                
                # 清零状态
                self.state.bonus_10_normal = 0
                self.state.welfare_limited = 0
                
                # 一次性抽完所有60送和限时福利
                for i in range(combined_pulls):
                    if i < bonus_10_count:
                        # 前 bonus_10_count 次循环：来自60送
                        bonus_used += 1
                        bonus_normal_used += 1
                    else:
                        # 后面的循环：来自限时福利
                        welfare_limited_used += 1
                    
                    is_ssr, is_up = self.single_pull_normal()
                    if is_ssr and is_up:
                        target_met = True
                
                # 抽完这批后，检查是否可以提前返回
                # 条件：已出UP并返回
                if target_met:
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls
                    }
                continue
            
            # 优先级2：30送的特殊10抽（强制一次性抽完，不计入保底）
            if self.state.bonus_10_special > 0:
                pulls_to_do = self.state.bonus_10_special
                self.state.bonus_10_special = 0
                for _ in range(pulls_to_do):
                    bonus_used += 1
                    bonus_special_used += 1
                    is_ssr, is_up = self.single_pull_special()
                    if is_ssr and is_up:
                        target_met = True
                # 抽完特殊10抽后，如果已出UP就可以返回了
                # 因为永久福利和实际抽数都是逐个使用的，可以随时停止
                if target_met:
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls
                    }
                continue
            
            # 优先级3：永久福利抽（逐个使用，可随时停止）
            if use_welfare and self.state.welfare_permanent > 0:
                self.state.welfare_permanent -= 1
                welfare_permanent_used += 1
                is_ssr, is_up = self.single_pull_normal()
                if is_ssr and is_up:
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls
                    }
                continue
            
            # 优先级4：使用实际抽数（逐个使用）
            actual_pulls += 1
            is_ssr, is_up = self.single_pull_normal()
            if is_ssr and is_up:
                return {
                    'pulls': actual_pulls,
                    'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                    'bonus_used': bonus_used,
                    'bonus_normal_used': bonus_normal_used,
                    'bonus_special_used': bonus_special_used,
                    'welfare_used': welfare_limited_used + welfare_permanent_used,
                    'welfare_limited_used': welfare_limited_used,
                    'welfare_permanent_used': welfare_permanent_used,
                    'pool_pulls': self.state.total_pulls
                }


class MonteCarloAnalyzer:
    """蒙特卡洛分析器 - 基础版"""
    
    def __init__(self, config: GachaConfig, iterations: int = 10000):
        self.config = config
        self.iterations = iterations
    
    def simulate_pool(self, prev_pool_pulls: int = 0) -> List[Dict]:
        """
        模拟单个卡池多次
        prev_pool_pulls: 上一个卡池的抽数
        返回: 模拟结果列表
        """
        results = []
        
        print(f"正在模拟卡池，共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            simulator.reset_for_new_pool(prev_pool_pulls)
            result = simulator.pull_until_target()
            results.append(result)
        
        return results
    
    def print_results(self, results: List[Dict]):
        """打印模拟结果"""
        actual_pulls = [r['pulls'] for r in results]
        total_pulls = [r['total_pulls'] for r in results]
        bonus_used = [r['bonus_used'] for r in results]
        bonus_normal_used = [r['bonus_normal_used'] for r in results]
        bonus_special_used = [r['bonus_special_used'] for r in results]
        
        actual_sorted = sorted(actual_pulls)
        n = len(actual_pulls)
        
        print("\n" + "=" * 60)
        print("【模拟结果】")
        print("=" * 60)
        print(f"\n模拟次数: {n}")
        print(f"\n实际消耗抽数:")
        print(f"  平均值: {sum(actual_pulls) / n:.2f} 抽")
        print(f"  中位数: {actual_sorted[n // 2]} 抽")
        print(f"  最小值: {min(actual_pulls)} 抽")
        print(f"  最大值: {max(actual_pulls)} 抽")
        print(f"  25%分位数: {actual_sorted[n // 4]} 抽")
        print(f"  75%分位数: {actual_sorted[n * 3 // 4]} 抽")
        print(f"  90%分位数: {actual_sorted[int(n * 0.9)]} 抽")
        
        print(f"\n总抽数 (含赠送):")
        print(f"  平均值: {sum(total_pulls) / n:.2f} 抽")
        
        print(f"\n赠送抽数统计:")
        print(f"  总赠送平均值: {sum(bonus_used) / n:.2f} 抽")
        print(f"  60送的正常10抽平均值: {sum(bonus_normal_used) / n:.2f} 抽")
        print(f"  30送的特殊10抽平均值: {sum(bonus_special_used) / n:.2f} 抽")
        
        print("\n" + "=" * 60 + "\n")


class StrategySimulator:
    """多池子策略模拟器"""
    
    def __init__(self, config: GachaConfig, iterations: int = 10000):
        self.config = config
        self.iterations = iterations
    
    def simulate_strategy_1_every_pool(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略1：每期都抽
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略1：每期都抽 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子，共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0  # 用户实际花费的抽数（不含任何赠送）
            welfare_invested = 0  # 策划投入的总福利数
            welfare_used_total = 0  # 实际使用的福利数
            prev_pool_pulls = 0
            pity_history = []  # 记录每个卡池结束时的小保底水位
            
            for pool_idx in range(num_pools):
                simulator.reset_for_new_pool(prev_pool_pulls)
                
                # 添加策划福利
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                
                result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                user_spent += result['pulls']  # pulls 就是用户自费的抽数
                welfare_used_total += result.get('welfare_used', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)  # 记录卡池结束时的小保底
            
            results.append({
                'user_spent': user_spent,  # 用户自费总数
                'num_targets': num_pools,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history  # 小保底历史
            })
        
        return results
    
    def simulate_strategy_2_skip_one(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略2：抽1跳1循环
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        num_cycles = num_pools // 2
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略2：抽1跳1循环 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子（{num_cycles} 个周期），共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0  # 用户实际花费的抽数（不含任何赠送）
            welfare_invested = 0
            welfare_used_total = 0
            prev_pool_pulls = 0
            pity_history = []
            
            for cycle in range(num_cycles):
                # 第1个池子：跳过（只用赠送和限时福利）
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                
                self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                prev_pool_pulls = simulator.state.total_pulls
                pity_history.append(simulator.state.small_pity_counter)
                
                # 第2个池子：抽
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                
                result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                user_spent += result['pulls']  # pulls 就是用户自费的抽数
                welfare_used_total += result.get('welfare_used', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
            
            results.append({
                'user_spent': user_spent,  # 用户自费总数
                'num_targets': num_cycles,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_3_random_two(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略3：以两个卡池为周期，随机选择其中一个抽
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        num_cycles = num_pools // 2
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略3：两池周期随机选一 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子（{num_cycles} 个周期），共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0
            welfare_invested = 0
            welfare_used_total = 0
            prev_pool_pulls = 0
            pity_history = []
            
            for cycle in range(num_cycles):
                # 随机选择抽哪个池子（0或1）
                pull_idx = random.randint(0, 1)
                
                for pool_in_cycle in range(2):
                    simulator.reset_for_new_pool(prev_pool_pulls)
                    
                    # 添加策划福利
                    if welfare_mode == 'limited':
                        simulator.state.welfare_limited = 10
                        welfare_invested += 10
                    elif welfare_mode == 'permanent':
                        simulator.state.welfare_permanent += 10
                        welfare_invested += 10
                    
                    if pool_in_cycle == pull_idx:
                        # 选中的池子：抽
                        result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                        user_spent += result['pulls']
                        welfare_used_total += result.get('welfare_used', 0)
                        prev_pool_pulls = result['pool_pulls']
                    else:
                        # 未选中的池子：跳过（只用赠送）
                        self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                        prev_pool_pulls = simulator.state.total_pulls
                    pity_history.append(simulator.state.small_pity_counter)
            
            results.append({
                'user_spent': user_spent,
                'num_targets': num_cycles,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_4_skip_two(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略4：抽1跳2循环
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        num_cycles = num_pools // 3
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略4：抽1跳2循环 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子（{num_cycles} 个周期），共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0
            welfare_invested = 0
            welfare_used_total = 0
            prev_pool_pulls = 0
            pity_history = []
            
            for cycle in range(num_cycles):
                # 第1个池子：跳过
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                prev_pool_pulls = simulator.state.total_pulls
                pity_history.append(simulator.state.small_pity_counter)
                
                # 第2个池子：跳过
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                prev_pool_pulls = simulator.state.total_pulls
                pity_history.append(simulator.state.small_pity_counter)
                
                # 第3个池子：抽
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                user_spent += result['pulls']
                welfare_used_total += result.get('welfare_used', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
            
            results.append({
                'user_spent': user_spent,
                'num_targets': num_cycles,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_5_random_three_pick_one(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略5：以三个卡池为周期，随机选择其中一个抽
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        num_cycles = num_pools // 3
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略5：三池周期随机选一 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子（{num_cycles} 个周期），共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0
            welfare_invested = 0
            welfare_used_total = 0
            prev_pool_pulls = 0
            pity_history = []
            
            for cycle in range(num_cycles):
                # 随机选择抽哪个池子（0, 1, 或2）
                pull_idx = random.randint(0, 2)
                
                for pool_in_cycle in range(3):
                    simulator.reset_for_new_pool(prev_pool_pulls)
                    
                    # 添加策划福利
                    if welfare_mode == 'limited':
                        simulator.state.welfare_limited = 10
                        welfare_invested += 10
                    elif welfare_mode == 'permanent':
                        simulator.state.welfare_permanent += 10
                        welfare_invested += 10
                    
                    if pool_in_cycle == pull_idx:
                        # 选中的池子：抽
                        result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                        user_spent += result['pulls']
                        welfare_used_total += result.get('welfare_used', 0)
                        prev_pool_pulls = result['pool_pulls']
                    else:
                        # 未选中的池子：跳过（只用赠送）
                        self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                        prev_pool_pulls = simulator.state.total_pulls
                    pity_history.append(simulator.state.small_pity_counter)
            
            results.append({
                'user_spent': user_spent,
                'num_targets': num_cycles,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_6_random_three_pick_two(self, num_pools: int, welfare_mode: str = None) -> List[Dict]:
        """
        策略6：以三个卡池为周期，随机选择其中两个抽
        welfare_mode: None(无福利), 'limited'(限时福利), 'permanent'(不限时福利)
        """
        results = []
        num_cycles = num_pools // 3
        
        mode_name = {None: "无福利", 'limited': "限时福利", 'permanent': "不限时福利"}
        print(f"\n【策略6：三池周期随机选二 - {mode_name.get(welfare_mode, '未知')}】")
        print(f"正在模拟 {num_pools} 个池子（{num_cycles} 个周期），共 {self.iterations} 次...")
        
        for i in range(self.iterations):
            if (i + 1) % 1000 == 0:
                print(f"进度: {i + 1}/{self.iterations}")
            
            simulator = GachaSimulator(self.config)
            user_spent = 0
            welfare_invested = 0
            welfare_used_total = 0
            prev_pool_pulls = 0
            pity_history = []
            
            for cycle in range(num_cycles):
                # 随机选择跳过哪个池子（0, 1, 或2）
                skip_idx = random.randint(0, 2)
                
                for pool_in_cycle in range(3):
                    simulator.reset_for_new_pool(prev_pool_pulls)
                    
                    # 添加策划福利
                    if welfare_mode == 'limited':
                        simulator.state.welfare_limited = 10
                        welfare_invested += 10
                    elif welfare_mode == 'permanent':
                        simulator.state.welfare_permanent += 10
                        welfare_invested += 10
                    
                    if pool_in_cycle == skip_idx:
                        # 跳过的池子：只用赠送
                        self._pull_bonus_only(simulator, use_limited_welfare=(welfare_mode == 'limited'))
                        prev_pool_pulls = simulator.state.total_pulls
                    else:
                        # 选中的池子：抽
                        result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                        user_spent += result['pulls']
                        welfare_used_total += result.get('welfare_used', 0)
                        prev_pool_pulls = result['pool_pulls']
                    pity_history.append(simulator.state.small_pity_counter)
            
            results.append({
                'user_spent': user_spent,
                'num_targets': num_cycles * 2,
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def _pull_bonus_only(self, simulator: GachaSimulator, use_limited_welfare: bool = False) -> None:
        """
        只抽赠送的抽数和限时福利，不投入额外资源
        use_limited_welfare: 是否使用限时福利（方案1）
        """
        # 使用限时福利10抽（方案1，与60送一起或单独）
        if use_limited_welfare and simulator.state.welfare_limited > 0:
            simulator.state.welfare_limited = 0
            for _ in range(10):
                simulator.single_pull_normal()
        
        # 使用60送的正常10抽
        if simulator.state.bonus_10_normal > 0:
            simulator.state.bonus_10_normal -= 10
            for _ in range(10):
                simulator.single_pull_normal()
        
        # 使用30送的特殊10抽
        if simulator.state.bonus_10_special > 0:
            simulator.state.bonus_10_special -= 10
            for _ in range(10):
                simulator.single_pull_special()


    def simulate_strategy_with_welfare_comparison(self, strategy_name: str, num_pools: int, 
                                                   strategy_func, *args) -> Dict:
        """
        对比分析两种策划福利方案
        返回: {
            'baseline': 无福利基准结果,
            'limited': 限时福利（方案1）结果,
            'permanent': 不限时福利（方案2）结果
        }
        """
        print(f"\n{'=' * 60}")
        print(f"【{strategy_name} - 策划福利方案对比】")
        print(f"{'=' * 60}")
        
        # 基准：无福利
        print(f"\n[1/3] 模拟基准（无策划福利）...")
        baseline_results = strategy_func(num_pools, *args, welfare_mode=None)
        
        # 方案1：限时福利
        print(f"\n[2/3] 模拟方案1（限时10抽）...")
        limited_results = strategy_func(num_pools, *args, welfare_mode='limited')
        
        # 方案2：不限时福利
        print(f"\n[3/3] 模拟方案2（不限时10抽）...")
        permanent_results = strategy_func(num_pools, *args, welfare_mode='permanent')
        
        return {
            'baseline': baseline_results,
            'limited': limited_results,
            'permanent': permanent_results
        }
    
    def print_welfare_comparison(self, strategy_name: str, baseline_results: List[Dict], 
                                limited_results: List[Dict], permanent_results: List[Dict], 
                                num_pools: int) -> None:
        """
        打印策划福利方案对比统计（关注用户实际花费）
        """
        print(f"\n{'=' * 70}")
        print(f"【{strategy_name} - 福利方案效率分析】")
        print(f"{'=' * 70}")
        
        # 基准统计（无福利）
        baseline_spent = [r['user_spent'] for r in baseline_results]
        baseline_targets = baseline_results[0]['num_targets']
        avg_baseline = sum(baseline_spent) / len(baseline_spent)
        
        # 限时福利统计（方案1）
        limited_spent = [r['user_spent'] for r in limited_results]
        limited_welfare_invested = limited_results[0]['welfare_invested']
        avg_limited = sum(limited_spent) / len(limited_spent)
        limited_saved = avg_baseline - avg_limited
        
        # 不限时福利统计（方案2）
        permanent_spent = [r['user_spent'] for r in permanent_results]
        permanent_welfare_invested = permanent_results[0]['welfare_invested']
        avg_permanent = sum(permanent_spent) / len(permanent_spent)
        permanent_saved = avg_baseline - avg_permanent
        
        # 输出对比
        print(f"\n模拟条件：")
        print(f"  • 卡池总数: {num_pools} 个")
        print(f"  • 获得UP数: {baseline_targets} 个")
        print(f"  • 策划投入: {limited_welfare_invested} 抽 (每池10抽)")
        print(f"  • 模拟次数: {len(baseline_results)} 次")
        
        print(f"\n一、用户实际花费对比（不含60送、30送、福利）")
        print(f"  ┌{'─' * 65}┐")
        print(f"  │ {'场景':<15} │ {'总花费(抽)':<15} │ {'每UP花费(抽)':<15} │")
        print(f"  ├{'─' * 65}┤")
        print(f"  │ {'基准(无福利)':<13} │ {avg_baseline:>13.1f}   │ {avg_baseline/baseline_targets:>13.1f}   │")
        print(f"  │ {'方案1(限时)':<13} │ {avg_limited:>13.1f}   │ {avg_limited/baseline_targets:>13.1f}   │")
        print(f"  │ {'方案2(不限时)':<11} │ {avg_permanent:>13.1f}   │ {avg_permanent/baseline_targets:>13.1f}   │")
        print(f"  └{'─' * 65}┘")
        
        print(f"\n二、福利效率分析")
        print(f"  ┌{'─' * 65}┐")
        print(f"  │ {'方案':<15} │ {'节省花费(抽)':<15} │ {'效率(倍)':<18} │")
        print(f"  ├{'─' * 65}┤")
        print(f"  │ {'方案1(限时)':<13} │ {limited_saved:>13.1f}   │ {limited_saved/limited_welfare_invested:>16.2f}   │")
        print(f"  │ {'方案2(不限时)':<11} │ {permanent_saved:>13.1f}   │ {permanent_saved/permanent_welfare_invested:>16.2f}   │")
        print(f"  └{'─' * 65}┘")
        
        # 计算方案对比
        efficiency_drop = (1 - limited_saved / permanent_saved) * 100 if permanent_saved > 0 else 0
        
        print(f"\n三、结论")
        print(f"  • 策划投入 {limited_welfare_invested} 抽福利：")
        print(f"    - 限时福利可为用户节省 {limited_saved:.1f} 抽 (效率: {limited_saved/limited_welfare_invested:.2f}倍)")
        print(f"    - 不限时福利可为用户节省 {permanent_saved:.1f} 抽 (效率: {permanent_saved/permanent_welfare_invested:.2f}倍)")
        print(f"  • 限时方案效率损失: {efficiency_drop:.1f}%")
        print(f"  • 换算: 1抽限时福利 ≈ {limited_saved/permanent_saved:.2f}抽不限时福利" if permanent_saved > 0 else "")
        print()
    
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
    
    # 打印策略1的福利对比统计
    strategy_sim.print_welfare_comparison("策略1：每期都抽", baseline_1, limited_1, permanent_1, num_pools)
    
    # 策略2的福利方案对比
    print("\n" + "▶" * 30)
    print("策略2：抽1跳1循环")
    print("▶" * 30)
    
    baseline_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode=None)
    limited_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode='limited')
    permanent_2 = strategy_sim.simulate_strategy_2_skip_one(num_pools, welfare_mode='permanent')
    
    # 打印策略2的福利对比统计
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
