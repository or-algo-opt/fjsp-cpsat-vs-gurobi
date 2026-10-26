# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

def plot_gantt(data, schedule, title, filename):
    num_machines = data["machine_count"]
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.tab20.colors
    
    for (j, o), info in schedule.items():
        start = info["start"]
        end = info["end"]
        mach = info["machine"]
        dur = end - start
        
        ax.barh(y=mach, width=dur, left=start, height=0.5, 
                color=colors[j % len(colors)], edgecolor='black', alpha=0.9)
        ax.text(start + dur / 2, mach, f"J{j}O{o}", ha='center', va='center', fontweight='bold', fontsize=8)

    maintenance = data.get("maintenance", {})
    for mach, maint_list in maintenance.items():
        for (m_start, m_dur) in maint_list:
            ax.barh(y=mach, width=m_dur, left=m_start, height=0.5, 
                    color='gray', hatch='//', edgecolor='black')
            ax.text(m_start + m_dur / 2, mach, "Maint", ha='center', va='center', color='white', fontsize=8)

    ax.set_yticks(range(num_machines))
    ax.set_yticklabels([f"Machine {m}" for m in range(num_machines)])
    ax.set_xlabel("Time")
    ax.set_title(title)
    ax.invert_yaxis()
    
    # 生成图例标签
    legend_patches = [mpatches.Patch(color=colors[j % len(colors)], label=f'Job {j}') for j in range(data["job_count"])]
    legend_patches.append(mpatches.Patch(facecolor='gray', edgecolor='black', hatch='//', label='Maintenance'))

    # 分多列，并放到图表右侧外部
    ax.legend(
        handles=legend_patches, 
        loc='center left',           # 定位点选在左侧居中
        bbox_to_anchor=(1.02, 0.5),  # 把图例挪到画布右侧边缘（1.02表示外侧一点点）
        ncol=2,                      # 分 2 列显示（如果工件特别多，可以改成 ncol=3）
        fontsize=9,                  # 稍微调小字体
        title="Legend"
    )

    plt.tight_layout() 
    
    os.makedirs("output", exist_ok=True)
    filepath = os.path.join("output", filename)
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight') 
    
    print(f"甘特图已保存: {filepath}")
    plt.close()