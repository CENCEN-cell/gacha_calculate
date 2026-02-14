"""
策略模拟器
包含6种不同的抽卡策略及其两种福利方案对比
"""
import random
from typing import List, Dict, Optional
from config import GachaConfig
from simulator_core import GachaSimulator


class StrategySimulator:
    """多池子策略模拟器"""
    
    def __init__(self, config: GachaConfig, iterations: int = 10000):
        self.config = config
        self.iterations = iterations
    
    def simulate_strategy_1_every_pool(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            pity_history = []  # 记录每个卡池结束抽取时的小保底水位
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
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
                user_spent += result['pulls']  # pulls = actual_pull 就是用户自费的抽数
                welfare_used_total += result.get('welfare_used', 0)
                old_up_count += result.get('old_up_count', 0)  # 统计往期UP
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)  # 记录卡池结束时的小保底
                expected_up_count += 1  # 想抽的池子计入期望
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,  # 用户自费总数
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history  # 小保底历史
            })
        
        return results
    
    def simulate_strategy_2_skip_one(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
            for cycle in range(num_cycles):
                # 第1个池子：跳过（只用赠送和限时福利）
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                
                result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                welfare_used_total += result.get('welfare_used', 0)
                old_up_count += result.get('old_up_count', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
                unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                
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
                old_up_count += result.get('old_up_count', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
                expected_up_count += 1  # 想抽的池子计入期望
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,  # 用户自费总数
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_3_random_two(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
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
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        expected_up_count += 1  # 想抽的池子计入期望
                    else:
                        # 未选中的池子：跳过（只用赠送）
                        result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                        welfare_used_total += result.get('welfare_used', 0)
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                    pity_history.append(simulator.state.small_pity_counter)
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_4_skip_two(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
            for cycle in range(num_cycles):
                # 第1个池子：跳过
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                welfare_used_total += result.get('welfare_used', 0)
                old_up_count += result.get('old_up_count', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
                unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                
                # 第2个池子：跳过
                simulator.reset_for_new_pool(prev_pool_pulls)
                if welfare_mode == 'limited':
                    simulator.state.welfare_limited = 10
                    welfare_invested += 10
                elif welfare_mode == 'permanent':
                    simulator.state.welfare_permanent += 10
                    welfare_invested += 10
                result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                welfare_used_total += result.get('welfare_used', 0)
                old_up_count += result.get('old_up_count', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
                unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                
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
                old_up_count += result.get('old_up_count', 0)
                prev_pool_pulls = result['pool_pulls']
                pity_history.append(simulator.state.small_pity_counter)
                expected_up_count += 1  # 想抽的池子计入期望
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_5_random_three_pick_one(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
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
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        expected_up_count += 1  # 想抽的池子计入期望
                    else:
                        # 未选中的池子：跳过（只用赠送）
                        result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                        welfare_used_total += result.get('welfare_used', 0)
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                    pity_history.append(simulator.state.small_pity_counter)
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results
    
    def simulate_strategy_6_random_three_pick_two(self, num_pools: int, welfare_mode: Optional[str] = None) -> List[Dict]:
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
            expected_up_count = 0  # 期望UP数（按策略规划想抽的池子数）
            unexpected_current_up_count = 0  # 跳过池意外获得的本期UP数
            old_up_count = 0  # 往期UP数
            
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
                        result = simulator.pull_bonus_and_free_limited_welfare(use_limited_welfare=(welfare_mode == 'limited'))
                        welfare_used_total += result.get('welfare_used', 0)
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        unexpected_current_up_count += result.get('current_up_count', 0)  # 跳过池意外当期UP数量
                    else:
                        # 选中的池子：抽
                        result = simulator.pull_until_target(use_welfare=(welfare_mode == 'permanent'))
                        user_spent += result['pulls']
                        welfare_used_total += result.get('welfare_used', 0)
                        old_up_count += result.get('old_up_count', 0)
                        prev_pool_pulls = result['pool_pulls']
                        expected_up_count += 1  # 想抽的池子计入期望
                    pity_history.append(simulator.state.small_pity_counter)
            
            total_current_up_count = expected_up_count + unexpected_current_up_count
            results.append({
                'user_spent': user_spent,
                'expected_up_count': expected_up_count,  # 期望UP数
                'unexpected_current_up_count': unexpected_current_up_count,  # 跳过池意外本期UP数
                'total_current_up_count': total_current_up_count,  # 总和当期UP数
                'old_up_count': old_up_count,  # 往期UP数
                'welfare_invested': welfare_invested,
                'welfare_used': welfare_used_total,
                'pity_history': pity_history
            })
        
        return results

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
        baseline_expected = baseline_results[0]['expected_up_count']
        baseline_unexpected = [r['unexpected_current_up_count'] for r in baseline_results]
        baseline_total_current = [r['total_current_up_count'] for r in baseline_results]
        baseline_old_up = [r.get('old_up_count', 0) for r in baseline_results]
        avg_baseline = sum(baseline_spent) / len(baseline_spent)
        avg_baseline_unexpected = sum(baseline_unexpected) / len(baseline_unexpected)
        avg_baseline_total_current = sum(baseline_total_current) / len(baseline_total_current)
        avg_baseline_old_up = sum(baseline_old_up) / len(baseline_old_up)
        
        # 限时福利统计（方案1）
        limited_spent = [r['user_spent'] for r in limited_results]
        limited_welfare_invested = limited_results[0]['welfare_invested']
        limited_unexpected = [r['unexpected_current_up_count'] for r in limited_results]
        limited_total_current = [r['total_current_up_count'] for r in limited_results]
        limited_old_up = [r.get('old_up_count', 0) for r in limited_results]
        avg_limited = sum(limited_spent) / len(limited_spent)
        avg_limited_unexpected = sum(limited_unexpected) / len(limited_unexpected)
        avg_limited_total_current = sum(limited_total_current) / len(limited_total_current)
        avg_limited_old_up = sum(limited_old_up) / len(limited_old_up)
        limited_saved = avg_baseline - avg_limited
        
        # 不限时福利统计（方案2）
        permanent_spent = [r['user_spent'] for r in permanent_results]
        permanent_welfare_invested = permanent_results[0]['welfare_invested']
        permanent_unexpected = [r['unexpected_current_up_count'] for r in permanent_results]
        permanent_total_current = [r['total_current_up_count'] for r in permanent_results]
        permanent_old_up = [r.get('old_up_count', 0) for r in permanent_results]
        avg_permanent = sum(permanent_spent) / len(permanent_spent)
        avg_permanent_unexpected = sum(permanent_unexpected) / len(permanent_unexpected)
        avg_permanent_total_current = sum(permanent_total_current) / len(permanent_total_current)
        avg_permanent_old_up = sum(permanent_old_up) / len(permanent_old_up)
        permanent_saved = avg_baseline - avg_permanent
        
        # 输出对比
        print(f"\n模拟条件：")
        print(f"  • 卡池总数: {num_pools} 个")
        print(f"  • 期望UP数: {baseline_expected} 个（按策略规划想抽的池子）")
        print(f"  • 跳过池意外获得本期UP数: 基准 {avg_baseline_unexpected:.2f} | 限时抽福利 {avg_limited_unexpected:.2f} | 永久抽福利 {avg_permanent_unexpected:.2f}")
        print(f"  • 所有当期UP数: 基准 {avg_baseline_total_current:.2f} | 限时抽福利 {avg_limited_total_current:.2f} | 永久抽福利 {avg_permanent_total_current:.2f}（期望UP + 跳过池意外UP）")
        print(f"  • 额外意外往期UP数: 基准 {avg_baseline_old_up:.2f} | 限时抽福利 {avg_limited_old_up:.2f} | 永久抽福利 {avg_permanent_old_up:.2f} （14.29%概率，2/7）")
        
        # 计算所有UP数（当期UP + 往期UP）
        avg_baseline_all_up = avg_baseline_total_current + avg_baseline_old_up
        avg_limited_all_up = avg_limited_total_current + avg_limited_old_up
        avg_permanent_all_up = avg_permanent_total_current + avg_permanent_old_up
        
        print(f"  • 所有UP数: 基准 {avg_baseline_all_up:.2f} | 限时抽福利 {avg_limited_all_up:.2f} | 永久抽福利 {avg_permanent_all_up:.2f}（当期UP + 往期UP）")
        print(f"  • 策划投入福利: {limited_welfare_invested} 抽 (每池5+5=10抽)")
        print(f"  • 模拟次数: {len(baseline_results)} 次")
        
        print(f"\n一、用户实际花费对比（不含60送、30送、福利）")
        print(f"  ┌{'─' * 105}┐")
        print(f"  │ {'场景':<12} │ {'总花费':<10} │ {'期望UP每UP花费':<15} │ {'当期UP每UP花费':<15} │ {'所有UP每UP花费':<15} │")
        print(f"  ├{'─' * 105}┤")
        print(f"  │ {'基准(无福利)':<10} │ {avg_baseline:>8.1f}   │ {avg_baseline/baseline_expected:>13.1f}   │ {avg_baseline/avg_baseline_total_current:>13.1f}   │ {avg_baseline/avg_baseline_all_up:>13.1f}   │")
        print(f"  │ {'方案1(限时)':<10} │ {avg_limited:>8.1f}   │ {avg_limited/baseline_expected:>13.1f}   │ {avg_limited/avg_limited_total_current:>13.1f}   │ {avg_limited/avg_limited_all_up:>13.1f}   │")
        print(f"  │ {'方案2(不限时)':<8} │ {avg_permanent:>8.1f}   │ {avg_permanent/baseline_expected:>13.1f}   │ {avg_permanent/avg_permanent_total_current:>13.1f}   │ {avg_permanent/avg_permanent_all_up:>13.1f}   │")
        print(f"  └{'─' * 105}┘")
        
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
    
