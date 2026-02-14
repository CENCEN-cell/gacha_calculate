"""
核心抽卡模拟器
"""
import random
from typing import Dict, Tuple
from config import GachaConfig
from pool_state import PoolState


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
    
    def determine_ssr_type(self) -> Tuple[bool, bool]:
        """
        判断六星的类型
        返回: (是否是当期UP, 是否是往期UP)
        
        概率分布：
        - 50%: 当期UP
        - 14.2857% (50% * 2/7): 往期UP
        - 35.7143% (50% * 5/7): 常驻六星
        """
        rand = random.random()
        
        if rand < 0.5:
            # 50%概率：当期UP
            return True, False
        elif rand < 0.5 + 0.5 * 2 / 7:  # 50% + 14.2857% ≈ 64.2857%
            # 14.2857%概率：往期UP
            return False, True
        else:
            # 35.7143%概率：常驻六星
            return False, False
    
    def single_pull_normal(self) -> Tuple[bool, bool, bool]:
        """
        正常单次抽卡（计入保底）
        返回: (是否出6星, 是否是当期UP, 是否是往期UP)
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
            return True, True, False  # 必定是当期UP
        
        
        # 小保底：80抽必出6星
        if self.state.small_pity_counter >= self.config.small_pity:
            is_ssr = True
        else:
            # 正常概率判定
            ssr_rate = self.calculate_current_ssr_rate()
            is_ssr = random.random() < ssr_rate
        
        if not is_ssr:
            return False, False, False
        
        # 出了6星，重置小保底
        self.state.small_pity_counter = 0
        
        # 判断六星类型
        is_current_up, is_old_up = self.determine_ssr_type()
        
        if is_current_up:
            # 出了当期UP，重置大保底
            self.state.large_pity_counter = 0
        
        return True, is_current_up, is_old_up
    
    def single_pull_special(self) -> Tuple[bool, bool, bool]:
        """
        特殊10抽（不计入保底，出货不重置保底）
        返回: (是否出6星, 是否是当期UP, 是否是往期UP)
        """
        # 特殊抽不增加任何保底计数器
        # 只使用基础概率判定，不受保底影响
        ssr_rate = self.config.base_ssr_rate
        is_ssr = random.random() < ssr_rate
        
        if not is_ssr:
            return False, False, False
        
        # 出了6星，判断类型（不重置任何保底）
        is_current_up, is_old_up = self.determine_ssr_type()
        
        return True, is_current_up, is_old_up
    
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
            'welfare_permanent_used': 永久福利使用数,
            'old_up_count': 往期UP数量
        }
        """
        actual_pulls = 0  # 实际消耗的抽数
        bonus_used = 0  # 使用的赠送抽数
        bonus_normal_used = 0  # 60送的正常10抽使用数
        bonus_special_used = 0  # 30送的特殊10抽使用数
        welfare_limited_used = 0  # 限时福利使用数
        welfare_permanent_used = 0  # 永久福利使用数
        current_up_count = 0  # 当期UP数量
        old_up_count = 0  # 往期UP数量
        
        while True:
            # 优先级1：60送正常10抽 + 限时福利10抽（同一优先级，一起抽完）
            if self.state.bonus_10_normal > 0 or self.state.welfare_limited > 0:
                # 记录要抽的数量（抽之前先记录，因为后面会清零）
                bonus_10_count = self.state.bonus_10_normal
                welfare_limited_count = self.state.welfare_limited
                combined_pulls = bonus_10_count + welfare_limited_count
                
                # 清零状态
                self.state.bonus_10_normal = 0
                self.state.welfare_limited = 0
                
                # 一次性抽完所有60送和限时福利
                for i in range(combined_pulls):
                    if i < bonus_10_count:
                        bonus_used += 1
                        bonus_normal_used += 1
                    else:
                        welfare_limited_used += 1
                    
                    is_ssr, is_current_up, is_old_up = self.single_pull_normal()
                    if is_old_up:
                        old_up_count += 1
                    if is_ssr and is_current_up:
                        current_up_count += 1
                
                if current_up_count > 0:
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls,
                        'old_up_count': old_up_count
                    }
                continue
            
            # 优先级2：30送的特殊10抽（强制一次性抽完，不计入保底）
            if self.state.bonus_10_special > 0:
                pulls_to_do = self.state.bonus_10_special
                self.state.bonus_10_special = 0
                for _ in range(pulls_to_do):
                    bonus_used += 1
                    bonus_special_used += 1
                    is_ssr, is_current_up, is_old_up = self.single_pull_special()
                    if is_old_up:
                        old_up_count += 1
                    if is_ssr and is_current_up:
                        current_up_count += 1
                
                if current_up_count > 0:
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls,
                        'old_up_count': old_up_count
                    }
                continue
            
            # 优先级3：永久福利抽（逐个使用，可随时停止）
            if use_welfare and self.state.welfare_permanent > 0:
                self.state.welfare_permanent -= 1
                welfare_permanent_used += 1
                is_ssr, is_current_up, is_old_up = self.single_pull_normal()
                if is_old_up:
                    old_up_count += 1
                if is_ssr and is_current_up:
                    current_up_count += 1
                    return {
                        'pulls': actual_pulls,
                        'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                        'bonus_used': bonus_used,
                        'bonus_normal_used': bonus_normal_used,
                        'bonus_special_used': bonus_special_used,
                        'welfare_used': welfare_limited_used + welfare_permanent_used,
                        'welfare_limited_used': welfare_limited_used,
                        'welfare_permanent_used': welfare_permanent_used,
                        'pool_pulls': self.state.total_pulls,
                        'old_up_count': old_up_count
                    }
                continue
            
            # 优先级4：使用实际抽数（逐个使用）
            actual_pulls += 1
            is_ssr, is_current_up, is_old_up = self.single_pull_normal()
            if is_old_up:
                old_up_count += 1
            if is_ssr and is_current_up:
                current_up_count += 1
                return {
                    'pulls': actual_pulls,
                    'total_pulls': actual_pulls + bonus_used + welfare_limited_used + welfare_permanent_used,
                    'bonus_used': bonus_used,
                    'bonus_normal_used': bonus_normal_used,
                    'bonus_special_used': bonus_special_used,
                    'welfare_used': welfare_limited_used + welfare_permanent_used,
                    'welfare_limited_used': welfare_limited_used,
                    'welfare_permanent_used': welfare_permanent_used,
                    'pool_pulls': self.state.total_pulls,
                    'old_up_count': old_up_count
                }
    
    def pull_bonus_and_free_limited_welfare(self, use_limited_welfare: bool = False) -> Dict:
        """
        只抽赠送的抽数和限时福利，不投入额外资源（用于跳过的池子）
        use_limited_welfare: 是否使用限时福利（方案1）
        
        抽卡优先级规则：
        1. 60送正常10抽 + 限时福利10抽（同一优先级，一起抽完，计入保底）
        2. 30送特殊10抽（一次性抽完，不计入保底）
        
        注意：永久福利不在此使用（留给想抽的池子）
        
        返回: {
            'pulls': 实际消耗的抽数（跳过池子为0）,
            'total_pulls': 总抽数（包括赠送和福利）,
            'bonus_used': 使用的赠送抽数,
            'bonus_normal_used': 60送的正常10抽使用数,
            'bonus_special_used': 30送的特殊10抽使用数,
            'welfare_used': 使用的策划福利抽数,
            'welfare_limited_used': 限时福利使用数,
            'welfare_permanent_used': 永久福利使用数（始终为0）,
            'got_target': 是否意外获得了UP（True/False）,
            'pool_pulls': 本期卡池总抽数,
            'old_up_count': 往期UP数量
        }
        """
        actual_pulls = 0  # 跳过池子不投入实际抽数
        bonus_used = 0
        bonus_normal_used = 0
        bonus_special_used = 0
        welfare_limited_used = 0
        welfare_permanent_used = 0  # 永久福利不在跳过池子中使用
        current_up_count = 0  # 意外获得的当期UP数量
        old_up_count = 0  # 往期UP数量
        
        # 优先级1：60送正常10抽 + 限时福利10抽（同一优先级，一起抽完）
        if self.state.bonus_10_normal > 0 or (use_limited_welfare and self.state.welfare_limited > 0):
            bonus_10_count = self.state.bonus_10_normal
            welfare_limited_count = self.state.welfare_limited if use_limited_welfare else 0
            combined_pulls = bonus_10_count + welfare_limited_count
            
            # 清零状态
            self.state.bonus_10_normal = 0
            if use_limited_welfare:
                self.state.welfare_limited = 0
            
            # 一次性抽完
            for i in range(combined_pulls):
                if i < bonus_10_count:
                    bonus_used += 1
                    bonus_normal_used += 1
                else:
                    welfare_limited_used += 1
                
                is_ssr, is_current_up, is_old_up = self.single_pull_normal()
                if is_old_up:
                    old_up_count += 1
                if is_ssr and is_current_up:
                    current_up_count += 1
        
        # 检查项
        if self.state.bonus_10_special > 0:
            assert False, "跳过的池子不应该够到30抽赠送10抽"
        
        return {
            'pulls': actual_pulls,
            'total_pulls': bonus_used + welfare_limited_used,
            'bonus_used': bonus_used,
            'bonus_normal_used': bonus_normal_used,
            'bonus_special_used': bonus_special_used,
            'welfare_used': welfare_limited_used,
            'welfare_limited_used': welfare_limited_used,
            'welfare_permanent_used': welfare_permanent_used,
            'got_target': current_up_count > 0,  # 是否意外获得了当期UP
            'current_up_count': current_up_count,  # 当期UP数量
            'pool_pulls': self.state.total_pulls,
            'old_up_count': old_up_count
        }
