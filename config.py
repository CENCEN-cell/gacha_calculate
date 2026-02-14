"""
抽卡配置类
"""
from dataclasses import dataclass


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
