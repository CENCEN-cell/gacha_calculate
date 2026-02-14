"""
蒙特卡洛分析器
"""
from typing import List, Dict
from config import GachaConfig
from simulator_core import GachaSimulator


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
