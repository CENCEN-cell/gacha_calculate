"""
数据可视化模块
用于生成抽卡模拟结果的图表

独立运行: python visualizer.py
需要先运行 gacha_simulator.py 生成 simulation_results.pkl
"""

import pickle
import os
import sys
import warnings

import matplotlib
from matplotlib import font_manager
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import List, Dict

sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.2)

# Configure Chinese fonts so labels do not render as boxes
CHINESE_FONTS = [
    'PingFang SC', 'Hiragino Sans GB', 'Songti SC', 'STHeiti', 'SimHei',
    'Microsoft YaHei', 'Noto Sans CJK SC', 'Source Han Sans SC', 'Arial Unicode MS',
    'DejaVu Sans'
]


def configure_chinese_font():
    for font_name in CHINESE_FONTS:
        try:
            # findfont raises if the font does not exist when fallback_to_default is False
            font_manager.findfont(font_name, fallback_to_default=False)
            matplotlib.rcParams['font.sans-serif'] = [font_name]
            matplotlib.rcParams['axes.unicode_minus'] = False
            return
        except ValueError:
            continue
    warnings.warn("未找到可用的中文字体，图表文字可能显示为方框")


configure_chinese_font()

MATPLOTLIB_AVAILABLE = True

# NeurIPS风格配色方案
NEURIPS_COLORS = {
    'baseline': '#7F7F7F',    # 灰色
    'limited': '#D62728',     # 红色
    'permanent': '#2CA02C',   # 绿色
    'palette': ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B']
}

# Global visual tweaks
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['axes.facecolor'] = '#f9fafb'
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.edgecolor'] = '#e5e7eb'
plt.rcParams['grid.color'] = '#e5e7eb'
plt.rcParams['grid.alpha'] = 0.8
sns.set_palette(NEURIPS_COLORS['palette'])


def style_axes(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='both', labelsize=10)
    ax.grid(True, linestyle='--', linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


class GachaVisualizer:
    """抽卡结果可视化器"""
    
    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            print("可视化功能需要安装 matplotlib")
            return
        
        self.colors = NEURIPS_COLORS
    
    def plot_welfare_efficiency_comparison(self, all_strategies_data: Dict, num_pools: int, save_path: str = None):
        """
        绘制所有策略的福利效率对比图（只显示效率）
        
        all_strategies_data: {
            'strategy_name': {
                'baseline': List[Dict],
                'limited': List[Dict],
                'permanent': List[Dict]
            }
        }
        """
        if not MATPLOTLIB_AVAILABLE:
            return
            
        fig, ax = plt.subplots(figsize=(12, 6))
        style_axes(ax)
        
        strategies = list(all_strategies_data.keys())
        x = np.arange(len(strategies))
        width = 0.35
        
        # 数据准备
        limited_efficiency_list = []
        permanent_efficiency_list = []
        
        for strategy_name in strategies:
            data = all_strategies_data[strategy_name]
            
            baseline_spent = [r['user_spent'] for r in data['baseline']]
            limited_spent = [r['user_spent'] for r in data['limited']]
            permanent_spent = [r['user_spent'] for r in data['permanent']]
            
            avg_baseline = np.mean(baseline_spent)
            avg_limited = np.mean(limited_spent)
            avg_permanent = np.mean(permanent_spent)
            
            limited_saved = avg_baseline - avg_limited
            permanent_saved = avg_baseline - avg_permanent
            
            welfare_invested = data['limited'][0]['welfare_invested']
            
            limited_efficiency_list.append(limited_saved / welfare_invested if welfare_invested > 0 else 0)
            permanent_efficiency_list.append(permanent_saved / welfare_invested if welfare_invested > 0 else 0)
        
        # 绘制效率条形图
        bars1 = ax.bar(x - width/2, limited_efficiency_list, width, label='限时福利', 
                       color=self.colors['limited'], alpha=0.85, edgecolor='white', linewidth=1.5)
        bars2 = ax.bar(x + width/2, permanent_efficiency_list, width, label='永久福利', 
                       color=self.colors['permanent'], alpha=0.85, edgecolor='white', linewidth=1.5)
        
        # 在条上标注具体数字
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}x',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}x',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_xlabel('策略', fontsize=13, fontweight='bold')
        ax.set_ylabel('效率（倍）', fontsize=13, fontweight='bold')
        ax.set_title(f'福利效率对比 - 平均效果 ({num_pools}个卡池)', fontsize=15, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=30, ha='right', fontsize=11)
        ax.legend(fontsize=11, frameon=True, shadow=True)
        ax.axhline(y=1, color='gray', linestyle='--', linewidth=1.5, alpha=0.6, label='基准线(1x)')
        ax.set_ylim(0, max(max(limited_efficiency_list), max(permanent_efficiency_list)) * 1.15)
        
        sns.despine()
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
        else:
            plt.savefig('welfare_efficiency_comparison.png', dpi=300, bbox_inches='tight')
            print("图表已保存至: welfare_efficiency_comparison.png")
        
        plt.close()
    
    def plot_user_spending_comparison(self, all_strategies_data: Dict, num_pools: int, save_path: str = None):
        """
        绘制各策略用户每UP实际投入对比（箱线图）
        """
        if not MATPLOTLIB_AVAILABLE:
            return
            
        fig, ax = plt.subplots(figsize=(16, 7))
        style_axes(ax)
        
        strategies = list(all_strategies_data.keys())
        all_data = []
        labels = []
        positions = []
        pos = 1
        
        for strategy_name in strategies:
            data = all_strategies_data[strategy_name]
            
            # 计算每UP实际投入（总花费/获得的UP数）
            baseline_per_up = [r['user_spent'] / r['num_targets'] for r in data['baseline']]
            limited_per_up = [r['user_spent'] / r['num_targets'] for r in data['limited']]
            permanent_per_up = [r['user_spent'] / r['num_targets'] for r in data['permanent']]
            
            all_data.extend([baseline_per_up, limited_per_up, permanent_per_up])
            labels.extend([f'{strategy_name}\n(无福利)', f'{strategy_name}\n(限时)', f'{strategy_name}\n(永久)'])
            positions.extend([pos, pos+1, pos+2])
            pos += 4
        
        # 使用seaborn绘制箱线图
        bp = ax.boxplot(all_data, positions=positions, widths=0.6, patch_artist=True,
                        showmeans=True, meanline=True,
                        boxprops=dict(linewidth=1.5, edgecolor='white'),
                        whiskerprops=dict(linewidth=1.5),
                        capprops=dict(linewidth=1.5),
                        medianprops=dict(linewidth=2, color='darkred'))
        
        # 设置颜色
        for i, box in enumerate(bp['boxes']):
            if i % 3 == 0:  # baseline
                box.set_facecolor(self.colors['baseline'])
            elif i % 3 == 1:  # limited
                box.set_facecolor(self.colors['limited'])
            else:  # permanent
                box.set_facecolor(self.colors['permanent'])
            box.set_alpha(0.75)
        
        ax.set_xlabel('策略', fontsize=13, fontweight='bold')
        ax.set_ylabel('每UP实际投入（抽）', fontsize=13, fontweight='bold')
        ax.set_title(f'各策略每UP实际投入分布对比({num_pools}个卡池)', fontsize=15, fontweight='bold', pad=20)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=9, rotation=30, ha='right')  # 倾斜x轴文字
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=self.colors['baseline'], alpha=0.75, label='无福利', edgecolor='white', linewidth=1.5),
            Patch(facecolor=self.colors['limited'], alpha=0.75, label='限时福利', edgecolor='white', linewidth=1.5),
            Patch(facecolor=self.colors['permanent'], alpha=0.75, label='永久福利', edgecolor='white', linewidth=1.5)
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=11, frameon=True, shadow=True)
        
        sns.despine()
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
        else:
            plt.savefig('user_spending_comparison.png', dpi=300, bbox_inches='tight')
            print("图表已保存至: user_spending_comparison.png")
        
        plt.close()
    
    def plot_pity_history(self, all_strategies_data: Dict, num_pools: int, save_path: str = None):
        """
        绘制小保底水位变化图（取平均）
        """
        if not MATPLOTLIB_AVAILABLE:
            return
            
        strategies = list(all_strategies_data.keys())
        n_strategies = len(strategies)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        axes = axes.flatten()
        
        for idx, strategy_name in enumerate(strategies):
            ax = axes[idx]
            style_axes(ax)
            data = all_strategies_data[strategy_name]
            
            # 计算平均小保底水位
            for mode, mode_name, color in [('baseline', '无福利', self.colors['baseline']),
                                           ('limited', '限时福利', self.colors['limited']),
                                           ('permanent', '永久福利', self.colors['permanent'])]:
                if mode in data and len(data[mode]) > 0 and 'pity_history' in data[mode][0]:
                    # 获取所有模拟的小保底历史
                    all_pity_histories = [r['pity_history'] for r in data[mode]]
                    # 计算平均值
                    avg_pity = np.mean(all_pity_histories, axis=0)
                    # 计算标准差
                    std_pity = np.std(all_pity_histories, axis=0)
                    
                    x = range(1, len(avg_pity) + 1)
                    ax.plot(x, avg_pity, label=mode_name, color=color, linewidth=2.5, alpha=0.9, marker='o', markersize=3, markevery=3)
                    ax.fill_between(x, np.maximum(0, avg_pity - std_pity), 
                                   np.minimum(80, avg_pity + std_pity), 
                                   color=color, alpha=0.15)
            
            ax.set_xlabel('卡池编号', fontsize=11, fontweight='bold')
            ax.set_ylabel('小保底水位', fontsize=11, fontweight='bold')
            ax.set_title(f'{strategy_name}', fontsize=12, fontweight='bold', pad=10)
            ax.legend(fontsize=9, frameon=True, shadow=True)
            ax.set_ylim(0, 80)
            ax.axhline(y=65, color='orange', linestyle='--', linewidth=1.5, alpha=0.6, label='递增阈值')
            sns.despine(ax=ax)
        
        # 隐藏多余的子图
        for idx in range(n_strategies, len(axes)):
            axes[idx].set_visible(False)
        
        plt.suptitle(f'各策略小保底水位变化({num_pools}个卡池)', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
        else:
            plt.savefig('pity_history.png', dpi=300, bbox_inches='tight')
            print("图表已保存至: pity_history.png")
        
        plt.close()
    
    def plot_pity_distribution(self, all_strategies_data: Dict, num_pools: int, save_path: str = None):
        """
        绘制小保底水位分布直方图
        显示所有卡池结束时小保底水位的分布情况，标注范围和概率
        """
        if not MATPLOTLIB_AVAILABLE:
            return
            
        strategies = list(all_strategies_data.keys())
        n_strategies = len(strategies)
        
        # 创建图表：2行3列
        fig, axes = plt.subplots(2, 3, figsize=(18, 11))
        axes = axes.flatten()
        
        # 定义水位区间（每10个为一组）
        bins = np.arange(0, 90, 10)
        bin_labels = [f'{int(bins[i])}-{int(bins[i+1])}' for i in range(len(bins)-1)]
        
        for idx, strategy_name in enumerate(strategies):
            ax = axes[idx]
            style_axes(ax)
            data = all_strategies_data[strategy_name]
            
            x_pos = np.arange(len(bin_labels))
            width = 0.25
            
            # 为每种福利方案绘制直方图
            for i, (mode, mode_name, color) in enumerate([('baseline', '无福利', self.colors['baseline']),
                                                           ('limited', '限时福利', self.colors['limited']),
                                                           ('permanent', '永久福利', self.colors['permanent'])]):
                if mode in data and len(data[mode]) > 0 and 'pity_history' in data[mode][0]:
                    # 收集所有小保底水位数据（所有模拟×所有卡池）
                    all_pity_values = []
                    for r in data[mode]:
                        all_pity_values.extend(r['pity_history'])
                    
                    # 计算每个区间的概率
                    hist, _ = np.histogram(all_pity_values, bins=bins)
                    hist_percent = (hist / len(all_pity_values)) * 100  # 转换为百分比
                    
                    # 绘制直方图
                    bars = ax.bar(x_pos + (i - 1) * width, hist_percent, width, 
                                  label=mode_name, color=color, alpha=0.85, 
                                  edgecolor='white', linewidth=1.5)
                    
                    # 标注概率（只标注大于1%的）
                    for j, (bar, prob) in enumerate(zip(bars, hist_percent)):
                        if prob > 1.0:  # 只标注概率大于1%的
                            height = bar.get_height()
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                   f'{prob:.1f}%',
                                   ha='center', va='bottom', fontsize=7, rotation=0)
            
            ax.set_xlabel('小保底水位区间', fontsize=11, fontweight='bold')
            ax.set_ylabel('出现概率 (%)', fontsize=11, fontweight='bold')
            ax.set_title(f'{strategy_name}', fontsize=12, fontweight='bold', pad=10)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(bin_labels, fontsize=8, rotation=45, ha='right')  # 倾斜x轴标签
            ax.legend(fontsize=9, loc='best', frameon=True, shadow=True)
            ax.set_ylim(0, None)
            
            # 标记关键水位区间
            # 65抽递增阈值在第7个区间（60-70）
            ax.axvspan(6 - 0.5, 8, alpha=0.1, color='orange', label='递增区域(60-80)')
            
            sns.despine(ax=ax)
        
        # 隐藏多余的子图
        for idx in range(n_strategies, len(axes)):
            axes[idx].set_visible(False)
        
        plt.suptitle(f'各策略小保底水位分布概率（以10为间隔）({num_pools}个卡池)', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存至: {save_path}")
        else:
            plt.savefig('pity_distribution.png', dpi=300, bbox_inches='tight')
            print("图表已保存至: pity_distribution.png")
        
        plt.close()
    
    def generate_all_plots(self, all_strategies_data: Dict, num_pools: int):
        """生成所有可视化图表"""
        print("\n" + "=" * 60)
        print("正在生成可视化图表...")
        print("=" * 60)
        
        # 1. 福利效率对比
        print("\n[1/4] 生成福利效率对比图...")
        self.plot_welfare_efficiency_comparison(all_strategies_data, num_pools)
        
        # 2. 用户花费对比
        print("\n[2/4] 生成用户花费分布图...")
        self.plot_user_spending_comparison(all_strategies_data, num_pools)
        
        # 3. 小保底水位变化
        print("\n[3/4] 生成小保底水位变化图...")
        self.plot_pity_history(all_strategies_data, num_pools)
        
        # 4. 小保底水位分布概率
        print("\n[4/4] 生成小保底水位分布概率图...")
        self.plot_pity_distribution(all_strategies_data, num_pools)
        
        print("\n所有图表生成完成！")


def load_simulation_results(file_path: str = 'simulation_results.pkl') -> dict:
    """
    加载模拟结果
    
    返回: {
        'all_strategies_data': Dict,
        'num_pools': int,
        'config': Dict
    }
    """
    if not os.path.exists(file_path):
        print(f"错误: 找不到模拟结果文件 '{file_path}'")
        print("请先运行 'python gacha_simulator.py' 生成模拟数据")
        sys.exit(1)
    
    print(f"正在加载模拟结果: {file_path}")
    
    with open(file_path, 'rb') as f:
        results = pickle.load(f)
    
    print(f"✓ 成功加载数据")
    print(f"  策略数量: {len(results['all_strategies_data'])}")
    print(f"  模拟池数: {results['num_pools']}")
    
    return results


def main():
    """主函数：独立运行可视化模块"""
    print("=" * 60)
    print("明日方舟终末地 - 数据可视化工具")
    print("=" * 60)
    
    # 加载模拟结果
    results = load_simulation_results()
    
    all_strategies_data = results['all_strategies_data']
    num_pools = results['num_pools']
    config = results['config']
    
    # 显示配置信息
    print("\n模拟配置:")
    print(f"  • 6星基础概率: {config['base_ssr_rate'] * 100}%")
    print(f"  • 小保底: {config['small_pity']}抽")
    print(f"  • 大保底: {config['large_pity']}抽")
    print(f"  • UP概率: {config['up_rate'] * 100}%")
    print(f"  • 递增阈值: {config['increase_threshold']}抽")
    
    # 生成可视化图表
    visualizer = GachaVisualizer()
    visualizer.generate_all_plots(all_strategies_data, num_pools)
    
    print("\n" + "=" * 60)
    print("可视化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()


def load_simulation_results(file_path: str = 'simulation_results.pkl') -> dict:
    """
    加载模拟结果
    
    返回: {
        'all_strategies_data': Dict,
        'num_pools': int,
        'config': Dict
    }
    """
    if not os.path.exists(file_path):
        print(f"错误: 找不到模拟结果文件 '{file_path}'")
        print("请先运行 'python gacha_simulator.py' 生成模拟数据")
        sys.exit(1)
    
    print(f"正在加载模拟结果: {file_path}")
    
    with open(file_path, 'rb') as f:
        results = pickle.load(f)
    
    print(f"✓ 成功加载数据")
    print(f"  策略数量: {len(results['all_strategies_data'])}")
    print(f"  模拟池数: {results['num_pools']}")
    
    return results


def main():
    """主函数：独立运行可视化模块"""
    print("=" * 60)
    print("明日方舟终末地 - 数据可视化工具")
    print("=" * 60)
    
    # 加载模拟结果
    results = load_simulation_results()
    
    all_strategies_data = results['all_strategies_data']
    num_pools = results['num_pools']
    config = results['config']
    
    # 显示配置信息
    print("\n模拟配置:")
    print(f"  • 6星基础概率: {config['base_ssr_rate'] * 100}%")
    print(f"  • 小保底: {config['small_pity']}抽")
    print(f"  • 大保底: {config['large_pity']}抽")
    print(f"  • UP概率: {config['up_rate'] * 100}%")
    print(f"  • 递增阈值: {config['increase_threshold']}抽")
    
    # 生成可视化图表
    visualizer = GachaVisualizer()
    visualizer.generate_all_plots(all_strategies_data, num_pools)
    
    print("\n" + "=" * 60)
    print("可视化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

