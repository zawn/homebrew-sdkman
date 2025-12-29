import os
import subprocess
import hashlib
import re

# --- 基础路径配置 ---
# GitHub Actions 会将仓库克隆到当前工作目录下的指定 path
BASE_DIR = os.getcwd()
CORE_DIR = os.path.join(BASE_DIR, "homebrew-core")
SDK_DIR = os.path.join(BASE_DIR, "homebrew-nojdk")

# 匹配目标：查找 openjdk 依赖行
TARGET_DEP = 'depends_on "openjdk"'
COMMENTED_DEP = '# depends_on "openjdk"'

def get_logic_hash(content):
    """
    计算内容的逻辑哈希值。
    在对比前，将已注释的行还原，确保对比的是代码逻辑而非由于注释产生的差异。
    """
    normalized = content.replace(COMMENTED_DEP, TARGET_DEP)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def run_command(command, cwd):
    """
    封装子进程调用，捕获输出并处理错误。
    """
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            # 记录错误信息但不中断脚本
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"      [运行报错]: {e}")
        return None

def sync_formulae():
    # 兼容处理：支持旧版扁平结构和新版分字母目录结构
    search_base = os.path.join(CORE_DIR, "Formula")
    if not os.path.exists(search_base):
        search_base = CORE_DIR

    print(f"🔍 正在递归扫描官方 Core 仓库: {search_base}")
    sync_count = 0

    # 深度遍历所有子目录
    for root, dirs, files in os.walk(search_base):
        for file_name in files:
            if not file_name.endswith(".rb"):
                continue

            src_file_path = os.path.join(root, file_name)
            # 计算相对于 core 根目录的路径 (例如: Formula/m/maven.rb)
            rel_path = os.path.relpath(src_file_path, CORE_DIR)
            dst_file_path = os.path.join(SDK_DIR, rel_path)

            try:
                with open(src_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                continue

            # 仅处理包含 openjdk 的 Formula
            if TARGET_DEP in content:
                # 哈希对比：如果目标已存在且逻辑一致，则跳过
                if os.path.exists(dst_file_path):
                    with open(dst_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        dst_content = f.read()
                    src_h = get_logic_hash(content)
                    dst_h = get_logic_hash(dst_content)
                    # 针对 maven.rb 开启超级追踪
                    is_maven = "maven.rb" in file_name
                    if is_maven :
                        print(f"   对比哈希: SRC({src_h}) vs DST({dst_h})")

                    if src_h == dst_h:
                        if is_maven: print(f"   ⏭️ 内容逻辑一致，跳过")
                        continue

                # 确保 SDK 仓库中的子目录结构与 Core 一致
                os.makedirs(os.path.dirname(dst_file_path), exist_ok=True)

                # 核心逻辑：注释掉依赖行
                new_content = content.replace(TARGET_DEP, COMMENTED_DEP)
                with open(dst_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                # 从 Core 仓库获取元数据（SHA, 提交信息, 日期）
                commit_sha = run_command(['git', 'log', '-1', '--format=%h', '--', rel_path], CORE_DIR)
                commit_msg = run_command(['git', 'log', '-1', '--format=%s', '--', rel_path], CORE_DIR)
                commit_date = run_command(['git', 'log', '-1', '--format=%ai', '--', rel_path], CORE_DIR)

                # 将修改添加到暂存区
                run_command(['git', 'add', rel_path], SDK_DIR)
                
                # 检查暂存区是否确实有变化（排除换行符等产生的虚假变化）
                diff_check = run_command(['git', 'status', '--porcelain', rel_path], SDK_DIR)
                
                if diff_check:
                    # 提交更改
                    log_entry = f"Sync {file_name} from core@{commit_sha or 'unknown'}"
                    commit_result = run_command(['git', 'commit', '-m', log_entry], SDK_DIR)
                    
                    if commit_result is not None:
                        print("-" * 60)
                        print(f"✅ 已同步并提交: {rel_path}")
                        print(f"   官方 SHA: {commit_sha}")
                        print(f"   官方日志: {commit_msg}")
                        print(f"   官方日期: {commit_date}")
                        sync_count += 1
                    else:
                        print(f"❌ 提交失败 (可能由于身份配置问题): {rel_path}")

    print("-" * 60)
    if sync_count == 0:
        print("✨ 所有组件已是最新，无需同步。")
    else:
        print(f"🚀 同步任务圆满结束，本次共更新 {sync_count} 个组件。")

if __name__ == "__main__":
    # 1. 环境预检
    if not os.path.exists(SDK_DIR) or not os.path.exists(CORE_DIR):
        print("❌ 错误: 未找到预期的目录结构，请检查 checkout 路径。")
    else:
        # 2. 关键修复：在 Python 内部配置 Git 身份，确保 commit 命令可用
        print("🔧 正在初始化 Git 机器人身份...")
        run_command(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], SDK_DIR)
        run_command(['git', 'config', 'user.name', 'github-actions[bot]'], SDK_DIR)
        
        # 3. 执行同步
        sync_formulae()